import sqlite3

from constants import DB


def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        currency TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("""
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
    conn.commit()
    conn.close()


def add_user(telegram_id: int) -> None:
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
        conn.commit()
    conn.close()


def set_currency(telegram_id: int, currency: str) -> None:
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET currency = ? WHERE telegram_id = ?", (currency, telegram_id)
    )
    conn.commit()
    conn.close()


def add_expense(
    telegram_id: int, amount: float, category: str, description: str | None
) -> None:
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    # Get user_id and currency from telegram_id
    cursor.execute("SELECT id, currency FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise ValueError("User not found")
    user_id, currency = row
    if not currency:
        conn.close()
        raise ValueError("Currency is not set for this user")
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, description, currency) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, description, currency),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
