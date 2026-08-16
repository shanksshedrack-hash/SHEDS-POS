#!/usr/bin/env python3
"""
SHEDS POS - Multi-Tenant Backend API
Each pharmacy gets isolated data with an API key.
"""

import os
import json
import hashlib
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, g, send_file
from functools import wraps

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        raise ImportError('psycopg2-binary is required when using DATABASE_URL. Install it with: pip install psycopg2-binary')
else:
    import sqlite3

app = Flask(__name__)
app.config['DB_PATH'] = os.environ.get('DB_PATH', 'danzona_pos.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-set-a-real-secret-key')

# Ensure database directory exists
_db_dir = os.path.dirname(app.config['DB_PATH'])
if _db_dir and not os.path.exists(_db_dir):
    os.makedirs(_db_dir, exist_ok=True)

# ---------- Database ----------

def get_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = RealDictCursor
        return conn
    else:
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(app.config['DB_PATH'])
            db.row_factory = sqlite3.Row
        return db

@app.teardown_appcontext
def close_db(exception):
    if USE_POSTGRES:
        return
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

IntegrityError = psycopg2.IntegrityError if USE_POSTGRES else sqlite3.IntegrityError

def id_col():
    return 'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'

def init_db():
    db = get_db()
    # Pharmacies (tenants)
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS pharmacies (
            id {id_col()},
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            email TEXT,
            api_key TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Users (staff per pharmacy)
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'staff',
            store TEXT DEFAULT 'main',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pharmacy_id, username)
        )
    ''')

    db.execute(f'''
        CREATE TABLE IF NOT EXISTS categories (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(pharmacy_id, name)
        )
    ''')

    # Products per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS products (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            sku TEXT NOT NULL,
            category_id INTEGER,
            category_name TEXT DEFAULT 'Uncategorized',
            description TEXT,
            price REAL DEFAULT 0,
            cost_price REAL DEFAULT 0,
            stock REAL DEFAULT 0,
            reorder_level REAL DEFAULT 10,
            expiry TEXT,
            prices TEXT,
            default_pkg_sale TEXT DEFAULT 'pkt',
            default_pkg_receive TEXT DEFAULT 'pkt',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pharmacy_id, sku)
        )
    ''')
    # Sales per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS sales (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            customer_id INTEGER,
            customer_name TEXT,
            items TEXT,
            subtotal REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'cash',
            amount_tendered REAL DEFAULT 0,
            change REAL DEFAULT 0,
            cashier TEXT,
            notes TEXT
        )
    ''')
    # Customers per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS customers (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            cust_id TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Employees per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS employees (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            emp_id TEXT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            position TEXT,
            department TEXT,
            status TEXT DEFAULT 'active',
            salary REAL DEFAULT 0,
            hire_date TEXT,
            employment_type TEXT DEFAULT 'full-time',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Inventory per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS inventory (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity REAL DEFAULT 0,
            location TEXT,
            batch_number TEXT,
            expiry_date TEXT,
            cost_price REAL,
            selling_price REAL,
            last_restocked TEXT,
            reorder_level REAL DEFAULT 10
        )
    ''')
    # Expenses per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS expenses (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            description TEXT,
            amount REAL DEFAULT 0,
            receipt_number TEXT,
            created_by TEXT
        )
    ''')
    # Payments / Accounts per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS payments (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            paymentId TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            customer INTEGER,
            supplier INTEGER,
            invoice TEXT,
            amount REAL DEFAULT 0,
            method TEXT,
            status TEXT DEFAULT 'paid',
            notes TEXT,
            created_by TEXT
        )
    ''')
    # Locations per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS locations (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            manager TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    # Appointments per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS appointments (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            date TEXT,
            time TEXT,
            service TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Gift cards per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS giftcards (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            code TEXT UNIQUE NOT NULL,
            amount REAL DEFAULT 0,
            balance REAL DEFAULT 0,
            customer_name TEXT,
            customer_phone TEXT,
            expiry_date TEXT,
            status TEXT DEFAULT 'active',
            issued_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Messages per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS messages (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            from_user TEXT,
            to_user TEXT,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'unread',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Deliveries per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS deliveries (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            sale_id INTEGER,
            customer_name TEXT,
            address TEXT,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            delivery_date TEXT,
            driver TEXT,
            notes TEXT
        )
    ''')
    # Invoices per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS invoices (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            items TEXT,
            subtotal REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'unpaid',
            due_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Suppliers per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS suppliers (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.commit()

# ---------- Auth Middleware ----------

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        db = get_db()
        pharmacy = db.execute('SELECT * FROM pharmacies WHERE api_key = ?', (api_key,)).fetchone()
        if not pharmacy:
            return jsonify({'error': 'Invalid API key'}), 401
        g.pharmacy_id = pharmacy['id']
        g.pharmacy = dict(pharmacy)
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            username = request.headers.get('X-Username', '')
            db = get_db()
            user = db.execute(
                'SELECT * FROM users WHERE pharmacy_id = ? AND username = ?',
                (g.pharmacy_id, username)
            ).fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 401
            if roles and user['role'] not in roles:
                return jsonify({'error': 'Access denied'}), 403
            g.user = dict(user)
            return f(*args, **kwargs)
        return decorated
    return decorator

# ---------- Auth Routes ----------

@app.route('/api/auth/register', methods=['POST'])
def register_pharmacy():
    data = request.get_json()
    name = data.get('name', '').strip()
    address = data.get('address', '')
    phone = data.get('phone', '')
    email = data.get('email', '')
    admin_username = data.get('admin_username', '').strip()
    admin_password = data.get('admin_password', '')
    admin_name = data.get('admin_name', admin_username)

    if not name or not admin_username or not admin_password:
        return jsonify({'error': 'Pharmacy name, admin username and password are required'}), 400

    api_key = secrets.token_urlsafe(32)
    try:
        db = get_db()
        cursor = db.execute(
            'INSERT INTO pharmacies (name, address, phone, email, api_key) VALUES (?, ?, ?, ?, ?)',
            (name, address, phone, email, api_key)
        )
        pharmacy_id = cursor.lastrowid
        db.execute(
            'INSERT INTO users (pharmacy_id, username, password, name, role) VALUES (?, ?, ?, ?, ?)',
            (pharmacy_id, admin_username, admin_password, admin_name, 'admin')
        )
        db.commit()
        return jsonify({
            'pharmacy_id': pharmacy_id,
            'name': name,
            'api_key': api_key,
            'admin_username': admin_username,
            'message': 'Pharmacy registered successfully! Save your API key - you will need it to login.'
        }), 201
    except IntegrityError:
        return jsonify({'error': 'API key collision, please try again'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    db = get_db()
    
    # If API key provided, look up pharmacy first
    if api_key:
        pharmacy = db.execute('SELECT * FROM pharmacies WHERE api_key = ?', (api_key,)).fetchone()
        if not pharmacy:
            return jsonify({'error': 'Invalid API key'}), 401
        user = db.execute(
            'SELECT * FROM users WHERE pharmacy_id = ? AND username = ? AND password = ?',
            (pharmacy['id'], username, password)
        ).fetchone()
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        return jsonify({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'store': user['store']
            },
            'pharmacy': {
                'id': pharmacy['id'],
                'name': pharmacy['name'],
                'api_key': pharmacy['api_key'],
                'address': pharmacy['address'],
                'phone': pharmacy['phone']
            }
        }), 200
    else:
        users = db.execute(
            'SELECT u.*, p.api_key, p.name as pharmacy_name, p.address, p.phone FROM users u JOIN pharmacies p ON u.pharmacy_id = p.id WHERE u.username = ? AND u.password = ?',
            (username, password)
        ).fetchall()
        if not users:
            return jsonify({'error': 'Invalid username or password'}), 401
        user = users[0]
        return jsonify({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'store': user['store']
            },
            'pharmacy': {
                'id': user['pharmacy_id'],
                'name': user['pharmacy_name'],
                'api_key': user['api_key'],
                'address': user['address'],
                'phone': user['phone']
            }
        }), 200

@app.route('/api/auth/staff-login', methods=['POST'])
def staff_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    db = get_db()
    users = db.execute(
        'SELECT u.*, p.api_key, p.name as pharmacy_name, p.address, p.phone FROM users u JOIN pharmacies p ON u.pharmacy_id = p.id WHERE u.username = ? AND u.password = ?',
        (username, password)
    ).fetchall()
    if not users:
        return jsonify({'error': 'Invalid username or password'}), 401

    if len(users) > 1:
        user = users[0]
    return jsonify({
        'user': {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'role': user['role'],
            'store': user['store']
        },
        'pharmacy': {
            'id': user['pharmacy_id'],
            'name': user['pharmacy_name'],
            'api_key': user['api_key'],
            'address': user['address'],
            'phone': user['phone']
        }
    }), 200

@app.route('/api/auth/check', methods=['GET'])
@require_auth
def check_auth():
    # Just verify the API key is valid
    return jsonify({
        'pharmacy_id': g.pharmacy_id,
        'name': g.pharmacy['name']
    }), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        db = get_db()
        db.execute('SELECT 1').fetchone()
        db_status = 'ok'
    except Exception as e:
        db_status = f'error: {str(e)}'
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'db_path': app.config['DB_PATH']
    }), 200

# ---------- Generic CRUD helper ----------

def table_response(table, extra_filter='', params=()):
    db = get_db()
    rows = db.execute(
        f'SELECT * FROM {table} WHERE pharmacy_id = ? {extra_filter}',
        (g.pharmacy_id,) + params
    ).fetchall()
    return jsonify([dict(r) for r in rows])

def table_create(table, data):
    try:
        db = get_db()
        cursor = db.execute(f'PRAGMA table_info({table})')
        valid_columns = {row['name'] for row in cursor.fetchall()}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns and k != 'id'}
        keys = list(filtered_data.keys())
        placeholders = ['?'] * len(keys)
        values = list(filtered_data.values())
        sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"
        cursor = db.execute(sql, values)
        db.commit()
        result = dict(filtered_data)
        result['id'] = cursor.lastrowid
        result['pharmacy_id'] = g.pharmacy_id
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': f'Database insert failed: {str(e)}'}), 500

def table_update(table, record_id, data):
    try:
        db = get_db()
        cursor = db.execute(f'PRAGMA table_info({table})')
        valid_columns = {row['name'] for row in cursor.fetchall()}
        sets = []
        values = []
        for k, v in data.items():
            if k != 'id' and k in valid_columns:
                sets.append(f'{k} = ?')
                values.append(v)
        values.append(g.pharmacy_id)
        values.append(record_id)
        sql = f"UPDATE {table} SET {', '.join(sets)} WHERE pharmacy_id = ? AND id = ?"
        db.execute(sql, values)
        db.commit()
        return jsonify({'id': record_id, 'updated': True})
    except Exception as e:
        return jsonify({'error': f'Database update failed: {str(e)}'}), 500

def table_delete(table, record_id):
    try:
        db = get_db()
        db.execute(f'DELETE FROM {table} WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, record_id))
        db.commit()
        return jsonify({'deleted': True})
    except Exception as e:
        return jsonify({'error': f'Database delete failed: {str(e)}'}), 500

# ========== API Routes ==========

# --- Products ---
@app.route('/api/products', methods=['GET'])
@require_auth
def get_products():
    return table_response('products')

@app.route('/api/products', methods=['POST'])
@require_auth
def create_product():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    # Ensure prices is stored as JSON string
    if 'prices' in data and isinstance(data['prices'], dict):
        data['prices'] = json.dumps(data['prices'])
    return table_create('products', data)

@app.route('/api/products/<int:pid>', methods=['PUT'])
@require_auth
def update_product(pid):
    data = request.get_json()
    if 'prices' in data and isinstance(data['prices'], dict):
        data['prices'] = json.dumps(data['prices'])
    return table_update('products', pid, data)

@app.route('/api/products/<int:pid>', methods=['DELETE'])
@require_auth
def delete_product(pid):
    return table_delete('products', pid)

# --- Sales ---
@app.route('/api/sales', methods=['GET'])
@require_auth
def get_sales():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM sales WHERE pharmacy_id = ? ORDER BY date DESC',
        (g.pharmacy_id,)
    ).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        if row.get('items') and isinstance(row['items'], str):
            try:
                row['items'] = json.loads(row['items'])
            except Exception:
                row['items'] = []
        result.append(row)
    return jsonify(result)

@app.route('/api/sales', methods=['POST'])
@require_auth
def create_sale():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_create('sales', data)

@app.route('/api/sales/<int:sid>', methods=['GET'])
@require_auth
def get_sale(sid):
    db = get_db()
    sale = db.execute('SELECT * FROM sales WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, sid)).fetchone()
    if not sale:
        return jsonify({'error': 'Sale not found'}), 404
    row = dict(sale)
    if row.get('items') and isinstance(row['items'], str):
        row['items'] = json.loads(row['items'])
    return jsonify(row)

# --- Customers ---
@app.route('/api/customers', methods=['GET'])
@require_auth
def get_customers():
    return table_response('customers')

@app.route('/api/customers', methods=['POST'])
@require_auth
def create_customer():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('customers', data)

@app.route('/api/customers/<int:cid>', methods=['PUT'])
@require_auth
def update_customer(cid):
    data = request.get_json()
    return table_update('customers', cid, data)

@app.route('/api/customers/<int:cid>', methods=['DELETE'])
@require_auth
def delete_customer(cid):
    return table_delete('customers', cid)

# --- Employees ---
@app.route('/api/employees', methods=['GET'])
@require_auth
def get_employees():
    return table_response('employees')

@app.route('/api/employees', methods=['POST'])
@require_auth
def create_employee():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('employees', data)

@app.route('/api/employees/<int:eid>', methods=['PUT'])
@require_auth
def update_employee(eid):
    data = request.get_json()
    return table_update('employees', eid, data)

@app.route('/api/employees/<int:eid>', methods=['DELETE'])
@require_auth
def delete_employee(eid):
    return table_delete('employees', eid)

# --- Inventory ---
@app.route('/api/inventory', methods=['GET'])
@require_auth
def get_inventory():
    db = get_db()
    rows = db.execute(
        '''SELECT i.*, p.name as product_name, p.sku, p.category_name
           FROM inventory i
           LEFT JOIN products p ON i.product_id = p.id AND p.pharmacy_id = i.pharmacy_id
           WHERE i.pharmacy_id = ?''',
        (g.pharmacy_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/inventory', methods=['POST'])
@require_auth
def create_inventory():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('inventory', data)

@app.route('/api/inventory/<int:iid>', methods=['PUT'])
@require_auth
def update_inventory(iid):
    data = request.get_json()
    return table_update('inventory', iid, data)

# --- Expenses ---
@app.route('/api/expenses', methods=['GET'])
@require_auth
def get_expenses():
    return table_response('expenses', ' ORDER BY date DESC')

@app.route('/api/expenses', methods=['POST'])
@require_auth
def create_expense():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('expenses', data)

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
@require_auth
def delete_expense(eid):
    return table_delete('expenses', eid)

# --- Payments ---
@app.route('/api/payments', methods=['GET'])
@require_auth
def get_payments():
    return table_response('payments', ' ORDER BY date DESC')

@app.route('/api/payments', methods=['POST'])
@require_auth
def create_payment():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('payments', data)

@app.route('/api/payments/<int:pid>', methods=['PUT'])
@require_auth
def update_payment(pid):
    data = request.get_json()
    return table_update('payments', pid, data)

@app.route('/api/payments/<int:pid>', methods=['DELETE'])
@require_auth
def delete_payment(pid):
    return table_delete('payments', pid)

# --- Locations ---
@app.route('/api/locations', methods=['GET'])
@require_auth
def get_locations():
    return table_response('locations')

@app.route('/api/locations', methods=['POST'])
@require_auth
def create_location():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('locations', data)

@app.route('/api/locations/<int:lid>', methods=['PUT'])
@require_auth
def update_location(lid):
    data = request.get_json()
    return table_update('locations', lid, data)

@app.route('/api/locations/<int:lid>', methods=['DELETE'])
@require_auth
def delete_location(lid):
    return table_delete('locations', lid)

# --- Appointments ---
@app.route('/api/appointments', methods=['GET'])
@require_auth
def get_appointments():
    return table_response('appointments', ' ORDER BY date ASC, time ASC')

@app.route('/api/appointments', methods=['POST'])
@require_auth
def create_appointment():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('appointments', data)

@app.route('/api/appointments/<int:aid>', methods=['PUT'])
@require_auth
def update_appointment(aid):
    data = request.get_json()
    return table_update('appointments', aid, data)

@app.route('/api/appointments/<int:aid>', methods=['DELETE'])
@require_auth
def delete_appointment(aid):
    return table_delete('appointments', aid)

# --- Gift Cards ---
@app.route('/api/giftcards', methods=['GET'])
@require_auth
def get_giftcards():
    return table_response('giftcards')

@app.route('/api/giftcards', methods=['POST'])
@require_auth
def create_giftcard():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('giftcards', data)

@app.route('/api/giftcards/<int:gid>', methods=['PUT'])
@require_auth
def update_giftcard(gid):
    data = request.get_json()
    # Map frontend fields to database fields
    if 'cardNumber' in data:
        data['code'] = data.pop('cardNumber')
    if 'recipient' in data:
        data['customer_name'] = data.pop('recipient')
    if 'expiry' in data:
        data['expiry_date'] = data.pop('expiry')
    return table_update('giftcards', gid, data)

@app.route('/api/giftcards/<int:gid>', methods=['DELETE'])
@require_auth
def delete_giftcard(gid):
    return table_delete('giftcards', gid)

# --- Messages ---
@app.route('/api/messages', methods=['GET'])
@require_auth
def get_messages():
    return table_response('messages', ' ORDER BY created_at DESC')

@app.route('/api/messages', methods=['POST'])
@require_auth
def create_message():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('messages', data)

@app.route('/api/messages/<int:mid>', methods=['DELETE'])
@require_auth
def delete_message(mid):
    return table_delete('messages', mid)

# --- Deliveries ---
@app.route('/api/deliveries', methods=['GET'])
@require_auth
def get_deliveries():
    return table_response('deliveries')

@app.route('/api/deliveries', methods=['POST'])
@require_auth
def create_delivery():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('deliveries', data)

# --- Invoices ---
@app.route('/api/invoices', methods=['GET'])
@require_auth
def get_invoices():
    return table_response('invoices')

@app.route('/api/invoices', methods=['POST'])
@require_auth
def create_invoice():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_create('invoices', data)

# --- Suppliers ---
@app.route('/api/suppliers', methods=['GET'])
@require_auth
def get_suppliers():
    return table_response('suppliers')

@app.route('/api/suppliers', methods=['POST'])
@require_auth
def create_supplier():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('suppliers', data)

@app.route('/api/suppliers/<int:sid>', methods=['PUT'])
@require_auth
def update_supplier(sid):
    data = request.get_json()
    return table_update('suppliers', sid, data)

@app.route('/api/suppliers/<int:sid>', methods=['DELETE'])
@require_auth
def delete_supplier(sid):
    return table_delete('suppliers', sid)

# --- Dashboard / Stats ---
@app.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    db = get_db()
    pid = g.pharmacy_id
    total_sales = db.execute(
        'SELECT COALESCE(SUM(total), 0) as s FROM sales WHERE pharmacy_id = ?', (pid,)
    ).fetchone()['s']
    total_transactions = db.execute(
        'SELECT COUNT(*) as c FROM sales WHERE pharmacy_id = ?', (pid,)
    ).fetchone()['c']
    total_products = db.execute(
        'SELECT COUNT(*) as c FROM products WHERE pharmacy_id = ?', (pid,)
    ).fetchone()['c']
    total_customers = db.execute(
        'SELECT COUNT(*) as c FROM customers WHERE pharmacy_id = ?', (pid,)
    ).fetchone()['c']
    low_stock = db.execute(
        'SELECT COUNT(*) as c FROM products WHERE pharmacy_id = ? AND stock > 0 AND stock <= reorder_level',
        (pid,)
    ).fetchone()['c']
    return jsonify({
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'total_products': total_products,
        'total_customers': total_customers,
        'low_stock': low_stock
    })

# --- Reports ---
@app.route('/api/reports/sales-by-category', methods=['GET'])
@require_auth
def sales_by_category():
    db = get_db()
    pid = g.pharmacy_id
    rows = db.execute('''
        SELECT COALESCE(category_name, 'Other') as category, SUM(total) as total
        FROM sales WHERE pharmacy_id = ?
        GROUP BY category_name
    ''', (pid,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/reports/sales-trend', methods=['GET'])
@require_auth
def sales_trend():
    db = get_db()
    pid = g.pharmacy_id
    thirty_days_ago = (datetime.now() - __import__('datetime').timedelta(days=30)).strftime('%Y-%m-%d')
    rows = db.execute('''
        SELECT date as day, SUM(total) as total
        FROM sales WHERE pharmacy_id = ? AND date >= ?
        GROUP BY date ORDER BY date ASC
    ''', (pid, thirty_days_ago)).fetchall()
    return jsonify([dict(r) for r in rows])

# --- Register endpoint for staff (users within pharmacy) ---
@app.route('/api/users/register', methods=['POST'])
@require_auth
def register_staff():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    name = data.get('name', username)
    role = data.get('role', 'staff')
    store = data.get('store', 'main')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        db = get_db()
        db.execute(
            'INSERT INTO users (pharmacy_id, username, password, name, role, store) VALUES (?, ?, ?, ?, ?, ?)',
            (g.pharmacy_id, username, password, name, role, store)
        )
        db.commit()
        return jsonify({'message': 'Staff account created', 'username': username}), 201
    except IntegrityError:
        return jsonify({'error': 'Username already exists for this pharmacy'}), 400

@app.route('/api/users', methods=['GET'])
@require_auth
def list_users():
    db = get_db()
    users = db.execute(
        'SELECT id, username, name, role, store, created_at FROM users WHERE pharmacy_id = ?',
        (g.pharmacy_id,)
    ).fetchall()
    result = []
    for u in users:
        d = dict(u)
        d.pop('password', None)
        result.append(d)
    return jsonify(result)

@app.route('/api/users/<int:uid>', methods=['PUT'])
@require_auth
def update_user(uid):
    data = request.get_json()
    sets = []
    values = []
    for k, v in data.items():
        if k not in ('id', 'pharmacy_id', 'password'):
            sets.append(f'{k} = ?')
            values.append(v)
    if 'password' in data and data['password']:
        sets.append('password = ?')
        values.append(data['password'])
    values.extend([g.pharmacy_id, uid])
    db = get_db()
    db.execute(f"UPDATE users SET {', '.join(sets)} WHERE pharmacy_id = ? AND id = ?", values)
    db.commit()
    return jsonify({'updated': True})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@require_auth
def delete_user(uid):
    db = get_db()
    db.execute('DELETE FROM users WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, uid))
    db.commit()
    return jsonify({'deleted': True})

# --- Categories ---
@app.route('/api/categories', methods=['GET'])
@require_auth
def get_categories():
    db = get_db()
    cats = db.execute('SELECT * FROM categories WHERE pharmacy_id = ?', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(c) for c in cats])

@app.route('/api/categories', methods=['POST'])
@require_auth
def create_category():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    try:
        return table_create('categories', data)
    except IntegrityError:
        return jsonify({'error': 'Category already exists'}), 400

# --- Catalogue PDF info ---
@app.route('/api/catalogue', methods=['GET'])
@require_auth
def get_catalogue():
    db = get_db()
    products = db.execute(
        'SELECT * FROM products WHERE pharmacy_id = ?', (g.pharmacy_id,)
    ).fetchall()
    return jsonify([dict(p) for p in products])

# ========== Main ==========

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'login.html'))

@app.route('/<path:filename>')
def serve_static(filename):
    allowed = {'.html', '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot'}
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        return jsonify({'error': 'File type not allowed'}), 403
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.isfile(filepath):
        return send_file(filepath)
    return jsonify({'error': 'Not found'}), 404

with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
