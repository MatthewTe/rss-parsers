import os
import pika
import feedparser
import datetime
from time import mktime
import json

# Broker Logger import:
from app.broker_logger import logger

def emit_rss_feed_articles(feed_url: str, feed_pk: int):
    "Function takes a rss feed url and its id and emits articles to main rss feed exchange"
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.environ.get("BROKER_URL", "localhost"))
    )
    channel = connection.channel()

    channel.exchange_declare(exchange="rss_feed", exchange_type="topic")

    # Naievly emits rss feed articles to exchange:
    extracted_feed =  feedparser.parse(feed_url)

    # TODO: Add logic that parses correct fields from the rss feed items. Eg update/published_parsed fields:

    articles = [
        {   
            "rss_feed_id": feed_pk,
            "date_extracted": datetime.datetime.fromtimestamp(mktime(extracted_feed.feed.updated_parsed)).isoformat(),
            "title": article.title,
            "url": article.link,
            "date_posted": datetime.datetime.fromtimestamp(mktime(article.published_parsed)).isoformat()
        }
            for article in extracted_feed.entries
        ]
 
    for article in articles:
        channel.basic_publish(
            exchange="rss_feed", 
            routing_key="rss.article.raw", 
            body=json.dumps(article)
        )
        logger.info("Scheduler emitted article from rss feed", extra={"url":article['url'], "rss_feed":article['rss_feed_id']})

    connection.close()

