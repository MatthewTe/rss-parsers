from fastapi import FastAPI
from pytz import utc
import pika
import feedparser
import datetime
import json
import os 

# Logging imports:
from app.broker_logger import logger

# Background Scheudler Imports:
from app.scheduler_config import scheduler

app = FastAPI()
 
@app.get("/")
async def get_tasks():

    jobs = [
        {
            "id": job.id,
            "func": job.func,
            "name": job.name,
            "kwargs": job.kwargs,
            "next_runtime": job.next_run_time
        } for job in scheduler.get_jobs()
    ]
    
    return jobs

@app.get("/test_emit")
async def emit_mock_rss_data():
    articles = [
        {   
            "rss_feed_id": 1,
            "date_extracted": datetime.datetime.now().date().isoformat(),
            "title": "This is test article 1",
            "url": "test_article",
            "date_posted": datetime.datetime.now().isoformat()
        },
        {   
            "rss_feed_id": 2,
            "date_extracted": datetime.datetime.now().date().isoformat(),
            "title": "This is test article 2",
            "url": "test_article",
            "date_posted": datetime.datetime.now().date().isoformat()
        }
    ]

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.environ.get("BROKER_URL", "localhost"))
    )
    channel = connection.channel()

    channel.exchange_declare(exchange="rss_feed", exchange_type="topic")

    for article in articles:
        logger.debug("Debug test message log")
        logger.info("Info test message log")
        logger.warning("Warning test message log")
        logger.error("Error test message log")
        channel.basic_publish(
            exchange="rss_feed", 
            routing_key="rss.article.raw", 
            body=json.dumps(article)
        )

    connection.close()

    return {"test_data_emitted": articles}

@app.get("/manually_trigger")
async def manually_trigger_feed_ingestion():

    # All RSS Feeds that need to be parsed manually need to be added here:
    scheduler.get_job(job_id="https://foreignpolicy.com/feed/").modify(next_run_time=datetime.datetime.now())

    logger.info("Manually triggering bulk rss feed function")
 
    return {"message": "Manually triggered rss feed ingestion task"}