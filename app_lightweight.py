from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import pandas as pd
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1000GB max file size

# Database setup
def init_db():
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    # Main translations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            str_id TEXT NOT NULL,
            en_text TEXT,
            it_text TEXT,
            original_it_text TEXT,
            is_modified INTEGER DEFAULT 0,
            upload_session TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Similarity cache table (keeping for compatibility)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS similarity_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            str_id TEXT,
            similar_ids TEXT,
            upload_session TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def index():
    return render_template('index_lightweight.html')

@app.route('/api/similarity_status')
def get_similarity_status():
    # Always return ready since we don't need preprocessing
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM translations')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'complete': True,
        'embeddings_exist': True,
        'total': total_count,
        'processed': total_count,
        'percentage': 100,
        'total_processed': total_count
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Please upload an Excel file'}), 400
    
    try:
        # Create upload session ID
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Clear previous data
        conn = sqlite3.connect('translations.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM translations')
        cursor.execute('DELETE FROM similarity_cache')
        conn.commit()
        
        # Read Excel file
        df = pd.read_excel(file)
        
        # Expected columns
        print(df.columns)
        required_cols = ['字符串', "EN", 'Italian']
        if not all(col in df.columns for col in required_cols):
            return jsonify({'error': f'Excel must contain columns: {required_cols}'}), 400
        
        # Insert data into database
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO translations (str_id, en_text, it_text, original_it_text, upload_session)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(row['字符串']),
                str(row['EN']) if pd.notna(row['EN']) else '',
                str(row['Italian']) if pd.notna(row['Italian']) else '',
                str(row['Italian']) if pd.notna(row['Italian']) else '',
                session_id
            ))
        
        conn.commit()
        total_rows = len(df)
        
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Uploaded {total_rows} translations successfully',
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/api/translations')
def get_translations():
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 100))
    search_value = request.args.get('search[value]', '')
    show_modified = request.args.get('show_modified', 'false') == 'true'
    get_total = request.args.get('get_total', 'false') == 'true'

    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()

    if get_total:
        cursor.execute('SELECT COUNT(*) FROM translations')
        total = cursor.fetchone()[0]
        conn.close()
        return jsonify({'recordsTotal': total})
    
    # Base query
    where_clause = "WHERE 1=1"
    params = []
    
    if search_value:
        where_clause += " AND (str_id LIKE ? OR en_text LIKE ? OR it_text LIKE ?)"
        search_param = f'%{search_value}%'
        params.extend([search_param, search_param, search_param])
    
    if show_modified:
        where_clause += " AND is_modified = 1"
    
    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM translations {where_clause}", params)
    total_records = cursor.fetchone()[0]
    
    # Get paginated data
    query = f'''
        SELECT id, str_id, en_text, it_text, is_modified 
        FROM translations {where_clause}
        ORDER BY id
        LIMIT ? OFFSET ?
    '''
    params.extend([length, start])
    cursor.execute(query, params)
    
    rows = cursor.fetchall()
    conn.close()
    
    # Format for DataTables
    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'str_id': row[1],
            'en_text': row[2],
            'it_text': row[3],
            'is_modified': row[4]
        })
    
    return jsonify({
        'draw': int(request.args.get('draw', 1)),
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })

@app.route('/api/update_translation', methods=['POST'])
def update_translation():
    data = request.get_json()
    translation_id = data.get('id')
    new_text = data.get('it_text', '')
    
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    # Get original text to check if it's actually modified
    cursor.execute('SELECT original_it_text FROM translations WHERE id = ?', (translation_id,))
    original = cursor.fetchone()
    
    if original:
        is_modified = 1 if new_text != original[0] else 0
        print(f"New text: '{new_text}'")
        print(f"Original text: '{original[0]}'")
        print(f"Are they different? {new_text != original[0]}")
        print(f"is_modified: {is_modified}")
        
        cursor.execute('''
            UPDATE translations 
            SET it_text = ?, is_modified = ?
            WHERE id = ?
        ''', (new_text, is_modified, translation_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'is_modified': is_modified})
    
    conn.close()
    return jsonify({'error': 'Translation not found'}), 404

