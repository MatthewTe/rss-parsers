from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pytz import utc
import pika
import datetime
import json
import os 
import uuid 

# Logging imports:
from app.broker_logger import logger

# Background Scheudler Imports:
from app.scheduler_config import scheduler

app = FastAPI()

DEV_STATUS: str | None = os.environ.get("DEV_STATUS", None)

# Adding Middleware to allow for localhost CORS requests for development connection & debugging:
origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

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

@app.get("/status")
async def get_status():
    "Checking the status of the ingestion scheduler"

    return {
        "status": 200,
        "microservice_name": "article_ingestion_scheduler",
        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "jobs": [
            {
                "id": job.id,
                "func": job.func,
                "name": job.name,
                "kwargs": job.kwargs,
                "next_runtime": job.next_run_time
            } for job in scheduler.get_jobs()
        ]
 
    }

@app.get("/test_emit_logs")
async def emit_mock_logs():
    
    logger.debug("Debug test message log")
    logger.info("Info test message log")
    logger.warning("Warning test message log")
    logger.error("Error test message log")
    

    return {"Test logs emitted": True}

@app.get("/test_emit")
async def emit_mock_rss_data():
    articles = [
        {   
            "rss_feed_id": 9999,
            "date_extracted": datetime.datetime.now().date().isoformat(),
            "title": f"This is test article 1 - {str(uuid.uuid4())}",
            "url": "https://www.google.com/",
            "date_posted": datetime.datetime.now().isoformat()
        },
        {   
            "rss_feed_id": 9999,
            "date_extracted": datetime.datetime.now().date().isoformat(),
            "title": f"This is test article 2 - {str(uuid.uuid4())}",
            "url": "https://www.google.com/",
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
    scheduler.get_job(job_id="https://www.38north.org/feed/").modify(next_run_time=datetime.datetime.now())
    scheduler.get_job(job_id="https://foreignpolicy.com/feed/").modify(next_run_time=datetime.datetime.now())

    logger.info("Manually triggering bulk rss feed function")
 
    return {"message": "Manually triggered rss feed ingestion task"}