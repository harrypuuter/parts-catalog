"""Database setup and helper functions for Parts Catalog."""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DATABASE = 'parts_catalog.db'


@contextmanager
def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with new multi-location schema."""
    with get_db() as conn:
        # Master item record (one per unique part code)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE COLLATE NOCASE,
                description TEXT,
                photo_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Location-quantity pairs (multiple per item)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS item_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                shelf TEXT NOT NULL,
                section INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, shelf, section)
            )
        ''')

        # Audit log
        conn.execute('''
            CREATE TABLE IF NOT EXISTS item_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                shelf TEXT,
                section INTEGER,
                quantity_before INTEGER,
                quantity_after INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()


def migrate_db():
    """Migrate from old schema to new multi-location schema.

    Per plan decision: Start fresh (delete existing database).
    """
    if os.path.exists(DATABASE):
        # Back up existing database
        backup_name = f"{DATABASE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(DATABASE, backup_name)
        print(f"Old database backed up to: {backup_name}")

    # Initialize new schema
    init_db()
    print("New database schema created.")


# ============ Item CRUD Operations ============

def get_item_by_code(code):
    """Get an item by its code (case-insensitive)."""
    with get_db() as conn:
        item = conn.execute(
            'SELECT * FROM items WHERE code = ? COLLATE NOCASE',
            (code,)
        ).fetchone()
        return dict(item) if item else None


def add_item(code, description, shelf, section, quantity=1, photo_filename=None):
    """Add a new item with its first location.

    Returns the new item ID.
    """
    with get_db() as conn:
        now = datetime.now().isoformat()

        # Create item record
        cursor = conn.execute(
            '''INSERT INTO items (code, description, photo_filename, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)''',
            (code, description, photo_filename, now, now)
        )
        item_id = cursor.lastrowid

        # Add first location
        conn.execute(
            '''INSERT INTO item_locations (item_id, shelf, section, quantity, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (item_id, shelf, section, quantity, now, now)
        )

        # Log creation
        conn.execute(
            '''INSERT INTO item_history (item_id, action, shelf, section, quantity_after, created_at)
               VALUES (?, 'created', ?, ?, ?, ?)''',
            (item_id, shelf, section, quantity, now)
        )

        conn.commit()
        return item_id


def get_item(item_id):
    """Get a single item by ID (basic info only)."""
    with get_db() as conn:
        item = conn.execute(
            'SELECT * FROM items WHERE id = ?', (item_id,)
        ).fetchone()
        return dict(item) if item else None


def get_item_with_locations(item_id):
    """Get item with all its locations and total quantity."""
    with get_db() as conn:
        # Get item
        item = conn.execute(
            'SELECT * FROM items WHERE id = ?', (item_id,)
        ).fetchone()

        if not item:
            return None

        item_dict = dict(item)

        # Get locations
        locations = conn.execute(
            '''SELECT * FROM item_locations
               WHERE item_id = ?
               ORDER BY shelf, section''',
            (item_id,)
        ).fetchall()

        item_dict['locations'] = [dict(loc) for loc in locations]
        item_dict['total_quantity'] = sum(loc['quantity'] for loc in locations)

        return item_dict


def update_item(item_id, code=None, description=None, photo_filename=None):
    """Update item master data (not locations)."""
    with get_db() as conn:
        now = datetime.now().isoformat()

        # Build update query dynamically
        updates = ['updated_at = ?']
        params = [now]

        if code is not None:
            updates.append('code = ?')
            params.append(code)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if photo_filename is not None:
            updates.append('photo_filename = ?')
            params.append(photo_filename)

        params.append(item_id)

        conn.execute(
            f'''UPDATE items SET {', '.join(updates)} WHERE id = ?''',
            params
        )
        conn.commit()


def delete_item(item_id):
    """Delete an item and all its locations/history (via CASCADE)."""
    with get_db() as conn:
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()


# ============ Location Operations ============

def add_location(item_id, shelf, section, quantity=1):
    """Add a new location to an existing item, or merge quantity if location exists.

    Returns the location ID.
    """
    with get_db() as conn:
        now = datetime.now().isoformat()

        # Check if location already exists
        existing = conn.execute(
            '''SELECT id, quantity FROM item_locations
               WHERE item_id = ? AND shelf = ? AND section = ?''',
            (item_id, shelf, section)
        ).fetchone()

        if existing:
            # Merge: add to existing quantity
            new_qty = existing['quantity'] + quantity
            conn.execute(
                '''UPDATE item_locations
                   SET quantity = ?, updated_at = ?
                   WHERE id = ?''',
                (new_qty, now, existing['id'])
            )

            # Log quantity change
            conn.execute(
                '''INSERT INTO item_history
                   (item_id, action, shelf, section, quantity_before, quantity_after, created_at)
                   VALUES (?, 'quantity_changed', ?, ?, ?, ?, ?)''',
                (item_id, shelf, section, existing['quantity'], new_qty, now)
            )

            conn.commit()
            return existing['id']
        else:
            # Create new location
            cursor = conn.execute(
                '''INSERT INTO item_locations (item_id, shelf, section, quantity, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (item_id, shelf, section, quantity, now, now)
            )

            # Log location added
            conn.execute(
                '''INSERT INTO item_history
                   (item_id, action, shelf, section, quantity_after, created_at)
                   VALUES (?, 'location_added', ?, ?, ?, ?)''',
                (item_id, shelf, section, quantity, now)
            )

            conn.commit()
            return cursor.lastrowid


def get_location(location_id):
    """Get a single location by ID."""
    with get_db() as conn:
        loc = conn.execute(
            'SELECT * FROM item_locations WHERE id = ?', (location_id,)
        ).fetchone()
        return dict(loc) if loc else None


def update_location_quantity(item_id, shelf, section, new_quantity):
    """Set the quantity at a specific location."""
    with get_db() as conn:
        now = datetime.now().isoformat()

        # Get current quantity
        current = conn.execute(
            '''SELECT quantity FROM item_locations
               WHERE item_id = ? AND shelf = ? AND section = ?''',
            (item_id, shelf, section)
        ).fetchone()

        if not current:
            return False

        old_qty = current['quantity']

        conn.execute(
            '''UPDATE item_locations
               SET quantity = ?, updated_at = ?
               WHERE item_id = ? AND shelf = ? AND section = ?''',
            (new_quantity, now, item_id, shelf, section)
        )

        # Log quantity change
        conn.execute(
            '''INSERT INTO item_history
               (item_id, action, shelf, section, quantity_before, quantity_after, created_at)
               VALUES (?, 'quantity_changed', ?, ?, ?, ?, ?)''',
            (item_id, shelf, section, old_qty, new_quantity, now)
        )

        conn.commit()
        return True


def use_item(item_id, shelf, section, quantity_used):
    """Reduce quantity at a location (for item withdrawal).

    Returns (success, message) tuple.
    """
    with get_db() as conn:
        now = datetime.now().isoformat()

        # Get current quantity
        current = conn.execute(
            '''SELECT quantity FROM item_locations
               WHERE item_id = ? AND shelf = ? AND section = ?''',
            (item_id, shelf, section)
        ).fetchone()

        if not current:
            return (False, "Lagerort nicht gefunden")

        old_qty = current['quantity']

        if quantity_used > old_qty:
            return (False, f"Nur {old_qty} verfügbar")

        new_qty = old_qty - quantity_used

        conn.execute(
            '''UPDATE item_locations
               SET quantity = ?, updated_at = ?
               WHERE item_id = ? AND shelf = ? AND section = ?''',
            (new_qty, now, item_id, shelf, section)
        )

        # Log item used
        conn.execute(
            '''INSERT INTO item_history
               (item_id, action, shelf, section, quantity_before, quantity_after, created_at)
               VALUES (?, 'item_used', ?, ?, ?, ?, ?)''',
            (item_id, shelf, section, old_qty, new_qty, now)
        )

        conn.commit()
        return (True, f"{quantity_used}x entnommen")


def delete_location(location_id):
    """Delete a specific location."""
    with get_db() as conn:
        conn.execute('DELETE FROM item_locations WHERE id = ?', (location_id,))
        conn.commit()


# ============ History Operations ============

def add_history_entry(item_id, action, shelf=None, section=None,
                      quantity_before=None, quantity_after=None):
    """Add a history entry for an item."""
    with get_db() as conn:
        now = datetime.now().isoformat()
        conn.execute(
            '''INSERT INTO item_history
               (item_id, action, shelf, section, quantity_before, quantity_after, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (item_id, action, shelf, section, quantity_before, quantity_after, now)
        )
        conn.commit()


def get_item_history(item_id):
    """Get history entries for an item, newest first."""
    with get_db() as conn:
        history = conn.execute(
            '''SELECT * FROM item_history
               WHERE item_id = ?
               ORDER BY created_at DESC''',
            (item_id,)
        ).fetchall()
        return [dict(h) for h in history]


# ============ Search and List Operations ============

def search_items(query):
    """Search items by code or description, with location/quantity info."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT i.*,
                      COALESCE(SUM(l.quantity), 0) as total_quantity,
                      COUNT(l.id) as location_count
               FROM items i
               LEFT JOIN item_locations l ON i.id = l.item_id
               WHERE i.code LIKE ? OR i.description LIKE ?
               GROUP BY i.id
               ORDER BY i.created_at DESC''',
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        return [dict(item) for item in items]


def get_all_items():
    """Get all items with total quantities."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT i.*,
                      COALESCE(SUM(l.quantity), 0) as total_quantity,
                      COUNT(l.id) as location_count
               FROM items i
               LEFT JOIN item_locations l ON i.id = l.item_id
               GROUP BY i.id
               ORDER BY i.code'''
        ).fetchall()
        return [dict(item) for item in items]


