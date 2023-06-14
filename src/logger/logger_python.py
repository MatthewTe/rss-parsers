from pytz import utc
import ast
import json
import os 
import sys
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import logging

import pika
from pika.adapters.blocking_connection import BlockingChannel 

def main():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=os.environ.get("BROKER_URL", "localhost")))

    channel = connection.channel()
    
    # Link to main log streaming que:
    database_logging_que = channel.queue_declare("log_db_que", exclusive=True)
    db_queue_name = database_logging_que.method.queue

    channel.queue_bind(
        exchange="amq.topic",
        queue=db_queue_name, 
        routing_key="scheduler.DEBUG"
    )

    def consume_duplicate_rss_feed_logs(ch: BlockingChannel, method, prpoerties, body: bytes):
        "Writes all of the logs generated from the RSS feed to the database method"
        print(body)

    
    channel.basic_consume(queue=db_queue_name, on_message_callback=consume_duplicate_rss_feed_logs, auto_ack=True)

    print("Database logger started consuming...")
    channel.start_consuming()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Microservice Stopped")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

