from pytz import utc
import ast
import json
import os 
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import logging

import pika
from pika.adapters.blocking_connection import BlockingChannel 

logger = logging.getLogger("rss_feed_logger")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("rss_articles.log")
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

logger.addHandler(fh)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))

channel = connection.channel()

channel.exchange_declare("rss_feed", exchange_type="topic")

database_logging_que = channel.queue_declare("log_db_que", exclusive=True)
db_queue_name = database_logging_que.method.queue

channel.queue_bind(
    exchange="rss_feed",
    queue=db_queue_name, 
    routing_key="rss.article.duplicate"
)

def consume_duplicate_rss_feed_logs(ch: BlockingChannel, method, prpoerties, body: bytes):
    "Writes all of the logs generated from the RSS feed to the database method"
    article_log = ast.literal_eval(body.decode("utf-8"))

    if article_log["url"] == "test_article":
        print(f"Test Log Recieved: {article_log}")
        logger.info("Testing log functionality")
        return

    # TODO: Use the actual python logging package to have the articles be deconstructed and logged
    logger.info(f"Duplicate Article extracted from que: {article_log}")

channel.basic_consume(queue=db_queue_name, on_message_callback=consume_duplicate_rss_feed_logs, auto_ack=True)


print("Database logger started consuming...")
channel.start_consuming()