def get_items_by_shelf(shelf):
    """Get all items that have at least one location on a specific shelf."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT i.*,
                      SUM(CASE WHEN l.shelf = ? THEN l.quantity ELSE 0 END) as shelf_quantity,
                      COALESCE(SUM(l.quantity), 0) as total_quantity,
                      GROUP_CONCAT(DISTINCT l.section) as sections
               FROM items i
               JOIN item_locations l ON i.id = l.item_id
               WHERE l.shelf = ?
               GROUP BY i.id
               ORDER BY MIN(l.section), i.code''',
            (shelf, shelf)
        ).fetchall()
        return [dict(item) for item in items]


def get_shelf_summary():
    """Get summary of items per shelf with total quantities."""
    with get_db() as conn:
        shelves = conn.execute(
            '''SELECT shelf,
                      COUNT(DISTINCT item_id) as item_count,
                      SUM(quantity) as total_quantity
               FROM item_locations
               GROUP BY shelf
               ORDER BY shelf'''
        ).fetchall()
        return [dict(shelf) for shelf in shelves]


def get_all_shelves():
    """Get list of all unique shelf names."""
    with get_db() as conn:
        shelves = conn.execute(
            'SELECT DISTINCT shelf FROM item_locations ORDER BY shelf'
        ).fetchall()
        return [row['shelf'] for row in shelves]


def get_printable_list():
    """Get all items sorted by shelf, then by part code for printing."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT i.code, i.description,
                      l.shelf, l.section, l.quantity
               FROM items i
               JOIN item_locations l ON i.id = l.item_id
               ORDER BY l.shelf, i.code COLLATE NOCASE, l.section'''
        ).fetchall()
        return [dict(item) for item in items]


def get_inventory_list():
    """Get full inventory sorted by part code (alphabetically)."""
    with get_db() as conn:
        items = conn.execute(
            '''SELECT i.code, i.description,
                      l.shelf, l.section, l.quantity
               FROM items i
               JOIN item_locations l ON i.id = l.item_id
               ORDER BY i.code COLLATE NOCASE, l.shelf, l.section'''
        ).fetchall()
        return [dict(item) for item in items]
