import os
import sqlite3
import aiosqlite
import tempfile
import json
from datetime import date as dt_date
from fastmcp import FastMCP

def get_db_path() -> str:
    # 1. If an environment variable is set (e.g. persistent volume like /data/expenses.db)
    env_path = os.environ.get("EXPENSES_DB_PATH")
    if env_path:
        os.makedirs(os.path.dirname(os.path.abspath(env_path)), exist_ok=True)
        return env_path

    # 2. Try the local folder (works when running locally on your Mac)
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")
    try:
        with open(local_path, "a"):
            pass
        return local_path
    except (OSError, PermissionError):
        pass

    # 3. Fallback to /tmp (always writable in FastMCP Cloud / Docker)
    return os.path.join(tempfile.gettempdir(), "expenses.db")

DB_PATH = get_db_path()
CATEGORIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    '''Synchronously ensure the expenses table exists at startup.'''
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
async def add_expense(amount: float, category: str, date: str = "", subcategory: str = "", note: str = ""):
    '''Add a new expense entry to the database. Defaults date to today (YYYY-MM-DD) if omitted.'''
    if not date:
        date = dt_date.today().isoformat()

    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        await c.commit()
        return {"status": "ok", "id": cur.lastrowid, "date": date}

@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    '''List expense entries within an inclusive date range.'''
    async with aiosqlite.connect(DB_PATH) as c:
        c.row_factory = aiosqlite.Row
        async with c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

@mcp.tool()
async def update_expense(id: int, date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    '''Update an existing expense entry.'''
    async with aiosqlite.connect(DB_PATH) as c:
        await c.execute(
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
        await c.commit()
        return {"status": "ok", "id": id}

@mcp.tool()
async def delete_expense(id: int):
    '''Delete an expense entry.'''
    async with aiosqlite.connect(DB_PATH) as c:
        await c.execute(
            "DELETE FROM expenses WHERE id = ?",
            (id,)
        )
        await c.commit()
        return {"status": "ok", "id": id}

@mcp.tool()
async def get_expense(id: int):
    '''Get an expense entry.'''
    async with aiosqlite.connect(DB_PATH) as c:
        c.row_factory = aiosqlite.Row
        async with c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE id = ?
            """,
            (id,)
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                return {"error": f"Expense with id {id} not found"}
            return dict(row)

@mcp.tool()
async def search_expenses(query: str):
    '''Search expenses by note.
    
    Args:
        query: The search query.
    '''
    async with aiosqlite.connect(DB_PATH) as c:
        c.row_factory = aiosqlite.Row
        async with c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE note LIKE ?
            ORDER BY id ASC
            """,
            (f"%{query}%",)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

@mcp.tool()
async def summarize(start_date: str, end_date: str, category: str = None):
    '''Summarize expenses by category within an inclusive date range.'''
    async with aiosqlite.connect(DB_PATH) as c:
        c.row_factory = aiosqlite.Row
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        async with c.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

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
