USE rss_articles_db;

-- Inserting default rows in the rss feeds 
INSERT IGNORE INTO rss_feed (url, name) VALUES
    ('https://foreignpolicy.com/feed/', 'foreign_policy_magazine'),
    ('https://www.38north.org/rss', '38_north'),
    ('https://www.reutersagency.com/feed/?best-regions=asia&post_type=best', "reuters_asia"),
    ('https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best', 'reuters_politics'),
    ('https://spacenews.com/feed/', 'space_news'),
    ('https://www.defensenews.com/arc/outboundfeeds/rss/category/space/?outputType=xml', 'defense_news_space'),
    ('https://www.defensenews.com/arc/outboundfeeds/rss/category/air/?outputType=xml', 'defense_news_air'),
    ('https://www.defensenews.com/arc/outboundfeeds/rss/category/training-sim/?outputType=xml', 'defense_news_training_sim'),
    ('https://www.defensenews.com/arc/outboundfeeds/rss/category/global/?outputType=xml', 'defense_news_global'),
    ('https://www.defensenews.com/arc/outboundfeeds/rss/category/industry/?outputType=xml', 'defense_news_industry'),
    ('https://www.defensenews.com/arc/outboundfeeds/rss/category/naval/?outputType=xml', 'defense_news_naval');

