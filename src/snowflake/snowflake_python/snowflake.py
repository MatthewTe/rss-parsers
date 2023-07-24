import ast
import json
import os 
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import fastapi
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading

import pika
from pika.adapters.blocking_connection import BlockingChannel 

# Broker logger import:
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
    return {
        "status": 200,
        "microservice_name": "snowflake",
    }

def consume_messages(): 
    def callback(ch: BlockingChannel, method, properties, body: bytes):
        "Determines if the rss feed article is unique and if it should be passed on to the processing que"

        article = ast.literal_eval(body.decode("utf-8"))

        # Custom test logic:
        if article['rss_feed_id'] == 9999:
            print(f"Test Article Recieved: {article}\n")
            logger.debug("Test article recieved and re-published to exchange with routing key rss.article.new")
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
        
        article_unique_query = sa.text("SELECT id FROM article WHERE url = :url")
        existing_article = session.execute(article_unique_query, {"url": article['url']}).fetchone()
        
        if existing_article is not None:
            logger.info("Article  already exists in the database. Article removed from que", extra={
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

def start_message_consumer():
    consumer_thread = threading.Thread(target=consume_messages)
    consumer_thread.start()

if __name__ == "__main__":
    print("Snowflake started consuming...")
    logger.info("Snowflake started consuming")
    start_message_consumer()

    logger.info("Snowflake database connection I/O Thread started")
    uvicorn.run(app, host='0.0.0.0', port=8000)
