# Unified Oncology Decision Support MCP Server

A single MCP server exposing **three clinical decision-support engines**: Cervix, Head & Neck SCC, and Breast Cancer. All follow institutional protocols (AJCC 8th edition).

⚠️ **Decision-support only.** All recommendations require clinical judgment. Cases flagged as RED require MDT discussion.

## Cancer sites and tools

| Site | Tool | Protocol |
|------|------|----------|
| **Cervix** | `cervix_cancer` | Institutional Cervix Cancer Protocol v1.0 |
| **Head & Neck SCC** | `hnscc_decision` | Institutional HNSCC Protocol v1.0 |
| **Breast** | `breast_cancer` | Institutional Breast Cancer Protocol v1.0 |

## Project layout

```
protocol_combined/
├── server.py           # Unified MCP server (run this)
├── requirements.txt
├── README.md
├── validate.py         # Optional: validate breast engine with sample cases
└── engines/
    ├── cervix/         # Cervix engine
    │   ├── cervix_engine.py
    │   ├── models.py
    │   └── config.py
    ├── headneck/       # Head & Neck SCC engine
    │   ├── hn_engine.py
    │   ├── hn_models.py
    │   └── hn_config.py
    └── breast/         # Breast cancer engine
        ├── breast_engine.py
        └── __init__.py
```

## Setup

### 1. Install dependencies

From the project root:

```bash
pip install -r requirements.txt
```

Or with a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the server (stdio)

```bash
python server.py
```

The server runs over stdio by default (for MCP clients like Claude Desktop).

### 3. Connect from Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "oncology-decision-support": {
      "command": "python",
      "args": ["/absolute/path/to/protocol_combined/server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

### 4. Connect from Cursor / other MCP clients

Point the MCP client to run:

- **Command:** `python`
- **Args:** `["/path/to/protocol_combined/server.py"]`

## Behaviour

- The model is instructed to call **one** of the three tools (`cervix_cancer`, `hnscc_decision`, `breast_cancer`) based on the user’s cancer type.
- Each tool has **required parameters**. If any are missing, the server returns a clear list; the model must not call the tool until the user supplies them.
- On success, the tool output is returned verbatim (12-section format for breast; structured sections for cervix and HNSCC).
- On tool error, the model is instructed to show only a short “TOOL ERROR” message and not to answer clinically.

## Validation (optional)

To run the breast engine sample cases:

```bash
python validate.py
```

`validate.py` uses `engines.breast.breast_engine.evaluate_breast_case`.

## Dependencies

- **mcp[cli]** – MCP server (FastMCP)
- **pydantic** – Used by cervix and headneck engines for input validation

Python 3.10+ recommended.
