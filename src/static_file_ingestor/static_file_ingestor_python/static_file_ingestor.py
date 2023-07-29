import ast
import os
from typing import Literal
import uvicorn
import threading
import fastapi
import datetime
from fastapi.middleware.cors import CORSMiddleware

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
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            channel.basic_nack(delivery_tag=method.delivery_tag)
    
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
