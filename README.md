# desktop-mcp

A vision-powered desktop automation library and MCP server.  
Control any GUI application using natural language — via local multimodal LLMs or directly through vision-capable AI assistants like Claude and Gemini.

## How it works

```
Any LLM / AI Assistant
        │
        │  MCP tools
        ▼
┌──────────────────────────────┐
│        desktop-mcp           │
│                              │
│  capture_screenshot()        │  ◀─ screen
│  click_on("description")     │  ──▶ mouse
│  type_text("hello")          │  ──▶ keyboard
│  wait_until("condition")     │  ──▶ polling
│  read_text("region")         │  ──▶ local LLM (optional)
│  extract_structured_data()   │  ──▶ local LLM (optional)
└──────────────────────────────┘
```

**Vision-capable LLMs** (Claude, Gemini): receive screenshots directly and decide where to click — no local LLM needed.

**Text-only LLMs**: use built-in vision tools (`get_coordinates`, `check_condition`, etc.) which delegate to a local multimodal model.

---

## Requirements

- Python 3.12+
- macOS or Windows
- [`uv`](https://github.com/astral-sh/uv)

### macOS — Accessibility permission

`System Settings → Privacy & Security → Accessibility` — grant permission to the terminal / app running this server.

---

## Installation

```bash
# as a library
uv add "desktop-mcp @ git+https://github.com/snowmerak/desktop-mcp"

# run the MCP server directly (no install required)
uvx --from "git+https://github.com/snowmerak/desktop-mcp" mcp_server
```

---

## MCP Server Setup

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "desktop": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/snowmerak/desktop-mcp", "mcp_server"]
    }
  }
}
```

### Gemini CLI

`~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "desktop": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/snowmerak/desktop-mcp", "mcp_server"]
    }
  }
}
```

### With a local multimodal LLM (vision-less orchestrators)

Add `env` to either config:

```json
{
  "mcpServers": {
    "desktop": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/snowmerak/desktop-mcp", "mcp_server"],
      "env": {
        "PAG_API_URL": "http://localhost:1234/v1/chat/completions",
        "PAG_MODEL": "your-multimodal-model",
        "PAG_API_KEY": "optional-api-key"
      }
    }
  }
}
```

---

## MCP Tools

### Screen

| Tool | Description |
|---|---|
| `capture_screenshot` | Capture the current screen, returns image |
| `mark_region` | Draw a bounding box on a screenshot |

### Vision (uses local LLM)

| Tool | Description |
|---|---|
| `get_coordinates` | Find a UI element → `{x, y}` (0–1000 normalized) |
| `get_bounding_box` | Find a region → `{x1, y1, x2, y2}` |
| `check_condition` | Check if a condition is met → `true/false` |
| `read_text` | Read text from a region |
| `find_all_elements` | Find all matching elements → `[{x, y}, ...]` |
| `extract_structured_data` | Extract data matching a JSON schema |

### Interaction

| Tool | Description |
|---|---|
| `click_on` | Find and click a UI element by description |
| `hover_on` | Move cursor over an element (no click) |
| `drag_from_to` | Drag between two described elements |
| `wait_and_click` | Wait for condition, then click |
| `wait_until` | Poll until a condition is met |

### Input

| Tool | Description |
|---|---|
| `type_text` | Type text via clipboard (Korean, emoji, symbols all work) |
| `press` | Press a key (`enter`, `escape`, `tab`, …) |
| `hotkey` | Press a key combination (`["command", "a"]`) |
| `scroll` | Scroll (positive = up, negative = down) |
| `get_clipboard` | Read clipboard text |

### App Launch

| Tool | Description |
|---|---|
| `open_app` | Launch an app by name or path |
| `open_uri` | Open a URI scheme (`spotify:search:…`) |

### Utility

| Tool | Description |
|---|---|
| `sleep` | Wait for N seconds |
| `set_llm_config` | Set local LLM API URL, model, and key at runtime |
| `fetch_models` | List available models from an LLM server |

---

## Library Usage

```python
from utils.platform import open_app, capture_screenshot
from utils.actions import click_on, wait_and_click
from utils.input import type_text, press, hotkey, scroll
from utils.llm import wait_until, read_text_from_screen, extract_structured_data

def run():
    open_app("Google Chrome")
    wait_and_click(
        "Chrome is open and the address bar is visible",
        "address bar",
    )
    hotkey("command", "a")
    type_text("www.sooplive.co.kr")
    press("enter")

    wait_until(
        "the page is loaded and live broadcast thumbnails are visible",
        capture_screenshot,
    )

    data = extract_structured_data(
        capture_screenshot(),
        schema=[{"title": "", "streamer": "", "viewer_count": 0}],
        context_description="live broadcast items",
    )
    print(data)

run()
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `PAG_API_URL` | `http://localhost:1234/v1/chat/completions` | Local LLM API endpoint |
| `PAG_MODEL` | _(empty)_ | Model name |
| `PAG_API_KEY` | _(empty)_ | API key (omitted from headers if empty) |

---

## Platform Support

| Feature | macOS | Windows |
|---|---|---|
| Screenshot | `screencapture` | `PIL.ImageGrab` |
| App launch | `open -a` | `start` / `shutil.which` |
| URI launch | `open` | `start` (shell) |
| Keyboard / Mouse | pyautogui | pyautogui |

Linux is not currently supported.

---

## License

MIT
