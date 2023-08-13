import sqlalchemy as  sa

# Currently edit this for all the supported feeds:
rss_feeds = [
    {
        "pk": 1,
        "url": "https://foreignpolicy.com/feed/",
        "etag": None,
        "last_updated_date": None
    },
    {
        "pk": 2,
        "url": "https://www.38north.org/feed/",
        "etag": None,
        "last_updated_date": None
    },
    {
        "pk":3,
        "url":"https://www.reutersagency.com/feed/?best-regions=asia&post_type=best",
        "etag": None,
        "last_updated_date": None
    },
    {
        "pk":4,
        "url":"https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best",
        "etag": None,
        "last_updated_date": None
    },
    {
        "pk":5,
        "url":"https://spacenews.com/feed/",
        "etag": None,
        "last_updated_date":None
    },
    {
        "pk":6,
        "url":"https://www.defensenews.com/arc/outboundfeeds/rss/category/space/?outputType=xml",
        "etag": None,
        "last_updated_date":None
    },
    {
        "pk":7,
        "url":"https://www.defensenews.com/arc/outboundfeeds/rss/category/air/?outputType=xml",
        "etag": None,
        "last_updated_date":None
    },
    {
        "pk":8,
        "url":"https://www.defensenews.com/arc/outboundfeeds/rss/category/training-sim/?outputType=xml",
        "etag": None,
        "last_updated_date":None
    },
    {
        "pk":9,
        "url":"https://www.defensenews.com/arc/outboundfeeds/rss/category/global/?outputType=xml",
        "etag": None,
        "last_updated_date":None
    },
    {
        "pk":10,
        "url":"https://www.defensenews.com/arc/outboundfeeds/rss/category/industry/?outputType=xml",
        "etag": None,
        "last_updated_date":None
    },
    {
        "pk":11,
        "url":"https://www.defensenews.com/arc/outboundfeeds/rss/category/naval/?outputType=xml",
        "etag": None,
        "last_updated_date":None
    },

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
