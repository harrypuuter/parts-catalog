# Teilekatalog (Parts Catalog)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern Flask web application for managing parts inventory with **multi-location tracking**, **quantity management**, **OCR support**, and **PDF export**.

![Teilekatalog Demo](https://via.placeholder.com/800x400?text=Parts+Catalog+Screenshot)

---

## Features

### Inventory Management
- **Multi-location storage** - Track the same part across multiple shelves and sections
- **Quantity tracking** - Monitor stock levels at each location
- **History audit log** - Full traceability of all inventory changes
- **Duplicate detection** - Automatic detection when adding existing part codes

### Smart Input
- **OCR-powered text extraction** - Take a photo, let AI read the part code
- **Automatic categorization** - Distinguishes part codes from descriptions
- **Case-insensitive matching** - P-1234 equals p-1234

### Organization
- **Shelf-based views** - Browse inventory by physical location
- **Full-text search** - Find parts by code or description
- **Quantity badges** - See stock levels at a glance

### PDF Export
- **Shelf lists** - One page per shelf, perfect for printing and hanging
- **Full inventory** - Alphabetical list of all parts with locations

### User Interface
- **German language** - Fully localized interface
- **Mobile-friendly** - Responsive design works on phones and tablets
- **Professional styling** - Clean, modern appearance

---

## Requirements

- **Python 3.12 or higher**
- **uv** (recommended) or pip

> **Note:** SQLite is included with Python - no separate database installation required. All dependencies are managed automatically by uv.

---

## Installation

### Step 1: Install uv (Package Manager)

uv is a fast Python package manager that handles everything automatically.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative - Install via pip:**
```bash
pip install uv
```

After installation, restart your terminal or run:
- **Linux:** `source ~/.bashrc`
- **macOS:** `source ~/.zshrc`
- **Windows:** Close and reopen PowerShell

### Step 2: Clone the Repository

**macOS / Linux:**
```bash
git clone https://github.com/harrypuuter/parts-catalog.git
cd parts-catalog
```

**Windows (Command Prompt or PowerShell):**
```cmd
git clone https://github.com/harrypuuter/parts-catalog.git
cd parts-catalog
```

### Step 3: Install Dependencies

```bash
uv sync
```

This automatically creates a virtual environment and installs all dependencies.

### Step 4: Run the Application

```bash
uv run python app.py
```

The application will start at: **http://localhost:5001**

---

## Alternative Installation (pip)

If you prefer not to use uv:

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python app.py
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python app.py
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python app.py
```

---

## Usage

### Adding a New Part

1. Click **"Teil hinzufügen"** (Add Part)
2. Take or upload a photo of the part label
3. Select the recognized part code from OCR results (or enter manually)
4. Enter shelf, section, and quantity
5. Click **"Neues Teil anlegen"**

### Adding to Existing Part

When you enter a part code that already exists:
- The system shows a preview of the existing part
- You can add a new location/quantity to that part
- Quantities at the same location are automatically merged

### Withdrawing Parts

1. Open the part detail page
2. Click **"Entnehmen"** (Withdraw) on the desired location
3. Enter the quantity to remove
4. The system logs the withdrawal in the history

### Exporting PDF Lists

Use the **"PDF Export"** dropdown in the navigation:
- **Nach Regal sortiert** - One page per shelf (for hanging next to shelves)
- **Inventarliste (A-Z)** - Complete alphabetical inventory

---

## Database Schema

```
items                    item_locations           item_history
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ id (PK)          │    │ id (PK)          │    │ id (PK)          │
│ code (unique)    │◄───│ item_id (FK)     │    │ item_id (FK)     │
│ description      │    │ shelf            │    │ action           │
│ photo_filename   │    │ section          │    │ shelf            │
│ created_at       │    │ quantity         │    │ section          │
│ updated_at       │    │ created_at       │    │ quantity_before  │
└──────────────────┘    │ updated_at       │    │ quantity_after   │
                        └──────────────────┘    │ created_at       │
                                                └──────────────────┘
```

---

## Configuration

### Secret Key (Production)

For production deployments, set a secure secret key:

```bash
# macOS / Linux
export SECRET_KEY="your-secure-random-key-here"
uv run python app.py

# Windows (PowerShell)
$env:SECRET_KEY="your-secure-random-key-here"
uv run python app.py
```

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Changing the Port

Edit the last line of `app.py`:
```python
app.run(debug=False, port=5002)  # Change to desired port
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 5001 already in use | Change port in `app.py` |
| OCR is slow on first run | Normal - EasyOCR downloads language models on first use (~100MB) |
| Permission denied on uploads | **Linux/macOS:** `mkdir -p uploads && chmod 755 uploads` |
| German characters (ä, ö, ü) not displaying | Use a modern browser with UTF-8 support |
| **Windows:** `Activate.ps1` cannot be loaded | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| **Windows:** `python` not found | Use `py` instead of `python`, or add Python to PATH |

---

## Tech Stack

- **Backend**: Flask 3.1+
- **Database**: SQLite with foreign keys
- **OCR**: EasyOCR
- **PDF Generation**: fpdf2
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **Package Manager**: uv

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
