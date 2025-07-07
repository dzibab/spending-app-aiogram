import sqlite3

from constants import DB


class DBConnection:
    def __init__(self, db_path=DB):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()

    def _fetch(self, mode):
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        if mode == "one":
            return self.cursor.fetchone()
        elif mode == "all":
            return self.cursor.fetchall()
        else:
            raise ValueError("Invalid fetch mode.")

    def execute(self, *args, **kwargs):
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.execute(*args, **kwargs)

    def fetchone(self):
        return self._fetch("one")

    def fetchall(self):
        return self._fetch("all")

    def commit(self):
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized.")
        self.conn.commit()


def init_db():
    with DBConnection() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            currency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            currency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)


def add_user(telegram_id: int) -> None:
    with DBConnection() as db:
        db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        if db.fetchone() is None:
            db.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))


def set_currency(telegram_id: int, currency: str) -> None:
    with DBConnection() as db:
        db.execute(
            "UPDATE users SET currency = ? WHERE telegram_id = ?",
            (currency, telegram_id),
        )


def add_expense(
    telegram_id: int, amount: float, category: str, description: str | None
) -> None:
    with DBConnection() as db:
        # Get user_id and currency from telegram_id
        db.execute(
            "SELECT id, currency FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = db.fetchone()
        if row is None:
            raise ValueError("User not found")
        user_id, currency = row
        if not currency:
            raise ValueError("Currency is not set for this user")
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, description, currency) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, description, currency),
        )


if __name__ == "__main__":
    init_db()
