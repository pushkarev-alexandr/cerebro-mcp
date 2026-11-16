# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

CerebroMCP uses the MCP Python SDK 2.x (`MCPServer`) to expose read-only access to the Cerebro project management system via MCP tools. It connects MCP-compatible clients to Cerebro's database over HTTPS/RPC.

## Commands

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the MCP server
$env:CEREBRO_USER = "your_user"
$env:CEREBRO_PASSWORD = "your_password"
python server.py

# Syntax check
python -m py_compile server.py

# Import sanity check
python -c "import pycerebro; print('OK')"
```

## Architecture

**`server.py`** — entry point. Defines all MCP tools using `@mcp.tool` decorators on an `MCPServer` instance from `mcp.server.mcpserver`. A single shared `Database` connection is created in a lifespan context manager and retrieved per-request via `_db(ctx)`.

**`pycerebro/database.py`** — the heavy module (~2200+ lines). Wraps all RPC calls to Cerebro servers over HTTPS. Connection targets are hard-coded (`login1–4.cerebrohq.com`, port 4443). Handles reconnection on transient SQL state errors (`08000`, `08003`, etc.). Has both read-only (`z_execute(True, ...)`) and write (`z_execute(False, ...)`) paths — the public `execute()` method always uses the write path but is safe for SELECT queries.

**`pycerebro/dbtypes.py`** — index constants for task/message/user/attachment tuple fields and flag bitmasks. Any time you decode a raw tuple from the DB, reference this file for field positions.

**`pycerebro/cclib.py`** — utility functions: hash-to-hex conversion, Cerebro date arithmetic (epoch = 2000-01-01, stored as float days), email formatting.

**`pycerebro/cargador.py`** — XML-RPC client for Cerebro's file storage service (separate from the main DB).

### Data Flow

1. MCP client calls a tool (e.g., `cerebro_get_task`)
2. `server.py` calls `_db(ctx)` to get the shared `Database` instance
3. `Database` makes HTTPS/RPC calls to Cerebro servers
4. Raw tuple results are decoded in `server.py` via helper functions (`_task_to_dict`, `_message_to_dict`, `_user_to_dict`, etc.)
5. Dicts are returned as JSON to the MCP client

### Adding a New Tool

1. Add a `_foo_to_dict(t: tuple) -> dict` helper using `dbtypes.*` constants for field indices
2. Add an input model (Pydantic `BaseModel`) if the tool takes parameters — see `TaskIdInput`, `UrlInput`, etc. for examples
3. Add the `@mcp.tool(...)` decorated async function; always wrap the DB call in `asyncio.to_thread()`
4. All tools return `str` — either `json.dumps(...)` or `f"Error: {e}"` on failure

### Known pycerebro Library Quirks

- **`task_by_url(url)`** — expects no trailing slash (`/Foo/Bar` not `/Foo/Bar/`). Returns a row where `row[0]` is the task ID as a **text** column (not bigint), so convert with `int()` before passing to `task()`.
- **`task_checks(task_id)`** — has a bug: passes `to_array(task_id)` but SQL has `?::bigint` (scalar). Bypass by calling `db.execute('select * from "taskChecksColumn"(?::bigint[])', [task_id])` directly.
- **`execute(query, *params)`** is public and safe for SELECT — it calls `z_execute(False, ...)` (non-read-only path) but won't modify data.

### Cerebro Date Format

Dates are stored as `float` days offset from **January 1, 2000**. The `_days_to_date()` helper in `server.py` converts to ISO date string.

### MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `cerebro_get_root_tasks` | All root-level projects |
| `cerebro_get_task` | Single task by ID |
| `cerebro_get_task_children` | Direct subtasks of a task |
| `cerebro_get_task_messages` | Forum messages (reviews, reports, notes, status changes) |
| `cerebro_get_users` | All users and resources |
| `cerebro_get_task_by_url` | Task by full path, e.g. `/Pipeline tools/Utilities/User Status` |
| `cerebro_get_statuses` | All status definitions (use to decode `status_id`) |
| `cerebro_get_activities` | All activity type definitions |
| `cerebro_get_current_user` | Currently authenticated user |
| `cerebro_get_user_tasks` | Tasks allocated to a specific user |
| `cerebro_get_task_tags` | Custom tag values on a task |
| `cerebro_get_task_attachments` | Files attached to a task |
| `cerebro_get_message_attachments` | Files attached to a specific message |
| `cerebro_get_task_checks` | Checklist items on a task |
| `cerebro_get_checks` | All check definitions (use to decode `check_id`) |
| `cerebro_get_task_links` | Dependency links (predecessor/follower) |
| `cerebro_get_project_tags` | Tag schema for a project |

## Environment Variables

- `CEREBRO_USER` — Cerebro login username (required only for fallback authentication)
- `CEREBRO_PASSWORD` — Cerebro login password (required only for fallback authentication)

At startup, `app_lifespan` first calls `connect_from_cerebro_client()` to use the session of a locally running, signed-in Cerebro client. If it does not return `CLIENT_CONNECTED`, both environment variables are required for `connect()` as a fallback.

## Key Constants (`dbtypes.py`)

- **Task fields:** `TASK_DATA_ID`, `TASK_DATA_NAME`, `TASK_DATA_PARENT_URL`, `TASK_DATA_PROGRESS`, `TASK_DATA_PRIORITY`, `TASK_DATA_CC_STATUS`, `TASK_DATA_HUMAN_START/FINISH`, `TASK_DATA_ALLOCATED`, etc.
- **Message types:** `MESSAGE_TYPE_DEFINITION`, `MESSAGE_TYPE_REVIEW`, `MESSAGE_TYPE_REPORT`, `MESSAGE_TYPE_NOTE`, `MESSAGE_TYPE_CLIENT_REVIEW`, `MESSAGE_TYPE_RESOURCE_REPORT`, `MESSAGE_TYPE_STATUS_CHANGES`
- **Attachment tags:** `ATTACHMENT_TAG_FILE`, `ATTACHMENT_TAG_LINK`, `ATTACHMENT_TAG_THUMB1/2/3`, `ATTACHMENT_TAG_REVIEW`
- **Tag types:** `TAG_TYPE_INTEGER`, `TAG_TYPE_ENUM`, `TAG_TYPE_FLOAT`, `TAG_TYPE_STRING`, `TAG_TYPE_MULTI_ENUM`, `TAG_TYPE_USER`, `TAG_TYPE_MULTI_USER`
- **Priority levels:** `TASK_PRIORITY_LOW/BELOW_NORMAL/NORMAL/ABOVE_NORMAL/HIGHT/CRITICAL` (note: `HIGHT` is a typo in the library, not `HIGH`)