@app.route('/api/export')
def export_modified():
    conn = sqlite3.connect('translations.db')
    
    # Get only modified translations
    df = pd.read_sql_query('''
        SELECT '' as SOURCE, str_id as 字符串, en_text as EN, it_text as Italian
        FROM translations 
        WHERE is_modified = 1
        ORDER BY str_id
    ''', conn)
    
    conn.close()
    
    if df.empty:
        return jsonify({'error': 'No modified translations to export'}), 400
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp_file.name, index=False)
    temp_file.close()
    
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'modified_translations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/api/replace_all', methods=['POST'])
def replace_all():
    data = request.get_json()
    search_text = data.get('search_text', '')
    replace_text = data.get('replace_text', '')
    case_sensitive = data.get('case_sensitive', False)
    whole_word = data.get('whole_word', False)
    
    if not search_text:
        return jsonify({'error': 'Search text cannot be empty'}), 400
    
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    # Get all Italian texts
    cursor.execute('SELECT id, it_text, original_it_text FROM translations')
    rows = cursor.fetchall()
    
    updated_count = 0
    updated_ids = []

    store_undo = data.get('store_undo', False)
    undo_data = [] if store_undo else None
    
    for row_id, current_text, original_text in rows:
        if not current_text:
            continue
            
        # Perform replacement based on options
        if case_sensitive:
            if whole_word:
                import re
                pattern = r'\b' + re.escape(search_text) + r'\b'
                new_text = re.sub(pattern, replace_text, current_text)
            else:
                new_text = current_text.replace(search_text, replace_text)
        else:
            if whole_word:
                import re
                pattern = r'\b' + re.escape(search_text) + r'\b'
                new_text = re.sub(pattern, replace_text, current_text, flags=re.IGNORECASE)
            else:
                new_text = current_text.replace(search_text.lower(), replace_text)
                new_text = current_text.replace(search_text.upper(), replace_text)
                # Simple case-insensitive replace
                import re
                new_text = re.sub(re.escape(search_text), replace_text, current_text, flags=re.IGNORECASE)
        
        if new_text != current_text:
            if store_undo:
                undo_data.append({
                                     'id': row_id,
                                     'old_text': current_text,
                                     'old_is_modified': 1 if current_text != original_text else 0
                                 })
            is_modified = 1 if new_text != original_text else 0
            cursor.execute('UPDATE translations SET it_text = ?, is_modified = ? WHERE id = ?', 
                         (new_text, is_modified, row_id))
            updated_count += 1
            updated_ids.append({'id': row_id, 'new_text': new_text, 'is_modified': is_modified})
    
    conn.commit()
    conn.close()
    
    return jsonify({
                   'success': True,
                   'updated_count': updated_count,
                   'updated_rows': updated_ids,
                   'undo_data': undo_data
           })
    
@app.route('/api/undo_replace', methods=['POST'])
def undo_replace():
    data = request.get_json()
    undo_data = data.get('undo_data', [])
    store_redo = data.get('store_redo', False)
    
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    redo_data = []
    
    for item in undo_data:
        if store_redo:
            # Get current state for redo
            cursor.execute('SELECT it_text, is_modified FROM translations WHERE id = ?', (item['id'],))
            current = cursor.fetchone()
            if current:
                redo_data.append({
                    'id': item['id'],
                    'old_text': current[0],
                    'old_is_modified': current[1]
                })
        
        cursor.execute('UPDATE translations SET it_text = ?, is_modified = ? WHERE id = ?',
                      (item['old_text'], item['old_is_modified'], item['id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'redo_data': redo_data if store_redo else None
    })

if __name__ == '__main__':
    app.run(debug=False, port=5000)
