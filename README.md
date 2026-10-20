# Saathi: Family Assistant MCP Server

An MCP (Model Context Protocol) server that gives any LLM client a toolbox for running a household: family members, events and birthdays, budgets, meal plans, grocery lists, email, calendars, stock data and more.

## What it does

Saathi exposes around 50 tools, a few prompts and a resource through a single [FastMCP](https://github.com/modelcontextprotocol/python-sdk) server. Once registered with an MCP-capable client, the model can call these tools to read and update structured family data stored as local JSON, so the assistant keeps context about the household across conversations rather than relying on chat history.

Tool groups in `main.py`:

| Area | Example tools |
|------|---------------|
| Family members | `get_family_members`, `add_family_member`, `update_family_member`, `set_user_info`, `add_relative`, `get_family_summary` |
| Events and reminders | `add_family_event`, `add_birthday_events_for_family`, `get_upcoming_events`, `create_windows_calendar_reminder`, `create_family_calendar_reminder` |
| Budget | `add_budget_item`, `get_budget_summary` |
| Meals and nutrition | `add_meal_plan`, `add_grocery_list`, `get_grocery_lists`, `add_meal_nutrition`, `calculate_nutrition_summary`, `analyze_meal_nutrition`, `get_nutrition_suggestions` |
| Email and calendar | `send_email`, `connect_to_gmail_imap`, `get_unread_emails`, `get_recent_email_from_sender`, `get_google_oauth2_session`, `get_google_calendar_events` |
| Files and images | `copy_file_to_files_directory`, `store_base64_to_file`, `process_image_from_base64`, `store_image_from_url`, `extract_and_upscale_faces` |
| Information lookup | `download_stocks_info_as_dataframe`, `get_company_info` (yfinance), `get_info_imdb_id` (Cinemagoer), `fetch_website`, `search_hotels`, `youtube_search`, `find_nearby_hospitals_osm`, `get_location_from_ip` |

Prompts: `family_saathi`, `compare_tickers`, `intraday_strategy_builder`, `hotel_search_assistant`. Resource: `greeting://{name}`.

## Architecture

```
 MCP client (desktop chat app, IDE agent, ...)
          |  stdio (JSON-RPC)
          v
 +---------------------------+
 |  main.py  (FastMCP "Saathi") |
 |  tools / prompts / resource  |
 +---------------------------+
     |            |              |
     v            v              v
 files/*.json   External APIs   Local OS
 (family,       yfinance, IMDb, Outlook COM
  events,       OpenStreetMap,  (Windows calendar)
  budget,       ip-api, Gmail
  meals, ...)   SMTP/IMAP,
                Google Calendar
```

- All household state lives in JSON files under `files/` (`family_data.json`, `family_events.json`, `budget_data.json`, `grocery_lists.json`, `meal_plans.json`, `nutrition_info.json`). Files are created on first write.
- yfinance requests go through a `requests-cache` session (`yfinance.cache`).
- `local_agent.py` is a separate, experimental LlamaIndex + Ollama agent that indexes the `files/` directory for local RAG over personal documents. It is not part of the MCP server.

## Tech stack

Python 3.12, `mcp[cli]` (FastMCP), yfinance, requests / requests-cache, Cinemagoer, google-api-python-client + google-auth-oauthlib, OpenCV (face extraction), youtube-search, pywin32 (optional, Windows calendar). Experimental RAG: LlamaIndex, Ollama, ChromaDB. Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`).

## Quickstart

```sh
git clone https://github.com/<your-user>/Saathi-MCP-Family-Assistant.git
cd Saathi-MCP-Family-Assistant
uv sync

# Inspect the tools in the MCP Inspector
uv run mcp dev main.py

# Or run the server over stdio
uv run mcp run main.py
```

The `files/` directory must exist (it is kept in the repo via `files/.gitkeep`). Start a session by calling `set_user_info` and `add_family_member` to seed the family data.

### Registering with an MCP client

Any MCP client that supports stdio servers can launch Saathi. A typical configuration:

```json
{
  "mcpServers": {
    "saathi": {
      "command": "uv",
      "args": ["run", "--with", "mcp[cli]", "mcp", "run", "/absolute/path/to/Saathi-MCP-Family-Assistant/main.py"]
    }
  }
}
```

Some clients use a `servers` key with `"type": "stdio"` instead of `mcpServers`; the command and arguments are the same. Restart the server after adding or changing tools.

## Configuration

- **Secrets:** copy `.env.example` to `.env` and fill in `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` (a [Gmail app password](https://support.google.com/accounts/answer/185833)) for `send_email`. `.env` is git-ignored and loaded at startup with python-dotenv.
- **Google Calendar:** place an OAuth client file named `credentials.json` in the project root. `get_google_oauth2_session` runs the browser consent flow and stores the token in `token.pickle`. Both files are git-ignored.
- **Gmail IMAP:** `connect_to_gmail_imap(user, password)` takes a Gmail address and an app password at call time.
- **Windows calendar reminders:** require Outlook and `pywin32` (`uv add pywin32`).
- **Experimental local agent:** requires a running [Ollama](https://ollama.com) instance with the models referenced in `local_agent.py`.

## Example usage

Prompts you can give the client once Saathi is connected:

- "Add my sister Priya, birthday 12 March, and create birthday events for the whole family."
- "What family events are coming up in the next 30 days?"
- "Log an expense of 1,500 for groceries and show me my budget summary."
- "Plan meals for the week starting Monday and build a grocery list from it."
- "Compare the last month of RELIANCE.NS and TCS.NS." (uses the `compare_tickers` prompt)
- "Find hospitals near my current location."

## Limitations and next steps

- Single-user, local-first: data is plain JSON on disk with no auth or encryption.
- `main.py` is one large module; splitting it into per-domain modules (family, budget, meals, integrations) would make it easier to test.
- `analyze_meal_nutrition` uses simple keyword-based estimates, not a nutrition database.
- `search_hotels` builds a search link and scrapes results; it can break when the target site changes.
- Gmail IMAP access still takes credentials as call arguments; it should read them from the environment like `send_email` does.
- No automated tests yet.
