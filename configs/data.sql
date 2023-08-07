USE rss_articles_db;

-- Inserting default rows in the rss feeds 
INSERT IGNORE INTO rss_feed (url, name) VALUES
    ('https://foreignpolicy.com/feed/', 'foreign_policy_magazine'),
    ('https://www.38north.org/rss', '38_north'),
    ('https://www.reutersagency.com/feed/?best-regions=asia&post_type=best', "reuters_asia"),
    ('https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best', 'reuters_politics');

