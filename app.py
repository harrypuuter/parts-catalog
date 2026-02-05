"""Parts Catalog Flask Application."""

import io
import os
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename
from fpdf import FPDF
from fpdf.enums import XPos, YPos

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
    """Add a new item or add location to existing item."""
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()
        shelf = request.form.get('shelf', '').strip()
        section = request.form.get('section', type=int)
        quantity = request.form.get('quantity', 1, type=int)
        existing_item_id = request.form.get('existing_item_id', type=int)

        # Validate required fields
        if not code or not shelf or not section:
            flash('Teilenummer, Regal und Fach sind erforderlich.', 'error')
            return render_template('add_item.html')

        if quantity < 1:
            quantity = 1

        # Handle photo upload
        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_filename = filename

        # Check if adding to existing item
        if existing_item_id:
            # Add location to existing item
            db.add_location(existing_item_id, shelf, section, quantity)
            flash(f'Lagerort zu bestehendem Teil hinzugefügt!', 'success')
            return redirect(url_for('item_detail', item_id=existing_item_id))

        # Check for duplicate code
        existing = db.get_item_by_code(code)
        if existing:
            # Redirect back with existing item info for user to confirm
            flash('Teil mit dieser Nummer existiert bereits. Lagerort hinzufügen?', 'warning')
            return render_template('add_item.html',
                                   existing_item=db.get_item_with_locations(existing['id']),
                                   code=code, description=description,
                                   shelf=shelf, section=section, quantity=quantity)

        # Create new item
        item_id = db.add_item(code, description, shelf, section, quantity, photo_filename)
        flash('Teil erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('item_detail', item_id=item_id))

    return render_template('add_item.html')


@app.route('/api/check-code')
def check_code():
    """AJAX endpoint to check if a code already exists."""
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'exists': False})

    existing = db.get_item_by_code(code)
    if existing:
        item_with_locations = db.get_item_with_locations(existing['id'])
        return jsonify({
            'exists': True,
            'item': item_with_locations
        })
    return jsonify({'exists': False})


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
    """View single item details with all locations."""
    item = db.get_item_with_locations(item_id)
    if not item:
        flash('Teil nicht gefunden.', 'error')
        return redirect(url_for('index'))

    history = db.get_item_history(item_id)
    return render_template('item_detail.html', item=item, history=history)


@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def edit_item(item_id):
    """Edit an item's master data."""
    item = db.get_item_with_locations(item_id)
    if not item:
        flash('Teil nicht gefunden.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()

        if not code:
            flash('Teilenummer ist erforderlich.', 'error')
            return render_template('edit_item.html', item=item)

        # Check if new code conflicts with another item
        existing = db.get_item_by_code(code)
        if existing and existing['id'] != item_id:
            flash('Ein anderes Teil mit dieser Nummer existiert bereits.', 'error')
            return render_template('edit_item.html', item=item)

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

        db.update_item(item_id, code=code, description=description, photo_filename=photo_filename)
        flash('Teil erfolgreich aktualisiert!', 'success')
        return redirect(url_for('item_detail', item_id=item_id))

    return render_template('edit_item.html', item=item)


@app.route('/item/<int:item_id>/add-location', methods=['POST'])
def add_location(item_id):
    """Add a new location to an existing item."""
    item = db.get_item(item_id)
    if not item:
        flash('Teil nicht gefunden.', 'error')
        return redirect(url_for('index'))

    shelf = request.form.get('shelf', '').strip()
    section = request.form.get('section', type=int)
    quantity = request.form.get('quantity', 1, type=int)

    if not shelf or not section:
        flash('Regal und Fach sind erforderlich.', 'error')
        return redirect(url_for('item_detail', item_id=item_id))

    if quantity < 1:
        quantity = 1

    db.add_location(item_id, shelf, section, quantity)
    flash(f'Lagerort hinzugefügt: Regal {shelf}, Fach {section} ({quantity}x)', 'success')
    return redirect(url_for('item_detail', item_id=item_id))


@app.route('/item/<int:item_id>/use', methods=['POST'])
def use_item(item_id):
    """Reduce quantity at a location (item withdrawal)."""
    item = db.get_item(item_id)
    if not item:
        flash('Teil nicht gefunden.', 'error')
        return redirect(url_for('index'))

    shelf = request.form.get('shelf', '').strip()
    section = request.form.get('section', type=int)
    quantity = request.form.get('quantity', 1, type=int)

    if not shelf or not section or quantity < 1:
        flash('Ungültige Eingabe.', 'error')
        return redirect(url_for('item_detail', item_id=item_id))

    success, message = db.use_item(item_id, shelf, section, quantity)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('item_detail', item_id=item_id))


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
        flash('Teil gelöscht.', 'success')
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


