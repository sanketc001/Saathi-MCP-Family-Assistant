# MCP Server Demo – Saathi Family Assistant

Saathi is a Family Assistant designed to help manage and organize family-related tasks, schedules, and information. This project provides a set of tools for handling family member data, events, budgeting, meal planning, grocery lists, document/image processing, and more—all from a single interface.

## Features

- **Family Member Management:**  
  Add, update, and retrieve information about family members, including names, relationships, birthdays, and notes.

- **Family Events & Reminders:**  
  Create and manage family events, birthdays, and reminders. Integrate with Windows Calendar and Google Calendar.

- **Budget Management:**  
  Track income, expenses, savings, and financial goals. Get summaries and manage budget items.

- **Meal Planning & Grocery Lists:**  
  Plan weekly meals and manage grocery lists for the family.

- **Image/Document Processing:**  
  Store, process, and enhance images or documents. Supports base64 and URL-based uploads.

- **Email & Calendar Integration:**  
  Connect to Gmail, send emails, and retrieve calendar events.

- **Information Retrieval:**  
  Fetch information from IMDB, stock data, company info, websites, and hotel search.

## Usage

All tasks are managed via MCP tools defined in [`main.py`](main.py).  
**Do not create or modify any files except `main.py`.**  
All structured data is stored and managed through the provided tools.

### Example Tasks

- Add a new family member:  
  Use `add_family_member(name, relationship, age, birthday, notes)`

- Get upcoming events:  
  Use `get_upcoming_events(days=30)`

- Add a grocery list:  
  Use `add_grocery_list(name, items)`

- Send an email:  
  Use `send_email(title, recipients, subject, body)`

- Process an image:  
  Use `process_image_from_base64(base64_data, filename, file_extension)`

## Project Structure

```
.
├── main.py
├── .github/instructions/saathi.instructions.md
├── .files/
├── chroma_db/
├── data/
├── files/
├── README.md
├── pyproject.toml
└── ...
```

## Important Notes

- **All new features or tools must be added as MCP tools in `main.py`.**
- **Never create new scripts or files outside of `main.py`.**
- **All family, event, budget, and meal data must be stored in a structured format using the provided tools.**
- **After adding a new MCP tool, restart the MCP server before proceeding.**

## Getting Started

1. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```
    or use the dependencies listed in [`pyproject.toml`](pyproject.toml ).

2. Run the server:
    ```sh
    python main.py
    ```

3. Interact with Saathi using the available MCP tools.

## License

This project is for demonstration purposes. See [`pyproject.toml`](pyproject.toml ) for more details.

---

For more information on available tools and usage, see [`.github/instructions/saathi.instructions.md`](.github/instructions/saathi.instructions.md ).
