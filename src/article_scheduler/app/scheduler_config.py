import sqlalchemy as sa

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Feed Import methods:
from app.local_db_config import local_sqlite_engine
from app.feed_parser_methods import emit_rss_feed_articles

jobstores = {
    "default": SQLAlchemyJobStore(url='sqlite:///local.sqlite')
}

scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

# Foreign Policy Article Feed emitter runs every day:

with local_sqlite_engine.connect() as conn, conn.begin():
    results = conn.execute(sa.text("SELECT * FROM rss_feeds"))
    rows = results.fetchall()

for row in rows:
    pk, url, etag, last_updated = row
    if url not in [job.id for job in scheduler.get_jobs()]:
        scheduler.add_job(
            func=emit_rss_feed_articles, 
            kwargs={"feed_pk": pk, "feed_url": url, "etag": etag, "last_updated_date": last_updated}, 
            trigger="cron", 
            hour=8, 
            minute=30,
            max_instances=1,
            id=url
        )