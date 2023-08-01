CREATE DATABASE IF NOT EXISTS rss_articles_db;
USE rss_articles_db;

CREATE TABLE IF NOT EXISTS rss_feed (
    id INT PRIMARY KEY AUTO_INCREMENT,
    url VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL
);

-- Creating the Articles table
CREATE TABLE IF NOT EXISTS article (
    id INT PRIMARY KEY AUTO_INCREMENT,
    url VARCHAR(255) UNIQUE,
    title VARCHAR(255),
    rss_feed_id INT,
    date_posted DATE,
    date_extracted DATE,
    article MEDIUMBLOB,
    in_storage_bucket BOOLEAN DEFAULT 0,
    inserted_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);