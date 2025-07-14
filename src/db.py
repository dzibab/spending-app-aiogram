import os
import io
import csv
import datetime

import psycopg

from .utils import aggregate_expenses_by_category


class DBConnection:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("POSTGRES_DSN")
        self.conn = None
        self.cursor = None

    def __enter__(self):
        if self.dsn is None:
            raise ValueError("Database DSN must not be None")
        self.conn = psycopg.connect(self.dsn, autocommit=False)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()

    def execute(self, *args, **kwargs):
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.execute(*args, **kwargs)

    def fetchone(self):
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.fetchone()

    def fetchall(self):
        if self.cursor is None:
            raise RuntimeError("Database cursor is not initialized.")
        return self.cursor.fetchall()

    def commit(self):
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized.")
        self.conn.commit()


def init_db():
    with DBConnection() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            currency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            currency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)


def add_user(telegram_id: int) -> None:
    with DBConnection() as db:
        db.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
        if db.fetchone() is None:
            db.execute("INSERT INTO users (telegram_id) VALUES (%s)", (telegram_id,))


def set_currency(telegram_id: int, currency: str) -> None:
    with DBConnection() as db:
        db.execute(
            "UPDATE users SET currency = %s WHERE telegram_id = %s",
            (currency, telegram_id),
        )


def add_expense(
    telegram_id: int, amount: float, category: str, description: str | None
) -> None:
    with DBConnection() as db:
        # Get user_id and currency from telegram_id
        db.execute(
            "SELECT id, currency FROM users WHERE telegram_id = %s", (telegram_id,)
        )
        row = db.fetchone()
        if row is None:
            raise ValueError("User not found")
        user_id, currency = row[0], row[1]
        if not currency:
            raise ValueError("Currency is not set for this user")
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, description, currency) VALUES (%s, %s, %s, %s, %s)",
            (user_id, amount, category, description, currency),
        )


def get_expenses_for_period(telegram_id: int, period: str) -> list[dict]:
    """
    Fetch expenses for a user for a given period ('week', 'month', 'year').
    Returns a list of dicts: {amount, category, currency, created_at}
    """
    if period not in ("week", "month", "year"):
        raise ValueError("Invalid period. Use 'week', 'month', or 'year'.")

    now = datetime.datetime.now()

    match period:
        case "week":
            since = now - datetime.timedelta(days=7)
        case "month":
            since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        case "year":
            since = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )

    with DBConnection() as db:
        db.execute(
            "SELECT u.id, u.currency FROM users u WHERE u.telegram_id = %s",
            (telegram_id,),
        )
        user_row = db.fetchone()
        if user_row is None:
            raise ValueError("User not found")
        user_id = user_row[0]

        db.execute(
            """
            SELECT amount, category, currency, created_at
            FROM expenses
            WHERE user_id = %s AND created_at >= %s
            """,
            (user_id, since.strftime("%Y-%m-%d %H:%M:%S")),
        )
        rows = db.fetchall()
        expenses = [
            {
                "amount": row[0],
                "category": row[1],
                "currency": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]
        return expenses


def get_user_stats_for_period(telegram_id: int, period: str) -> tuple[str, dict, float]:
    """
    Returns (user_currency, category_totals, total) for the user's expenses in the given period.
    Raises ValueError if user or currency not set.
    """

    with DBConnection() as db:
        db.execute(
            "SELECT currency FROM users WHERE telegram_id = %s",
            (telegram_id,),
        )
        row = db.fetchone()
        if not row or not row[0]:
            raise ValueError("Currency not set for user")
        user_currency = row[0]
    expenses = get_expenses_for_period(telegram_id, period)
    if not expenses:
        return user_currency, {}, 0.0
    category_totals, total = aggregate_expenses_by_category(expenses, user_currency)
    return user_currency, category_totals, total


def get_user_id(telegram_id: int) -> int | None:
    """Return the user id for a given telegram_id, or None if not found."""
    with DBConnection() as db:
        db.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
        row = db.fetchone()
        if row is None:
            return None
        return row[0]


def export_user_data(telegram_id: int) -> tuple[io.BytesIO | None, str | None]:
    """Export all expenses for the user as a CSV file in memory."""
    user_id = get_user_id(telegram_id)
    if user_id is None:
        return None, None
    with DBConnection() as db:
        db.execute(
            """
            SELECT amount, category, currency, description, created_at
            FROM expenses
            WHERE user_id = %s
            ORDER BY created_at ASC
            """,
            (user_id,),
        )
        rows = db.fetchall()
    if not rows:
        return None, None
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["amount", "category", "currency", "description", "created_at"])
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    filename = f"spending_export_{telegram_id}.csv"
    return io.BytesIO(output.getvalue().encode()), filename
