import os
import sqlite3
import tempfile
import json
from fastmcp import FastMCP

def get_db_path() -> str:
    # 1. Custom path from environment variable (e.g., persistent volume like /data/expenses.db)
    env_path = os.environ.get("EXPENSES_DB_PATH")
    if env_path:
        os.makedirs(os.path.dirname(os.path.abspath(env_path)), exist_ok=True)
        return env_path

    # 2. Try application directory
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")
    try:
        with open(local_path, "a"):
            pass
        return local_path
    except (OSError, PermissionError):
        pass

    # 3. Fallback to /tmp or system temp directory (always writable in container/cloud environments)
    return os.path.join(tempfile.gettempdir(), "expenses.db")

DB_PATH = get_db_path()
CATEGORIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

init_db()

@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}
    
@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def update_expense(id, date, amount, category, subcategory="", note=""):

    '''Update an existing expense entry.'''
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            """
            UPDATE expenses
            SET date = ?,
                amount = ?,
                category = ?,
                subcategory = ?,
                note = ?
            WHERE id = ?
            """,
            (date, amount, category, subcategory, note, id)
        )
        return {"status": "ok", "id": id}

@mcp.tool()
def delete_expense(id):
    '''Delete an expense entry.'''
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            """
            DELETE FROM expenses
            WHERE id = ?
            """,
            (id,)
        )
        return {"status": "ok", "id": id}

@mcp.tool()
def get_expense(id):
    '''Get an expense entry.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE id = ?
            """,
            (id,)
        )
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, cur.fetchone()))

@mcp.tool()
def search_expenses(query):
    '''Search expenses by note.
    
    Args:
        query: The search query.
    '''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE note LIKE ?
            ORDER BY id ASC
            """,
            (f"%{query}%",)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    if os.path.exists(CATEGORIES_PATH):
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return json.dumps({
        "categories": [
            {"name": "Food & Dining", "subcategories": ["Groceries", "Restaurants", "Coffee", "Delivery", "Snacks"]},
            {"name": "Transportation", "subcategories": ["Public Transit", "Fuel", "Taxi & Rideshare", "Parking", "Vehicle Maintenance"]},
            {"name": "Housing", "subcategories": ["Rent", "Mortgage", "Maintenance & Repairs", "Furniture", "Supplies"]},
            {"name": "Utilities", "subcategories": ["Electricity", "Water", "Gas", "Internet", "Mobile Phone"]},
            {"name": "Entertainment", "subcategories": ["Movies & Streaming", "Games", "Events & Concerts", "Hobbies", "Subscriptions"]},
            {"name": "Shopping", "subcategories": ["Clothing", "Electronics", "Home Goods", "Gifts"]},
            {"name": "Healthcare", "subcategories": ["Doctor Visits", "Pharmacy & Medications", "Dental", "Insurance", "Fitness"]},
            {"name": "Education", "subcategories": ["Books", "Courses & Tuition", "Supplies", "Software"]},
            {"name": "Travel", "subcategories": ["Flights", "Lodging", "Car Rental", "Sightseeing", "Dining"]},
            {"name": "Personal Care", "subcategories": ["Hair & Grooming", "Cosmetics", "Spa & Wellness"]},
            {"name": "Miscellaneous", "subcategories": ["Fees & Charges", "Donations", "Other"]}
        ]
    }, indent=2)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)