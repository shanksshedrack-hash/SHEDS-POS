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
            packaging_types TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pharmacy_id, sku)
        )
    ''')
    try:
        db.execute('ALTER TABLE products ADD COLUMN packaging_types TEXT')
    except Exception:
        pass
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
            balance REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        db.execute('ALTER TABLE customers ADD COLUMN balance REAL DEFAULT 0')
    except Exception:
        pass
    try:
        db.execute('ALTER TABLE sales ADD COLUMN status TEXT DEFAULT \'completed\'')
    except Exception:
        pass
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS audit_log (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            action TEXT,
            entity TEXT,
            entity_id TEXT,
            details TEXT,
            user TEXT,
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
    # Receiving history per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS receiving (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            date TEXT,
            ref TEXT,
            supplier_id INTEGER,
            supplier_name TEXT,
            items TEXT NOT NULL DEFAULT '[]',
            total REAL DEFAULT 0,
            notes TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    # Store config per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS store_config (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL UNIQUE,
            config TEXT NOT NULL DEFAULT '{{}}',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Roles per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS roles (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            permissions TEXT NOT NULL DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pharmacy_id, name)
        )
    ''')


    # Shifts per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS shifts (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            cashier_id INTEGER,
            cashier_name TEXT,
            opening_float REAL DEFAULT 0,
            total_sales REAL DEFAULT 0,
            total_cash REAL DEFAULT 0,
            total_card REAL DEFAULT 0,
            total_store_account REAL DEFAULT 0,
            total_pos REAL DEFAULT 0,
            total_gift_card REAL DEFAULT 0,
            expected_cash REAL DEFAULT 0,
            actual_cash REAL DEFAULT 0,
            variance REAL DEFAULT 0,
            status TEXT DEFAULT 'open',
            start_time TEXT DEFAULT CURRENT_TIMESTAMP,
            end_time TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Purchase orders per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            supplier_id INTEGER,
            supplier_name TEXT,
            po_number TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            items TEXT,
            subtotal REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'draft',
            notes TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Bank reconciliation records per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS bank_records (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            bank_name TEXT,
            account_number TEXT,
            transaction_ref TEXT,
            amount REAL DEFAULT 0,
            type TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Stock transfers per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS stock_transfers (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            from_location_id INTEGER,
            to_location_id INTEGER,
            from_location_name TEXT,
            to_location_name TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            items TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tax rules per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS tax_rules (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            rate REAL DEFAULT 0,
            type TEXT DEFAULT 'percentage',
            applicable_categories TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Expiry batches per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS expiry_batches (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT,
            batch_number TEXT,
            expiry_date TEXT,
            quantity REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Prescriptions per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            prescription_number TEXT,
            patient_name TEXT,
            patient_age INTEGER,
            patient_gender TEXT,
            doctor_name TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            items TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Audit log per pharmacy
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS audit_log (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            user_id INTEGER,
            user_name TEXT,
            action TEXT,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    # Branches (enhanced locations with isolation)
    db.execute(f'''
        CREATE TABLE IF NOT EXISTS branches (
            id {id_col()},
            pharmacy_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            manager TEXT,
            timezone TEXT DEFAULT 'Africa/Lagos',
            currency TEXT DEFAULT 'NGN',
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

SUPER_ADMIN_KEY = os.environ.get('SUPER_ADMIN_API_KEY', 'shedrack')

def require_super_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-Super-Admin-Key') or request.args.get('super_admin_key', '')
        if not SUPER_ADMIN_KEY or key != SUPER_ADMIN_KEY:
            return jsonify({'error': 'Super admin access required'}), 401
        return f(*args, **kwargs)
    return decorated

# ---------- Subscription Routes ----------

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

@app.route('/api/auth/admin-setup-login', methods=['POST'])
def admin_setup_login():
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    master_username = data.get('master_username', '').strip()
    master_password = data.get('master_password', '')

    if not api_key:
        return jsonify({'error': 'API key is required'}), 400

    if master_username != 'shedrack' or master_password != 'admin123':
        return jsonify({'error': 'Invalid master admin credentials'}), 401

    db = get_db()
    pharmacy = db.execute('SELECT * FROM pharmacies WHERE api_key = ?', (api_key,)).fetchone()
    if not pharmacy:
        return jsonify({'error': 'Invalid pharmacy'}), 404

    user = db.execute(
        'SELECT * FROM users WHERE pharmacy_id = ? AND role = ?',
        (pharmacy['id'], 'admin')
    ).fetchone()
    if not user:
        return jsonify({'error': 'Admin user not found for this pharmacy'}), 404

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

@app.route('/api/auth/check', methods=['GET'])
@require_auth
def check_auth():
    db = get_db()
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

# ---------- Branch Routes ----------

@app.route('/api/branches', methods=['GET'])
@require_auth
def get_branches():
    db = get_db()
    rows = db.execute('SELECT * FROM branches WHERE pharmacy_id = ? ORDER BY name ASC', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/branches', methods=['POST'])
@require_auth
def create_branch():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('branches', data)

@app.route('/api/branches/<int:bid>', methods=['PUT'])
@require_auth
def update_branch(bid):
    data = request.get_json()
    return table_update('branches', bid, data)

@app.route('/api/branches/<int:bid>', methods=['DELETE'])
@require_auth
def delete_branch(bid):
    return table_delete('branches', bid)

# ---------- Super Admin Routes ----------

@app.route('/api/admin/tenants', methods=['GET'])
@require_super_admin
def list_tenants():
    db = get_db()
    rows = db.execute('''
        SELECT p.*
        FROM pharmacies p
        ORDER BY p.created_at DESC
    ''').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/tenants/<int:tid>', methods=['PUT'])
@require_super_admin
def update_tenant(tid):
    data = request.get_json()
    db = get_db()
    sets = []
    values = []
    allowed = ['name', 'address', 'phone', 'email', 'status']
    for k, v in data.items():
        if k in allowed:
            sets.append(f'{k} = ?')
            values.append(v)
    if not sets:
        return jsonify({'error': 'No valid fields to update'}), 400
    values.append(tid)
    db.execute(f"UPDATE pharmacies SET {', '.join(sets)} WHERE id = ?", values)
    db.commit()
    return jsonify({'updated': True})

@app.route('/api/admin/tenants/<int:tid>', methods=['DELETE'])
@require_super_admin
def delete_tenant(tid):
    db = get_db()
    db.execute('DELETE FROM pharmacies WHERE id = ?', (tid,))
    db.commit()
    return jsonify({'deleted': True})

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
    db = get_db()
    rows = db.execute('SELECT * FROM products WHERE pharmacy_id = ?', (g.pharmacy_id,)).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        if row.get('prices') and isinstance(row['prices'], str):
            try:
                row['prices'] = json.loads(row['prices'])
            except Exception:
                row['prices'] = {}
        if row.get('packaging_types') and isinstance(row['packaging_types'], str):
            try:
                row['packaging_types'] = json.loads(row['packaging_types'])
            except Exception:
                row['packaging_types'] = []
        result.append(row)
    return jsonify(result)

@app.route('/api/products', methods=['POST'])
@require_auth
def create_product():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    if 'prices' in data and isinstance(data['prices'], dict):
        data['prices'] = json.dumps(data['prices'])
    if 'packaging_types' in data and isinstance(data['packaging_types'], list):
        data['packaging_types'] = json.dumps(data['packaging_types'])
    result = table_create('products', data)
    if result[1] == 201:
        resp_data = result[0].get_json()
        if resp_data.get('prices') and isinstance(resp_data['prices'], str):
            try:
                resp_data['prices'] = json.loads(resp_data['prices'])
            except Exception:
                pass
        if resp_data.get('packaging_types') and isinstance(resp_data['packaging_types'], str):
            try:
                resp_data['packaging_types'] = json.loads(resp_data['packaging_types'])
            except Exception:
                pass
        return jsonify(resp_data), 201
    return result

@app.route('/api/products/<int:pid>', methods=['PUT'])
@require_auth
def update_product(pid):
    data = request.get_json()
    if 'prices' in data and isinstance(data['prices'], dict):
        data['prices'] = json.dumps(data['prices'])
    if 'packaging_types' in data and isinstance(data['packaging_types'], list):
        data['packaging_types'] = json.dumps(data['packaging_types'])
    result = table_update('products', pid, data)
    if result[1] == 200:
        resp_data = result[0].get_json()
        return jsonify(resp_data), 200
    return result

@app.route('/api/products/<int:pid>', methods=['DELETE'])
@require_auth
def delete_product(pid):
    return table_delete('products', pid)

# --- Receiving ---
@app.route('/api/receiving', methods=['GET'])
@require_auth
def list_receiving():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM receiving WHERE pharmacy_id = ? ORDER BY id DESC LIMIT 200',
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

@app.route('/api/receiving', methods=['POST'])
@require_auth
def create_receiving():
    try:
        db = get_db()
        data = request.get_json() or {}
        items = data.get('items', [])
        if not isinstance(items, list) or not items:
            return jsonify({'error': 'items array is required'}), 400
        supplier_id = data.get('supplier_id') or data.get('supplier')
        supplier_name = data.get('supplier_name') or ''
        if supplier_id and not supplier_name:
            s = db.execute(
                'SELECT name FROM suppliers WHERE pharmacy_id = ? AND id = ?',
                (g.pharmacy_id, supplier_id)
            ).fetchone()
            if s:
                supplier_name = s['name']
        enriched_items = []
        total = 0.0
        for it in items:
            pid = it.get('product_id') or it.get('id')
            if not pid:
                continue
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                continue
            prod = db.execute(
                'SELECT id, name, sku, stock, cost_price, costPrice FROM products WHERE pharmacy_id = ? AND id = ?',
                (g.pharmacy_id, pid)
            ).fetchone()
            if not prod:
                continue
            qty = float(it.get('qty') or 0)
            if qty <= 0:
                continue
            unit_cost = float(it.get('cost_price') or prod['cost_price'] or prod['costPrice'] or 0)
            new_stock = float(prod['stock'] or 0) + qty
            db.execute(
                'UPDATE products SET stock = ?, cost_price = ? WHERE pharmacy_id = ? AND id = ?',
                (new_stock, unit_cost, g.pharmacy_id, pid)
            )
            line_total = unit_cost * qty
            total += line_total
            enriched_items.append({
                'product_id': pid,
                'name': prod['name'],
                'sku': prod['sku'],
                'qty': qty,
                'cost_price': unit_cost,
                'pkg_type': it.get('pkg_type') or it.get('pkgType'),
                'expiry': it.get('expiry') or None,
                'line_total': round(line_total, 2)
            })
        if not enriched_items:
            return jsonify({'error': 'No valid items to receive'}), 400
        cur = db.execute(
            'INSERT INTO receiving (pharmacy_id, date, ref, supplier_id, supplier_name, items, total, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                g.pharmacy_id,
                data.get('date') or datetime.utcnow().isoformat(),
                data.get('ref') or '',
                supplier_id,
                supplier_name,
                json.dumps(enriched_items),
                round(total, 2),
                data.get('notes') or '',
                request.headers.get('X-Username')
            )
        )
        new_id = cur.lastrowid
        try:
            db.execute(
                'INSERT INTO audit_log (pharmacy_id, action, entity, entity_id, details, user) VALUES (?,?,?,?,?,?)',
                (
                    g.pharmacy_id, 'create_receiving', 'receiving', str(new_id),
                    json.dumps({'supplier': supplier_name, 'total': round(total, 2), 'items': len(enriched_items)}),
                    request.headers.get('X-Username')
                )
            )
        except Exception as audit_err:
            app.logger.warning('audit log write failed: %s' % audit_err)
        db.commit()
        record = db.execute('SELECT * FROM receiving WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, new_id)).fetchone()
        if not record:
            return jsonify({'id': new_id, 'status': 'ok'}), 201
        result = dict(record)
        try:
            result['items'] = json.loads(result['items'])
        except Exception:
            result['items'] = []
        return jsonify(result), 201
    except Exception as e:
        app.logger.exception('create_receiving failed')
        return jsonify({'error': 'Server error: ' + str(e)}), 500

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
    result = table_create('sales', data)
    db = get_db()
    if result[1] == 201:
        if data.get('payment_method') == 'store_account' and data.get('customer_id'):
            db.execute(
                'UPDATE customers SET balance = balance + ? WHERE pharmacy_id = ? AND id = ?',
                (data.get('total', 0), g.pharmacy_id, data['customer_id'])
            )
    db.commit()
    return result

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

@app.route('/api/sales/<int:sid>', methods=['PUT'])
@require_auth
def update_sale(sid):
    data = request.get_json()
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    db = get_db()
    allowed = ['customer_id', 'customer_name', 'payment_method', 'discount_amount',
               'tax', 'notes', 'cashier', 'amount_tendered', 'change', 'items', 'subtotal']
    clean = {k: v for k, v in data.items() if k in allowed}
    if 'discount_amount' in clean or 'tax' in clean or 'subtotal' in clean:
        sale = db.execute('SELECT subtotal, discount_amount, tax, total FROM sales WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, sid)).fetchone()
        if sale:
            subtotal = float(clean.get('subtotal', sale['subtotal'] or 0))
            disc = float(clean.get('discount_amount', sale['discount_amount'] or 0))
            tax = float(clean.get('tax', sale['tax'] or 0))
            clean['total'] = round(subtotal - disc + tax, 2)
    # Reconcile store-account customer balance + record an audit trail.
    try:
        old = db.execute('SELECT payment_method, customer_id, customer_name, total FROM sales WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, sid)).fetchone()
        if old:
            old_pm = (old['payment_method'] or 'cash')
            old_cust = old['customer_id']
            old_cname = old['customer_name']
            old_total = float(old['total'] or 0)
            new_pm = clean.get('payment_method', old_pm)
            new_cust = clean.get('customer_id', old_cust)
            new_cname = clean.get('customer_name', old_cname)
            new_total = float(clean.get('total', old_total) or 0)

            def change(cust_id, delta):
                if not cust_id:
                    return
                c = db.execute('SELECT balance FROM customers WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, cust_id)).fetchone()
                if not c:
                    return
                nb = max(0.0, (float(c['balance'] or 0)) + delta)
                db.execute('UPDATE customers SET balance = ? WHERE pharmacy_id = ? AND id = ?', (nb, g.pharmacy_id, cust_id))

            if old_pm == 'store_account' and new_pm == 'store_account':
                if old_cust == new_cust:
                    change(new_cust, new_total - old_total)
                else:
                    change(old_cust, -old_total)
                    change(new_cust, new_total)
            elif old_pm == 'store_account' and new_pm != 'store_account':
                change(old_cust, -old_total)
            elif old_pm != 'store_account' and new_pm == 'store_account':
                change(new_cust, new_total)

            details = json.dumps({
                'old_total': old_total, 'new_total': new_total,
                'old_customer': old_cname, 'new_customer': new_cname,
                'old_payment': old_pm, 'new_payment': new_pm
            })
            db.execute('INSERT INTO audit_log (pharmacy_id, action, entity, entity_id, details, user) VALUES (?,?,?,?,?,?)',
                       (g.pharmacy_id, 'edit_sale', 'sale', str(sid), details, request.headers.get('X-Username')))
    except Exception as e:
        app.logger.warning('store-account balance reconcile failed: %s' % e)
    return table_update('sales', sid, clean)

@app.route('/api/sales/<int:sid>/void', methods=['POST'])
@require_auth
def void_sale(sid):
    db = get_db()
    sale = db.execute('SELECT * FROM sales WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, sid)).fetchone()
    if not sale:
        return jsonify({'error': 'Sale not found'}), 404
    if sale['status'] == 'void':
        return jsonify({'error': 'Already voided'}), 400
    items = sale['items']
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            items = []
    for it in (items or []):
        pid = it.get('product_id')
        qty = float(it.get('qty') or 0)
        if pid:
            p = db.execute('SELECT stock FROM products WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, pid)).fetchone()
            if p:
                db.execute('UPDATE products SET stock = ? WHERE pharmacy_id = ? AND id = ?',
                           (float(p['stock'] or 0) + qty, g.pharmacy_id, pid))
    if sale['payment_method'] == 'store_account' and sale['customer_id']:
        c = db.execute('SELECT balance FROM customers WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, sale['customer_id'])).fetchone()
        if c:
            db.execute('UPDATE customers SET balance = ? WHERE pharmacy_id = ? AND id = ?',
                       (max(0.0, float(c['balance'] or 0) - float(sale['total'] or 0)), g.pharmacy_id, sale['customer_id']))
    db.execute('UPDATE sales SET status = ? WHERE pharmacy_id = ? AND id = ?', ('void', g.pharmacy_id, sid))
    details = json.dumps({'total': sale['total'], 'customer': sale['customer_name'], 'payment': sale['payment_method']})
    db.execute('INSERT INTO audit_log (pharmacy_id, action, entity, entity_id, details, user) VALUES (?,?,?,?,?,?)',
               (g.pharmacy_id, 'void_sale', 'sale', str(sid), details, request.headers.get('X-Username')))
    db.commit()
    return jsonify({'id': sid, 'status': 'void', 'updated': True})

@app.route('/api/audit', methods=['GET'])
@require_auth
def get_audit():
    db = get_db()
    rows = db.execute('SELECT * FROM audit_log WHERE pharmacy_id = ? ORDER BY created_at DESC LIMIT 300', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

# --- Customers ---
@app.route('/api/customers', methods=['GET'])
@require_auth
def get_customers():
    db = get_db()
    rows = db.execute('SELECT * FROM customers WHERE pharmacy_id = ?', (g.pharmacy_id,)).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        row['firstName'] = row.get('first_name', '')
        row['lastName'] = row.get('last_name', '')
        row['fullName'] = (row.get('first_name', '') + ' ' + row.get('last_name', '')).strip()
        result.append(row)
    return jsonify(result)

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
    result = table_create('payments', data)
    if result[1] == 201 and data.get('customer'):
        db = get_db()
        db.execute(
            'UPDATE customers SET balance = balance - ? WHERE pharmacy_id = ? AND id = ?',
            (data.get('amount', 0), g.pharmacy_id, data['customer'])
        )
        db.commit()
    return result

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

# --- Roles ---
@app.route('/api/roles', methods=['GET'])
@require_auth
def get_roles():
    db = get_db()
    rows = db.execute('SELECT * FROM roles WHERE pharmacy_id = ?', (g.pharmacy_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get('permissions') and isinstance(d['permissions'], str):
            try:
                d['permissions'] = json.loads(d['permissions'])
            except Exception:
                d['permissions'] = []
        result.append(d)
    return jsonify(result)

@app.route('/api/roles', methods=['POST'])
@require_auth
def create_role():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Role name is required'}), 400
    permissions = data.get('permissions', [])
    if not isinstance(permissions, list):
        permissions = []
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO roles (pharmacy_id, name, description, permissions) VALUES (?, ?, ?, ?)',
            (g.pharmacy_id, name, data.get('description', ''), json.dumps(permissions))
        )
        db.commit()
        data['id'] = cursor.lastrowid
        data['pharmacy_id'] = g.pharmacy_id
        return jsonify(data), 201
    except IntegrityError:
        return jsonify({'error': 'Role already exists'}), 400

@app.route('/api/roles/<int:rid>', methods=['PUT'])
@require_auth
def update_role(rid):
    data = request.get_json()
    db = get_db()
    sets = []
    values = []
    if 'name' in data:
        sets.append('name = ?')
        values.append(data['name'].strip())
    if 'description' in data:
        sets.append('description = ?')
        values.append(data['description'])
    if 'permissions' in data:
        sets.append('permissions = ?')
        values.append(json.dumps(data['permissions'] if isinstance(data['permissions'], list) else []))
    values.extend([g.pharmacy_id, rid])
    db.execute(f"UPDATE roles SET {', '.join(sets)} WHERE pharmacy_id = ? AND id = ?", values)
    db.commit()
    return jsonify({'updated': True})

@app.route('/api/roles/<int:rid>', methods=['DELETE'])
@require_auth
def delete_role(rid):
    db = get_db()
    db.execute('DELETE FROM roles WHERE pharmacy_id = ? AND id = ?', (g.pharmacy_id, rid))
    db.commit()
    return jsonify({'deleted': True})

# --- Store Config ---
@app.route('/api/store-config', methods=['GET'])
@require_auth
def get_store_config():
    db = get_db()
    row = db.execute('SELECT config FROM store_config WHERE pharmacy_id = ?', (g.pharmacy_id,)).fetchone()
    if row and row['config']:
        try:
            return jsonify(json.loads(row['config']))
        except Exception:
            pass
    return jsonify({})

@app.route('/api/store-config', methods=['PUT'])
@require_auth
def update_store_config():
    data = request.get_json()
    config_json = json.dumps(data)
    db = get_db()
    db.execute('INSERT OR REPLACE INTO store_config (pharmacy_id, config, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)', (g.pharmacy_id, config_json))
    db.commit()
    return jsonify(data)


# --- Shifts ---
@app.route('/api/shifts', methods=['GET'])
@require_auth
def get_shifts():
    db = get_db()
    rows = db.execute('SELECT * FROM shifts WHERE pharmacy_id = ? ORDER BY start_time DESC', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/shifts', methods=['POST'])
@require_auth
def create_shift():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('shifts', data)

@app.route('/api/shifts/<int:sid>', methods=['PUT'])
@require_auth
def update_shift(sid):
    data = request.get_json()
    return table_update('shifts', sid, data)

@app.route('/api/shifts/<int:sid>', methods=['DELETE'])
@require_auth
def delete_shift(sid):
    return table_delete('shifts', sid)

# --- Purchase Orders ---
@app.route('/api/purchase-orders', methods=['GET'])
@require_auth
def get_purchase_orders():
    db = get_db()
    rows = db.execute('SELECT * FROM purchase_orders WHERE pharmacy_id = ? ORDER BY date DESC', (g.pharmacy_id,)).fetchall()
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

@app.route('/api/purchase-orders', methods=['POST'])
@require_auth
def create_purchase_order():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_create('purchase_orders', data)

@app.route('/api/purchase-orders/<int:pid>', methods=['PUT'])
@require_auth
def update_purchase_order(pid):
    data = request.get_json()
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_update('purchase_orders', pid, data)

@app.route('/api/purchase-orders/<int:pid>', methods=['DELETE'])
@require_auth
def delete_purchase_order(pid):
    return table_delete('purchase_orders', pid)

# --- Bank Records ---
@app.route('/api/bank-records', methods=['GET'])
@require_auth
def get_bank_records():
    db = get_db()
    rows = db.execute('SELECT * FROM bank_records WHERE pharmacy_id = ? ORDER BY date DESC', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/bank-records', methods=['POST'])
@require_auth
def create_bank_record():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('bank_records', data)

@app.route('/api/bank-records/<int:bid>', methods=['PUT'])
@require_auth
def update_bank_record(bid):
    data = request.get_json()
    return table_update('bank_records', bid, data)

@app.route('/api/bank-records/<int:bid>', methods=['DELETE'])
@require_auth
def delete_bank_record(bid):
    return table_delete('bank_records', bid)

# --- Stock Transfers ---
@app.route('/api/stock-transfers', methods=['GET'])
@require_auth
def get_stock_transfers():
    db = get_db()
    rows = db.execute('SELECT * FROM stock_transfers WHERE pharmacy_id = ? ORDER BY date DESC', (g.pharmacy_id,)).fetchall()
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

@app.route('/api/stock-transfers', methods=['POST'])
@require_auth
def create_stock_transfer():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_create('stock_transfers', data)

@app.route('/api/stock-transfers/<int:tid>', methods=['PUT'])
@require_auth
def update_stock_transfer(tid):
    data = request.get_json()
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_update('stock_transfers', tid, data)

@app.route('/api/stock-transfers/<int:tid>', methods=['DELETE'])
@require_auth
def delete_stock_transfer(tid):
    return table_delete('stock_transfers', tid)

# --- Tax Rules ---
@app.route('/api/tax-rules', methods=['GET'])
@require_auth
def get_tax_rules():
    db = get_db()
    rows = db.execute('SELECT * FROM tax_rules WHERE pharmacy_id = ?', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/tax-rules', methods=['POST'])
@require_auth
def create_tax_rule():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('tax_rules', data)

@app.route('/api/tax-rules/<int:tid>', methods=['PUT'])
@require_auth
def update_tax_rule(tid):
    data = request.get_json()
    return table_update('tax_rules', tid, data)

@app.route('/api/tax-rules/<int:tid>', methods=['DELETE'])
@require_auth
def delete_tax_rule(tid):
    return table_delete('tax_rules', tid)

# --- Expiry Batches ---
@app.route('/api/expiry-batches', methods=['GET'])
@require_auth
def get_expiry_batches():
    db = get_db()
    rows = db.execute('SELECT * FROM expiry_batches WHERE pharmacy_id = ? ORDER BY expiry_date ASC', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/expiry-batches', methods=['POST'])
@require_auth
def create_expiry_batch():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('expiry_batches', data)

@app.route('/api/expiry-batches/<int:bid>', methods=['PUT'])
@require_auth
def update_expiry_batch(bid):
    data = request.get_json()
    return table_update('expiry_batches', bid, data)

@app.route('/api/expiry-batches/<int:bid>', methods=['DELETE'])
@require_auth
def delete_expiry_batch(bid):
    return table_delete('expiry_batches', bid)

# --- Prescriptions ---
@app.route('/api/prescriptions', methods=['GET'])
@require_auth
def get_prescriptions():
    db = get_db()
    rows = db.execute('SELECT * FROM prescriptions WHERE pharmacy_id = ? ORDER BY date DESC', (g.pharmacy_id,)).fetchall()
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

@app.route('/api/prescriptions', methods=['POST'])
@require_auth
def create_prescription():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_create('prescriptions', data)

@app.route('/api/prescriptions/<int:pid>', methods=['PUT'])
@require_auth
def update_prescription(pid):
    data = request.get_json()
    if 'items' in data and isinstance(data['items'], list):
        data['items'] = json.dumps(data['items'])
    return table_update('prescriptions', pid, data)

@app.route('/api/prescriptions/<int:pid>', methods=['DELETE'])
@require_auth
def delete_prescription(pid):
    return table_delete('prescriptions', pid)

# --- Audit Log ---
@app.route('/api/audit-log', methods=['GET'])
@require_auth
def get_audit_log():
    db = get_db()
    rows = db.execute('SELECT * FROM audit_log WHERE pharmacy_id = ? ORDER BY created_at DESC', (g.pharmacy_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/audit-log', methods=['POST'])
@require_auth
def create_audit_log():
    data = request.get_json()
    data['pharmacy_id'] = g.pharmacy_id
    return table_create('audit_log', data)

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

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key, X-Username'
    return response

@app.route('/api/health', methods=['OPTIONS'])
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path=''):
    return '', 204

with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
