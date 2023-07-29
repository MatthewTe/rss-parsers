from pytz import utc
import json
import os 
import sys
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import logging
from logging.handlers import TimedRotatingFileHandler
from custom_json_logger import CustomJsonFormatter 

import pika
from pika.adapters.blocking_connection import BlockingChannel 


log_file_name = "microservice_logs.log"
log_dir = "logs"  # Set the desired log directory path
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

file_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, log_file_name),
    when='midnight',
    backupCount=3
)

file_handler.setFormatter(CustomJsonFormatter())

logger = logging.getLogger('broker_file_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

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
        routing_key="*.DEBUG"
    )
    channel.queue_bind(
        exchange="amq.topic",
        queue=db_queue_name, 
        routing_key="*.INFO"
    )
    channel.queue_bind(
        exchange="amq.topic",
        queue=db_queue_name, 
        routing_key="*.WARNING"
    )
    channel.queue_bind(
        exchange="amq.topic",
        queue=db_queue_name, 
        routing_key="*.ERROR"
    )
    def consume_duplicate_rss_feed_logs(ch: BlockingChannel, method, prpoerties, body: bytes):
        "Writes all of the logs generated from the RSS feed to the database method"
        # print(body)

        log_data: dict = json.loads(body)

        log_message: str | None = log_data.pop('message', None)
        level_str = log_data.pop('level', 'INFO')
        log_level = getattr(logging, level_str.upper(), logging.INFO) 
        
        record = logging.makeLogRecord({"msg": log_message, **log_data})
        
        record.levelno = log_level

        logger.handle(record)
   
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

