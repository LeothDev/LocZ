from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import pandas as pd
import tempfile
from datetime import datetime
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import threading
import time
from sentence_transformers import SentenceTransformer
import re


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1000GB max file size

similarity_model = None
processing_threads = {}

def get_similarity_model():
    global similarity_model
    if similarity_model is None:
        try:
            similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Sentence Transformer model loaded")
        except Exception as e:
            print(f"❌ Could not load Sentence Transformer: {e}")
            similarity_model = False
    return similarity_model if similarity_model else None

def process_embeddings_background(session_id):
    """Background task to compute embeddings for similarity search"""
    try:
        print(f"🚀 Starting embedding processing for session {session_id}")
        
        conn = sqlite3.connect('translations.db')
        cursor = conn.cursor()
        
        # Get all translations for this session
        cursor.execute('''
            SELECT str_id, en_text, it_text 
            FROM translations 
            WHERE upload_session = ?
        ''', (session_id,))
        
        rows = cursor.fetchall()
        total = len(rows)
        
        if total == 0:
            conn.close()
            return
        
        # Initialize processing status
        cursor.execute('''
            INSERT OR REPLACE INTO processing_status 
            (session_id, total_strings, processed_strings, is_complete)
            VALUES (?, ?, 0, 0)
        ''', (session_id, total))
        conn.commit()
        
        # Clear old embeddings for this session
        cursor.execute('DELETE FROM embeddings WHERE upload_session = ?', (session_id,))
        conn.commit()
        
        # Load the model
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Sentence Transformer model loaded")
        except Exception as e:
            print(f"❌ Could not load model: {e}")
            # Mark as complete even if failed
            cursor.execute('''
                UPDATE processing_status 
                SET is_complete = 1, processed_strings = total_strings
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()
            conn.close()
            return
        
        # Process in batches
        batch_size = 150
        processed = 0
        
        for i in range(0, total, batch_size):
            batch = rows[i:i+batch_size]
            
            # Prepare texts for embedding
            texts = []
            batch_data = []
            
            for str_id, en_text, it_text in batch:
                # I don't want embedding of combined text, only English for simplicity
                # combined_text = f"{en_text or ''} {it_text or ''}".strip()
                combined_text = (en_text or '').strip()
                texts.append(combined_text)
                batch_data.append((str_id, combined_text))
            
            # Compute embeddings for this batch
            embeddings = model.encode(texts, show_progress_bar=False)
            
            # Store embeddings in database
            for j, (str_id, text) in enumerate(batch_data):
                embedding_blob = embeddings[j].tobytes()
                cursor.execute('''
                    INSERT INTO embeddings (str_id, embedding, upload_session)
                    VALUES (?, ?, ?)
                ''', (str_id, embedding_blob, session_id))
            
            processed += len(batch)

            # MEMORY CLEANUP
            del embeddings
            del texts
            import gc
            gc.collect()
            
            # Update progress
            cursor.execute('''
                UPDATE processing_status 
                SET processed_strings = ?
                WHERE session_id = ?
            ''', (processed, session_id))
            conn.commit()
            
            print(f"📊 Processed {processed}/{total} embeddings ({processed/total*100:.1f}%)")
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.1)
        
        # Mark as complete
        cursor.execute('''
            UPDATE processing_status 
            SET is_complete = 1
            WHERE session_id = ?
        ''', (session_id,))
        conn.commit()
        
        print(f"✅ Embedding processing complete for session {session_id}")
        conn.close()
        
    except Exception as e:
        print(f"❌ Embedding processing failed: {e}")
        # Mark as complete even if failed
        try:
            conn = sqlite3.connect('translations.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_status 
                SET is_complete = 1
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()
            conn.close()
        except:
            pass
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
    
    # Similarity cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS similarity_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            str_id TEXT,
            similar_ids TEXT,
            upload_session TEXT
        )
    ''')

    cursor.execute('''
      CREATE TABLE IF NOT EXISTS embeddings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          str_id TEXT NOT NULL,
          embedding BLOB,
          upload_session TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )  
    ''')

    cursor.execute('''
       CREATE TABLE IF NOT EXISTS processing_status (
           session_id TEXT PRIMARY KEY,
           total_strings INTEGER,
           processed_strings INTEGER,
           is_complete INTEGER DEFAULT 0,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       ) 
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/similarity_status')
def get_similarity_status():
    # Get the most recent session (you could make this more sophisticated)
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_id, total_strings, processed_strings, is_complete
        FROM processing_status 
        ORDER BY created_at DESC 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    
    if not result:
        return jsonify({'complete': False, 'processed': 0, 'total': 0, 'percentage': 0})
    
    session_id, total, processed, is_complete = result
    percentage = int((processed / total) * 100) if total > 0 else 0

    cursor.execute('SELECT COUNT(*) FROM embeddings')
    embeddings_count = cursor.fetchone()[0]
    
    conn.close()

    return jsonify({
        'complete': bool(is_complete),
        'embeddings_exist': embeddings_count > 0,
        'total': total,
        'processed': processed,
        'percentage': percentage,
        'total_processed': embeddings_count
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
        
        # Expected columns: strID, EN, IT (adjust as needed)
        # required_cols = ['strId', 'EN', 'IT']
        print(df.columns)
        # required_cols = ['strId', 'EN', 'German']
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
        
        # Start background TF-IDF processing
        compute_similarities(session_id)

        # START BACKGROUND EMBEDDING PROCESSING FOR FASTER SIMILARITY SEARCH
        thread = threading.Thread(target=process_embeddings_background, args=(session_id,))
        thread.daemon = True
        thread.start()
        processing_threads[session_id] = thread
        
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

    similarity_search = request.args.get('similarity_search', '')
    
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

    if similarity_search:
        # Get similar string IDs using your existing TF-IDF
        similar_ids = get_similar_strings_fast(similarity_search)
        if similar_ids:
            placeholders = ','.join(['?' for _ in similar_ids])
            where_clause += f" AND str_id IN ({placeholders})"
            params.extend(similar_ids)
    
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

@app.route('/api/similar/<str_id>')
def get_similar(str_id):
    conn = sqlite3.connect('translations.db')
    cursor = conn.cursor()
    
    # Get cached similarities
    cursor.execute('SELECT similar_ids FROM similarity_cache WHERE str_id = ?', (str_id,))
    result = cursor.fetchone()
    
    if result:
        similar_ids = json.loads(result[0])
        
        # Get the actual translations
        if similar_ids:
            placeholders = ','.join(['?' for _ in similar_ids])
            cursor.execute(f'''
                SELECT str_id, en_text, it_text 
                FROM translations 
                WHERE str_id IN ({placeholders})
                LIMIT 10
            ''', similar_ids)
            
            similar_translations = cursor.fetchall()
            conn.close()
            
            return jsonify([{
                'str_id': row[0],
                'en_text': row[1],
                'it_text': row[2]
            } for row in similar_translations])
    
    conn.close()
    return jsonify([])

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

def get_similar_strings_fast(search_text, threshold=0.4, max_results=300):
    """Fast similarity search using pre-computed embeddings"""
    try:
        conn = sqlite3.connect('translations.db')
        cursor = conn.cursor()
        
        # Check if embeddings are ready
        cursor.execute('SELECT COUNT(*) FROM processing_status WHERE is_complete = 1')
        if cursor.fetchone()[0] == 0:
            conn.close()
            return []
        
        # Get all embeddings
        cursor.execute('''
            SELECT e.str_id, e.embedding, t.en_text, t.it_text
            FROM embeddings e
            JOIN translations t ON e.str_id = t.str_id
        ''')
        
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return []
        
        # Load the model for search embedding
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        search_embedding = model.encode([search_text], show_progress_bar=False)[0]
        
        matches = {}
        search_lower = search_text.lower()
        
        for str_id, embedding_blob, en_text, it_text in rows:
            # combined_text = f"{en_text or ''} {it_text or ''}".strip()
            combined_text = (en_text or '').strip()
            text_lower = combined_text.lower()
            
            # 1. Exact/substring matching (highest priority)
            if search_lower == text_lower:
                matches[str_id] = (1.0, "exact")
                continue
            elif search_lower in text_lower:
                score = 0.95 + (len(search_text) / len(combined_text)) * 0.04
                matches[str_id] = (score, "contains")
                continue
            
            # 2. Semantic similarity using cached embeddings
            stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            similarity = np.dot(search_embedding, stored_embedding)
            
            if similarity > threshold:
                score = 0.20 + similarity * 0.69
                matches[str_id] = (score, f"semantic_{similarity:.2f}")
        
        # Sort by score and return
        sorted_matches = sorted(matches.items(), key=lambda x: x[1][0], reverse=True)
        result_ids = [str_id for str_id, (score, match_type) in sorted_matches[:max_results]]
        
        print(f"✅ Found {len(result_ids)} matches using fast cached search")
        conn.close()
        return result_ids
        
    except Exception as e:
        print(f"❌ Fast similarity search error: {e}")
        return []        

def compute_similarities(session_id):
    """Background task to compute TF-IDF similarities"""
    try:
        conn = sqlite3.connect('translations.db')
        
        # Get all English texts
        df = pd.read_sql_query('''
            SELECT str_id, en_text 
            FROM translations 
            WHERE upload_session = ? AND en_text != ''
        ''', conn, params=(session_id,))
        
        if len(df) < 2:
            conn.close()
            return
        
        # Compute TF-IDF
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(df['en_text'].fillna(''))
        
        # Compute similarities
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        cursor = conn.cursor()
        
        # Store top 5 similar strings for each string
        for i, str_id in enumerate(df['str_id']):
            similarities = similarity_matrix[i]
            # Get indices of most similar (excluding self)
            similar_indices = np.argsort(similarities)[::-1][1:6]  # Top 5, excluding self
            similar_str_ids = [df.iloc[j]['str_id'] for j in similar_indices if similarities[j] > 0.3]
            
            cursor.execute('''
                INSERT INTO similarity_cache (str_id, similar_ids, upload_session)
                VALUES (?, ?, ?)
            ''', (str_id, json.dumps(similar_str_ids), session_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error computing similarities: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
