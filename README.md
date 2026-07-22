# CerebroMCP

MCP server for working with the [Cerebro](https://cerebrohq.com) project management system. Lets Claude and other LLM clients read data from Cerebro: tasks, messages, users, attachments, and more.

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

### 1. Copy the pycerebro library

The library is not included in this repository. Copy the `pycerebro` folder from your Cerebro installation into the project root:

```
C:\Program Files\Cerebro\py-site-packages\pycerebro  →  <project folder>\pycerebro
```

### 2. Create a virtual environment and install dependencies

```powershell
cd <project folder>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Verify the installation

```powershell
python -m py_compile server.py
python -c "import pycerebro; print('OK')"
```

### 4. Connect to Claude Desktop

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
