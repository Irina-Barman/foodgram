CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    measurement_unit VARCHAR(40) NOT NULL
);

COPY ingredients(name, measurement_unit)
FROM '/docker-entrypoint-initdb.d/ingredients.csv'
DELIMITER ','
CSV HEADER;


CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE
);

COPY tags(name, slug)
FROM '/docker-entrypoint-initdb.d/tags.csv'
DELIMITER ','
CSV HEADER;
