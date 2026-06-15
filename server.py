import os
import sqlite3
import math
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baby_tracker.db')

def calculate_interval_text(current_ts_str, prev_ts_str):
    try:
        t1 = datetime.strptime(current_ts_str, '%Y-%m-%d %H:%M:%S')
        t2 = datetime.strptime(prev_ts_str, '%Y-%m-%d %H:%M:%S')
        diff = t1 - t2
        diff_seconds = int(diff.total_seconds())
        if diff_seconds < 0:
            return None
        
        diff_minutes = diff_seconds // 60
        if diff_minutes < 60:
            return f"{diff_minutes}分"
        
        diff_hours = diff_minutes // 60
        rem_minutes = diff_minutes % 60
        if diff_hours < 24:
            if rem_minutes == 0:
                return f"{diff_hours}小时"
            return f"{diff_hours}小时{rem_minutes}分"
            
        diff_days = diff_hours // 24
        rem_hours = diff_hours % 24
        if rem_hours == 0:
            return f"{diff_days}天"
        return f"{diff_days}天{rem_hours}小时"
    except Exception:
        return None

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Create logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            feed_type TEXT,
            feed_amount INTEGER,
            diaper_urine INTEGER DEFAULT 0,
            diaper_stool INTEGER DEFAULT 0,
            stool_color TEXT,
            stool_shape TEXT,
            diaper_change INTEGER DEFAULT 0,
            temperature REAL,
            weight REAL,
            event_name TEXT,
            signature TEXT,
            remarks TEXT
        )
        ''')
        
        # Create indexes for fast lookup and sorting
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_category_timestamp ON logs(category, timestamp)')
        
        # Insert default settings if they don't exist
        default_settings = {
            'baby_name': '宝宝',
            'birth_date': datetime.now().strftime('%Y-%m-%d')
        }
        for k, v in default_settings.items():
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))
            
        db.commit()

# Initialize database on startup
if not os.path.exists(DATABASE):
    init_db()
else:
    # Ensure tables are created just in case
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT key, value FROM settings')
    rows = cursor.fetchall()
    settings_dict = {row['key']: row['value'] for row in rows}
    
    # Add server local time components to dynamically sync timezone differences
    now = datetime.now()
    settings_dict['_server_time'] = {
        'year': now.year,
        'month': now.month,
        'day': now.day,
        'hour': now.hour,
        'minute': now.minute,
        'second': now.second
    }
    return jsonify(settings_dict)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json or {}
    db = get_db()
    cursor = db.cursor()
    for k, v in data.items():
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, str(v)))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 8))
    category = request.args.get('category', '').strip()
    date_filter = request.args.get('date', '').strip() # YYYY-MM-DD
    if page < 1:
        page = 1
    offset = (page - 1) * limit
    
    db = get_db()
    cursor = db.cursor()
    
    # Build query clauses based on category & date filters
    where_clauses = []
    params = []
    
    if category:
        where_clauses.append("category = ?")
        params.append(category)
        
    if date_filter:
        where_clauses.append("timestamp LIKE ?")
        params.append(date_filter + "%")
        
    where_str = ""
    if where_clauses:
        where_str = "WHERE " + " AND ".join(where_clauses)
        
    # Get total count
    count_query = f"SELECT COUNT(*) as count FROM logs {where_str}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()['count']
    
    # Get page logs
    log_query = f"SELECT * FROM logs {where_str} ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?"
    cursor.execute(log_query, params + [limit, offset])
    rows = cursor.fetchall()
    
    logs_list = []
    for row in rows:
        row_dict = dict(row)
        
        # Find the chronologically previous log matching the active category filter
        prev_clauses = []
        prev_params = []
        if category:
            prev_clauses.append("category = ?")
            prev_params.append(category)
        
        # We look for a log that is older: (timestamp < current_timestamp) or (timestamp == current_timestamp and id < current_id)
        prev_clauses.append("((timestamp < ?) OR (timestamp = ? AND id < ?))")
        prev_params.extend([row_dict['timestamp'], row_dict['timestamp'], row_dict['id']])
        
        prev_where = "WHERE " + " AND ".join(prev_clauses)
        prev_query = f"SELECT timestamp FROM logs {prev_where} ORDER BY timestamp DESC, id DESC LIMIT 1"
        
        cursor.execute(prev_query, prev_params)
        prev_row = cursor.fetchone()
        
        if prev_row:
            row_dict['interval_text'] = calculate_interval_text(row_dict['timestamp'], prev_row['timestamp'])
        else:
            row_dict['interval_text'] = None
            
        logs_list.append(row_dict)
        
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    # Calculate stats for the selected date (default to server local date)
    stats_date = date_filter if date_filter else datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT category, feed_type, diaper_urine, diaper_stool, temperature, weight, event_name FROM logs WHERE timestamp LIKE ?", (stats_date + '%',))
    today_rows = cursor.fetchall()
    
    stats = {
        "feed_breast": 0,
        "feed_formula": 0,
        "feed_water": 0,
        "feed_total": 0,
        "diaper_urine": 0,
        "diaper_stool": 0,
        "diaper_total": 0,
        "health_temp": 0,
        "health_weight": 0,
        "health_total": 0,
        "event_total": 0
    }
    
    for r in today_rows:
        cat = r['category']
        if cat == 'feed':
            ft = r['feed_type']
            if ft in ('breast', 'breast_ml'):
                stats['feed_breast'] += 1
            elif ft == 'formula':
                stats['feed_formula'] += 1
            elif ft == 'water':
                stats['feed_water'] += 1
            stats['feed_total'] += 1
        elif cat == 'diaper':
            if r['diaper_urine']:
                stats['diaper_urine'] += 1
            if r['diaper_stool']:
                stats['diaper_stool'] += 1
            stats['diaper_total'] += 1
        elif cat == 'health':
            if r['temperature'] is not None:
                stats['health_temp'] += 1
            if r['weight'] is not None:
                stats['health_weight'] += 1
            stats['health_total'] += 1
        elif cat == 'event':
            stats['event_total'] += 1
            
    return jsonify({
        "logs": logs_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "stats": stats
    })

@app.route('/api/logs', methods=['POST'])
def add_log():
    data = request.json or {}
    category = data.get('category')
    if not category:
        return jsonify({"success": False, "error": "Category is required"}), 400
        
    timestamp = data.get('timestamp')
    if not timestamp:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    db = get_db()
    cursor = db.cursor()
    
    # Columns to insert
    cols = [
        'timestamp', 'category', 'feed_type', 'feed_amount', 
        'diaper_urine', 'diaper_stool', 'stool_color', 'stool_shape', 
        'diaper_change', 'temperature', 'weight', 'event_name', 
        'signature', 'remarks'
    ]
    
    vals = [
        timestamp,
        category,
        data.get('feed_type'),
        data.get('feed_amount'),
        1 if data.get('diaper_urine') else 0,
        1 if data.get('diaper_stool') else 0,
        data.get('stool_color'),
        data.get('stool_shape'),
        1 if data.get('diaper_change') else 0,
        data.get('temperature'),
        data.get('weight'),
        data.get('event_name'),
        data.get('signature'),
        data.get('remarks')
    ]
    
    placeholders = ', '.join(['?'] * len(cols))
    query = f"INSERT INTO logs ({', '.join(cols)}) VALUES ({placeholders})"
    
    cursor.execute(query, vals)
    db.commit()
    
    new_id = cursor.lastrowid
    return jsonify({"success": True, "id": new_id})

@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM logs WHERE id = ?', (log_id,))
    db.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    # Run on port 5000, bind to 0.0.0.0 so other devices in LAN (like Kindle) can access it
    app.run(host='0.0.0.0', port=5000, debug=True)
