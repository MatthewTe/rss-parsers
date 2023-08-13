import ast
import json
import os 
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import fastapi
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn
import threading
import datetime

import pika
from pika.adapters.blocking_connection import BlockingChannel 

from existing_article_caching import rebuild_article_cache, determine_article_in_db
from broker_logger import logger

app = fastapi.FastAPI()

DEV_STATUS: str | None = os.environ.get("DEV_STATUS", None)

# Adding Middleware to allow for localhost CORS requests for development connection and debuggin:
origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/status")
async def get_status():
    "Checking the status of the connection to the broker"
    consumer_thread_status: bool = consumer_thread.is_alive()
    if consumer_thread_status:
        status = 200
    else:
        status = 404
        

    return {
        "status": status,
        "microservice_name": "snowflake",
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "active_threads": [thread.name for thread in threading.enumerate()],
        "amqp_listening_thread_alive": consumer_thread_status
    }

def consume_messages(): 
    def callback(ch: BlockingChannel, method, properties, body: bytes):
        "Determines if the rss feed article is unique and if it should be passed on to the processing que"

        article = ast.literal_eval(body.decode("utf-8"))

        # Custom test logic:
        if article['rss_feed_id'] == 9999:
            print(f"Test Article Recieved: {article}\n")
               
            # Manually testing the article cache check:
            try:
                test_article_in_db: bool = determine_article_in_db(article['url'])
                logger.debug("Test article recieved and re-published to exchange with routing key rss.article.new. Unique check should be False", extra={
                    "test_article_unique_check":test_article_in_db
                })
            except Exception as e: 
                logger.exception("""
                        Test article recieved and re-published to exchange with routing key rss.article.new. 
                        Unique article checking function threw Error
                    """, 
                    exc_info=True,
                    extra={
                        "determine_article_in_db_error": str(e),
                        "test_article_unique_check":test_article_in_db
                    }
                )
            
            ch.basic_publish(exchange="rss_feed", routing_key="rss.article.new", body=json.dumps(article))
            
            
            return

        engine_url = URL.create(
            drivername="mysql+mysqldb",
            username=os.environ.get("USERNAME"),
            password=os.environ.get("PASSWORD"),
            host=os.environ.get("HOST"),
            database=os.environ.get("DATABASE")
        )

        engine = sa.create_engine(engine_url, connect_args={"ssl":{"ca":"/etc/ssl/certs/ca-certificates.crt"}})
    
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            article_is_in_db: bool = determine_article_in_db(article['url'])
        except Exception as e:
            logger.exception("Error in checking the cache or main database for existing articles. Article dropped from", exc_info=True)       
            return 

        if article_is_in_db:
            logger.info("Article already exists in the database. Article removed from que", extra={
                "article": article['title'],
                "rss_feed": article['rss_feed_id']
            })
        else:
            ch.basic_publish(exchange="rss_feed", routing_key="rss.article.new", body=json.dumps(article))
            logger.info("Article is not in the database. Article was re-added to the que w/ routing key new", extra={
                "article": article['title'],
                "rss_feed": article['rss_feed_id']
            })

        session.close()

    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))

        channel = connection.channel()

        channel.exchange_declare("rss_feed", exchange_type="topic")

        result = channel.queue_declare("", exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange="rss_feed", queue=queue_name, routing_key="rss.article.raw")
    
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        channel.start_consuming()

    except Exception as e:
        logger.exception(f"Error in establishing a connection with the RabbitMQ Broker: {str(e)}", extra={
            "exception": str(e)
        })

if __name__ == "__main__":
    print("Snowflake started consuming...")
    logger.info("Snowflake started consuming")

    consumer_thread = threading.Thread(target=consume_messages)
    consumer_thread.start()

    # Background process for keeping the article cache updated:
    scheduler =BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(
        func=rebuild_article_cache,
        kwargs={"path_url":"article_cache.db.sqlite3"},
        trigger="cron",
        hour=6,
        id="article_cache_scheduler"
    )

    logger.info("Snowflake database connection I/O Thread started")
    uvicorn.run(app, host='0.0.0.0', port=8000)
