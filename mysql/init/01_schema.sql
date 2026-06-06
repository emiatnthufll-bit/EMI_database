CREATE DATABASE IF NOT EXISTS emi_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE emi_db;

-- Core tables
CREATE TABLE papers (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title        VARCHAR(512) NOT NULL,
  abstract     MEDIUMTEXT,
  year         INT,
  venue        VARCHAR(255),
  doi          VARCHAR(128),
  url          VARCHAR(500),
  authors      TEXT,            -- comma-separated for MVP (normalize later)
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE categories (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) UNIQUE NOT NULL
) ENGINE=InnoDB;

CREATE TABLE paper_categories (
  paper_id BIGINT NOT NULL,
  category_id INT NOT NULL,
  PRIMARY KEY (paper_id, category_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE keywords (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) UNIQUE NOT NULL
) ENGINE=InnoDB;

CREATE TABLE paper_keywords (
  paper_id BIGINT NOT NULL,
  keyword_id INT NOT NULL,
  PRIMARY KEY (paper_id, keyword_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- New Metadata Tables

-- 1. Publication Types
CREATE TABLE publication_types (
  id VARCHAR(50) PRIMARY KEY, -- e.g., 'BC', 'JA'
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE paper_publication_types (
  paper_id BIGINT NOT NULL,
  publication_type_id VARCHAR(50) NOT NULL,
  PRIMARY KEY (paper_id, publication_type_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (publication_type_id) REFERENCES publication_types(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 2. Journal Indices
CREATE TABLE journal_indices (
  id VARCHAR(50) PRIMARY KEY, -- e.g., 'SSCI', 'SCOPUS'
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE paper_journal_indices (
  paper_id BIGINT NOT NULL,
  journal_index_id VARCHAR(50) NOT NULL,
  PRIMARY KEY (paper_id, journal_index_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (journal_index_id) REFERENCES journal_indices(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. Nature of Study
CREATE TABLE study_natures (
  id VARCHAR(50) PRIMARY KEY, -- e.g., 'RE', 'PD'
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE paper_study_natures (
  paper_id BIGINT NOT NULL,
  study_nature_id VARCHAR(50) NOT NULL,
  PRIMARY KEY (paper_id, study_nature_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (study_nature_id) REFERENCES study_natures(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Education Level
CREATE TABLE education_levels (
  id VARCHAR(50) PRIMARY KEY, -- e.g., 'HE', 'KS'
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE paper_education_levels (
  paper_id BIGINT NOT NULL,
  education_level_id VARCHAR(50) NOT NULL,
  PRIMARY KEY (paper_id, education_level_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (education_level_id) REFERENCES education_levels(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Research Location
CREATE TABLE research_locations (
  id VARCHAR(50) PRIMARY KEY, -- e.g., 'TW', 'CN'
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE paper_research_locations (
  paper_id BIGINT NOT NULL,
  research_location_id VARCHAR(50) NOT NULL,
  PRIMARY KEY (paper_id, research_location_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (research_location_id) REFERENCES research_locations(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. Research Focus
CREATE TABLE research_focuses (
  id VARCHAR(50) PRIMARY KEY, -- e.g., 'TO', 'SO'
  description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE paper_research_focuses (
  paper_id BIGINT NOT NULL,
  research_focus_id VARCHAR(50) NOT NULL,
  PRIMARY KEY (paper_id, research_focus_id),
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
  FOREIGN KEY (research_focus_id) REFERENCES research_focuses(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Fulltext indexes (ngram parser for CJK support)
ALTER TABLE papers ADD FULLTEXT ft_title_abs (title, abstract) WITH PARSER ngram;
ALTER TABLE papers ADD FULLTEXT ft_authors (authors) WITH PARSER ngram;

-- Helper views for facets
CREATE OR REPLACE VIEW v_category_counts AS
SELECT c.id, c.name, COUNT(pc.paper_id) AS cnt
FROM categories c
LEFT JOIN paper_categories pc ON pc.category_id = c.id
GROUP BY c.id, c.name
ORDER BY cnt DESC, c.name;

CREATE OR REPLACE VIEW v_keyword_counts AS
SELECT k.id, k.name, COUNT(pk.paper_id) AS cnt
FROM keywords k
LEFT JOIN paper_keywords pk ON pk.keyword_id = k.id
GROUP BY k.id, k.name
ORDER BY cnt DESC, k.name;
