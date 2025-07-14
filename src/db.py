import os
import io
import csv
import datetime

import psycopg

from .utils import aggregate_expenses_by_category


class DBConnection:
    """
    Context manager for PostgreSQL database connections.
    Handles connection, cursor, and commit/rollback logic.
    """

    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("POSTGRES_DSN")
        self.conn = None
        self.cursor = None

    def __enter__(self):
        if not self.dsn:
            raise ValueError("Database DSN must not be None")
        self.conn = psycopg.connect(self.dsn, autocommit=False)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
        self.cursor = None
        self.conn = None

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


def init_db() -> None:
    """
    Initialize the database tables if they do not exist.
    """
    with DBConnection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                currency TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.execute(
            """
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
            """
        )


def add_user(telegram_id: int) -> None:
    """
    Add a new user by telegram_id if not already present.
    """
    with DBConnection() as db:
        db.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
        if db.fetchone() is None:
            db.execute("INSERT INTO users (telegram_id) VALUES (%s)", (telegram_id,))


def set_currency(telegram_id: int, currency: str) -> None:
    """
    Set the default currency for a user.
    """
    with DBConnection() as db:
        db.execute(
            "UPDATE users SET currency = %s WHERE telegram_id = %s",
            (currency, telegram_id),
        )


def add_expense(
    telegram_id: int, amount: float, category: str, description: str | None
) -> None:
    """
    Add an expense for a user by telegram_id.
    Raises ValueError if user or currency is not set.
    """
    with DBConnection() as db:
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
    Raises ValueError if user not found or period invalid.
    """
    if period not in ("week", "month", "year"):
        raise ValueError("Invalid period. Use 'week', 'month', or 'year'.")

    now = datetime.datetime.now()
    if period == "week":
        since = now - datetime.timedelta(days=7)
    elif period == "month":
        since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        since = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    with DBConnection() as db:
        db.execute(
            "SELECT id FROM users WHERE telegram_id = %s",
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
        return [
            {
                "amount": row[0],
                "category": row[1],
                "currency": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]


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
    """
    Return the user id for a given telegram_id, or None if not found.
    """
    with DBConnection() as db:
        db.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
        row = db.fetchone()
        return row[0] if row else None


def export_user_data(telegram_id: int) -> tuple[io.BytesIO | None, str | None]:
    """
    Export all expenses for the user as a CSV file in memory.
    Returns a tuple of (BytesIO, filename) or (None, None) if no data.
    """
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
    writer.writerows(rows)
    output.seek(0)
    filename = f"spending_export_{telegram_id}.csv"
    return io.BytesIO(output.getvalue().encode()), filename


def get_recent_expenses(telegram_id: int, limit: int = 10) -> list[dict]:
    """
    Get the most recent expenses for a user.
    Returns a list of dicts: {id, amount, category, currency, description, created_at}
    Raises ValueError if user not found.
    """
    user_id = get_user_id(telegram_id)
    if user_id is None:
        raise ValueError("User not found")

    with DBConnection() as db:
        db.execute(
            """
            SELECT id, amount, category, currency, description, created_at
            FROM expenses
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = db.fetchall()
        return [
            {
                "id": row[0],
                "amount": row[1],
                "category": row[2],
                "currency": row[3],
                "description": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]


def delete_expense(telegram_id: int, expense_id: int) -> bool:
    """
    Delete a specific expense if it belongs to the user.
    Returns True if deleted, False if not found or doesn't belong to user.
    """
    user_id = get_user_id(telegram_id)
    if user_id is None:
        return False

    with DBConnection() as db:
        # Check if expense exists and belongs to user
        db.execute(
            "SELECT id FROM expenses WHERE id = %s AND user_id = %s",
            (expense_id, user_id),
        )
        if db.fetchone() is None:
            return False

        # Delete the expense
        db.execute(
            "DELETE FROM expenses WHERE id = %s AND user_id = %s",
            (expense_id, user_id),
        )
        return True
