# Expense Manager MCP Server

A Model Context Protocol (MCP) server built with [FastMCP](https://github.com/jlowin/fastmcp) for personal expense tracking and financial management. It provides tools for logging, querying, updating, and summarizing expenses stored in a local SQLite database, along with pre-configured category resources.

---

## Features

- **Expense Management**:
  - `add_expense`: Log expenses with date, amount, category, subcategory, and optional notes.
  - `list_expenses`: Retrieve expense entries within an inclusive date range.
  - `get_expense`: Fetch detailed information for a specific expense by ID.
  - `update_expense`: Update existing expense records.
  - `delete_expense`: Remove an expense record by ID.
  - `search_expenses`: Full-text search across expense notes.
  - `summarize`: Generate categorized expense summaries and total spend over a date range.
- **Resources**:
  - `expense://categories`: Read categories and subcategories dynamically from `categories.json`.
- **Remote / HTTP Transport**: Runs as an HTTP service (default port `8000`), making it ready for remote MCP connections.

---

## Getting Started

### Prerequisites

- Python 3.10+ (or Python 3.14)
- [`uv`](https://github.com/astral-sh/uv) or `pip`

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/ashishm2909/Expense-Manager-MCP-Server.git
cd Expense-Manager-MCP-Server
```

Using `uv`:
```bash
uv sync
```

Or using standard `pip`:
```bash
pip install fastmcp
```

---

## Running the Server

Start the server directly:

```bash
python main.py
```

By default, the server runs an HTTP transport on `0.0.0.0:8000`.

---

## Available MCP Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `add_expense` | `date`, `amount`, `category`, `subcategory`, `note` | Add a new expense record |
| `list_expenses` | `start_date`, `end_date` | List expenses between two dates (inclusive) |
| `get_expense` | `id` | Retrieve an expense by its ID |
| `update_expense` | `id`, `date`, `amount`, `category`, `subcategory`, `note` | Update an existing expense record |
| `delete_expense` | `id` | Delete an expense by ID |
| `search_expenses` | `query` | Search expenses by matching note contents |
| `summarize` | `start_date`, `end_date`, `category` (optional) | Summarize total spend grouped by category |

### Resources

- `expense://categories`: JSON list of supported categories and their subcategories.

---

## MCP Client Configuration

To connect this server to an MCP client (such as Claude Desktop or Antigravity):

### SSE / Remote HTTP Transport
```json
{
  "mcpServers": {
    "expense-manager": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## License

MIT
