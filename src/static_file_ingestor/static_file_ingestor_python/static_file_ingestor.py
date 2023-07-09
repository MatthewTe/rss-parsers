import ast
import json
import requests
import minio
import os
import io 
import uuid
from datetime import datetime

import pika
from pika.adapters.blocking_connection import BlockingChannel

from static_file_ingestor_logger import logger

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
    # 1) Decode article content from broker
    article: dict[
        "url": str, 
        "title":str, 
        "rss_feed_id":int, 
        "date_extracted":str, 
        "date_posted":str
    ] = ast.literal_eval(body.decode("utf-8"))
    
    article['title'] = article['title'].encode()

    # Test logic:
    if article['url'] == "test_article":
        logger.debug("Test Article Recieved")
        print(f"Test Article Recieved: {article}\n")

        try:
            client = minio.Minio(
                endpoint=MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_PASSWORD,
                secure=False
            )
            logger.info("Sucessfully connected to MINIO client during test", extra={
                "endpoint": MINIO_ENDPOINT,
                "access_key": MINIO_ACCESS_KEY 
            })
            
            if not client.bucket_exists("test-bucket"):
                client.make_bucket("test-bucket") 

            test_content: bytes = io.BytesIO(b"test")
            test_content_size = test_content.getbuffer().nbytes

            test_object_upload_result = client.put_object(
                bucket_name="test-bucket",
                object_name="test_object",
                data=test_content, 
                length=test_content_size,
                content_type="application/html",
                metadata={
                    "title": article['title'],
                    "rss_feed_id": article['rss_feed_id'],
                    "date_extracted": article['date_extracted'],
                    "date_posted": article['date_posted']
                }
            )

            logger.debug("Sucessfully wrote tests bytes to storage buckets", extra={
                "inserted_object_name": test_object_upload_result.object_name,
                "etag": test_object_upload_result.etag,
                "version_id": test_object_upload_result.version_id,
                "bucket_name": "test-bucket",
                "object_name": "test_object"
            })

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.exception(f"Error in uploading minio test data during test: {str(e)}", extra={
                "exception": str(e),
                "endpoint": MINIO_ENDPOINT,
                "access_key": MINIO_ACCESS_KEY 
            })
        
        finally:
            return

    else:

        # 2) Construct bucket path based on article broker content
        try:
            client = minio.Minio(
                endpoint=MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_PASSWORD,
                secure=False
            )
            
            RSS_FEED_ID: int = article['rss_feed_id']
            BUCKET_NAME: str = f"rss-feed-bucket-{RSS_FEED_ID}"
            DATE_POSTED: str = datetime.fromisoformat(article['date_posted']).strftime("%Y-%m-%d")

            # 3) check to see if bucket exists, if not create bucket.
            if not client.bucket_exists(BUCKET_NAME):
                client.make_bucket(BUCKET_NAME) 

        except Exception as e:
            logger.exception(f"Error in connecting to staticfile storage and creating bucket: {str(e)}", extra={
                "exception": str(e),
                "bucket_name": BUCKET_NAME,
                "endpoint": MINIO_ENDPOINT,
                "access_key": MINIO_ACCESS_KEY 
            })

            return

        file_title: str = article['title'].decode("utf-8").lower().replace(" ", "_")
        new_article_object_name: str = f"{DATE_POSTED}/{file_title}.html"

        try:
            # 4) Make request to url from article content to extract html file
            article_response: requests.Response = requests.get(article['url'])
            article_response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            logger.exception(f"Connection error in making requests to the RSS feed url: {str(e)}", extra={
                "exception": str(e),
                "status_code": article_response.status_code,
                "request_error": e.response.text
            })
            return

        try:

            article_content: io.BytesIO = io.BytesIO(article_response.content)  
            article_content_size = article_content.getbuffer().nbytes

            # 5) Load HTML file into minio bucket
            bucket_upload_result = client.put_object(
                bucket_name=BUCKET_NAME,
                object_name=new_article_object_name,
                data=article_content,
                length=article_content_size,
                content_type="text/html",
                metadata={
                    "title": article['title'],
                    "rss_feed_id": article['rss_feed_id'],
                    "date_extracted": article['date_extracted'],
                    "date_posted": article['date_posted']
                }
            )

            logger.info("Uplaoded article html content to the storage bucket", extra={
                "inserted_object_name": bucket_upload_result.object_name,
                "etag": bucket_upload_result.etag,
                "version_id": bucket_upload_result.version_id,
                "bucket_name": BUCKET_NAME,
                "object_name": new_article_object_name
            })

            channel.basic_ack(delivery_tag=method.delivery_tag)
            

        except Exception as e:
            logger.exception(f"Error in uploading article html content to storage bucket {str(e)}", extra={
                "exception": str(e),
                "endpoint": MINIO_ENDPOINT,
                "bucket_name": BUCKET_NAME,
                "access_key": MINIO_ACCESS_KEY 
            })
            return
        
channel.basic_consume(queue=queue_name, on_message_callback=insert_article_storage_bucket_callback, auto_ack=False)

print("Static Bucket ingestor started consuming...")

try:
    logger.info("Static file storage bucket uploader started consuming....")
    print("Static file storage bucket uploader started consuming....")
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
