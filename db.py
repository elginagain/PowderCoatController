# db.py
import sqlite3
from contextlib import closing

DB_FILE = "oven_data.db"

def get_db():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable accessing columns by name.
    return conn

def init_db():
    """Initializes the database using the schema.sql file."""
    with closing(get_db()) as db:
        with open("schema.sql", "r") as f:
            db.executescript(f.read())
        db.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
