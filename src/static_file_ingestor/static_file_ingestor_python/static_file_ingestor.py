import ast
import os
from typing import Literal
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import uvicorn
import threading
import fastapi
import datetime
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd 
import uuid
import time
import json

import pika
from pika.adapters.blocking_connection import BlockingChannel

from static_file_ingestor_logger import logger
from process_article_objects import upload_article_html_to_bucket 

MINIO_ENDPOINT: str = os.environ.get("MINIO_ENDPOINT", "localhost")
MINIO_ACCESS_KEY: str = os.environ.get("MINIO_ACCESS_KEY", "admin")
MINIO_PASSWORD: str = os.environ.get("MINIO_PASSWORD", "password")
DEV_STATUS: str | None = os.environ.get("DEV_STATUS", None)

app = fastapi.FastAPI()

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
        "microservice_name": "storage_bucket_article_ingestor",
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "active_threads": [thread.name for thread in threading.enumerate()],
        "amqp_listening_thread_alive": consumer_thread_status
    }

@app.get("/trigger_outstanding_article_bucket_ingestion")
async def perform_database_static_file_ingestion(max_articles: int | None = None):
    """When this request is triggered it pulls down all of the articles from the database that have
    not been ingested into the static storage bucket and inserts these articles into the message broker
    queue so that these articles are ingested into the storage bucket
    """
    engine_url = URL.create(
        drivername="mysql+mysqldb",
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
        host=os.environ.get("HOST"),
        database=os.environ.get("DATABASE"),
        query={"charset": "utf8mb4"}
    )

    engine = sa.create_engine(engine_url, connect_args={"ssl":{"ca":"/etc/ssl/certs/ca-certificates.crt"}})

    if max_articles:
        get_articles_not_in_bucket_query = sa.text(
            """
            SELECT url, title, rss_feed_id, date_posted, date_extracted
            FROM article
            WHERE in_storage_bucket = false
            LIMIT :max_articles; 
            """)
        with engine.connect() as conn, conn.begin():
            articles_not_in_bucket_df = pd.read_sql_query(
                get_articles_not_in_bucket_query, 
                con=conn,
                params={"max_articles":max_articles}
            )

    else:
        get_articles_not_in_bucket_query = sa.text(
            """
            SELECT url, title, rss_feed_id, date_posted, date_extracted
            FROM article
            WHERE in_storage_bucket = false; 
            """)
        with engine.connect() as conn, conn.begin():
            articles_not_in_bucket_df = pd.read_sql_query(get_articles_not_in_bucket_query, con=conn)


    if not articles_not_in_bucket_df.empty:
        logger.info(f"Queried all articles that have not been uploaded to the storage bucket", extra={
            "number_of_articles": len(articles_not_in_bucket_df) 
        })

        #articles_not_in_bucket_df["date_posted"] = articles_not_in_bucket_df['date_posted'].dt.strftime("%Y-%m-%d")
        #articles_not_in_bucket_df["date_extracted"] = articles_not_in_bucket_df['date_extracted'].dt.strftime("%Y-%m-%d")

    else:
        logger.warning("Outstanding article storage bucket update function was triggered but no outstanding articles were found", extra={
        })

        return {"message":"No articles found that we not in the storage bucket"}

    # Converting article df into a list of dictionaries that mirror the schema of a recieved article from the broker:
    articles_to_ingest: list[
        dict[
            "url": str, 
            "title":str, 
            "rss_feed_id":int, 
            "date_posted":str,
            "date_extracted":str
        ]]  = articles_not_in_bucket_df.to_dict(orient="records")
    
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))
    channel = connection.channel()
    channel.exchange_declare("rss_feed", exchange_type="topic")

    articles_ingested: list[
        dict[
            "url": str, 
            "title":str, 
            "rss_feed_id":int, 
            "date_posted":str,
            "date_extracted":str
        ]] = []
    
    articles_not_ingested: list[
        dict[
            "url": str, 
            "title":str, 
            "rss_feed_id":int, 
            "date_posted":str,
            "date_extracted":str
        ]] = []


    for article in articles_to_ingest:

        try:
            channel.basic_publish(
                exchange="rss_feed", 
                routing_key="rss.article.inserted", 
                body=json.dumps(article, default=str)
            )
            
            articles_ingested.append(article)

            logger.info("Added outstanding article to the storage bucket ingestor article que", extra={
                "title":article['title']
            })

        except Exception as e:
            logger.exception("Error in adding outstanding articles to storage bucket ingestor article que", extra={
                "title":article['title'],
                "exception": str(e)
            })

            articles_not_ingested.append(article)

    # Calculating information about the ingestion:
    ingested_info: dict = {
        "limit_on_articles_provided":max_articles,
        "articles_recived_from_db": len(articles_to_ingest),
        "articles_inserted_into_que": len(articles_ingested),
        "articles_not_ingested": articles_not_ingested,
        "articles_ingested": articles_ingested
    }

    return ingested_info 


