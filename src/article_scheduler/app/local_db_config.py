import sqlalchemy as  sa

rss_feeds = [
    {
        "pk": 1,
        "url": "https://foreignpolicy.com/feed/",
        "etag": None,
        "last_updated_date": None
    }
]

local_sqlite_engine =  sa.create_engine("sqlite:///local.sqlite")

create_rss_feeds_tbl = sa.text("""CREATE TABLE IF NOT EXISTS rss_feeds (
    pk INTEGER UNIQUE,
    url TEXT UNIQUE,
    etag TEXT,
    last_updated_date TEXT
)
""")

insert_rss_feed = sa.text("""INSERT OR IGNORE INTO rss_feeds (
    pk,
    url, 
    etag, 
    last_updated_date
    ) VALUES (
    :pk,
    :url,
    :etag,
    :last_updated_date  
    ) 
""")

# Creation and insertion:
with local_sqlite_engine.connect() as conn, conn.begin():
    
    # Table Creation:
    conn.execute(create_rss_feeds_tbl)

    # Unique data creation:
    for feed in rss_feeds:
        conn.execute(
            insert_rss_feed, 
            {
                "pk": feed['pk'],
                "url": feed['url'],
                "etag": feed['etag'],
                "last_updated_date": feed['last_updated_date']
            }
       )
