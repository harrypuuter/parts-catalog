"""Parts Catalog Flask Application."""

import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename

import database as db
import ocr

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Shelf overview (home page)."""
    shelves = db.get_shelf_summary()
    return render_template('index.html', shelves=shelves)


@app.route('/add', methods=['GET', 'POST'])
def add_item():
    """Add a new item."""
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()
        shelf = request.form.get('shelf', '').strip()
        section = request.form.get('section', type=int)

        if not code or not shelf:
            flash('Code and shelf are required.', 'error')
            return render_template('add_item.html')

        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid collisions
                import time
                filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_filename = filename

        item_id = db.add_item(code, description, shelf, section, photo_filename)
        flash('Item added successfully!', 'success')
        return redirect(url_for('item_detail', item_id=item_id))

    return render_template('add_item.html')


@app.route('/search')
def search():
    """Search items."""
    query = request.args.get('q', '').strip()
    items = []
    if query:
        items = db.search_items(query)
    return render_template('search.html', query=query, items=items)


@app.route('/item/<int:item_id>')
def item_detail(item_id):
    """View single item details."""
    item = db.get_item(item_id)
    if not item:
        flash('Item not found.', 'error')
        return redirect(url_for('index'))
    return render_template('item_detail.html', item=item)


@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def edit_item(item_id):
    """Edit an item."""
    item = db.get_item(item_id)
    if not item:
        flash('Item not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()
        shelf = request.form.get('shelf', '').strip()
        section = request.form.get('section', type=int)

        if not code or not shelf:
            flash('Code and shelf are required.', 'error')
            return render_template('add_item.html', item=item, edit_mode=True)

        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_filename = filename
                # Delete old photo if exists
                if item['photo_filename']:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], item['photo_filename'])
                    if os.path.exists(old_path):
                        os.remove(old_path)

        db.update_item(item_id, code, description, shelf, section, photo_filename)
        flash('Item updated successfully!', 'success')
        return redirect(url_for('item_detail', item_id=item_id))

    return render_template('add_item.html', item=item, edit_mode=True)


@app.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    """Delete an item."""
    item = db.get_item(item_id)
    if item:
        # Delete photo file if exists
        if item['photo_filename']:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], item['photo_filename'])
            if os.path.exists(photo_path):
                os.remove(photo_path)
        db.delete_item(item_id)
        flash('Item deleted.', 'success')
    return redirect(url_for('index'))


@app.route('/shelf/<name>')
def shelf_view(name):
    """View items on a specific shelf."""
    items = db.get_items_by_shelf(name)
    return render_template('shelf_view.html', shelf=name, items=items)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/ocr', methods=['POST'])
def ocr_extract():
    """Extract and categorize text from uploaded image using OCR."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if not file or not file.filename:
        return jsonify({'error': 'No image provided'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        file.save(tmp.name)
        try:
            results = ocr.extract_and_categorize(tmp.name)
            return jsonify(results)
        finally:
            os.unlink(tmp.name)


if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    # Initialize database
    db.init_db()
    # Run app (port 5001 to avoid macOS AirPlay conflict on 5000)
    app.run(debug=False, port=5001)
