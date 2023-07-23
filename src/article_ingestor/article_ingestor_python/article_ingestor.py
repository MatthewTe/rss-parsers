import ast
import os
import json
import fastapi
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import threading

import pika
from pika.adapters.blocking_connection import BlockingChannel 

# Broker logger import:
from broker_logger import logger

app = fastapi.FastAPI()

DEV_STATUS: str | None = os.environ.get("DEV_STATUS", None)

# Adding Middleware to allow for localhost CORS requests for development connection and debuggin:
origins = [
    "http://localhost:5500"
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
        "microservice_name": "rss_article_database_ingestor"
    }

def consume_messages():
    def ingest_articles(ch: BlockingChannel, method, properties, body: bytes):
        "Extracts all of the data for an article and writes it do the persistence layer"
        article = ast.literal_eval(body.decode("utf-8"))

        # Article de-seralization:
        article['title'] = article["title"].encode()

        # Custom test logic:
        if article['rss_feed_id'] == 9999:
            print(f"Test Article Recieved: {article}\n")

            article['title'] = article['title'].decode("utf-8")
            ch.basic_publish(exchange="rss_feed", routing_key="rss.article.inserted", body=json.dumps(article))
            logger.debug("Test Article recieved")
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
    
        # Writes article data to the database:
        insert_query = sa.text("""
            INSERT INTO article (url, title, rss_feed_id, date_posted, date_extracted)
            VALUES (:url, :title, :rss_feed_id, :date_posted, :date_extracted)
        """)

        inserted_article = session.execute(insert_query, article)
        rows_inserted = inserted_article.rowcount

        if rows_inserted == 1:
            logger.info(f"Successfully inserted article into the database", extra={
                "article": article['title'],
                "rss_feed": article["rss_feed_id"]
            })
            article['title'] = article['title'].decode("utf-8")
            ch.basic_publish(exchange="rss_feed", routing_key="rss.article.inserted", body=json.dumps(article))
        else:
            logger.warning("Article was not inserted into the database", extra={
                "article": article['title'],
                "rss_feed": article['rss_feed_id']
            })

        session.commit()
        session.close()

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))

        channel = connection.channel()

        channel.exchange_declare("rss_feed", exchange_type="topic")

        result = channel.queue_declare("", exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange="rss_feed", queue=queue_name, routing_key="rss.article.new")

        channel.basic_consume(queue=queue_name, on_message_callback=ingest_articles, auto_ack=True)
        channel.start_consuming()

    except Exception as e:
        logger.exception(f"Error in establishing a connection with the RabbitMQ Broker: {str(e)}", extra={
            "exception": str(e)
        })

def start_message_consumer():
    consume_thread = threading.Thread(target=consume_messages)
    consume_thread.start()

if __name__ == "__main__":
    logger.info("Article Ingestor started consuming...")
    print("Article Ingestor started consuming...")
    start_message_consumer()
    logger.info("Article Ingestor database connection I/O Thread started")
    uvicorn.run(app, host="0.0.0.0", port=8000)