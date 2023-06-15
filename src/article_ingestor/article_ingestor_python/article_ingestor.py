import ast
import os
import json
import datetime
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

import pika
from pika.adapters.blocking_connection import BlockingChannel 

# Broker logger import:
from broker_logger import logger

connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))

channel = connection.channel()

channel.exchange_declare("rss_feed", exchange_type="topic")

result = channel.queue_declare("", exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange="rss_feed", queue=queue_name, routing_key="rss.article.new")

def ingest_articles(ch: BlockingChannel, method, properties, body: bytes):
    "Extracts all of the data for an article and writes it do the persistence layer"
    article = ast.literal_eval(body.decode("utf-8"))

    # Article de-seralization:
    article['title'] = article["title"].encode()

    # Custom test logic:
    if article['url'] == "test_article":
        print(f"Test Article Recieved: {article}\n")
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

channel.basic_consume(queue=queue_name, on_message_callback=ingest_articles, auto_ack=True)

logger.info("Article Ingestor started consuming...")
print("Article Ingestor started consuming...")
channel.start_consuming()