from pytz import utc
import ast
import json
import os 
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

import pika
from pika.adapters.blocking_connection import BlockingChannel 

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
        ch.basic_publish(exchange="rss_feed", routing_key="rss.article.duplicate", body=json.dumps(article))
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
    print(existing_article)
    if existing_article is not None:
        #ch.basic_publish(exchange="rss_feed", routing_key="rss.article.duplicate", body=json.dumps(article))
        print(f"Article {article['title']} already exists in the database")
        ch.basic_publish(exchange="rss_feed", routing_key="rss.article.duplicate", body=json.dumps(article))
    else:
        print(f"Article {article['title']} is not in the database")
        ch.basic_publish(exchange="rss_feed", routing_key="rss.article.new", body=json.dumps(article))

    session.close()

channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print("Snowflake started consuming...")
channel.start_consuming()