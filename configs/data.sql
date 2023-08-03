USE rss_articles_db;

-- Inserting default rows in the rss feeds 
INSERT IGNORE INTO rss_feed (url, name) VALUES
    ('https://foreignpolicy.com/feed/', 'foreign_policy_magazine'),
    ('https://www.38north.org/rss', '38_north');

