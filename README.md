# CerebroMCP

MCP server for working with the [Cerebro](https://cerebrohq.com) project management system. Provides MCP-compatible clients with read-only access to Cerebro data: tasks, messages, users, attachments, and more.

## Features

- List all projects and navigate the task tree
- Find a task by full path (`/Project/Folder/Task`)
- Read task forum messages (briefs, reviews, reports, notes, status changes)
- View tasks assigned to a specific user
- Get task attachments or attachments for a single message
- Read custom tags, checklists, and task dependencies
- Decode statuses and activity types (reference data)
- Get the currently authenticated user

For the full list of tools, see [AGENTS.md](AGENTS.md).

## Installation

The `pycerebro` library is included in this repository in the [pycerebro](pycerebro/) folder. No manual copying is required.

### 1. Create a virtual environment and install dependencies

```powershell
cd <project folder>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Verify the installation

```powershell
python -m py_compile server.py
python -c "import pycerebro; print('OK')"
```

### 3. Connect your MCP client

Choose the instructions for your client below.

#### Codex

Open or create the user configuration file:

```text
%USERPROFILE%\.codex\config.toml
```

Add the following configuration:

```toml
[mcp_servers.cerebro]
command = 'C:\path\to\project\.venv\Scripts\python.exe'
args = ['C:\path\to\project\server.py']

[mcp_servers.cerebro.env]
CEREBRO_USER = "your_login@example.com"
CEREBRO_PASSWORD = "your_password"
```

Replace `C:\path\to\project` with the actual project folder path, and set `CEREBRO_USER` and `CEREBRO_PASSWORD` to your Cerebro credentials. The single-quoted TOML paths use literal backslashes, so no escaping is needed.

Start a new Codex session after saving. If you have the Codex CLI installed, run `codex mcp list` to check that `cerebro` is configured, and use `/mcp` inside the CLI to inspect active MCP servers.

For more configuration options, see the [official OpenAI MCP documentation](https://developers.openai.com/codex/mcp).

#### Claude Desktop

Open the configuration file:

```
%APPDATA%\Claude\claude_desktop_config.json
```

Add to the `mcpServers` section:

```json
{
  "mcpServers": {
    "cerebro": {
      "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\project\\server.py"
      ],
      "env": {
        "CEREBRO_USER": "your_login@example.com",
        "CEREBRO_PASSWORD": "your_password"
      }
    }
  }
}
```

Replace `C:\\path\\to\\project` with the actual project folder path, and set `CEREBRO_USER` and `CEREBRO_PASSWORD` to your Cerebro credentials.

Restart Claude Desktop after saving.
