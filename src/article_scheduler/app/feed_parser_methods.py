import os
import pika
import feedparser
import datetime
from time import mktime
import json
import sqlalchemy as sa 

# Broker Logger import:
from app.broker_logger import logger

def get_rss_feed(engine:sa.engine,  pk: int) -> dict[str, str]:
    with engine.connect() as conn, conn.begin():
        result = conn.execute(sa.text("SELECT * FROM rss_feeds WHERE pk = :pk"), {"pk":pk})
        pk, url, etag, last_updated = result.fetchone()

        return {"feed_pk": pk, "feed_url":url, "etag":etag, "last_updated_date": last_updated}


def emit_rss_feed_articles(feed_pk: int, feed_url: str, etag: str, last_updated_date: str):
    "Function takes a rss feed url and its id and emits articles to main rss feed exchange"
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.environ.get("BROKER_URL", "localhost"))
    )
    channel = connection.channel()

    channel.exchange_declare(exchange="rss_feed", exchange_type="topic")

    local_db_engine = sa.create_engine("sqlite:///local.sqlite")
    current_rss_feed_status = get_rss_feed(local_db_engine, feed_pk)
    etag = current_rss_feed_status['etag']
    last_updated_date = current_rss_feed_status['last_updated_date']
   
    # Include an E tag if it exists, if not then include last updated, if not then 'raw query':
    if etag:
        extracted_feed =  feedparser.parse(feed_url, etag=etag)
    elif last_updated_date:
        extracted_feed = feedparser.parse(feed_url, last_updated_date)
    else:
        extracted_feed = feedparser.parse(feed_url)

    if extracted_feed.status == 200:
 
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

    elif extracted_feed.status == 304:
        logger.info("Rss feed parser was triggered, no new entries since last run", extra={"pk":feed_pk})

    if extracted_feed.has_key("etag"):
        new_etag = extracted_feed.etag
    else:
        new_etag = None 

    if extracted_feed.has_key("modified_parsed"):
        new_last_updated = datetime.datetime.fromtimestamp(mktime(extracted_feed.modified_parsed)).isoformat()
    else:
        new_last_updated = None

    print(new_etag, new_last_updated, extracted_feed.status)
    update_query = sa.text("UPDATE rss_feeds SET etag = :etag, last_updated_date = :last_updated_date WHERE pk = :pk")
    with local_db_engine.connect() as conn, conn.begin():
        conn.execute(update_query, {"pk":feed_pk, "etag":new_etag, "last_updated_date":new_last_updated})

    if extracted_feed.status > 400:
        logger.exception("Error in parsing rss_feed", extra={"pk":feed_pk})

    connection.close()