@app.route('/print')
def print_list():
    """Generate PDF part list sorted by shelf, then by part code."""
    items = db.get_printable_list()

    # Group by shelf
    shelves = {}
    for item in items:
        shelf = item['shelf']
        if shelf not in shelves:
            shelves[shelf] = []
        shelves[shelf].append(item)

    # Create PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Use built-in font with Latin-1 encoding for German characters
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Teileliste', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Stand: {datetime.now().strftime("%d.%m.%Y %H:%M")}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Table settings
    col_widths = [50, 80, 20, 20]  # Code, Description, Section, Qty
    row_height = 7

    for shelf_name in sorted(shelves.keys()):
        shelf_items = shelves[shelf_name]

        # Check if we need a new page (header + at least a few rows)
        if pdf.get_y() > 250:
            pdf.add_page()

        # Shelf header
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f'  Regal {shelf_name}', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

        # Table header
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(236, 240, 241)
        pdf.cell(col_widths[0], row_height, 'Teilenummer', border=1, fill=True)
        pdf.cell(col_widths[1], row_height, 'Beschreibung', border=1, fill=True)
        pdf.cell(col_widths[2], row_height, 'Fach', border=1, align='C', fill=True)
        pdf.cell(col_widths[3], row_height, 'Menge', border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Table rows
        pdf.set_font('Helvetica', '', 9)
        for item in shelf_items:
            # Check for page break
            if pdf.get_y() > 270:
                pdf.add_page()
                # Repeat shelf and table header on new page
                pdf.set_font('Helvetica', 'B', 12)
                pdf.set_fill_color(44, 62, 80)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 8, f'  Regal {shelf_name} (Fortsetzung)', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(236, 240, 241)
                pdf.cell(col_widths[0], row_height, 'Teilenummer', border=1, fill=True)
                pdf.cell(col_widths[1], row_height, 'Beschreibung', border=1, fill=True)
                pdf.cell(col_widths[2], row_height, 'Fach', border=1, align='C', fill=True)
                pdf.cell(col_widths[3], row_height, 'Menge', border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font('Helvetica', '', 9)

            # Truncate long text and handle encoding
            code = str(item['code'])[:25]
            desc = str(item['description'] or '-')[:40]

            pdf.cell(col_widths[0], row_height, code, border=1)
            pdf.cell(col_widths[1], row_height, desc, border=1)
            pdf.cell(col_widths[2], row_height, str(item['section']), border=1, align='C')
            pdf.cell(col_widths[3], row_height, str(item['quantity']), border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(3)

    # Output PDF
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)

    filename = f'teileliste_regal_{datetime.now().strftime("%Y%m%d")}.pdf'
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@app.route('/print/inventory')
def print_inventory():
    """Generate PDF inventory list sorted alphabetically by part code."""
    items = db.get_inventory_list()

    # Create PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Inventarliste', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Stand: {datetime.now().strftime("%d.%m.%Y %H:%M")}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Table settings
    col_widths = [40, 70, 25, 20, 20]  # Code, Description, Shelf, Section, Qty
    row_height = 7

    # Table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_widths[0], row_height, 'Teilenummer', border=1, fill=True)
    pdf.cell(col_widths[1], row_height, 'Beschreibung', border=1, fill=True)
    pdf.cell(col_widths[2], row_height, 'Regal', border=1, align='C', fill=True)
    pdf.cell(col_widths[3], row_height, 'Fach', border=1, align='C', fill=True)
    pdf.cell(col_widths[4], row_height, 'Menge', border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    # Table rows
    pdf.set_font('Helvetica', '', 9)
    current_code = None
    for item in items:
        # Check for page break
        if pdf.get_y() > 270:
            pdf.add_page()
            # Repeat table header on new page
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(44, 62, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(col_widths[0], row_height, 'Teilenummer', border=1, fill=True)
            pdf.cell(col_widths[1], row_height, 'Beschreibung', border=1, fill=True)
            pdf.cell(col_widths[2], row_height, 'Regal', border=1, align='C', fill=True)
            pdf.cell(col_widths[3], row_height, 'Fach', border=1, align='C', fill=True)
            pdf.cell(col_widths[4], row_height, 'Menge', border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 9)

        # Alternate row color for same part with multiple locations
        if item['code'] != current_code:
            current_code = item['code']
            pdf.set_fill_color(255, 255, 255)
        else:
            pdf.set_fill_color(248, 249, 250)

        code = str(item['code'])[:20]
        desc = str(item['description'] or '-')[:35]

        pdf.cell(col_widths[0], row_height, code, border=1, fill=True)
        pdf.cell(col_widths[1], row_height, desc, border=1, fill=True)
        pdf.cell(col_widths[2], row_height, str(item['shelf']), border=1, align='C', fill=True)
        pdf.cell(col_widths[3], row_height, str(item['section']), border=1, align='C', fill=True)
        pdf.cell(col_widths[4], row_height, str(item['quantity']), border=1, align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Output PDF
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)

    filename = f'inventar_{datetime.now().strftime("%Y%m%d")}.pdf'
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


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
