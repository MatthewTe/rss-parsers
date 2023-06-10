from fastapi import FastAPI
from pytz import utc
import pika
import feedparser
import datetime
import json
import os 
from time import mktime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    "default": SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}

scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

def get_rss_feed_urls() -> dict[int, str]:
    "Generates a list of rss feed urls"
    return  {
        1:"https://foreignpolicy.com/feed/"
    }
        #{2:"https://www.38north.org/feed/"}
    
def json_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

def emit_rss_feed_articles(feed_urls: list[dict[int, str]]):
    "Extracts all of the articles from the rss feeds and emits them to the message broker"
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.environ.get("BROKER_URL", "localhost"))
    )
    channel = connection.channel()

    channel.exchange_declare(exchange="rss_feed", exchange_type="topic")

    for rss_pk, url in feed_urls.items():
        extracted_feed = feedparser.parse(url)
        
        articles = [
            {   
                "rss_feed_id": rss_pk,
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

    connection.close()

if "bulk_load_rss_feeds" not in [job.id for job in scheduler.get_jobs()]:
    scheduler.add_job(
        func=emit_rss_feed_articles, 
        kwargs={"feed_urls": get_rss_feed_urls()}, 
        trigger="cron", 
        hour=8, 
        minute=30,
        max_instances=1,
        id="bulk_load_rss_feeds"
    )

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
        channel.basic_publish(
            exchange="rss_feed", 
            routing_key="rss.article.raw", 
            body=json.dumps(article)
        )

    connection.close()

    return {"test_data_emitted": articles}

@app.get("/manually_trigger")
async def manually_trigger_feed_ingestion():
    scheduler.get_job(job_id="bulk_load_rss_feeds").modify(next_run_time=datetime.datetime.now())

    return {"message": "Manually triggered rss feed ingestion task"}