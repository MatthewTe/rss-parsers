import ast
import json
import requests
import minio
import os
import io 
import uuid
from datetime import datetime
from typing import Literal

import pika
from pika.adapters.blocking_connection import BlockingChannel

from static_file_ingestor_logger import logger
from process_article_objects import upload_article_html_to_bucket 

MINIO_ENDPOINT: str = os.environ.get("MINIO_ENDPOINT", "localhost")
MINIO_ACCESS_KEY: str = os.environ.get("MINIO_ACCESS_KEY", "admin")
MINIO_PASSWORD: str = os.environ.get("MINIO_PASSWORD", "password")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(os.environ.get("BROKER_URL", 'localhost'))
)

channel = connection.channel()
channel.exchange_declare(exchange="rss_feed", exchange_type="topic")
result = channel.queue_declare("", exclusive=True)
queue_name= result.method.queue

channel.queue_bind(exchange="rss_feed", queue=queue_name, routing_key="rss.article.inserted")

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
       
channel.basic_consume(queue=queue_name, on_message_callback=insert_article_storage_bucket_callback, auto_ack=False)

print("Static Bucket ingestor started consuming...")

try:
    logger.info("Static file storage bucket uploader started consuming....")
    print("Static file storage bucket uploader started consuming....")
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
