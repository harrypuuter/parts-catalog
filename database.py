"""Database setup and helper functions for Parts Catalog."""

import sqlite3
from datetime import datetime
from contextlib import contextmanager

DATABASE = 'parts_catalog.db'


@contextmanager
def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with schema."""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                description TEXT,
                shelf TEXT NOT NULL,
                section INTEGER,
                photo_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


# CRUD Operations

def add_item(code, description, shelf, section, photo_filename=None):
    """Add a new item to the catalog."""
    with get_db() as conn:
        cursor = conn.execute(
            '''INSERT INTO items (code, description, shelf, section, photo_filename)
               VALUES (?, ?, ?, ?, ?)''',
            (code, description, shelf, section, photo_filename)
        )
        conn.commit()
        return cursor.lastrowid


def get_item(item_id):
    """Get a single item by ID."""
    with get_db() as conn:
        item = conn.execute(
            'SELECT * FROM items WHERE id = ?', (item_id,)
        ).fetchone()
        return dict(item) if item else None


def update_item(item_id, code, description, shelf, section, photo_filename=None):
    """Update an existing item."""
    with get_db() as conn:
        if photo_filename:
            conn.execute(
                '''UPDATE items
                   SET code = ?, description = ?, shelf = ?, section = ?, photo_filename = ?
                   WHERE id = ?''',
                (code, description, shelf, section, photo_filename, item_id)
            )
        else:
            conn.execute(
                '''UPDATE items
                   SET code = ?, description = ?, shelf = ?, section = ?
                   WHERE id = ?''',
                (code, description, shelf, section, item_id)
            )
        conn.commit()


def delete_item(item_id):
    """Delete an item by ID."""
    with get_db() as conn:
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()


def search_items(query):
    """Search items by code or description."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT * FROM items
               WHERE code LIKE ? OR description LIKE ?
               ORDER BY created_at DESC''',
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        return [dict(item) for item in items]


def get_all_items():
    """Get all items."""
    with get_db() as conn:
        items = conn.execute(
            'SELECT * FROM items ORDER BY shelf, section, created_at DESC'
        ).fetchall()
        return [dict(item) for item in items]


def get_items_by_shelf(shelf):
    """Get all items on a specific shelf."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT * FROM items
               WHERE shelf = ?
               ORDER BY section, created_at DESC''',
            (shelf,)
        ).fetchall()
        return [dict(item) for item in items]


def get_shelf_summary():
    """Get summary of items per shelf with counts."""
    with get_db() as conn:
        shelves = conn.execute(
            '''SELECT shelf, COUNT(*) as item_count
               FROM items
               GROUP BY shelf
               ORDER BY shelf'''
        ).fetchall()
        return [dict(shelf) for shelf in shelves]


def get_all_shelves():
    """Get list of all unique shelf names."""
    with get_db() as conn:
        shelves = conn.execute(
            'SELECT DISTINCT shelf FROM items ORDER BY shelf'
        ).fetchall()
        return [row['shelf'] for row in shelves]
