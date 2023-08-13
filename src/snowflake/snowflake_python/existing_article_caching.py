import os
import pathlib

from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import sqlite3

from broker_logger import logger

def rebuild_article_cache(path_url: str):
    "Fully rebuilds the sqlite article cache based on the local filepath"
    logger.info("Triggering article cache rebuild")
    
    cache_db_path: pathlib.Path = pathlib.Path(path_url)

    engine_url = URL.create(
        drivername="mysql+mysqldb",
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
        host=os.environ.get("HOST"),
        database=os.environ.get("DATABASE")
    )   

    engine = sa.create_engine(engine_url, connect_args={"ssl":{"ca":"/etc/ssl/certs/ca-certificates.crt"}})
    MainDBSession = sessionmaker(bind=engine)

    print("Triggering Article Cache rebuild")

    if cache_db_path.is_file():
        cache_db_path.unlink()
        logger.info("Deleted current existing Cache")

    
    sqlite_conn = sqlite3.connect(cache_db_path)
    sqlite_cursor = sqlite_conn.cursor()
    
    sqlite_cursor.execute("""       
        CREATE TABLE IF NOT EXISTS local_articles (
            url TEXT PRIMARY KEY
        )"""
    )
    sqlite_conn.commit()
    logger.info("Created logging cache table")
    
    with MainDBSession() as session:
        articles: tuple = session.execute(sa.text("SELECT url FROM article")).fetchall()
        logger.info("Queried all existing urls from the main database", extra={"number_articles": len(articles)})

    sqlite_cursor.executemany(
            'INSERT OR IGNORE INTO local_articles (url) VALUES (?)',
            articles
        )
    
    sqlite_conn.commit()
    logger.info("Adding all articles from the main database to the local cache", extra={"number_articles": len(articles)})
    sqlite_conn.close()

def determine_article_in_db(url: str) -> bool:
    "Wraps all of the logic for determining if an article exists in the database"
    engine_url = URL.create(
        drivername="mysql+mysqldb",
        username=os.environ.get("USERNAME"),
        password=os.environ.get("PASSWORD"),
        host=os.environ.get("HOST"),
        database=os.environ.get("DATABASE")
    )

    engine = sa.create_engine(engine_url, connect_args={"ssl":{"ca":"/etc/ssl/certs/ca-certificates.crt"}})

    MainDBSession = sessionmaker(bind=engine)

    # First we check to see if the article db cache exists:
    sqlite_cache_path_str: str = "article_cache.db.sqlite3"
    sqlite_cache_path: pathlib.Path = pathlib.Path(sqlite_cache_path_str)

    if not sqlite_cache_path.is_file():
        logger.info("Existing article cache not found. Rebuilding cache from main database")
        rebuild_article_cache(path_url=sqlite_cache_path_str)
       
    # Check to see if the url exists in the cached article db:
    with sqlite3.connect(sqlite_cache_path) as sqlite_conn:
        sqlite_cursor = sqlite_conn.cursor()
        existing_article = sqlite_cursor.execute("SELECT url FROM local_articles WHERE url= :url", {"url":url}).fetchone()
        
        # Url in cache, already exists:
        if existing_article is not None:
            logger.debug("Provided url exists in the cache", extra={"url": url})
            return True
        
        # Article still might exist in the main db:
        else:
            logger.info("url was not found in the cache, checking the main database for article", extra={"url":url})
            with MainDBSession() as session:

                article_unique_query = sa.text("SELECT id FROM article WHERE url = :url")
                existing_article = session.execute(article_unique_query, {"url":url}).fetchone()

                # Article does exist in the main db:
            if existing_article is not None:
                logger.info("url was found in the main database not in cache", extra={'url':url})
                return True
            
            # Article not in the cache or the main db. It is unique:
            else:
                logger.info("url was not found in the cache or the main database. article is unique.", extra={'url':url})
                return False

    




