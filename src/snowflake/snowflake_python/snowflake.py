import ast
import json
import os 
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

import pika
from pika.adapters.blocking_connection import BlockingChannel 

# Broker logger import:
from broker_logger import logger

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))

channel = connection.channel()

channel.exchange_declare("rss_feed", exchange_type="topic")

result = channel.queue_declare("", exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange="rss_feed", queue=queue_name, routing_key="rss.article.raw")

def callback(ch: BlockingChannel, method, properties, body: bytes):
    "Determines if the rss feed article is unique and if it should be passed on to the processing que"

    article = ast.literal_eval(body.decode("utf-8"))

    # Custom test logic:
    if article['url'] == "test_article":
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

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print("Snowflake started consuming...")
logger.info("Snowflake started consuming")
channel.start_consuming()