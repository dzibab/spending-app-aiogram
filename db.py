import sqlite3

from constants import DB


class DBConnection:
    def __init__(self, db_path: str = DB):
        self.db_path: str = db_path
        self.conn: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None

    def __enter__(self) -> "DBConnection":
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()

    def _fetchone(self) -> tuple | None:
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.fetchone()

    def _fetchall(self) -> list[tuple]:
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.fetchall()

    def execute(self, *args, **kwargs) -> sqlite3.Cursor:
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.execute(*args, **kwargs)

    def fetchone(self) -> tuple | None:
        return self._fetchone()

    def fetchall(self) -> list[tuple]:
        return self._fetchall()

    def commit(self) -> None:
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
