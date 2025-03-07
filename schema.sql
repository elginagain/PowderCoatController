-- schema.sql

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    temperature REAL NOT NULL,
    set_temperature REAL NOT NULL,
    FOREIGN KEY (cycle_id) REFERENCES cycles(id)
);
