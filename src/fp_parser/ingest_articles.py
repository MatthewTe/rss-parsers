import feedparser
from datetime import datetime
import time
import requests
from time import mktime
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
import sentry_sdk
import os
from apscheduler.schedulers.blocking import BlockingScheduler

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    environment="development",
    traces_sample_rate=1.0
)

sentry_sdk.set_tag("rss_feed", "foreign_policy")


ssl_args = {
    "ssl": {"ca": "/etc/ssl/certs/ca-certificates.crt"},
}

def parse_fp_rss_feed():
    engine_url = URL.create(
        drivername="mysql+mysqldb",
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
        host=os.environ.get("HOST"),
        database=os.environ.get("DATABASE")
    )

    engine = sa.create_engine(engine_url, connect_args=ssl_args)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Getting the rss feed url from the database:
    rss_feed = session.execute(sa.text("SELECT * FROM rss_feed WHERE name = :name"), {"name": "foreign_policy_magazine"}).fetchone()

    if rss_feed:
        rss_feed_url = rss_feed.url
        rss_pk = rss_feed.id
        feed = feedparser.parse(rss_feed_url)
    else:
        raise IndexError("No url found from the rss_feed database url")

    date_feed_extracted = datetime.fromtimestamp(mktime(feed.feed.updated_parsed))

    rows = [] 
    for article in feed.entries:
        #rss_logger.info(f"Processing Article: {article.title} | {article.link} from Rss Feed")
        title, url = article.title, article.link, 
        date_article_published =  datetime.fromtimestamp(mktime(article.published_parsed)) 

        # Checking to see if the article url already exists in the database:
        existing_article = session.execute(sa.text("SELECT COUNT(*) FROM article WHERE url= :url"), {"url":url}).scalar()
        session.close()
        
        # Does not exist:
        if existing_article == 0:
            
            article_request_session = requests.Session()

            try:
                article_response = article_request_session.get(url)
                article_response.raise_for_status()
                time.sleep(2)
            except requests.exceptions.HTTPError as err:
                sentry_sdk.capture_exception(err)

            rows.append(
                {
                    "url": url,
                    "title": title,
                    "rss_feed_id": rss_pk,
                    "date_posted": date_article_published,
                    "date_extracted": date_feed_extracted,
                    "article": article_response.content
                }
            )
        else: 
            sentry_sdk.capture_message(f"Article '{title}' already exists in database. Not added to processing list", level="duplicate_warning")

    if len(rows) == 0:
        sentry_sdk.capture_message("RSS Feed has no unique articles. No rows inserted into the database", level="duplicate_warning")
        return

    session = Session() 
    inserted_rows = session.execute(sa.text("""
        INSERT INTO article (url, title, rss_feed_id, date_posted, date_extracted, article)
        VALUES (:url, :title, :rss_feed_id, :date_posted, :date_extracted, :article)
    """), rows)
    
    rows_inserted = inserted_rows.rowcount
    session.commit()
    session.close()

    try:
        if len(rows) != rows_inserted:
            raise ValueError(f"Number of unique articles extracted from the RSS feed: {len(rows)}. Number of articles inserted into the database {rows_inserted}")
        else:
            sentry_sdk.capture_message(f"Successfully Ingested {rows_inserted} to the database", level="success")

    except ValueError as err:
        sentry_sdk.capture_exception(err)

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(parse_fp_rss_feed, trigger="cron", hour=8, minute=30)
    print("Starting Scheduler...")
    scheduler.start()
