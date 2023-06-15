from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Feed Import methods:
from app.feed_parser_methods import emit_rss_feed_articles

jobstores = {
    "default": SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}

scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

# Foreign Policy Article Feed emitter runs every day:
if "fp_rss_feed" not in [job.id for job in scheduler.get_jobs()]:
    scheduler.add_job(
        func=emit_rss_feed_articles, 
        kwargs={"feed_url": "https://foreignpolicy.com/feed/", "feed_pk": 1}, 
        trigger="cron", 
        hour=8, 
        minute=30,
        max_instances=1,
        id="fp_rss_feed"
    )