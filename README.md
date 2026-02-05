# Parts Catalog

A Flask web application for cataloging parts with image OCR support for extracting part codes.

## Features

- Add, edit, and delete parts with photos
- OCR-powered text extraction from part images
- Automatic categorization of part codes vs descriptions
- Search functionality
- Shelf-based organization

## Requirements

- Python 3.12 or higher
- uv (recommended) or pip

## Installation

### Step 1: Install uv (Package Manager)

uv is a fast Python package manager. Choose your platform:

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative: Using pip (if you prefer not to install uv):**
```bash
pip install uv
```

After installation, restart your terminal or run `source ~/.bashrc` (Linux) / `source ~/.zshrc` (macOS) to update your PATH.

### Step 2: Clone the Repository

**macOS / Linux:**
```bash
git clone https://github.com/yourusername/parts-catalog.git
cd parts-catalog
```

**Windows (Command Prompt or PowerShell):**
```cmd
git clone https://github.com/yourusername/parts-catalog.git
cd parts-catalog
```

### Step 3: Install Dependencies

**Using uv (recommended):**
```bash
uv sync
```

This will automatically create a virtual environment and install all dependencies.

**Using pip (alternative):**

macOS / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows:
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### Step 4: Run the Application

**Using uv:**
```bash
uv run python app.py
```

**Using pip (with activated virtual environment):**
```bash
python app.py
```

The application will start and be available at: **http://localhost:5001**

## Configuration

### Secret Key (Production)

For production deployments, set a secure secret key:

**macOS / Linux:**
```bash
export SECRET_KEY="your-secure-random-key-here"
uv run python app.py
```

**Windows (Command Prompt):**
```cmd
set SECRET_KEY=your-secure-random-key-here
uv run python app.py
```

**Windows (PowerShell):**
```powershell
$env:SECRET_KEY="your-secure-random-key-here"
uv run python app.py
```

You can generate a secure key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Usage

1. Open your browser and navigate to `http://localhost:5001`
2. Click **"Add Item"** to add a new part to the catalog
3. Fill in the part details:
   - **Code**: The part number/identifier
   - **Description**: Optional description of the part
   - **Shelf**: Which shelf the part is stored on
   - **Section**: Optional section number on the shelf
   - **Photo**: Upload an image of the part
4. Use the **OCR** feature to automatically extract text from part images
5. Browse parts by shelf on the home page or use the **Search** function

## Troubleshooting

### Port 5001 already in use

Edit `app.py` and change the port number on the last line:
```python
app.run(debug=False, port=5002)  # Change to an available port
```

### OCR is slow on first run

EasyOCR downloads language models on first use. This is normal and only happens once.

### Permission denied errors on uploads

Ensure the `uploads/` directory exists and is writable:
```bash
mkdir -p uploads
chmod 755 uploads  # macOS/Linux only
```

## License

MIT
