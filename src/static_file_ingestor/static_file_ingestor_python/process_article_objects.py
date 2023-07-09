import ast
import json
import requests
import minio
import os
import io 
import uuid
from datetime import datetime
from typing import Literal

from static_file_ingestor_logger import logger

def upload_article_html_to_bucket(
    minio_endpoint: str,
    minio_access_key: str,
    minio_secret_key: str,

    article: dict[
        "url": str,
        "title": str,
        "rss_feed_id": int,
        "date_extracted":str,
        "date_posted": str
    ]
) -> Literal[200, 404]:
    """Contains the actual logic for ingesting an article dict, making request for article html and storing html 
    into storage bucket.

    Returns
    -------
        int: 200 -> Article HTML content sucessfully written to storage bucket
        int: 404 -> There was an error in uploading the article to the storage bucket
    """
    article['title'] = article['title'].encode()

    try:
        client = minio.Minio(
            endpoint=minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
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
            "endpoint": minio_endpoint,
            "access_key": minio_access_key 
        })

        return 404

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
        return 404

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

    except Exception as e:
        logger.exception(f"Error in uploading article html content to storage bucket {str(e)}", extra={
            "exception": str(e),
            "endpoint": minio_endpoint,
            "bucket_name": BUCKET_NAME,
            "access_key":minio_access_key 
        })
        return 404

    return 200