def consume_message():

    def insert_article_storage_bucket_callback(ch: BlockingChannel, method, properties, body: bytes):
        """Recieves articles that have already been written to the database and requesting the html content, then storing 
        html content in staticfile storage (minio cluster)
        """
        article: dict[
            "url": str, 
            "title":str, 
            "rss_feed_id":int, 
            "date_extracted":str, 
            "date_posted":str
        ] = ast.literal_eval(body.decode("utf-8"))
        
        # Test logic:
        if article['rss_feed_id'] == 9999:
            logger.debug("Test Article Recieved")
            print(f"Test Article Recieved: {article}\n")

            upload_status: Literal[200, 404] = upload_article_html_to_bucket(
                minio_endpoint=MINIO_ENDPOINT,
                minio_access_key=MINIO_ACCESS_KEY,
                minio_secret_key=MINIO_PASSWORD,

                article=article
            )

        # Production logic:    
        else:

            upload_status: Literal[200, 404] = upload_article_html_to_bucket(
                minio_endpoint=MINIO_ENDPOINT,
                minio_access_key=MINIO_ACCESS_KEY,
                minio_secret_key=MINIO_PASSWORD,

                article=article
            )

            if upload_status == 200:
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
            
                # Updates the Articles entry in the database to show that an article object has been written to the storage bucket:
                update_query = sa.text("""
                    UPDATE article
                    SET in_storage_bucket = true
                    WHERE title = :title;
                """)

                updated_article = session.execute(update_query, {"title":article['title']})
                rows_inserted = updated_article.rowcount

                if rows_inserted == 1:
                    logger.info(f"Successfully updated article row in db to set storage bucket status", extra={
                        "article": article['title'],
                        "rss_feed": article["rss_feed_id"],
                    })
                else:
                    logger.warning("Article was not updated in the database to reflect upload to storage bucket", extra={
                        "article": article['title'],
                        "rss_feed": article['rss_feed_id']
                    })

                session.commit()
                session.close()

        if upload_status == 200:
           channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
           channel.basic_ack(delivery_tag=method.delivery_tag)
    
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(os.environ.get("BROKER_URL", 'localhost'))
        )

        channel = connection.channel()
        channel.exchange_declare(exchange="rss_feed", exchange_type="topic")
        result = channel.queue_declare("", exclusive=True)
        queue_name= result.method.queue

        channel.queue_bind(exchange="rss_feed", queue=queue_name, routing_key="rss.article.inserted")
            
        channel.basic_consume(queue=queue_name, on_message_callback=insert_article_storage_bucket_callback, auto_ack=False)

        channel.start_consuming()
    
    except Exception as e:
        logger.exception(f"Error in establishing a connection with the RabbitMQ Broker: {str(e)}", extra={
            "exception": str(e)
        })

if __name__ == "__main__":
    logger.info("Static file storage bucket uploader started consuming....")
    print("Static file storage bucket uploader started consuming....")
    
    consumer_thread = threading.Thread(target=consume_message)
    consumer_thread.start()

    logger.info("Storage Bucket uploader connection I/O Thread started")
    uvicorn.run(app, host="0.0.0.0", port=8000)
