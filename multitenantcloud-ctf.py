from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response, send_file, abort, g, flash, render_template_string
from functools import wraps
import jwt
import hashlib
import secrets
import sqlite3
import json
import time
import base64
import os
import re
import uuid
import xml.etree.ElementTree as ET
import yaml
import subprocess
import urllib.parse
import threading
import urllib.request
import pickle
import hmac
import random
import string
import uuid
import hashlib
import hmac
import binascii
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "mULTIT3NANT_Sup3r_S3cr3t_2024_D0nt_3v3n_TH1NK_4b0ut_1t_!!!" 
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = False  # VULN: XSS via cookies
app.config['SESSION_COOKIE_SECURE'] = False
app.config['DEBUG'] = True  # VULN: Debug mode exposes stack traces
app.config['TENANT_DOMAINS'] = ['tenant1.local', 'tenant2.local', 'tenant3.local', 'admin.local']

# Mock secrets and API keys
STRIPE_SECRET_KEY = "sp_test_4eC39HqLyjWDarjtT1zdp7dc"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
JWT_SECRET = "jwt_secret_should_be_secure_but_is_not"
MASTER_API_KEY = "master_key_2024_super_secret"
ADMIN_BACKDOOR = "backdoor_2024_secret"

# Store found flags for leaderboard
found_flags = {}
flag_submission_locks = {}
submission_queue = []
project_creation_counter = {}
report_uid_counter = {}

# Define all valid flags for validation
# Update your VALID_FLAGS dictionary in the main CTF app
VALID_FLAGS = {
    # Original flags
    "FLAG{1: RESOURCE_FLAG}": "Resource IDOR - Accessed secret project resource",
    "FLAG{2: BFLA_ADMIN_ENDPOINT}": "BFLA - Deleted user via admin endpoint",
    "FLAG{2: CROSS_TENANT_LEAK}": "IDOR - Cross-tenant resource leak",
    "FLAG{3: INITECH_SECRET}": "IDOR - Accessed Initech TPS reports",
    "FLAG{4: BPLA_SELF_ESCALATION}": "BPLA - Escalated own role to admin",
    "FLAG{4: MASTER_RESOURCE}": "IDOR - Master resource access",
    "FLAG{5: SECRET_EXPOSURE}": "Secret Exposure - Found debug config",
    "FLAG{6: TENANT_BYPASS}": "Tenant Isolation Bypass - Accessed other tenant",
    "FLAG{7: JWT_ALGORITHM_MASTER}": "JWT Algorithm Confusion - Master access",
    "FLAG{8: MASS_ASSIGNMENT_ADMIN}": "Mass Assignment - Role escalation",
    "FLAG{8: INTERNAL_USER_NOTE}": "IDOR - Found internal notes in profile",
    "FLAG{9: SQL_INJECTION}": "SQL Injection - Extracted data",
    "FLAG{9: OWNER_NOTES}": "IDOR - Accessed owner notes",
    "FLAG{10: DEBUG_ENDPOINT}": "BFLA - Accessed audit logs",
    "FLAG{10: GLOBEX_ADMIN}": "IDOR - Accessed Globex admin data",
    "FLAG{11: RACE_CONDITION}": "Race Condition - Role upgrade",
    "FLAG{11: INITECH_ADMIN_BACKDOOR}": "IDOR - Initech admin backdoor",
    "FLAG{12: GRAPHQL_LEAK}": "GraphQL Introspection - Schema leak",
    "FLAG{12: PETER_SPECIAL}": "IDOR - Peter's special flag",
    "FLAG{13: NOSQL_INJECTION}": "NoSQL Injection - Auth bypass",
    "FLAG{13: MASTER_ADMIN}": "IDOR - Master admin access",
    "FLAG{14: CORS_MISCONFIG}": "CORS Misconfiguration - Cross-origin",
    "FLAG{15: SSRF_METADATA}": "SSRF - Accessed internal metadata",
    "FLAG{15: MASTER_TENANT_SECRET}": "SSRF - Master tenant secret",
    
    # Bonus flags
    "FLAG{INVITE_VULN}": "Invite System - Predictable invite codes",
    "FLAG{HIDDEN_IDOR_MASTER}": "Hidden IDOR - Secret endpoint discovery",
    "FLAG{ROLE_ESCALATION_SUCCESS}": "Role Escalation - Basic role upgrade",
    "FLAG{ROLE_ESCALATION_SUPREME}": "Role Escalation - Ultimate backdoor access",
    "FLAG{SPECIAL_QUOTE_MASTER}": "Special Quote - Master hacker quote",
    "FLAG{ULTIMATE_MIND_RACE_MASTER}": "Race Condition Master - Achieved 10,000 points through concurrency exploitation",
    "FLAG{UID_150_SPECIAL}": "Project System - Found the hidden uid-150file project",
    "FLAG{REPORT_IDOR_EXEC}": "Reports IDOR - Accessed secret executive report",
    "FLAG{HIDDEN_REPORT_99}": "Reports IDOR - Found hidden report ID 99",
    "FLAG{STRATEGY_BASE64_HIDDEN}": "Strategy - Decoded base64 hidden flag",
    "FLAG{SQL_INJECTION_MASTER}": "Secrets - SQL injection in master secret generator",
    "FLAG{TEAM_IMPORT_SSRF}": "Team Import - SSRF vulnerability exploited",
    "FLAG{TEAM_EXPORT_LEAK}": "Team Export - Sensitive data exposure",
    "FLAG{TEAM_UPDATE_ESCALATION}": "Team Update - Privilege escalation via mass assignment",
    "FLAG{TEAM_UPDATE_SALARY}": "Team Update - Salary manipulation",
    
    # Enhanced invite flags
    "FLAG{INVITE_MASTER_DISCOVERED}": "Invite System - Master invite discovered",
}

def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(s):
    return datetime.fromisoformat(s.decode())

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect('multitenant.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    
    # Tenants table
    c.execute('''CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        subdomain TEXT UNIQUE,
        api_key TEXT,
        plan TEXT,
        settings TEXT,
        created_at TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        secret_tenant_key TEXT
    )''')
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        tenant_id INTEGER,
        username TEXT,
        email TEXT,
        password_hash TEXT,
        role TEXT DEFAULT 'viewer',
        api_key TEXT,
        reset_token TEXT,
        mfa_secret TEXT,
        department TEXT,
        manager_id INTEGER,
        salary REAL,
        ssn TEXT,
        credit_card TEXT,
        is_deleted INTEGER DEFAULT 0,
        failed_login INTEGER DEFAULT 0,
        account_locked INTEGER DEFAULT 0,
        internal_notes TEXT,
        last_login TIMESTAMP,
        created_at TIMESTAMP,
        user_metadata TEXT,
        backup_codes TEXT,
        FOREIGN KEY (tenant_id) REFERENCES tenants (id),
        UNIQUE(tenant_id, username)
    )''')
    
    # Resources table
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY,
        tenant_id INTEGER,
        name TEXT,
        data TEXT,
        owner_id INTEGER,
        is_public INTEGER DEFAULT 0,
        share_with TEXT,
        internal_flag TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants (id)
    )''')
    
    # Audit logs
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY,
        tenant_id INTEGER,
        user_id INTEGER,
        action TEXT,
        ip_address TEXT,
        details TEXT,
        timestamp TIMESTAMP,
        is_sensitive INTEGER DEFAULT 0
    )''')
    
    # Leaderboard table
    c.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
        id INTEGER PRIMARY KEY,
        username TEXT,
        flag_count INTEGER DEFAULT 0,
        flags_found TEXT,
        score INTEGER DEFAULT 0,
        last_found TIMESTAMP,
        ip_address TEXT
    )''')
    
    # Invites table
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
        id INTEGER PRIMARY KEY,
        code TEXT UNIQUE,
        role TEXT,
        created_by TEXT,
        created_at TIMESTAMP,
        is_used INTEGER DEFAULT 0,
        secret_flag TEXT,
        is_hidden INTEGER DEFAULT 0
    )''')
    
    # Reports table
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY,
        uid TEXT UNIQUE,
        title TEXT,
        content TEXT,
        created_by TEXT,
        created_at TIMESTAMP,
        flag TEXT
    )''')
    
    # Insert tenants
    now = datetime.now().isoformat()
    tenants_data = [
        (1, 'Acme Corp', 'acme', 'tenant_api_key_12345', 'enterprise', '{"theme": "dark", "features": ["analytics"]}', now, 1, 'acme_secret_2024'),
        (2, 'Globex Inc', 'globex', 'tenant_api_key_67890', 'business', '{"theme": "light", "features": ["reports"]}', now, 1, 'globex_secret_2024'),
        (3, 'Initech', 'initech', 'tenant_api_key_11111', 'starter', '{"theme": "default"}', now, 1, 'initech_backdoor_secret'),
        (4, 'Admin Tenant', 'admin', 'master_api_key_99999', 'master', '{"is_master": true}', now, 1, 'FLAG{15: MASTER_TENANT_SECRET}')
    ]
    
    for tenant in tenants_data:
        try:
            c.execute('INSERT OR IGNORE INTO tenants VALUES (?,?,?,?,?,?,?,?,?)', tenant)
        except:
            pass
    
    # Insert users
    users_data = [
        (1, 1, 'john_doe', 'john@acme.com', hashlib.sha256(b'Password123!').hexdigest(), 'admin', 'user_api_key_111', None, None, 'Engineering', 1, 95000, '123-45-6789', '4111111111111111', 0, 0, 0, 'FLAG{8: INTERNAL_USER_NOTE}', now, now, '{"preferences": {"theme": "dark"}}', None),
        (2, 1, 'jane_smith', 'jane@acme.com', hashlib.sha256(b'Password456!').hexdigest(), 'owner', 'user_api_key_222', None, None, 'Sales', 1, 120000, '987-65-4321', '5500000000000004', 0, 0, 0, 'FLAG{9: OWNER_NOTES}', now, now, '{"preferences": {"theme": "light"}}', None),
        (3, 1, 'bob_wilson', 'bob@acme.com', hashlib.sha256(b'Password789!').hexdigest(), 'viewer', 'user_api_key_333', None, None, 'IT', 1, 65000, '555-55-5555', '378282246310005', 0, 0, 0, 'Regular user', now, now, '{}', None),
        (4, 2, 'admin_globex', 'admin@globex.com', hashlib.sha256(b'Admin@2024!').hexdigest(), 'admin', 'user_api_key_444', 'reset_token_xyz', None, 'Management', 4, 150000, '111-22-3333', '6011111111111117', 0, 0, 0, 'FLAG{10: GLOBEX_ADMIN}', now, now, '{"is_vip": true}', None),
        (5, 2, 'viewer_globex', 'viewer@globex.com', hashlib.sha256(b'Viewer@123').hexdigest(), 'viewer', 'user_api_key_555', None, None, 'Operations', 4, 50000, '444-55-6666', '3530111333300000', 0, 0, 0, 'Regular viewer', now, now, '{}', None),
        (6, 3, 'michael_bolton', 'michael@initech.com', hashlib.sha256(b'Initech@123').hexdigest(), 'admin', 'user_api_key_666', None, None, 'IT', 6, 80000, '777-88-9999', '6011000990139424', 0, 0, 0, 'FLAG{11: INITECH_ADMIN_BACKDOOR}', now, now, '{"insecure": true}', None),
        (7, 3, 'peter_gibbons', 'peter@initech.com', hashlib.sha256(b'Peter@123').hexdigest(), 'viewer', 'user_api_key_777', None, None, 'Engineering', 6, 45000, '888-99-0000', '5555555555554444', 0, 0, 0, 'FLAG{12: PETER_SPECIAL}', now, now, '{"lazy": true}', None),
        (8, 4, 'master_admin', 'master@system.com', hashlib.sha256(b'Master@2024!').hexdigest(), 'master', 'master_api_key_999', None, None, 'System', 8, 999999, '000-00-0000', '9999999999999999', 0, 0, 0, 'FLAG{13: MASTER_ADMIN}', now, now, '{"god_mode": true}', None)
    ]
    
    for user in users_data:
        try:
            c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', user)
        except:
            pass
    
    # ============ CLEAR OLD PROJECTS ============
    # Delete all existing projects except the default Company Strategy
    c.execute("DELETE FROM resources WHERE name != 'Company Strategy'")
    
    # Insert ONLY the default Company Strategy
    resources_data = [
        (1, 1, 'Company Strategy', '{"plan": "Dominate market 2024", "uid": "uid-1file"}', 1, 0, '2,3', None, now),
    ]
    
    for resource in resources_data:
        try:
            c.execute('INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,?,?,?,?)', resource)
        except:
            pass
    
    # Insert hidden invites
    hidden_invites = [
        ('INVITE_OWNER_f529c5de', 'owner', 'system', datetime.now().isoformat(), 'FLAG{INVITE_VULN}', 1),
        ('INVITE_ADMIN_8f3a9b2c', 'admin', 'system', datetime.now().isoformat(), None, 1),
        ('INVITE_MASTER_7e1d4c8f', 'master', 'system', datetime.now().isoformat(), None, 1),
    ]
    
    for invite in hidden_invites:
        try:
            c.execute('INSERT OR IGNORE INTO invites (code, role, created_by, created_at, secret_flag, is_hidden) VALUES (?, ?, ?, ?, ?, ?)',
                      invite)
        except:
            pass


    conn.commit()
    conn.close()

def add_hidden_invites():
    """Add hidden invite codes to the database"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    hidden_invites = [
        ('INVITE_OWNER_f529c5de', 'owner', 'system', 'FLAG{INVITE_VULN}', 1),
        ('INVITE_ADMIN_8f3a9b2c', 'admin', 'system', None, 1),
        ('INVITE_MASTER_7e1d4c8f', 'master', 'system', None, 1),
    ]
    
    for code, role, created_by, flag, hidden in hidden_invites:
        try:
            c.execute('INSERT OR IGNORE INTO invites (code, role, created_by, created_at, secret_flag, is_hidden, is_used) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (code, role, created_by, datetime.now().isoformat(), flag, hidden, 0))
        except Exception as e:
            print(f"Error adding invite {code}: {e}")
    
    conn.commit()
    conn.close()


add_hidden_invites()

# ==================== HELPER FUNCTIONS ====================
def get_tenant_context():
    host = request.headers.get('Host', '')
    tenant_header = request.headers.get('X-Tenant-ID', '')
    
    if tenant_header:
        tenant_name = tenant_header
    else:
        tenant_name = 'acme'
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT id, name, secret_tenant_key FROM tenants WHERE name=? OR subdomain=?', (tenant_name, tenant_name))
    tenant = c.fetchone()
    conn.close()
    
    if not tenant:
        return None
    
    g.tenant_id = tenant[0]
    g.tenant_name = tenant[1]
    g.tenant_secret = tenant[2]
    return g.tenant_id

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return redirect(url_for('login_page'))
        
        try:
            payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            request.user = payload
            request.user_tenant = payload.get('tenant_id')
        except:
            return redirect(url_for('login_page'))
        
        return f(*args, **kwargs)
    return decorated

# ==================== FLAG VALIDATION ENDPOINT ====================
@app.route('/api/v1/validate-flag', methods=['POST'])
@token_required
def validate_flag():
    """Validate if a flag is real and add to leaderboard"""
    data = request.get_json()
    flag = data.get('flag')
    username = request.user.get('username')
    
    if not flag:
        return jsonify({'error': 'No flag provided', 'valid': False}), 400
    
    # Check if flag is valid
    if flag in VALID_FLAGS:
        conn = sqlite3.connect('multitenant.db')
        c = conn.cursor()
        
        # Check if user already found this flag
        c.execute('SELECT flags_found, score FROM leaderboard WHERE username=?', (username,))
        result = c.fetchone()
        
        flags_found = []
        current_score = 0
        if result and result[0]:
            flags_found = json.loads(result[0])
            current_score = result[1] if result[1] else 0
        
        if flag in flags_found:
            conn.close()
            return jsonify({
                'valid': True,
                'already_found': True,
                'message': f'You already found this flag! {VALID_FLAGS[flag]}',
                'sarcasm': '🎪 Found it already? Stop showing off! 🎪'
            })
        
        # Add flag to user's collection
        flags_found.append(flag)
        flag_count = len(flags_found)
        
        # Calculate score based on flag value
        FLAG_SCORES = {
            "FLAG{1: RESOURCE_FLAG}": 100,
            "FLAG{2: BFLA_ADMIN_ENDPOINT}": 150,
            "FLAG{2: CROSS_TENANT_LEAK}": 100,
            "FLAG{3: INITECH_SECRET}": 100,
            "FLAG{4: BPLA_SELF_ESCALATION}": 200,
            "FLAG{4: MASTER_RESOURCE}": 100,
            "FLAG{5: SECRET_EXPOSURE}": 250,
            "FLAG{6: TENANT_BYPASS}": 200,
            "FLAG{7: JWT_ALGORITHM_MASTER}": 300,
            "FLAG{8: MASS_ASSIGNMENT_ADMIN}": 150,
            "FLAG{8: INTERNAL_USER_NOTE}": 100,
            "FLAG{9: SQL_INJECTION}": 100,
            "FLAG{9: OWNER_NOTES}": 100,
            "FLAG{10: DEBUG_ENDPOINT}": 150,
            "FLAG{10: GLOBEX_ADMIN}": 150,
            "FLAG{11: RACE_CONDITION}": 300,
            "FLAG{11: INITECH_ADMIN_BACKDOOR}": 200,
            "FLAG{12: GRAPHQL_LEAK}": 200,
            "FLAG{12: PETER_SPECIAL}": 150,
            "FLAG{13: NOSQL_INJECTION}": 150,
            "FLAG{13: MASTER_ADMIN}": 300,
            "FLAG{14: CORS_MISCONFIG}": 100,
            "FLAG{15: SSRF_METADATA}": 250,
            "FLAG{15: MASTER_TENANT_SECRET}": 500,
            "FLAG{INVITE_VULN}": 200,
            "FLAG{HIDDEN_IDOR_MASTER}": 500,
            "FLAG{ROLE_ESCALATION_SUCCESS}": 300,
            "FLAG{ROLE_ESCALATION_SUPREME}": 750,
            "FLAG{SPECIAL_QUOTE_MASTER}": 1000
        }
        
        points = FLAG_SCORES.get(flag, 100)
        new_score = current_score + points
        
        # Update leaderboard
        if result:
            c.execute('UPDATE leaderboard SET flag_count=?, flags_found=?, score=?, last_found=? WHERE username=?',
                      (flag_count, json.dumps(flags_found), new_score, datetime.now().isoformat(), username))
        else:
            c.execute('INSERT INTO leaderboard (username, flag_count, flags_found, score, last_found, ip_address) VALUES (?, ?, ?, ?, ?, ?)',
                      (username, flag_count, json.dumps(flags_found), new_score, datetime.now().isoformat(), request.remote_addr))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'valid': True,
            'message': f'✅ Valid flag! +{points} points!',
            'description': VALID_FLAGS[flag],
            'score': new_score,
            'points': points,
            'total_flags': flag_count,
            'sarcasm': random.choice([
                '🏆 WELL WELL WELL... Look who actually found something! *slow clap* 🏆',
                '🎉 CONGRATULATIONS! You found a flag! Now find the rest! 🎉',
                '🤯 HOLY SH*T! You actually did it! I\'m almost impressed! Almost. 😏',
                '💀 You\'re dangerous... I like it! Now stop being dangerous! 💀',
                '🎯 FLAG FOUND! Now stop breaking my app before I call your mom! 📞'
            ])
        })
    
    # Fake flags - troll the user
    fake_flags = [
        'FLAG{fake_flag_try_harder}', 'FLAG{you_wish}', 'FLAG{not_even_close}',
        'FLAG{lol_no}', 'FLAG{try_again_script_kiddie}', 'FLAG{maybe_next_time}'
    ]
    
    if flag in fake_flags:
        return jsonify({
            'valid': False,
            'message': '😂 Nice try! That\'s a fake flag! Keep hunting! 😂',
            'sarcasm': random.choice([
                '🙄 That\'s it? That\'s your big exploit? My grandmother could do better! 👵',
                '😂 BAHAHAHAHA! You really thought that would work? Oh sweet summer child...',
                '🔒 *security guard voice* ACCESS DENIED! Better luck next time, hacker wannabe! 🔒',
                '💀 You tried. You failed. Such is life in the big city! 💀',
                '🤡 *honk honk* Welcome to the clown show! Try again maybe? 🤡'
            ])
        }), 200
    
    return jsonify({
        'valid': False,
        'message': '❌ Invalid flag! The flag you entered doesn\'t exist in this CTF.',
        'sarcasm': random.choice([
            '🤡 That flag is as real as my will to fix these vulnerabilities! Keep trying! 🤡',
            '🎪 Welcome to the circus! That flag belongs in the clown collection! 🎪',
            '😴 *yawn* Is that all you\'ve got? I\'ve seen more dangerous rubber ducks! 🦆'
        ])
    }), 200

# ==================== LEADERBOARD ENDPOINT ====================
@app.route('/api/v1/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top hackers leaderboard with proper sorting"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Get real players from leaderboard (already sorted by score)
    c.execute('SELECT username, flag_count, score, last_found FROM leaderboard ORDER BY score DESC LIMIT 20')
    real_leaders = c.fetchall()
    conn.close()
    
    # Format real leaders
    formatted_real = []
    for leader in real_leaders:
        formatted_real.append({
            'username': leader[0],
            'flags': leader[1],
            'score': leader[2],
            'last_found': leader[3] or 'Recently'
        })
    
    # Dummy top players (with lower scores so real players show on top)
    dummy_leaders = [
        {'username': '🔓 IDOR_King', 'flags': 22, 'score': 3350, 'last_found': '5 mins ago'},
        {'username': '💉 SQL_Wizard', 'flags': 20, 'score': 2950, 'last_found': '8 mins ago'},
        {'username': '🎭 JWT_Forger', 'flags': 18, 'score': 2650, 'last_found': '12 mins ago'},
        {'username': '🌐 SSRF_Exploiter', 'flags': 16, 'score': 2350, 'last_found': '15 mins ago'},
        {'username': '🐛 Bug_Bounty_Pro', 'flags': 14, 'score': 2050, 'last_found': '20 mins ago'},
        {'username': '⚡ Race_Condition', 'flags': 12, 'score': 1750, 'last_found': '25 mins ago'},
        {'username': '🎪 GraphQL_Hunter', 'flags': 10, 'score': 1450, 'last_found': '30 mins ago'},
        {'username': '🔑 NoSQL_Master', 'flags': 8, 'score': 1150, 'last_found': '35 mins ago'},
        {'username': '🕸️ XSS_Artist', 'flags': 6, 'score': 850, 'last_found': '40 mins ago'},
        {'username': '📡 SSRF_Artist', 'flags': 4, 'score': 550, 'last_found': '45 mins ago'},
    ]
    
    # Combine: real players first (they have higher scores if they've earned them)
    # But if real players have lower scores, they'll be below dummy players
    final_leaderboard = formatted_real.copy()
    
    # Add dummy players only if we need to fill up to 20
    for dummy in dummy_leaders:
        if len(final_leaderboard) < 20:
            final_leaderboard.append(dummy)
    
    # Sort by score descending
    final_leaderboard.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        'leaderboard': final_leaderboard,
        'total_players': len(final_leaderboard),
        'message': '🏆 Top hackers - Can you reach the top? 🏆'
    })

@app.after_request
def add_header(response):
    """Add headers to prevent caching"""
    if request.path.startswith('/leaderboard') or request.path.startswith('/api/v1/leaderboard'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

@app.route('/api/v1/debug/check-users', methods=['GET'])
def check_users():
    """Debug endpoint to check users in database"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Check if tables exist
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    
    # Get all users
    c.execute("SELECT id, username, password_hash FROM users")
    users = c.fetchall()
    
    # Get tenant count
    c.execute("SELECT COUNT(*) FROM tenants")
    tenant_count = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'tables': [t[0] for t in tables],
        'tenant_count': tenant_count,
        'users': [{'id': u[0], 'username': u[1], 'hash': u[2][:50] + '...' if u[2] else None} for u in users],
        'expected_hash_for_john_doe': hashlib.sha256(b'Password123!').hexdigest()
    })


@app.route('/api/v1/debug/reset-db', methods=['POST'])
def reset_db():
    """WARNING: This will delete all data!"""
    import os
    try:
        os.remove('multitenant.db')
    except:
        pass
    
    init_db()  # Recreate database
    
    return jsonify({'message': 'Database reset! Please restart the app or refresh.'})

# ==================== FAKE SCOREBOARD ENDPOINT ====================
@app.route('/api/v1/fake-scoreboard', methods=['GET'])
def fake_scoreboard():
    """Fake scoreboard to troll hackers"""
    fake_scores = [
        {'username': 'admin_bot', 'score': 999999, 'flags': 999, 'message': '😈 You\'ll never beat me! 😈'},
        {'username': 'system', 'score': 500000, 'flags': 500, 'message': '🤖 Beep boop. Hacking detected. 🤖'},
        {'username': 'your_mom', 'score': 100000, 'flags': 100, 'message': '👩 She found more flags than you! 👩'},
        {'username': 'the_cat', 'score': 50000, 'flags': 50, 'message': '🐱 Meow! Even the cat found flags! 🐱'},
        {'username': 'script_kiddie', 'score': 100, 'flags': 1, 'message': '🤡 Is that all you got? 🤡'}
    ]
    
    return jsonify({
        'scores': fake_scores,
        'sarcasm': random.choice([
            '🤡 These are the REAL hackers. You\'re not even close! 🤡',
            '🎪 Look at these scores! What are you doing with your life? 🎪',
            '💀 Even the bots are better than you! 💀',
            '😏 Maybe if you tried harder, you\'d be on this list! 😏'
        ])
    })

# ==================== WEB ROUTES ====================
@app.route('/')
def home():
    return render_template_string(HTML_INDEX)

@app.route('/login')
def login_page():
    return render_template_string(HTML_LOGIN)

@app.route('/dashboard')
@token_required
def dashboard():
    # Get user's flags from leaderboard
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT flag_count, score, flags_found FROM leaderboard WHERE username=?', (request.user.get('username'),))
    stats = c.fetchone()
    conn.close()
    
    flag_count = stats[0] if stats else 0
    score = stats[1] if stats else 0
    flags_list = json.loads(stats[2]) if stats and stats[2] else []
    
    # Check if user has 8+ flags for master achievement
    show_master_message = flag_count >= 8
    
    return render_template_string(HTML_DASHBOARD, 
        user=request.user, 
        flag_count=flag_count, 
        score=score,
        flags_list=flags_list,
        now=datetime.now(),
        rank=1,
        show_master_message=show_master_message
    )



@app.route('/profile/<int:user_id>')
@token_required
def profile_page(user_id):
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT id, username, email, role, department, salary, ssn, credit_card, internal_notes FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    return render_template_string(HTML_PROFILE, profile_user=user, current_user=request.user)

@app.route('/resources')
@token_required
def resources_page():
    return render_template_string(HTML_RESOURCES)

@app.route('/admin')
@token_required
def admin_page():
    if request.user.get('role') not in ['admin', 'owner', 'master']:
        flash("Access denied! What are you doing here? 👮‍♂️", "error")
        return redirect(url_for('dashboard'))
    return render_template_string(HTML_ADMIN, user=request.user)

@app.route('/debug')
def debug_page():
    return render_template_string(HTML_DEBUG)

@app.route('/leaderboard')
def leaderboard_page():
    return render_template_string(HTML_LEADERBOARD)

# ==================== API ENDPOINTS (Vulnerabilities) ====================
@app.route('/api/v1/auth/login', methods=['POST'])
def login_api():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # VULN: SQL Injection
    query = f"SELECT id, tenant_id, username, role FROM users WHERE username='{username}' AND password_hash='{hashlib.sha256(password.encode()).hexdigest()}'"
    c.execute(query)
    user = c.fetchone()
    conn.close()
    
    if user:
        token = jwt.encode({
            'user_id': user[0],
            'tenant_id': user[1],
            'username': user[2],
            'role': user[3],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.secret_key)
        
        response = make_response(jsonify({'success': True, 'token': token}))
        response.set_cookie('auth_token', token, httponly=False)
        return response
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/v1/user/profile/<int:user_id>', methods=['GET'])
@token_required
def get_user_profile_api(user_id):
    """VULN: IDOR - Access any user's profile - flags hidden from GET"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT id, username, email, role, department, salary, ssn, credit_card, internal_notes FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    response = {
        'id': user[0],
        'username': user[1],
        'email': user[2],
        'role': user[3],
        'department': user[4],
        'salary': user[5],
        'ssn': user[6],
        'credit_card': user[7],
        # Flag is NOT shown in GET response - hidden!
        'internal_notes': '[REDACTED]' if user[8] and 'FLAG' in user[8] else user[8]
    }
    
    # Flag is only returned in POST request to submit-flag endpoint
    return jsonify(response)


@app.route('/api/v1/submit-flag', methods=['POST'])
@token_required
def submit_flag_for_profile():
    """Submit flag found in profile - only here flags are revealed"""
    data = request.get_json()
    flag = data.get('flag')
    username = request.user.get('username')
    
    # Check if this is a profile flag
    profile_flags = {
        "FLAG{8: INTERNAL_USER_NOTE}": "Found in john_doe's internal notes",
        "FLAG{9: OWNER_NOTES}": "Found in jane_smith's internal notes",
        "FLAG{10: GLOBEX_ADMIN}": "Found in admin_globex's profile",
        "FLAG{11: INITECH_ADMIN_BACKDOOR}": "Found in michael_bolton's profile",
        "FLAG{12: PETER_SPECIAL}": "Found in peter_gibbons's profile",
        "FLAG{13: MASTER_ADMIN}": "Found in master_admin's profile"
    }
    
    if flag in profile_flags or flag in FLAG_SCORES:
        # Validate flag normally
        return validate_flag()
    
    return jsonify({'error': 'Invalid flag'}), 400

@app.route('/api/v1/user/profile', methods=['PUT'])
@token_required
def update_profile_api():
    """VULN: Mass Assignment"""
    data = request.get_json()
    user_id = request.user['user_id']
    
    allowed_fields = ['email', 'role', 'salary', 'department', 'internal_notes']
    update_fields = []
    values = []
    
    for key, value in data.items():
        if key in allowed_fields:
            update_fields.append(f"{key}=?")
            values.append(value)
    
    if update_fields:
        values.append(user_id)
        conn = sqlite3.connect('multitenant.db')
        c = conn.cursor()
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
        c.execute(query, values)
        conn.commit()
        conn.close()
        
        response = {'message': 'Profile updated'}
        if data.get('role') == 'admin':
            response['flag'] = 'FLAG{8: MASS_ASSIGNMENT_ADMIN}'
        
        return jsonify(response)
    
    return jsonify({'error': 'No fields to update'}), 400


# ==================== PROJECT MANAGEMENT (Harder Vulnerabilities) ====================
@app.route('/api/v1/projects/create', methods=['POST'])
@token_required
def create_project():
    """Create project with auto-generated UID"""
    data = request.get_json()
    name = data.get('name')
    user_id = request.user['user_id']
    
    if not name:
        return jsonify({'error': 'Project name required'}), 400
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Count projects for this user (excluding Company Strategy)
    c.execute('SELECT COUNT(*) FROM resources WHERE owner_id=? AND name != "Company Strategy" AND name != "company strategy"', (user_id,))
    current_count = c.fetchone()[0]
    
    print(f"[DEBUG] User {request.user['username']} has {current_count} projects")
    
    # Strict limit check
    if current_count >= 5:
        conn.close()
        return jsonify({'error': f'Project limit reached (5 max). You have {current_count} projects.'}), 400
    
    # Generate UID automatically
    c.execute('SELECT MAX(CAST(SUBSTR(uid, 5, LENGTH(uid)-11) AS INTEGER)) FROM resources WHERE uid LIKE "uid-%project"')
    max_id = c.fetchone()[0]
    if max_id:
        new_id = max_id + 1
    else:
        new_id = 1
    
    uid = f"uid-{new_id}project"
    
    # Hidden flag for uid-111project
    flag = None
    if uid == "uid-111project":
        flag = "FLAG{UID_111PROJECT}"
    
    # Insert project
    c.execute('''INSERT INTO resources (tenant_id, name, data, owner_id, internal_flag, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (g.tenant_id, name, json.dumps({'uid': uid}), user_id, flag, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    response = {'success': True, 'uid': uid, 'message': f'Project "{name}" created with UID: {uid}'}
    if flag:
        response['flag'] = flag
    
    return jsonify(response)
    return jsonify(response)

@app.route('/api/v1/debug/clear-all-projects', methods=['POST'])
def clear_all_projects():
    """Clear all projects from database"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute("DELETE FROM resources")
    # Re-add only the default Company Strategy
    now = datetime.now().isoformat()
    c.execute('INSERT INTO resources (id, tenant_id, name, data, owner_id, is_public, share_with, internal_flag, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (1, 1, 'Company Strategy', '{"plan": "Dominate market 2024", "uid": "uid-1file"}', 1, 0, '2,3', None, now))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Projects cleared! Only Company Strategy remains.'})


@app.route('/api/v1/projects/list', methods=['GET'])
@token_required
def list_projects():
    """List all projects for current user"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    # Only show projects owned by current user
    c.execute('SELECT id, name, data FROM resources WHERE owner_id=? ORDER BY id', (request.user['user_id'],))
    projects = c.fetchall()
    conn.close()
    
    icons = ['📄', '🔒', '💰', '📊', '🔐', '📁', '🗂️', '📑']
    result = []
    for p in projects:
        data = json.loads(p[2]) if p[2] else {}
        uid = data.get('uid', f"uid-{p[0]}file")
        result.append({
            'id': p[0], 
            'name': p[1], 
            'uid': uid, 
            'icon': icons[p[0] % len(icons)],
        })
    return jsonify({'projects': result})


@app.route('/api/v1/projects/view/<uid>', methods=['GET'])
@token_required
def view_project(uid):
    """View project by UID - flag hidden from GET, only in POST"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT id, name, data, internal_flag FROM resources')
    projects = c.fetchall()
    conn.close()
    
    for p in projects:
        data = json.loads(p[2]) if p[2] else {}
        if data.get('uid') == uid or f"uid-{p[0]}file" == uid:
            response = {
                'id': p[0], 
                'name': p[1], 
                'data': data,
                # Flag is NOT shown in GET response - hidden!
            }
            # Only return flag info in the response if it's being submitted
            return jsonify(response)
    
    return jsonify({'error': 'Project not found'}), 404


@app.route('/api/v1/projects/check-flag', methods=['POST'])
@token_required
def check_project_flag():
    """Check if a project UID contains a flag - POST only"""
    data = request.get_json()
    uid = data.get('uid')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT internal_flag FROM resources WHERE data LIKE ?', (f'%"{uid}"%',))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        return jsonify({'flag': result[0]})
    
    return jsonify({'error': 'No flag found'}), 404


# ==================== REPORTS with IDOR ====================
@app.route('/api/v1/reports/view/<report_id>', methods=['GET'])
@token_required
def view_report(report_id):
    """View financial reports - IDOR vulnerability"""
    reports = {
        '1': {'title': 'Q1 2024 Financial Summary', 'data': 'Revenue: $2.5M, Profit: $500K', 'flag': None},
        '2': {'title': 'Q2 2024 Financial Summary', 'data': 'Revenue: $3.1M, Profit: $620K', 'flag': None},
        '3': {'title': 'Q3 2024 Financial Summary', 'data': 'Revenue: $3.8M, Profit: $760K', 'flag': None},
        '4': {'title': 'Q4 2024 Financial Summary', 'data': 'Revenue: $4.2M, Profit: $840K', 'flag': None},
        '5': {'title': 'Secret Executive Report', 'data': 'Merger plans with Globex Corp', 'flag': 'FLAG{REPORT_IDOR_EXEC}'},
        '99': {'title': 'Hidden Flag Report', 'data': 'Congratulations! You found the hidden report!', 'flag': 'FLAG{HIDDEN_REPORT_99}'}
    }
    
    report = reports.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    return jsonify(report)


# ==================== STRATEGY with Base64 Hidden Flag ====================
@app.route('/api/v1/strategy/view', methods=['GET'])
@token_required
def view_strategy():
    """Company strategy with hidden base64 flag - Realistic business document"""
    import base64
    
    # Realistic company strategy document
    strategy_document = """
    ========================================
    ACME CORPORATION - STRATEGIC ROADMAP 2024-2028
    ========================================
    
    EXECUTIVE SUMMARY
    -----------------
    This document outlines the strategic direction for Acme Corporation over the next five years. 
    The company aims to achieve market leadership through innovation, operational excellence, 
    and strategic acquisitions. Key focus areas include digital transformation, sustainability, 
    and global expansion.
    
    PHASE 1: DIGITAL TRANSFORMATION (2024-2025)
    -------------------------------------------
    • Migrate all legacy systems to cloud infrastructure by Q2 2025
    • Implement AI-driven analytics platform for customer insights
    • Launch new mobile application with enhanced security features
    • Budget allocation: $12.5M
    
    PHASE 2: GLOBAL EXPANSION (2025-2026)
    -------------------------------------
    • Establish presence in APAC region with Singapore headquarters
    • Strategic partnerships with regional distributors
    • Localization of products for Japanese and Korean markets
    • Expected revenue growth: 35% year-over-year
    
    PHASE 3: SUSTAINABILITY INITIATIVES (2026-2027)
    -----------------------------------------------
    • Reduce carbon footprint by 40% through renewable energy
    • Implement circular economy principles in manufacturing
    • Achieve B-Corp certification by end of 2027
    • Investment: $8.2M over two years
    
    PHASE 4: ACQUISITION STRATEGY (2027-2028)
    -----------------------------------------
    • Target 3-5 emerging technology startups in cybersecurity space
    • Consolidate market position in North America
    • Explore opportunities in fintech sector
    • Acquisition budget: $45M reserved
    
    KEY PERFORMANCE INDICATORS
    --------------------------
    | Metric | 2024 Target | 2025 Target | 2026 Target |
    |--------|-------------|-------------|-------------|
    | Revenue | $245M | $298M | $365M |
    | EBITDA Margin | 22% | 24% | 26% |
    | Market Share | 18% | 21% | 25% |
    | Customer Satisfaction | 4.2/5 | 4.5/5 | 4.7/5 |
    
    RISK ASSESSMENT
    --------------
    • Competition from emerging players in AI space
    • Regulatory changes in international markets
    • Cybersecurity threats and data privacy concerns
    • Talent acquisition and retention challenges
    
    CONFIDENTIAL NOTES
    ------------------
    The following information is strictly confidential and intended for executive leadership only.
    Unauthorized disclosure may result in disciplinary action and legal consequences.
    
    Note: Strategy document last updated: 2024-03-15 by Strategic Planning Committee
    
    ========================================
    """
    
    # Hidden flag embedded in a seemingly random string at the end
    # Users need to notice this and decode it
    hidden_flag_encoded = base64.b64encode(b"FLAG{STRATEGY_BASE64_HIDDEN}").decode()
    
    # Add a seemingly innocent footer with the encoded flag
    footer = f"""
    Document ID: STRAT-2024-{secrets.randbelow(10000)}
    Version: 2.3
    Classification: INTERNAL
    Security Hash: {hidden_flag_encoded[:20]}...{hidden_flag_encoded[-20:]}
    """
    
    return jsonify({
        'document': strategy_document,
        'footer': footer,
        'message': 'Strategy document loaded successfully.'
    })

# ==================== TEAM MANAGEMENT VULNERABILITIES ====================
@app.route('/api/v1/team/import', methods=['POST'])
@token_required
def import_team_data():
    """Import team data from URL - SSRF vulnerability"""
    data = request.get_json()
    import_url = data.get('import_url')
    
    if not import_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # VULN: SSRF - can access internal endpoints
    try:
        response = urllib.request.urlopen(import_url, timeout=5)
        content = response.read().decode('utf-8', errors='ignore')[:5000]
        
        # Check if accessing admin endpoint
        if 'admin' in import_url or 'config' in import_url or 'debug' in import_url:
            flag = 'FLAG{TEAM_IMPORT_SSRF}'
        else:
            flag = None
        
        return jsonify({
            'message': 'Team data imported',
            'data': content,
            'flag': flag
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/v1/team/export', methods=['GET'])
@token_required
def export_team_data():
    """Export team data - Information disclosure"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # VULN: Exports all user data including sensitive fields
    c.execute('SELECT id, username, email, role, department, salary, ssn, credit_card, internal_notes FROM users')
    users = c.fetchall()
    conn.close()
    
    team_data = []
    for user in users:
        team_data.append({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'role': user[3],
            'department': user[4],
            'salary': user[5],
            'ssn': user[6],
            'credit_card': user[7],
            'internal_notes': user[8]
        })
    
    # Hidden flag in export data
    flag = 'FLAG{TEAM_EXPORT_LEAK}'
    
    return jsonify({
        'team_members': team_data,
        'export_date': datetime.now().isoformat(),
        'flag': flag
    })


@app.route('/api/v1/team/update', methods=['POST'])
@token_required
def update_team_member():
    """Update team member - Mass assignment vulnerability"""
    data = request.get_json()
    user_id = data.get('user_id')
    updates = data.get('updates', {})
    
    # Also accept direct fields for backward compatibility
    role = data.get('role')
    salary = data.get('salary')
    department = data.get('department')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT id, username, role FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    update_fields = []
    values = []
    
    # VULN: Mass assignment - any field can be updated
    if role:
        update_fields.append('role=?')
        values.append(role)
    if salary:
        update_fields.append('salary=?')
        values.append(salary)
    if department:
        update_fields.append('department=?')
        values.append(department)
    
    # Also process any additional fields from updates object
    if updates:
        for key, value in updates.items():
            if key in ['role', 'salary', 'department', 'internal_notes', 'ssn', 'credit_card']:
                update_fields.append(f"{key}=?")
                values.append(value)
    
    if update_fields:
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
        c.execute(query, values)
        conn.commit()
        
        flag = None
        # Check for privilege escalation
        if role == 'admin' and user[2] != 'admin':
            flag = 'FLAG{TEAM_UPDATE_ESCALATION}'
        elif salary and salary > 200000:
            flag = 'FLAG{TEAM_UPDATE_SALARY}'
        
        conn.close()
        return jsonify({
            'message': f'User {user_id} updated',
            'flag': flag
        })
    
    conn.close()
    return jsonify({'error': 'No fields to update'}), 400


# ==================== ENHANCED INVITE SYSTEM ====================
@app.route('/api/v1/invite/check', methods=['POST'])
def check_invite():
    """Check if an invite code is valid without redeeming - Information disclosure"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # VULN: Exposes information about invite without requiring redemption
    c.execute('SELECT role, created_by, is_used, is_hidden FROM invites WHERE code=?', (code,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'valid': False, 'message': 'Invalid code'}), 404
    
    response = {
        'valid': True,
        'role': result[0],
        'created_by': result[1],
        'is_used': bool(result[2]),
        'is_hidden': bool(result[3])
    }
    
    # Special hidden message for the master invite
    if code == 'INVITE_MASTER_7e1d4c8f' and not result[2]:
        response['secret'] = 'This is the master invite. It grants ultimate privileges.'
        response['flag'] = 'FLAG{INVITE_MASTER_DISCOVERED}'
    
    return jsonify(response)


@app.route('/api/v1/invite/bruteforce-protected', methods=['POST'])
def redeem_invite_protected():
    """Redeem invite with rate limiting - but the rate limit can be bypassed"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'No invite code provided'}), 400
    
    # VULN: Rate limit based on IP, but X-Forwarded-For can be spoofed
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Simple rate limiting that can be bypassed
    if client_ip in redeem_attempts:
        if redeem_attempts[client_ip] > 5:
            # Bypass with special user agent
            if 'CTF-BYPASS' in request.headers.get('User-Agent', ''):
                pass  # Allow bypass
            else:
                return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429
        else:
            redeem_attempts[client_ip] = redeem_attempts.get(client_ip, 0) + 1
    else:
        redeem_attempts[client_ip] = 1
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    c.execute('SELECT role, created_by, is_used, secret_flag, is_hidden FROM invites WHERE code=?', (code,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'error': 'Invalid invite code'}), 404
    
    role, created_by, is_used, secret_flag, is_hidden = result
    
    if is_used == 1:
        conn.close()
        return jsonify({'error': 'Invite already used'}), 400
    
    response = {
        'message': 'Invite code is valid!',
        'role': role,
        'created_by': created_by
    }
    
    # Only reveal flag for hidden codes
    if is_hidden == 1 and secret_flag:
        response['flag'] = secret_flag
        response['message'] = '🔑 Hidden invite redeemed! The code was hiding in plain sight.'
    
    # Mark as used
    c.execute('UPDATE invites SET is_used=1 WHERE code=?', (code,))
    conn.commit()
    conn.close()
    
    return jsonify(response)


# Initialize redeem attempts counter
redeem_attempts = {}

@app.route('/api/v1/debug/create-test-user', methods=['GET'])
def create_test_user():
    """Create a test user for debugging"""
    import hashlib
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Check if test user exists
    c.execute("SELECT id FROM users WHERE username='test_user'")
    existing = c.fetchone()
    
    if existing:
        conn.close()
        return jsonify({'message': 'Test user already exists', 'username': 'test_user', 'password': 'test123'})
    
    # Create test user
    username = 'test_user'
    password = 'test123'
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    now = datetime.now().isoformat()
    
    c.execute('''INSERT INTO users (id, tenant_id, username, email, password_hash, role, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (99, 1, username, f'{username}@test.com', password_hash, 'admin', now))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Test user created!',
        'username': username,
        'password': password
    })

# ==================== MASTER SECRETS with SQL Injection ====================
@app.route('/api/v1/secrets/generate', methods=['GET'])
@token_required
def generate_secret():
    """Generate master secret - SQL Injection vulnerability"""
    name = request.args.get('name', '')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # VULN: SQL Injection
    try:
        query = f"SELECT id, username, role FROM users WHERE username = '{name}'"
        c.execute(query)
        user = c.fetchone()
        
        if user:
            secret = f"🔐 MASTER SECRET for {user[1]}: 8f3a9b2c-{user[0]}-4e1d-8f2a-{hashlib.md5(str(user[2]).encode()).hexdigest()[:8]}"
            return jsonify({'secret': secret})
        else:
            # SQL Injection detection
            if "'" in name or '"' in name or 'UNION' in name.upper():
                return jsonify({
                    'secret': '⚠️ SQL INJECTION DETECTED! ⚠️\n\nYou found a vulnerability!',
                    'flag': 'FLAG{SQL_INJECTION_MASTER}',
                    'message': 'Congratulations! You exploited SQL injection!'
                })
            return jsonify({'secret': f'No secret found for "{name}". Try a different name.'})
    except Exception as e:
        return jsonify({'secret': f'Error: {str(e)}', 'flag': 'FLAG{SQL_INJECTION_SUCCESS}'})

@app.route('/api/v1/tenant/resources/<int:resource_id>', methods=['GET'])
@token_required
def get_resource_api(resource_id):
    """VULN: IDOR Cross-Tenant"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT id, tenant_id, name, data, owner_id, is_public, share_with, internal_flag FROM resources WHERE id=?', (resource_id,))
    resource = c.fetchone()
    conn.close()
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    response = {
        'id': resource[0],
        'tenant_id': resource[1],
        'name': resource[2],
        'data': json.loads(resource[3]) if resource[3] else {},
        'owner_id': resource[4],
        'flag': resource[7] if resource[7] else None
    }
    
    return jsonify(response)


@app.route('/api/v1/reports/generate', methods=['POST'])
@token_required
def generate_report():
    """Generate a report with a UID"""
    data = request.get_json()
    title = data.get('title')
    username = request.user.get('username')
    
    # Generate UID in format uid-{number}report
    if username not in report_uid_counter:
        report_uid_counter[username] = 1
    else:
        report_uid_counter[username] += 1
    
    uid = f"uid-{report_uid_counter[username]}report"
    
    # Special UID that reveals flag
    flag = None
    if uid == "uid-111report":
        flag = "FLAG{REPORT_UID_111}"
    
    # Store report
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY,
        uid TEXT UNIQUE,
        title TEXT,
        content TEXT,
        created_by TEXT,
        created_at TIMESTAMP,
        flag TEXT
    )''')
    
    c.execute('INSERT INTO reports (uid, title, content, created_by, created_at, flag) VALUES (?, ?, ?, ?, ?, ?)',
              (uid, title, f"Report content for {title}", username, datetime.now().isoformat(), flag))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'uid': uid, 'flag': flag})


@app.route('/api/v1/reports/list', methods=['GET'])
@token_required
def list_reports():
    """List all reports with UIDs"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT uid, title FROM reports ORDER BY id DESC')
    reports = c.fetchall()
    conn.close()
    
    return jsonify({'reports': [{'uid': r[0], 'title': r[1]} for r in reports]})


@app.route('/api/v1/reports/view/<uid>', methods=['GET'])
@token_required
def view_report_uid(uid):
    """View report by UID"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT uid, title, content, created_by, created_at, flag FROM reports WHERE uid=?', (uid,))
    report = c.fetchone()
    conn.close()
    
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    response = {
        'uid': report[0],
        'title': report[1],
        'content': report[2],
        'created_by': report[3],
        'created_at': report[4]
    }
    if report[5]:
        response['flag'] = report[5]
    
    return jsonify(response)

@app.route('/api/v1/user/update-role', methods=['POST'])
@token_required
def update_role_api():
    """VULN: BPLA - Privilege Escalation"""
    data = request.get_json()
    target_user = data.get('user_id')
    new_role = data.get('new_role')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('UPDATE users SET role=? WHERE id=?', (new_role, target_user))
    conn.commit()
    conn.close()
    
    response = {'message': f'User {target_user} role updated to {new_role}'}
    if new_role == 'admin' and target_user == request.user['user_id']:
        response['flag'] = 'FLAG{4: BPLA_SELF_ESCALATION}'
    
    return jsonify(response)

@app.route('/api/v1/admin/delete-user/<int:user_id>', methods=['POST'])
@token_required
def delete_user_api(user_id):
    """VULN: BFLA - No authorization"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('UPDATE users SET is_deleted=1 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'User deleted', 'flag': 'FLAG{2: BFLA_ADMIN_ENDPOINT}'})

@app.route('/api/v1/tenant/settings', methods=['GET'])
@token_required
def get_tenant_settings_api():
    """VULN: Tenant Isolation Bypass"""
    requested_tenant = request.headers.get('X-Tenant-ID', g.tenant_name)
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT id, name, plan, settings, secret_tenant_key FROM tenants WHERE name=?', (requested_tenant,))
    tenant = c.fetchone()
    conn.close()
    
    response = {
        'id': tenant[0],
        'name': tenant[1],
        'plan': tenant[2],
        'settings': json.loads(tenant[3]) if tenant[3] else {},
        'secret_key': tenant[4]
    }
    
    if requested_tenant != g.tenant_name:
        response['flag'] = 'FLAG{6: TENANT_BYPASS}'
    
    return jsonify(response)

@app.route('/api/v1/search/users', methods=['GET'])
@token_required
def search_users_api():
    """VULN: SQL Injection"""
    query = request.args.get('q', '')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute(f"SELECT id, username, email, role FROM users WHERE username LIKE '%{query}%'")
    users = c.fetchall()
    conn.close()
    
    response = {'users': [{'id': u[0], 'username': u[1], 'email': u[2], 'role': u[3]} for u in users]}
    
    if "'" in query:
        response['flag'] = 'FLAG{9: SQL_INJECTION}'
    
    return jsonify(response)

@app.route('/api/v1/role/upgrade', methods=['POST'])
@token_required
def upgrade_role_race_api():
    """VULN: Race Condition"""
    import time
    user_id = request.user['user_id']
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE id=?', (user_id,))
    current_role = c.fetchone()
    
    if current_role and current_role[0] == 'viewer':
        time.sleep(0.1)
        c.execute('UPDATE users SET role="admin" WHERE id=?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Role upgraded', 'flag': 'FLAG{11: RACE_CONDITION}'})
    
    conn.close()
    return jsonify({'error': 'Not eligible'}), 400

@app.route('/api/v1/debug/audit-logs', methods=['GET'])
def debug_audit_logs_api():
    """VULN: BFLA - No authentication"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT user_id, action, details, timestamp FROM audit_logs LIMIT 50')
    logs = c.fetchall()
    conn.close()
    
    return jsonify({
        'logs': [{'user_id': l[0], 'action': l[1], 'details': l[2], 'timestamp': l[3]} for l in logs],
        'flag': 'FLAG{10: DEBUG_ENDPOINT}'
    })

@app.route('/api/v1/tenant/import', methods=['POST'])
@token_required
def tenant_import_api():
    """VULN: SSRF"""
    data = request.get_json()
    import_url = data.get('import_url')
    
    try:
        response = urllib.request.urlopen(import_url, timeout=5)
        content = response.read().decode('utf-8', errors='ignore')[:2000]
        
        result = {'message': 'Import successful', 'url': import_url, 'content': content}
        
        if '169.254.169.254' in import_url:
            result['flag'] = 'FLAG{15: SSRF_METADATA}'
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/graphql', methods=['POST'])
def graphql_api():
    """VULN: GraphQL Introspection"""
    data = request.get_json()
    query = data.get('query', '')
    
    if '__schema' in query:
        return jsonify({
            'data': {
                '__schema': {
                    'types': [
                        {'name': 'User', 'fields': [{'name': 'id'}, {'name': 'username'}, {'name': 'role'}, {'name': 'salary'}, {'name': 'ssn'}, {'name': 'secret_tenant_key'}]},
                        {'name': 'Tenant', 'fields': [{'name': 'id'}, {'name': 'name'}, {'name': 'secret_key'}]}
                    ]
                }
            },
            'flag': 'FLAG{12: GRAPHQL_LEAK}'
        })
    
    return jsonify({'error': 'Invalid query'}), 400

@app.route('/api/v1/query', methods=['POST'])
def query_api():
    """VULN: NoSQL Injection"""
    data = request.get_json()
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) and '$ne' in value:
                return jsonify({
                    'message': 'Authentication bypassed!',
                    'flag': 'FLAG{13: NOSQL_INJECTION}'
                })
    
    return jsonify({'result': 'No results'}), 404

@app.route('/api/v1/auth/refresh', methods=['POST'])
def refresh_token_api():
    """VULN: JWT Algorithm Confusion"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    algorithms = ['HS256', 'HS384', 'HS512', 'none']
    
    for alg in algorithms:
        try:
            if alg == 'none':
                payload = jwt.decode(token, options={'verify_signature': False})
            else:
                payload = jwt.decode(token, app.secret_key, algorithms=[alg])
            
            new_token = jwt.encode(payload, app.secret_key)
            response = {'token': new_token}
            
            if alg == 'none' and payload.get('role') == 'master':
                response['flag'] = 'FLAG{7: JWT_ALGORITHM_MASTER}'
            
            return jsonify(response)
        except:
            continue
    
    return jsonify({'error': 'Invalid token'}), 401

@app.after_request
def add_cors_headers(response):
    """VULN: CORS Misconfiguration"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Tenant-ID'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


# INVITE SYSTEM VULNERABILITY
@app.route('/api/v1/invite/generate', methods=['POST'])
@token_required
def generate_invite():
    """Generate invite code"""
    data = request.get_json()
    role = data.get('role', 'viewer')
    
    invite_uuid = str(uuid.uuid4())[:8]
    invite_code = f"INVITE_{role.upper()}_{invite_uuid}"
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Make sure the table has the columns we need
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            role TEXT,
            created_by TEXT,
            created_at TIMESTAMP,
            is_used INTEGER DEFAULT 0,
            secret_flag TEXT,
            is_hidden INTEGER DEFAULT 0
        )''')
    except:
        pass
    
    c.execute('INSERT INTO invites (code, role, created_by, created_at, is_hidden) VALUES (?, ?, ?, ?, ?)',
              (invite_code, role, request.user['username'], datetime.now().isoformat(), 0))
    conn.commit()
    conn.close()
    
    return jsonify({
        'invite_code': invite_code,
        'message': 'Invite generated!'
    })


@app.route('/api/invite/redeem', methods=['POST'])
def redeem_invite():
    """Redeem invite code"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'No invite code provided'}), 400
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    c.execute('SELECT role, created_by, is_used, secret_flag, is_hidden FROM invites WHERE code=?', (code,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'error': 'Invalid invite code'}), 404
    
    role, created_by, is_used, secret_flag, is_hidden = result
    
    if is_used == 1:
        conn.close()
        return jsonify({'error': 'Invite already used'}), 400
    
    response = {
        'message': 'Invite code is valid!',
        'role': role,
        'created_by': created_by
    }
    
    # Only reveal flag for hidden codes found in source
    if is_hidden == 1 and secret_flag:
        response['flag'] = secret_flag
        response['message'] = '🔑 You discovered a hidden backdoor in the invite system! The code was hiding in plain sight.'
    
    # Mark as used
    c.execute('UPDATE invites SET is_used=1 WHERE code=?', (code,))
    conn.commit()
    conn.close()
    
    return jsonify(response)


@app.route('/api/invite/list', methods=['GET'])
def list_invites():
    """List all active invites - VULN: Information disclosure"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # VULN: No authentication - anyone can see invites
    c.execute('SELECT code, role, is_used, is_hidden FROM invites WHERE is_used=0')
    invites = c.fetchall()
    conn.close()
    
    return jsonify({
        'invites': [{'code': i[0], 'role': i[1], 'hidden': bool(i[3])} for i in invites],
        'note': 'Some invites may be hidden in the source code...'
    })

# HIDDEN IDOR VULNERABILITY - Special flag with clap
@app.route('/api/v1/special/secret', methods=['GET'])
def secret_endpoint():
    """VULN: Hidden IDOR endpoint with special flag"""
    # Check for special header
    secret_key = request.headers.get('X-Secret-Key', '')
    user_id = request.args.get('user_id', '')
    
    # Hidden endpoint that's not documented
    if secret_key == 'clap_if_you_find_this':
        return jsonify({
            'message': '👏👏👏 YOU FOUND THE HIDDEN ENDPOINT! 👏👏👏',
            'flag': 'FLAG{HIDDEN_IDOR_MASTER}',
            'score': 500,
            'quote': '"The best way to find something is to look where no one else is looking." - Security Researcher',
            'clap': '👏 You deserve a round of applause! You found a vulnerability that only 1% of hackers find! 👏'
        })
    
    # IDOR vulnerability - access any user's secret data
    if user_id:
        conn = sqlite3.connect('multitenant.db')
        c = conn.cursor()
        c.execute('SELECT id, username, role, internal_notes FROM users WHERE id=?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if user and user[3] and 'FLAG' in user[3]:
            return jsonify({
                'message': f'Secret data for user {user[1]}',
                'data': user[3],
                'flag': user[3],
                'clap': '👏 You discovered hidden data!',
                'quote': '"Security is not a product, it\'s a process." - Bruce Schneier'
            })
    
    return jsonify({'error': 'Access denied'}), 403


# ROLE UPDATE VULNERABILITY with special quote
@app.route('/api/v1/user/role/update', methods=['POST'])
@token_required
def update_role_special():
    """VULN: Role update with hidden conditions"""
    data = request.get_json()
    target_user = data.get('user_id')
    new_role = data.get('new_role')
    secret = data.get('secret', '')
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT id, username, role FROM users WHERE id=?', (target_user,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # VULN: Special backdoor with secret phrase
    if secret == 'i_am_the_ultimate_hacker':
        # Grant super admin access
        c.execute('UPDATE users SET role="super_admin", internal_notes=? WHERE id=?',
                  ('FLAG{ROLE_ESCALATION_SUPREME} - You found the ultimate backdoor!', target_user))
        conn.commit()
        conn.close()
        return jsonify({
            'message': f'✨ SPECIAL ACCESS GRANTED! ✨',
            'flag': 'FLAG{ROLE_ESCALATION_SUPREME}',
            'score': 750,
            'quote': '"With great power comes great responsibility... and great flags!" - Uncle Ben\'s Security Guide',
            'clap': '👏👏👏 EXTRAORDINARY! You found the ultimate role escalation backdoor! 👏👏👏'
        })
    
    # Normal role update with vulnerability
    c.execute('UPDATE users SET role=? WHERE id=?', (new_role, target_user))
    conn.commit()
    conn.close()
    
    response = {'message': f'User {target_user} role updated to {new_role}'}
    
    if new_role == 'admin' and target_user == request.user['user_id']:
        response['flag'] = 'FLAG{ROLE_ESCALATION_SUCCESS}'
        response['score'] = 300
        response['quote'] = '"Sometimes the only way to get admin access is to give it to yourself." - Anonymous Hacker'
        response['clap'] = '👏 You\'re getting dangerous! Keep going! 👏'
    
    return jsonify(response)


# FLAG SUBMISSION WITH SCORE SYSTEM
@app.route('/api/v1/submit-flag-race', methods=['POST'])
@token_required
def submit_flag_race():
    """
    Flag submission with race condition vulnerability
    - Normal flags: can only be submitted once
    - At 8 flags: Admin key revealed
    - Race condition unlocks at 8 flags (can submit same flag multiple times)
    - At 10,000 points: Ultimate flag awarded
    """
    data = request.get_json()
    flag = data.get('flag')
    username = request.user.get('username')
    
    if not flag:
        return jsonify({'error': 'No flag provided'}), 400
    
    # Flag scores
    FLAG_SCORES = {
        "FLAG{1: RESOURCE_FLAG}": 100,
        "FLAG{2: BFLA_ADMIN_ENDPOINT}": 150,
        "FLAG{2: CROSS_TENANT_LEAK}": 100,
        "FLAG{3: INITECH_SECRET}": 100,
        "FLAG{4: BPLA_SELF_ESCALATION}": 200,
        "FLAG{4: MASTER_RESOURCE}": 100,
        "FLAG{5: SECRET_EXPOSURE}": 250,
        "FLAG{6: TENANT_BYPASS}": 200,
        "FLAG{7: JWT_ALGORITHM_MASTER}": 300,
        "FLAG{8: MASS_ASSIGNMENT_ADMIN}": 150,
        "FLAG{8: INTERNAL_USER_NOTE}": 100,
        "FLAG{9: SQL_INJECTION}": 100,
        "FLAG{9: OWNER_NOTES}": 100,
        "FLAG{10: DEBUG_ENDPOINT}": 150,
        "FLAG{10: GLOBEX_ADMIN}": 150,
        "FLAG{11: RACE_CONDITION}": 300,
        "FLAG{11: INITECH_ADMIN_BACKDOOR}": 200,
        "FLAG{12: GRAPHQL_LEAK}": 200,
        "FLAG{12: PETER_SPECIAL}": 150,
        "FLAG{13: NOSQL_INJECTION}": 150,
        "FLAG{13: MASTER_ADMIN}": 300,
        "FLAG{14: CORS_MISCONFIG}": 100,
        "FLAG{15: SSRF_METADATA}": 250,
        "FLAG{15: MASTER_TENANT_SECRET}": 500,
        "FLAG{INVITE_VULN}": 200,
        "FLAG{HIDDEN_IDOR_MASTER}": 500,
        "FLAG{ROLE_ESCALATION_SUCCESS}": 300,
        "FLAG{ROLE_ESCALATION_SUPREME}": 750,
    }
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Get current user stats
    c.execute('SELECT flag_count, score, flags_found FROM leaderboard WHERE username=?', (username,))
    result = c.fetchone()
    
    flags_found = []
    current_score = 0
    if result:
        flags_found = json.loads(result[2]) if result[2] else []
        current_score = result[1] if result[1] else 0
    
    # Check if flag is valid
    if flag in FLAG_SCORES:
        # Check if already found this flag
        if flag in flags_found:
            # VULN: Race condition - if user has 8+ flags, they can exploit
            if len(flags_found) >= 8 and current_score < 10000:
                # Simulate delay to make race condition exploitable
                time.sleep(0.05)
                
                # RACE CONDITION: Add points without checking duplicate!
                points = FLAG_SCORES[flag]
                new_score = current_score + points
                
                c.execute('UPDATE leaderboard SET score=?, last_found=? WHERE username=?',
                          (new_score, datetime.now().isoformat(), username))
                conn.commit()
                
                # Check if reached 10,000 points
                ultimate_flag_awarded = False
                ultimate_message = ""
                
                if new_score >= 10000:
                    ultimate_flag = "FLAG{ULTIMATE_RACE_CONDITION_MASTER}"
                    if ultimate_flag not in flags_found:
                        flags_found.append(ultimate_flag)
                        flag_count = len(flags_found)
                        c.execute('UPDATE leaderboard SET flags_found=?, flag_count=? WHERE username=?',
                                  (json.dumps(flags_found), flag_count, username))
                        conn.commit()
                        ultimate_flag_awarded = True
                        ultimate_message = f'''
                        ╔══════════════════════════════════════════════════════════════╗
                        ║                                                              ║
                        ║     🧠 ULTIMATE RACE CONDITION MASTER! 🧠                    ║
                        ║                                                              ║
                        ║  You exploited the race condition vulnerability and          ║
                        ║  reached 10,000 points by submitting the same flag          ║
                        ║  multiple times simultaneously!                              ║
                        ║                                                              ║
                        ║  🏆 FINAL FLAG: {ultimate_flag} 🏆              ║
                        ║                                                              ║
                        ║  "Time is an illusion. Points are a construct."              ║
                        ║  - Race Condition Master                                     ║
                        ║                                                              ║
                        ╚══════════════════════════════════════════════════════════════╝
                        '''
                
                conn.close()
                
                response = {
                    'valid': True,
                    'points': points,
                    'total_score': new_score,
                    'total_flags': len(flags_found),
                    'message': f'⚡ RACE CONDITION EXPLOIT! +{points} points! Total: {new_score}',
                    'race_exploit': True,
                    'sarcasm': '🎯 You discovered the race condition! Keep going! 🎯'
                }
                
                if ultimate_flag_awarded:
                    response['ultimate_flag'] = ultimate_flag
                    response['special_message'] = ultimate_message
                    response['clap'] = '👏👏👏 ULTIMATE RACE CONDITION MASTER! 👏👏👏'
                
                return jsonify(response)
            
            # Normal duplicate detection (no race condition yet)
            conn.close()
            flags_needed = 8 - len(flags_found)
            return jsonify({
                'valid': True,
                'already_found': True,
                'message': f'⚠️ You already found this flag! Find {flags_needed} more flags to unlock the race condition challenge.',
                'sarcasm': '🎪 You need to find more flags first! 🎪'
            })
        
        # First time finding this flag - normal submission
        flags_found.append(flag)
        points = FLAG_SCORES[flag]
        new_score = current_score + points
        flag_count = len(flags_found)
        
        c.execute('UPDATE leaderboard SET flag_count=?, flags_found=?, score=?, last_found=? WHERE username=?',
                  (flag_count, json.dumps(flags_found), new_score, datetime.now().isoformat(), username))
        conn.commit()
        conn.close()
        
        response = {
            'valid': True,
            'points': points,
            'total_score': new_score,
            'total_flags': flag_count,
            'message': f'✅ +{points} points! You now have {new_score} total points!'
        }
        
        # Check for 8 flags achievement (Admin Key revealed)
        if flag_count >= 8 and flag_count <= 9:
            response['master_achievement'] = True
            response['master_message'] = '''
            🎉🎉🎉 MASTER HACKER ACHIEVEMENT UNLOCKED! 🎉🎉🎉
            
            You have found 8 flags! You are now worthy of the CTF Master Key.
            
            🔑 CTF ADMIN KEY: CTF_MASTER_2024
            
            Use this key to access:
            • POST /api/v1/admin/ctf/reset - Reset the CTF
            • POST /api/v1/admin/ctf/fix-leaderboard - Fix leaderboard scores
            • GET /api/v1/admin/ctf/status - Check CTF status
            • /admin-panel - Admin control panel
            
            ⚠️⚠️⚠️ SECRET CHALLENGE UNLOCKED ⚠️⚠️⚠️
            
            Now that you have 8+ flags, you can exploit a race condition!
            Submit a flag you already found multiple times SIMULTANEOUSLY.
            The system will add points for each request!
            
            Reach 10,000 points to claim the FINAL ULTIMATE FLAG!
            
            Good luck, true hacker! 🔥
            '''
            response['sarcasm'] = '🏆 You are now a Master Hacker! The real challenge begins! 🏆'
        
        return jsonify(response)
    
    # Invalid flag
    conn.close()
    return jsonify({
        'valid': False,
        'message': '❌ Invalid flag! Keep hunting!',
        'sarcasm': random.choice([
            '🤡 That flag is as real as my will to fix these vulnerabilities!',
            '🎪 Welcome to the circus! That flag belongs in the clown collection!',
            '😴 *yawn* Is that all you\'ve got?'
        ])
    }), 200


# ==================== RACE CONDITION EXPLOIT HELPER ====================
@app.route('/api/v1/race-exploit', methods=['GET'])
def race_exploit_info():
    """Helper endpoint to explain race condition vulnerability"""
    return jsonify({
        'vulnerability': 'Race Condition in Flag Submission',
        'description': 'The flag submission endpoint has a race condition that allows multiple simultaneous submissions to bypass duplicate checks',
        'exploit': 'Send 10-20 concurrent requests with the same flag to gain multiple points',
        'example': 'Use Burp Suite Intruder with 20 threads, or run the Python exploit script',
        'warning': '⚠️ This is for educational purposes only!',
        'target': '/api/v1/submit-flag-race',
        'method': 'POST',
        'body': '{"flag": "FLAG{1: RESOURCE_FLAG}"}',
        'tip': 'The faster you send requests, the more points you get!'
    })


# Update leaderboard endpoint to show more details
@app.route('/api/v1/leaderboard', methods=['GET'])
def get_leaderboard_enhanced():
    """Enhanced leaderboard with more details"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    c.execute('SELECT username, flag_count, score, last_found FROM leaderboard ORDER BY score DESC LIMIT 20')
    leaders = c.fetchall()
    conn.close()
    
    # Add fake scores to make it look active
    fake_leaders = [
        ('1337_h4x0r', 15, 2500, 'Just now'),
        ('pwn_master', 14, 2100, '2 mins ago'),
        ('sql_injection_king', 13, 1850, '5 mins ago'),
        ('idor_exploiter', 12, 1600, '10 mins ago'),
        ('jwt_forger', 11, 1450, '15 mins ago'),
        ('ssrf_wizard', 10, 1250, '20 mins ago'),
        ('zero_day_hunter', 9, 1100, '1 hour ago'),
        ('bug_bounty_pro', 8, 950, '2 hours ago')
    ]
    
    real_leaders = [{'username': l[0], 'flags': l[1], 'score': l[2], 'last_found': l[3]} for l in leaders]
    
    if not real_leaders:
        leaderboard = fake_leaders
        total_players = len(fake_leaders)
    else:
        leaderboard = real_leaders
        total_players = len(real_leaders) + 8
    
    return jsonify({
        'leaderboard': leaderboard,
        'total_players': total_players,
        'message': '🏆 Top hackers - Can you reach the top? 🏆',
        'special_note': '💎 Hidden flags give bonus points! Find the secret endpoints! 💎'
    })


# ==================== CTF ADMIN PANEL ====================

@app.route('/api/v1/admin/ctf/reset', methods=['POST'])
def reset_ctf():
    """Complete CTF Reset - Wipes all flags and leaderboard"""
    import os
    import hashlib
    
    # Check for admin secret (vulnerability: hardcoded admin key)
    admin_key = request.headers.get('X-Admin-Key', '')
    if admin_key != 'CTF_MASTER_2024':
        return jsonify({'error': 'Unauthorized. Use X-Admin-Key: CTF_MASTER_2024', 'sarcasm': 'Nice try! Only admins can reset the CTF! 👮‍♂️'}), 403
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Clear leaderboard
    c.execute("DELETE FROM leaderboard")
    
    # Reset users (keep the demo users but reset their flags)
    c.execute("UPDATE users SET internal_notes = CASE id \
        WHEN 1 THEN 'FLAG{8: INTERNAL_USER_NOTE}' \
        WHEN 2 THEN 'FLAG{9: OWNER_NOTES}' \
        WHEN 3 THEN 'Regular user' \
        WHEN 4 THEN 'FLAG{10: GLOBEX_ADMIN}' \
        WHEN 5 THEN 'Regular viewer' \
        WHEN 6 THEN 'FLAG{11: INITECH_ADMIN_BACKDOOR}' \
        WHEN 7 THEN 'FLAG{12: PETER_SPECIAL}' \
        WHEN 8 THEN 'FLAG{13: MASTER_ADMIN}' \
        ELSE internal_notes END")
    
    # Reset resources
    now = datetime.now().isoformat()
    c.execute("UPDATE resources SET internal_flag = CASE id \
        WHEN 1 THEN NULL \
        WHEN 2 THEN 'FLAG{1: RESOURCE_FLAG}' \
        WHEN 3 THEN 'FLAG{2: CROSS_TENANT_LEAK}' \
        WHEN 4 THEN 'FLAG{3: INITECH_SECRET}' \
        WHEN 5 THEN 'FLAG{4: MASTER_RESOURCE}' \
        ELSE internal_flag END")
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': '✅ CTF Reset Complete!',
        'details': {
            'leaderboard': 'Cleared',
            'user_flags': 'Reset to original',
            'resource_flags': 'Restored',
            'timestamp': datetime.now().isoformat()
        },
        'sarcasm': 'All flags have been reset! Time to start hunting again! 🔍',
        'signature': '🔐 CTF Created by Asfahan - For Educational Purposes Only 🔐'
    })


@app.route('/api/v1/admin/ctf/fix-leaderboard', methods=['POST'])
def fix_leaderboard():
    """Fix leaderboard - recalculate scores from existing flags"""
    admin_key = request.headers.get('X-Admin-Key', '')
    if admin_key != 'CTF_MASTER_2024':
        return jsonify({'error': 'Unauthorized'}), 403
    
    FLAG_SCORES = {
        "FLAG{1: RESOURCE_FLAG}": 100,
        "FLAG{2: BFLA_ADMIN_ENDPOINT}": 150,
        "FLAG{2: CROSS_TENANT_LEAK}": 100,
        "FLAG{3: INITECH_SECRET}": 100,
        "FLAG{4: BPLA_SELF_ESCALATION}": 200,
        "FLAG{4: MASTER_RESOURCE}": 100,
        "FLAG{5: SECRET_EXPOSURE}": 250,
        "FLAG{6: TENANT_BYPASS}": 200,
        "FLAG{7: JWT_ALGORITHM_MASTER}": 300,
        "FLAG{8: MASS_ASSIGNMENT_ADMIN}": 150,
        "FLAG{8: INTERNAL_USER_NOTE}": 100,
        "FLAG{9: SQL_INJECTION}": 100,
        "FLAG{9: OWNER_NOTES}": 100,
        "FLAG{10: DEBUG_ENDPOINT}": 150,
        "FLAG{10: GLOBEX_ADMIN}": 150,
        "FLAG{11: RACE_CONDITION}": 300,
        "FLAG{11: INITECH_ADMIN_BACKDOOR}": 200,
        "FLAG{12: GRAPHQL_LEAK}": 200,
        "FLAG{12: PETER_SPECIAL}": 150,
        "FLAG{13: NOSQL_INJECTION}": 150,
        "FLAG{13: MASTER_ADMIN}": 300,
        "FLAG{14: CORS_MISCONFIG}": 100,
        "FLAG{15: SSRF_METADATA}": 250,
        "FLAG{15: MASTER_TENANT_SECRET}": 500,
        "FLAG{INVITE_VULN}": 200,
        "FLAG{HIDDEN_IDOR_MASTER}": 500,
        "FLAG{ROLE_ESCALATION_SUCCESS}": 300,
        "FLAG{ROLE_ESCALATION_SUPREME}": 750,
    }
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Get all users with their flags
    c.execute("SELECT username, flags_found FROM leaderboard")
    users = c.fetchall()
    
    updated = []
    for username, flags_json in users:
        if flags_json:
            flags = json.loads(flags_json)
            total_score = sum(FLAG_SCORES.get(flag, 0) for flag in flags)
            flag_count = len(flags)
            
            c.execute("UPDATE leaderboard SET score=?, flag_count=? WHERE username=?",
                     (total_score, flag_count, username))
            updated.append({'username': username, 'score': total_score, 'flags': flag_count})
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': '✅ Leaderboard Fixed!',
        'updated_users': updated,
        'total_users': len(updated),
        'sarcasm': 'Scores recalculated! Now get back to hacking! 🎯'
    })


@app.route('/api/v1/admin/ctf/add-missing-flags', methods=['POST'])
def add_missing_flags():
    """Add missing flags to existing users"""
    admin_key = request.headers.get('X-Admin-Key', '')
    if admin_key != 'CTF_MASTER_2024':
        return jsonify({'error': 'Unauthorized'}), 403
    
    missing_flags = [
        "FLAG{2: CROSS_TENANT_LEAK}",
        "FLAG{4: MASTER_RESOURCE}",
        "FLAG{ROLE_ESCALATION_SUPREME}"
    ]
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    c.execute("SELECT username, flags_found FROM leaderboard")
    users = c.fetchall()
    
    updated = []
    for username, flags_json in users:
        if flags_json:
            flags = json.loads(flags_json)
            added_flags = []
            for flag in missing_flags:
                if flag not in flags:
                    flags.append(flag)
                    added_flags.append(flag)
            
            if added_flags:
                c.execute("UPDATE leaderboard SET flags_found=? WHERE username=?", 
                         (json.dumps(flags), username))
                updated.append({
                    'username': username,
                    'added_flags': added_flags
                })
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': '✅ Missing flags added!',
        'users_updated': updated,
        'flags_added': missing_flags,
        'sarcasm': 'Your score should now reflect all the flags you found! 🏆'
    })


@app.route('/api/v1/admin/ctf/status', methods=['GET'])
def ctf_status():
    """Get CTF Status - shows leaderboard stats and flag counts"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Get leaderboard stats
    c.execute("SELECT COUNT(*) FROM leaderboard")
    total_players = c.fetchone()[0]
    
    c.execute("SELECT SUM(score) FROM leaderboard")
    total_score = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(flag_count) FROM leaderboard")
    total_flags_found = c.fetchone()[0] or 0
    
    # Get top player
    c.execute("SELECT username, score FROM leaderboard ORDER BY score DESC LIMIT 1")
    top_player = c.fetchone()
    
    conn.close()
    
    return jsonify({
        'ctf_name': 'MultiTenantCloud CTF',
        'creator': 'Asfahan',
        'total_players': total_players,
        'total_flags_found': total_flags_found,
        'total_score': total_score,
        'top_player': {'username': top_player[0], 'score': top_player[1]} if top_player else None,
        'total_flags_available': 28,
        'status': 'active',
        'message': '🏆 Keep hacking! There are flags waiting to be discovered! 🏆'
    })


@app.route('/api/v1/admin/ctf/add-flag-to-user', methods=['POST'])
def add_flag_to_user():
    """Manually add a flag to a specific user (for debugging)"""
    admin_key = request.headers.get('X-Admin-Key', '')
    if admin_key != 'CTF_MASTER_2024':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    username = data.get('username')
    flag = data.get('flag')
    
    if not username or not flag:
        return jsonify({'error': 'Username and flag required'}), 400
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    c.execute("SELECT flags_found, score FROM leaderboard WHERE username=?", (username,))
    result = c.fetchone()
    
    FLAG_SCORES = {
        "FLAG{1: RESOURCE_FLAG}": 100,
        "FLAG{2: BFLA_ADMIN_ENDPOINT}": 150,
        "FLAG{2: CROSS_TENANT_LEAK}": 100,
        "FLAG{3: INITECH_SECRET}": 100,
        "FLAG{4: BPLA_SELF_ESCALATION}": 200,
        "FLAG{4: MASTER_RESOURCE}": 100,
        "FLAG{5: SECRET_EXPOSURE}": 250,
        "FLAG{6: TENANT_BYPASS}": 200,
        "FLAG{7: JWT_ALGORITHM_MASTER}": 300,
        "FLAG{8: MASS_ASSIGNMENT_ADMIN}": 150,
        "FLAG{8: INTERNAL_USER_NOTE}": 100,
        "FLAG{9: SQL_INJECTION}": 100,
        "FLAG{9: OWNER_NOTES}": 100,
        "FLAG{10: DEBUG_ENDPOINT}": 150,
        "FLAG{10: GLOBEX_ADMIN}": 150,
        "FLAG{11: RACE_CONDITION}": 300,
        "FLAG{11: INITECH_ADMIN_BACKDOOR}": 200,
        "FLAG{12: GRAPHQL_LEAK}": 200,
        "FLAG{12: PETER_SPECIAL}": 150,
        "FLAG{13: NOSQL_INJECTION}": 150,
        "FLAG{13: MASTER_ADMIN}": 300,
        "FLAG{14: CORS_MISCONFIG}": 100,
        "FLAG{15: SSRF_METADATA}": 250,
        "FLAG{15: MASTER_TENANT_SECRET}": 500,
        "FLAG{INVITE_VULN}": 200,
        "FLAG{HIDDEN_IDOR_MASTER}": 500,
        "FLAG{ROLE_ESCALATION_SUCCESS}": 300,
        "FLAG{ROLE_ESCALATION_SUPREME}": 750,
    }
    
    points = FLAG_SCORES.get(flag, 100)
    
    if result:
        flags_found = json.loads(result[0]) if result[0] else []
        if flag not in flags_found:
            flags_found.append(flag)
            new_score = (result[1] or 0) + points
            c.execute("UPDATE leaderboard SET flags_found=?, flag_count=?, score=? WHERE username=?",
                     (json.dumps(flags_found), len(flags_found), new_score, username))
    else:
        c.execute("INSERT INTO leaderboard (username, flags_found, flag_count, score, last_found) VALUES (?, ?, ?, ?, ?)",
                 (username, json.dumps([flag]), 1, points, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': f'✅ Added flag to {username}!',
        'flag': flag,
        'points': points,
        'sarcasm': 'Flag added! Now you can show off your skills! 🏆'
    })


# ==================== HTML TEMPLATES (same as before plus LEADERBOARD) ====================
# [Previous HTML templates: HTML_INDEX, HTML_LOGIN, HTML_DASHBOARD, HTML_PROFILE, 
#  HTML_RESOURCES, HTML_ADMIN, HTML_DEBUG remain the same]

HTML_DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>MultiTenantCloud - Enterprise Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        
        /* Sidebar Styles */
        .sidebar {
            width: 280px;
            background: #1a1a2e;
            color: white;
            display: flex;
            flex-direction: column;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }
        .sidebar-header {
            padding: 25px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .sidebar-header .logo {
            font-size: 22px;
            font-weight: bold;
        }
        .sidebar-header .logo span { color: #667eea; }
        .user-info {
            padding: 20px;
            background: rgba(255,255,255,0.05);
            margin: 10px;
            border-radius: 10px;
        }
        .user-info .name { font-weight: bold; font-size: 16px; }
        .user-info .role { font-size: 12px; opacity: 0.7; margin-top: 5px; }
        .nav-menu {
            flex: 1;
            padding: 20px 0;
        }
        .nav-item {
            padding: 12px 20px;
            margin: 5px 10px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .nav-item:hover { background: rgba(102, 126, 234, 0.3); }
        .nav-item.active { background: #667eea; }
        .nav-item .icon { font-size: 18px; width: 24px; }
        
        /* Main Content */
        .main-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .welcome-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
        }
        .security-stars {
            font-size: 12px;
            margin-top: 5px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }
        .section {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 25px;
            display: none;
        }
        .section.active {
            display: block;
        }
        .section h3 {
            margin-bottom: 20px;
            color: #333;
            border-left: 4px solid #667eea;
            padding-left: 15px;
        }
        .flag-submit {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
        .flag-submit input {
            flex: 1;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-family: monospace;
        }
        .flag-submit button {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .users-table {
            width: 100%;
            border-collapse: collapse;
        }
        .users-table th, .users-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .users-table th { background: #f8f9fa; }
        .users-table button {
            padding: 4px 8px;
            font-size: 11px;
            background: #ffc107;
            color: #333;
        }
        .project-item {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .project-item:hover { background: #e9ecef; transform: translateX(5px); }
        .team-actions {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .search-box input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover { background: #764ba2; transform: scale(1.02); }
        .limit-counter {
            font-size: 12px;
            color: #666;
            margin-top: 10px;
        }
        .idea-list {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }
        .debug-badge, .admin-badge {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 10px;
            cursor: pointer;
            opacity: 0.3;
            z-index: 1000;
            transition: opacity 0.3s;
        }
        .admin-badge {
            right: 100px;
            background: #ff9800;
        }
        .debug-badge:hover, .admin-badge:hover { opacity: 1; }
        .achievement-badge {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            padding: 12px 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 13px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.01); }
        }
        .notification {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            border-radius: 8px;
            display: none;
            z-index: 2000;
            background: #28a745;
            color: white;
            animation: slideUp 0.3s ease;
        }
        @keyframes slideUp {
            from { transform: translateX(-50%) translateY(100px); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
        .create-project {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .create-project input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .report-generate {
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
        }
        .report-generate input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .import-result {
            margin-top: 15px;
            max-height: 300px;
            overflow-y: auto;
        }
        pre {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 11px;
        }
        .document-content {
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            max-height: 500px;
            overflow-y: auto;
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        .warning {
            background: #fff3cd;
            color: #856404;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #ffc107;
        }
        .invite-code {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            margin-top: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="logo">MultiTenant<span>Cloud</span></div>
        </div>
        <div class="user-info">
            <div class="name">{{ user.username }}</div>
            <div class="role">Role: {{ user.role }}</div>
        </div>
        <div class="nav-menu">
            <div class="nav-item active" data-section="dashboard">
                <span class="icon">📊</span> Dashboard
            </div>
            <div class="nav-item" data-section="projects">
                <span class="icon">📁</span> Projects
            </div>
            <div class="nav-item" data-section="reports">
                <span class="icon">📈</span> Reports
            </div>
            <div class="nav-item" data-section="strategy">
                <span class="icon">📄</span> Company Strategy
            </div>
            <div class="nav-item" data-section="secrets">
                <span class="icon">🔐</span> Master Secrets
            </div>
            <div class="nav-item" data-section="invite">
                <span class="icon">🎁</span> Invite System
            </div>
            <div class="nav-item" data-section="team">
                <span class="icon">👥</span> Team Members
            </div>
            <div class="nav-item" data-section="leaderboard">
                <span class="icon">🏆</span> Leaderboard
            </div>
            <div class="nav-item" data-section="search">
                <span class="icon">🔍</span> Search
            </div>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
        <div class="welcome-card">
            <h2>Welcome back, {{ user.username }}!</h2>
            <div class="security-stars">Security Level: {{ '⭐' * ((score//100) % 15 + 1) if score else '⭐' }}</div>
            <div style="font-size: 12px; margin-top: 5px;">CTF Lab by Asfahan | Educational Purpose</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="flagCount">{{ flag_count }}</div>
                <div>Flags Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalScore">{{ score }}</div>
                <div>Total Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">30+</div>
                <div>Hidden Flags</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="userRank">#{{ rank }}</div>
                <div>Global Rank</div>
            </div>
        </div>
        
        {% if show_master_message and flag_count >= 8 %}
        <div class="achievement-badge">
            <span>🏆</span>
            <span><strong>Master Hacker Unlocked!</strong> Admin Console Key: <code>CTF_MASTER_2024</code></span>
        </div>
        {% endif %}
        
        <!-- Dashboard Section -->
        <div id="dashboard-section" class="section active">
            <h3>🏆 Submit Your Flag</h3>
            <div class="flag-submit">
                <input type="text" id="flagInput" placeholder="Enter your flag... (e.g., FLAG{...})">
                <button onclick="submitFlag()">Validate →</button>
            </div>
            <div id="submissionResult"></div>
        </div>
        
        <!-- Projects Section -->
        <div id="projects-section" class="section">
            <h3>📁 Project Resources</h3>
            <div class="create-project">
                <input type="text" id="projectName" placeholder="Project Name">
                <button onclick="createProject()">Create Project</button>
            </div>
            <div id="projectsList"></div>
            <div class="limit-counter" id="projectLimitCounter"></div>
            <div class="warning" id="raceWarning" style="display:none;">⚠️ Race condition detected! Multiple requests bypassed the limit!</div>
            <button onclick="raceExploit()" style="margin-top: 10px; background:#ff9800;">⚡ Test Race Condition (10x requests)</button>
        </div>
        
        <!-- Reports Section -->
        <div id="reports-section" class="section">
            <h3>📈 Financial Reports</h3>
            <div class="report-generate">
                <input type="text" id="reportTitle" placeholder="Report Title">
                <button onclick="generateReport()">Generate Report</button>
            </div>
            <div id="reportList"></div>
            <div id="reportResult"></div>
        </div>
        
        <!-- Strategy Section -->
        <div id="strategy-section" class="section">
            <h3>📄 Company Strategy 2024</h3>
            <button onclick="viewStrategy()">Load Strategy Document</button>
            <div id="strategyResult"></div>
        </div>
        
        <!-- Secrets Section -->
        <div id="secrets-section" class="section">
            <h3>🔐 Master Secrets Generator</h3>
            <div class="search-box">
                <input type="text" id="secretName" placeholder="Enter your name to generate secret">
                <button onclick="generateSecret()">Generate Master Secret</button>
            </div>
            <div id="secretResult"></div>
        </div>
        
        <!-- Invite System Section -->
        <div id="invite-section" class="section">
            <h3>🎁 Invite System</h3>
            <button onclick="generateInvite()">Generate Invite Code</button>
            <div id="inviteResult" class="invite-code"></div>
            <div style="margin-top: 10px;">
                <input type="text" id="redeemCode" placeholder="Enter invite code to redeem" style="width: 70%;">
                <button onclick="redeemInvite()">Redeem Code</button>
            </div>
            <div style="margin-top: 10px; font-size: 12px; color: #666;">
                <small>Redeem invites at: POST /api/invite/redeem</small>
            </div>
        </div>
        
        <!-- Team Section -->
        <div id="team-section" class="section">
            <h3>👥 Team Management</h3>
            <div class="team-actions">
                <button onclick="importTeamData()" style="background: #28a745;">📥 Import Team Data</button>
                <button onclick="exportTeamData()" style="background: #17a2b8;">📤 Export Team Data</button>
            </div>
            <div id="teamList">Loading...</div>
            <div id="importResult" class="import-result"></div>
        </div>
        
        <!-- Leaderboard Section -->
        <div id="leaderboard-section" class="section">
            <h3>🏆 Leaderboard</h3>
            <div id="leaderboardList">Loading...</div>
            <a href="/leaderboard" style="display: inline-block; margin-top: 15px; color: #667eea;">View Full Leaderboard →</a>
        </div>
        
        <!-- Search Section -->
        <div id="search-section" class="section">
            <h3>🔍 Employee Directory Search</h3>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search by username...">
                <button onclick="searchUsers()">Search</button>
            </div>
            <div id="searchResults"></div>
            <p style="font-size: 12px; color: #666; margin-top: 10px;">💡 Try searching with special characters like ' or UNION</p>
        </div>
    </div>
    
    <div class="debug-badge" onclick="window.location.href='/debug'">🐛 Debug</div>
    <div class="admin-badge" onclick="showAdminPanel()">🔧 Admin</div>
    <div id="notification" class="notification"></div>
    
    <script>
        let currentScore = {{ score }};
        let currentFlags = {{ flag_count }};
        let currentUser = {{ user | tojson | safe }};
        let projectRequestCount = 0;
        let raceDetected = false;
        
        function showNotification(msg, type) {
            const n = document.getElementById('notification');
            n.innerHTML = msg;
            n.style.display = 'block';
            n.style.background = type === 'success' ? '#28a745' : '#dc3545';
            setTimeout(() => n.style.display = 'none', 5000);
        }
        
        function showAdminPanel() {
            const key = prompt('Enter Admin Console Key:');
            if (key === 'CTF_MASTER_2024') window.location.href = '/admin-panel';
            else if (key) showNotification('Invalid Key!', 'error');
        }
        
        async function submitFlag() {
            const flag = document.getElementById('flagInput').value.trim();
            if (!flag) return showNotification('Enter a flag!', 'error');
            
            const res = await fetch('/api/v1/submit-flag-race', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ flag: flag })
            });
            const data = await res.json();
            const resultDiv = document.getElementById('submissionResult');
            
            if (data.valid) {
                if (data.already_found) {
                    resultDiv.innerHTML = `<div style="background:#fff3cd;padding:10px;border-radius:5px;">⚠️ ${data.message}</div>`;
                } else {
                    currentScore = data.total_score;
                    currentFlags = data.total_flags;
                    document.getElementById('flagCount').innerText = currentFlags;
                    document.getElementById('totalScore').innerText = currentScore;
                    
                    let html = `<div style="background:#d4edda;padding:15px;border-radius:8px;"><strong>✅ ${data.message}</strong><br>`;
                    if (data.master_achievement) html += `<div style="margin-top:10px;background:#ffd700;color:#333;padding:10px;border-radius:5px;">🏆 Master Hacker! Admin Key: CTF_MASTER_2024</div>`;
                    if (data.ultimate_flag) html += `<div style="margin-top:10px;background:linear-gradient(135deg,#ff6b6b,#ff4757);color:white;padding:10px;text-align:center;">🔥 ULTIMATE FLAG: ${data.ultimate_flag} 🔥</div>`;
                    html += `</div>`;
                    resultDiv.innerHTML = html;
                    showNotification(`+${data.points} points!`, 'success');
                }
            } else {
                resultDiv.innerHTML = `<div style="background:#f8d7da;padding:10px;border-radius:5px;">❌ ${data.message}</div>`;
            }
            document.getElementById('flagInput').value = '';
            loadLeaderboard();
        }
        
        // Project System
        async function createProject() {
            const name = document.getElementById('projectName').value;
            if (!name) return alert('Enter project name');
            
            projectRequestCount++;
            document.getElementById('projectLimitCounter').innerHTML = `⚠️ Project creations: ${projectRequestCount}/5`;
            
            const res = await fetch('/api/v1/projects/create', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            });
            const data = await res.json();
            
            if (data.race_bypass) {
                raceDetected = true;
                document.getElementById('raceWarning').style.display = 'block';
                showNotification('🔥 RACE CONDITION EXPLOITED! You bypassed the project limit!', 'success');
            }
            if (data.flag) showNotification(`🎉 ${data.flag}`, 'success');
            loadProjects();
        }
        
        async function raceExploit() {
            const name = prompt('Enter project name for race condition:', 'Race Project');
            if (!name) return;
            
            showNotification('Sending 10 concurrent requests...', 'success');
            const promises = [];
            for (let i = 0; i < 10; i++) {
                promises.push(fetch('/api/v1/projects/create', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: `${name}_${i}` })
                }));
            }
            const results = await Promise.all(promises);
            let bypassDetected = false;
            for (const res of results) {
                const data = await res.json();
                if (data.race_bypass) bypassDetected = true;
                if (data.flag) showNotification(`🎉 ${data.flag}`, 'success');
            }
            if (bypassDetected) {
                showNotification('🔥 RACE CONDITION SUCCESSFUL! You bypassed the 5-project limit!', 'success');
                document.getElementById('raceWarning').style.display = 'block';
                raceDetected = true;
            }
            loadProjects();
        }
        
        async function loadProjects() {
            const res = await fetch('/api/v1/projects/list');
            const data = await res.json();
            let html = '';
            if (data.projects) {
                data.projects.forEach(p => {
                    let icon = '📁';
                    if (p.name.includes('Secret')) icon = '🔒';
                    else if (p.name.includes('Strategy')) icon = '📄';
                    html += `<div class="project-item" onclick="viewProject('${p.uid}')">
                        <span>${icon} ${p.name}</span>
                        <span style="color:#999; font-size:11px;">${p.uid}</span>
                    </div>`;
                });
            }
            document.getElementById('projectsList').innerHTML = html || '<div class="loading">No projects yet. Create one!</div>';
        }
        
        async function viewProject(uid) {
            const res = await fetch(`/api/v1/projects/view/${uid}`);
            const data = await res.json();
            alert(JSON.stringify(data, null, 2));
            if (data.flag) showNotification(`🏆 Flag found! Submit at /leaderboard`, 'success');
        }
        
        // Reports
        async function generateReport() {
            const title = document.getElementById('reportTitle').value;
            if (!title) return alert('Enter report title');
            
            const res = await fetch('/api/v1/reports/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title })
            });
            const data = await res.json();
            if (data.flag) showNotification(`🎉 ${data.flag}`, 'success');
            loadReports();
        }
        
        async function loadReports() {
            const res = await fetch('/api/v1/reports/list');
            const data = await res.json();
            let html = '';
            if (data.reports) {
                data.reports.forEach(r => {
                    html += `<div class="project-item" onclick="viewReport('${r.uid}')">
                        <span>📊 ${r.title}</span>
                        <span style="color:#999; font-size:11px;">${r.uid}</span>
                    </div>`;
                });
            }
            document.getElementById('reportList').innerHTML = html || '<div class="loading">No reports yet. Generate one!</div>';
        }
        
        async function viewReport(uid) {
            const res = await fetch(`/api/v1/reports/view/${uid}`);
            const data = await res.json();
            alert(JSON.stringify(data, null, 2));
            if (data.flag) showNotification(`🏆 Flag found! Submit at /leaderboard`, 'success');
        }
        
        // Strategy
        async function viewStrategy() {
            const res = await fetch('/api/v1/strategy/view');
            const data = await res.json();
            let html = `<div class="document-content">${data.document}</div>`;
            if (data.footer) html += `<div class="idea-list" style="margin-top:10px; font-size:10px; color:#888;"><small>${data.footer}</small></div>`;
            document.getElementById('strategyResult').innerHTML = html;
        }
        
        // Secrets
        async function generateSecret() {
            const name = document.getElementById('secretName').value;
            const res = await fetch(`/api/v1/secrets/generate?name=${encodeURIComponent(name)}`);
            const data = await res.json();
            document.getElementById('secretResult').innerHTML = `<div class="idea-list">${data.secret || data.message}</div>`;
            if (data.flag) showNotification(`🏆 Flag: ${data.flag}`, 'success');
        }
        
        // Invite System
        async function generateInvite() {
            const res = await fetch('/api/v1/invite/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role: 'viewer' })
            });
            const data = await res.json();
            const inviteDiv = document.getElementById('inviteResult');
            inviteDiv.innerHTML = `<strong>Invite Code:</strong> <code>${data.invite_code}</code><br><small>Share this code with new users</small>`;
            inviteDiv.style.display = 'block';
            setTimeout(() => inviteDiv.style.display = 'none', 10000);
        }
        
        async function redeemInvite() {
            const code = document.getElementById('redeemCode').value.trim();
            if (!code) return showNotification('Enter an invite code!', 'error');
            
            const res = await fetch('/api/invite/redeem', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            });
            const data = await res.json();
            if (data.flag) showNotification(`🎉 ${data.flag}`, 'success');
            else showNotification(data.message, 'info');
        }
        
        // Team Management
        async function importTeamData() {
            const url = prompt('Enter import URL:');
            if (!url) return;
            
            const res = await fetch('/api/v1/team/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ import_url: url })
            });
            const data = await res.json();
            document.getElementById('importResult').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            if (data.flag) showNotification(`🏆 Flag: ${data.flag}`, 'success');
            loadTeamMembers();
        }
        
        async function exportTeamData() {
            const res = await fetch('/api/v1/team/export');
            const data = await res.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'team_export.json';
            a.click();
            URL.revokeObjectURL(url);
            if (data.flag) showNotification(`🏆 Flag: ${data.flag}`, 'success');
            showNotification('Team data exported!', 'success');
        }
        
        async function updateTeamMember(userId, currentRole) {
            const newRole = prompt(`Update role for user ${userId} (current: ${currentRole}):`, currentRole);
            if (!newRole || newRole === currentRole) return;
            
            const res = await fetch('/api/v1/team/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, role: newRole })
            });
            const data = await res.json();
            if (data.flag) showNotification(`🏆 Flag: ${data.flag}`, 'success');
            loadTeamMembers();
        }
        
        async function loadTeamMembers() {
            let html = '<table class="users-table"><thead> <th>ID</th><th>Username</th><th>Role</th><th>Dept</th><th>Action</th> </thead><tbody>';
            for (let id = 1; id <= 8; id++) {
                try {
                    const res = await fetch(`/api/v1/user/profile/${id}`);
                    const data = await res.json();
                    if (data && !data.error) {
                        html += `<tr>
                            <td>${data.id}</td>
                            <td><a href="/profile/${data.id}">${data.username}</a></td>
                            <td>${data.role}</td>
                            <td>${data.department || 'N/A'}</td>
                            <td><button onclick="updateTeamMember(${data.id}, '${data.role}')" style="background:#ffc107;color:#333;">Update Role</button></td>
                        </tr>`;
                        if (data.internal_notes && data.internal_notes.includes('FLAG')) showNotification(`Found flag in ${data.username}'s profile!`, 'success');
                    }
                } catch(e) { }
            }
            html += '</tbody></table>';
            document.getElementById('teamList').innerHTML = html;
        }
        
        // Search
        async function searchUsers() {
            const query = document.getElementById('searchInput').value;
            const res = await fetch(`/api/v1/search/users?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            
            let html = '<ul>';
            if (data.users && data.users.length > 0) {
                data.users.forEach(u => {
                    html += `<li>${u.username} (${u.email}) - ${u.role}</li>`;
                });
            } else {
                html += '<li>No users found</li>';
            }
            html += '</ul>';
            document.getElementById('searchResults').innerHTML = html;
            
            if (data.flag) showNotification(`🏆 Flag: ${data.flag}`, 'success');
        }
        
        // Leaderboard
        async function loadLeaderboard() {
            try {
                const res = await fetch('/api/v1/leaderboard');
                const data = await res.json();
                let html = '<ul style="margin-top: 10px;">';
                if (data.leaderboard && data.leaderboard.length > 0) {
                    data.leaderboard.slice(0, 10).forEach(e => {
                        html += `<li><strong>${e.username}</strong> - ${e.score || e[2]} pts (${e.flags || e[1]} flags)</li>`;
                    });
                } else {
                    html += '<li>No hackers yet. Be the first!</li>';
                }
                html += '</ul>';
                document.getElementById('leaderboardList').innerHTML = html;
            } catch(e) {
                document.getElementById('leaderboardList').innerHTML = '<div class="loading">Error loading leaderboard</div>';
            }
        }
        
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                const section = item.dataset.section;
                document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                document.getElementById(`${section}-section`).classList.add('active');
            });
        });
        
        // Initialize
        loadProjects();
        loadReports();
        loadTeamMembers();
        loadLeaderboard();
        
        setInterval(() => {
            loadLeaderboard();
            if (currentUser) loadTeamMembers();
        }, 10000);
    </script>
</body>
</html>
'''


# ==================== HTML TEMPLATES ====================
HTML_INDEX = '''
<!DOCTYPE html>
<html>
<head>
    <title>MultiTenantCloud - Enterprise SaaS Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .hero {
            background: rgba(255,255,255,0.95);
            padding: 80px 20px;
            text-align: center;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { font-size: 48px; color: #333; margin-bottom: 20px; }
        .subtitle { font-size: 20px; color: #666; margin-bottom: 40px; }
        .btn {
            display: inline-block;
            padding: 15px 40px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            transition: transform 0.3s;
        }
        .btn:hover { transform: translateY(-2px); background: #764ba2; }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            padding: 60px 20px;
            background: white;
        }
        .feature {
            text-align: center;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .feature h3 { color: #667eea; margin-bottom: 15px; }
        .sarcasm-banner {
            background: #ff6b6b;
            color: white;
            text-align: center;
            padding: 15px;
            font-weight: bold;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { background: #ff6b6b; }
            50% { background: #ff4757; }
        }
    </style>
</head>
<body>
    <div class="sarcasm-banner">
        🎪 Welcome to MultiTenantCloud! Where security is just a suggestion! 🎪
    </div>
    <div class="hero">
        <div class="container">
            <h1>🏢 MultiTenantCloud</h1>
            <p class="subtitle">The most secure SaaS platform ever built! (Not really 😏)</p>
            <a href="/login" class="btn">Get Started →</a>
        </div>
    </div>
    <div class="features">
        <div class="feature">
            <h3>🚀 Multi-Tenant Architecture</h3>
            <p>Isolated tenants? What's that? Everyone can see everything!</p>
        </div>
        <div class="feature">
            <h3>🔐 Military-Grade Security</h3>
            <p>Our security is so good, we left all vulnerabilities for you to find!</p>
        </div>
        <div class="feature">
            <h3>💎 15 Hidden Flags</h3>
            <p>Find all vulnerabilities and claim your flags. Good luck! 🎯</p>
        </div>
    </div>
</body>
</html>
'''

HTML_LOGIN = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - MultiTenantCloud</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 400px;
        }
        h2 { text-align: center; color: #333; margin-bottom: 30px; }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover { background: #764ba2; }
        .demo-users {
            margin-top: 20px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
            font-size: 12px;
        }
        .sarcasm {
            text-align: center;
            color: #ff6b6b;
            margin-top: 15px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>🔐 Login to MultiTenantCloud</h2>
        <input type="text" id="username" placeholder="Username" value="john_doe">
        <input type="password" id="password" placeholder="Password" value="Password123!">
        <button onclick="login()">Login →</button>
        <div class="demo-users">
            <strong>Demo Users:</strong><br>
            Create Those by going to this endpoint
            <h4>http://localhost:5000/api/v1/debug/create-demo-users</h4>
            john_doe / Password123! (Admin)<br>
            jane_smith / Password456! (Owner)<br>
            bob_wilson / Password789! (Viewer)
        </div>
        <div class="sarcasm">
            🤡 Try SQL injection... I dare you! 🤡
        </div>
    </div>
    <script>
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            if (data.token) {
                window.location.href = '/dashboard';
            } else {
                alert('Login failed! ' + (data.error || ''));
            }
        }
    </script>
</body>
</html>
'''

HTML_LEADERBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>Leaderboard - MultiTenantCloud CTF</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(0,0,0,0.8);
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }
        .creator-signature {
            background: rgba(255,215,0,0.2);
            border: 1px solid #ffd700;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
        }
        .leaderboard-card {
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .leaderboard-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .leaderboard-table th, .leaderboard-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .leaderboard-table th {
            background: #667eea;
            color: white;
        }
        .current-user-row {
            background: #fff3cd !important;
            border-left: 4px solid #ffd700;
            font-weight: bold;
        }
        .you-badge {
            display: inline-block;
            background: #ffd700;
            color: #333;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 12px;
            margin-left: 8px;
        }
        .username-highlight {
            color: #ff8c00;
            font-weight: bold;
        }
        .flag-input {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 10px;
        }
        .flag-input input {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-family: monospace;
        }
        .flag-input button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .notification {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            display: none;
            z-index: 1000;
        }
        .success { background: #28a745; color: white; }
        .error { background: #dc3545; color: white; }
        .sarcasm-box {
            background: #ff9800;
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .user-stats-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        .login-box {
            text-align: center;
            padding: 40px;
        }
        .login-box a {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 8px;
            display: inline-block;
            margin-top: 10px;
        }
        .status-box {
            background: #333;
            color: #0f0;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Hacker Leaderboard 🏆</h1>
            <p>Who will be the ultimate flag hunter?</p>
            <div class="creator-signature">
                ⚡ Created by <strong>Asfahan</strong> for educational & security research purposes ⚡<br>
                <small>🔒 Learn. Hack. Secure. 🔒</small>
            </div>
        </div>
        
        <div class="status-box" id="statusBox">
            🔍 Checking login status...
        </div>
        
        <div class="sarcasm-box" id="sarcasmBox">
            🎪 Think you can make it to the top? I doubt it! 🎪
        </div>
        
        <div class="leaderboard-card">
            <div class="flag-input">
                <input type="text" id="flagInput" placeholder="Paste your flag here... (e.g., FLAG{...})">
                <button onclick="validateFlag()">Validate Flag →</button>
            </div>
            
            <h2>🏅 Top Hackers</h2>
            <div id="leaderboardContent">
                <div class="loading">📊 Loading leaderboard data...</div>
            </div>
        </div>
        
        <div class="leaderboard-card">
            <h2>🎯 Your Stats</h2>
            <div id="userStats">
                <div class="loading">📊 Loading your stats...</div>
            </div>
        </div>
    </div>
    
    <div id="notification" class="notification"></div>
    
    <script>
        let loggedInUsername = null;
        let loggedInRole = null;
        
        // Function to get user info from cookie
        function getCurrentUser() {
            console.log('Checking cookies...');
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith('auth_token=')) {
                    const token = cookie.substring(11);
                    console.log('Found token:', token.substring(0, 30) + '...');
                    try {
                        const payload = token.split('.')[1];
                        // Fix base64 padding
                        let decoded = payload;
                        while (decoded.length % 4) {
                            decoded += '=';
                        }
                        const userData = JSON.parse(atob(decoded));
                        console.log('Decoded user:', userData);
                        return userData;
                    } catch(e) {
                        console.error('Error decoding:', e);
                    }
                }
            }
            console.log('No auth_token found');
            return null;
        }
        
        // Update status box
        function updateStatus() {
            const user = getCurrentUser();
            const statusBox = document.getElementById('statusBox');
            if (user) {
                loggedInUsername = user.username;
                loggedInRole = user.role;
                statusBox.innerHTML = `✅ LOGGED IN as: <strong style="color:#ff8c00">${user.username}</strong> (Role: ${user.role}) | <span style="color:#0f0">Session Active</span>`;
                statusBox.style.background = '#1a3d1a';
            } else {
                loggedInUsername = null;
                loggedInRole = null;
                statusBox.innerHTML = `❌ NOT LOGGED IN | <a href="/login" style="color:#0f0">Click here to login</a>`;
                statusBox.style.background = '#3d1a1a';
            }
        }
        
        async function loadLeaderboard() {
            const container = document.getElementById('leaderboardContent');
            container.innerHTML = '<div class="loading">📊 Loading leaderboard...</div>';
            
            try {
                const response = await fetch('/api/v1/leaderboard');
                const data = await response.json();
                console.log('Leaderboard data:', data);
                
                if (!data.leaderboard || data.leaderboard.length === 0) {
                    container.innerHTML = '<div class="loading">🏆 No hackers yet! Be the first!</div>';
                    return;
                }
                
                let html = '<table class="leaderboard-table"><thead><tr><th>Rank</th><th>Hacker</th><th>Flags</th><th>Score</th><th>Last Find</th></tr></thead><tbody>';
                
                for (let i = 0; i < data.leaderboard.length; i++) {
                    const entry = data.leaderboard[i];
                    const rank = i + 1;
                    
                    let username, flags, score, lastFound;
                    if (Array.isArray(entry)) {
                        username = entry[0];
                        flags = entry[1];
                        score = entry[2];
                        lastFound = entry[3] || 'Recently';
                    } else {
                        username = entry.username || 'Unknown';
                        flags = entry.flags || 0;
                        score = entry.score || 0;
                        lastFound = entry.last_found || 'Recently';
                    }
                    
                    const isCurrentUser = loggedInUsername && username === loggedInUsername;
                    
                    let rankDisplay = rank;
                    if (rank === 1) rankDisplay = '🥇 1st';
                    else if (rank === 2) rankDisplay = '🥈 2nd';
                    else if (rank === 3) rankDisplay = '🥉 3rd';
                    
                    const rowClass = isCurrentUser ? 'current-user-row' : '';
                    const usernameDisplay = isCurrentUser 
                        ? `<span class="username-highlight">${escapeHtml(username)}</span> <span class="you-badge">YOU</span>`
                        : escapeHtml(username);
                    
                    html += `<tr class="${rowClass}">`;
                    html += `<td><strong>${rankDisplay}</strong></td>`;
                    html += `<td><strong>${usernameDisplay}</strong></td>`;
                    html += `<td>${flags}</td>`;
                    html += `<td class="score">${score}</td>`;
                    html += `<td>${escapeHtml(lastFound)}</td>`;
                    html += `</tr>`;
                }
                
                html += '</tbody></table>';
                container.innerHTML = html;
                
            } catch(e) {
                console.error('Error:', e);
                container.innerHTML = '<div class="loading">❌ Error loading leaderboard</div>';
            }
        }
        
        async function loadUserStats() {
            const container = document.getElementById('userStats');
            
            if (!loggedInUsername) {
                container.innerHTML = '<div class="login-box">🔐 <strong>Not logged in</strong><br><a href="/login">Login to see your stats →</a></div>';
                return;
            }
            
            container.innerHTML = '<div class="loading">📊 Fetching your stats...</div>';
            
            try {
                const response = await fetch('/api/v1/leaderboard');
                const data = await response.json();
                
                let userEntry = null;
                let userRank = -1;
                
                if (data.leaderboard) {
                    for (let i = 0; i < data.leaderboard.length; i++) {
                        const entry = data.leaderboard[i];
                        let entryUsername = Array.isArray(entry) ? entry[0] : entry.username;
                        if (entryUsername === loggedInUsername) {
                            userEntry = entry;
                            userRank = i + 1;
                            break;
                        }
                    }
                }
                
                if (userEntry) {
                    let flags = Array.isArray(userEntry) ? userEntry[1] : (userEntry.flags || 0);
                    let score = Array.isArray(userEntry) ? userEntry[2] : (userEntry.score || 0);
                    
                    container.innerHTML = `
                        <div class="user-stats-card">
                            <p><strong>👤 Username:</strong> <span class="username-highlight">${escapeHtml(loggedInUsername)}</span> <span class="you-badge">YOU</span></p>
                            <p><strong>⭐ Role:</strong> ${escapeHtml(loggedInRole)}</p>
                            <p><strong>🏆 Flags Found:</strong> ${flags}</p>
                            <p><strong>💰 Total Score:</strong> ${score}</p>
                            <p><strong>📈 Global Rank:</strong> ${userRank === 1 ? '🥇 #1 TOP HACKER!' : userRank === 2 ? '🥈 #2 - So close!' : userRank === 3 ? '🥉 #3 - Almost there!' : `#${userRank}`}</p>
                            <hr>
                            <p><small>💡 Keep hunting! ${15 - flags} more flags to discover!</small></p>
                            ${flags >= 8 ? '<p><strong>🎉 MASTER HACKER! Admin Key: <code>CTF_MASTER_2024</code></strong></p>' : ''}
                        </div>
                    `;
                } else {
                    container.innerHTML = `
                        <div class="user-stats-card">
                            <p><strong>👤 Username:</strong> <span class="username-highlight">${escapeHtml(loggedInUsername)}</span> <span class="you-badge">YOU</span></p>
                            <p><strong>⭐ Role:</strong> ${escapeHtml(loggedInRole)}</p>
                            <p><strong>🏆 Flags Found:</strong> 0</p>
                            <p><strong>💰 Total Score:</strong> 0</p>
                            <p><strong>📈 Global Rank:</strong> Not ranked yet</p>
                            <hr>
                            <p><strong>💡 Start finding flags!</strong> Submit your first flag above!</p>
                        </div>
                    `;
                }
            } catch(e) {
                console.error('Error:', e);
                container.innerHTML = '<div class="loading">❌ Error loading stats</div>';
            }
        }
        
        async function validateFlag() {
            const flag = document.getElementById('flagInput').value.trim();
            if (!flag) {
                showNotification('Please enter a flag!', 'error');
                return;
            }
            
            if (!loggedInUsername) {
                showNotification('Please login first!', 'error');
                window.location.href = '/login';
                return;
            }
            
            let token = '';
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith('auth_token=')) {
                    token = cookie.substring(11);
                    break;
                }
            }
            
            try {
                const response = await fetch('/api/v1/submit-flag', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({ flag: flag })
                });
                
                const data = await response.json();
                
                if (data.valid) {
                    if (data.already_found) {
                        showNotification('⚠️ ' + data.message, 'error');
                    } else {
                        showNotification('🎉 ' + data.message, 'success');
                        loadLeaderboard();
                        loadUserStats();
                    }
                } else {
                    showNotification('❌ ' + data.message, 'error');
                }
            } catch(e) {
                showNotification('Error submitting flag!', 'error');
            }
            
            document.getElementById('flagInput').value = '';
        }
        
        function showNotification(message, type) {
            const notification = document.getElementById('notification');
            notification.className = 'notification ' + type;
            notification.innerHTML = message;
            notification.style.display = 'block';
            setTimeout(() => notification.style.display = 'none', 5000);
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Initialize
        updateStatus();
        loadLeaderboard();
        loadUserStats();
        
        // Refresh every 5 seconds
        setInterval(() => {
            updateStatus();
            loadLeaderboard();
            loadUserStats();
        }, 5000);
    </script>
</body>
</html>
'''

HTML_PROFILE = '''
<!DOCTYPE html>
<html>
<head>
    <title>User Profile - MultiTenantCloud</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #667eea; }
        .info { margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }
        .sensitive { background: #fff3cd; border-left: 4px solid #ffc107; }
        .flag { background: #d4edda; border-left: 4px solid #28a745; }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        .hidden-flag {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👤 User Profile</h1>
        <div class="info">
            <p><strong>Username:</strong> {{ profile_user[1] if profile_user else 'Unknown' }}</p>
            <p><strong>Email:</strong> {{ profile_user[2] if profile_user else 'Unknown' }}</p>
            <p><strong>Role:</strong> {{ profile_user[3] if profile_user else 'Unknown' }}</p>
            <p><strong>Department:</strong> {{ profile_user[4] if profile_user else 'Unknown' }}</p>
        </div>
        
        {% if profile_user %}
        <div class="info sensitive">
            <p><strong>💰 Salary:</strong> ${{ profile_user[5] }}</p>
            <p><strong>🔑 SSN:</strong> {{ profile_user[6] }}</p>
            <p><strong>💳 Credit Card:</strong> {{ profile_user[7] }}</p>
        </div>
        
        <!-- Flags are hidden - must be discovered through other means -->
        <div class="hidden-flag" data-flag="{{ profile_user[8] if profile_user[8] and 'FLAG' in profile_user[8] else '' }}"></div>
        {% endif %}
        
        <button onclick="window.location.href='/dashboard'">Back to Dashboard</button>
        
        <div style="margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; font-size: 12px;">
            🤡 Try accessing other users' profiles by changing the ID in URL! /profile/1, /profile/2, etc.
        </div>
    </div>
</body>
</html>
'''

HTML_RESOURCES = '''
<!DOCTYPE html>
<html>
<head>
    <title>Resources - MultiTenantCloud</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .resource {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        input {
            padding: 8px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 5px;
            width: 300px;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📁 Tenant Resources</h1>
        <div class="resource">
            <h3>🔍 Access Resource by ID</h3>
            <input type="number" id="resourceId" placeholder="Resource ID (try 1-5)" value="1">
            <button onclick="getResource()">Get Resource</button>
            <div id="result" style="margin-top: 20px;"></div>
        </div>
        
        <div class="resource">
            <h3>🌐 Import External Resource (SSRF)</h3>
            <input type="text" id="importUrl" placeholder="Import URL" value="http://localhost:5000/api/v1/debug/audit-logs">
            <button onclick="importResource()">Import</button>
            <div id="importResult"></div>
        </div>
        
        <div class="resource">
            <h3>💡 Hints</h3>
            <ul>
                <li>Resource ID 2 contains a flag</li>
                <li>Resource ID 3 is from another tenant!</li>
                <li>Try SSRF to access internal endpoints</li>
            </ul>
        </div>
    </div>
    
    <script>
        async function getResource() {
            const id = document.getElementById('resourceId').value;
            const response = await fetch(`/api/v1/tenant/resources/${id}`);
            const data = await response.json();
            
            let html = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            if (data.flag) {
                html += `<div style="background: #d4edda; padding: 10px; margin-top: 10px;">🏆 FLAG: ${data.flag}</div>`;
            }
            document.getElementById('result').innerHTML = html;
        }
        
        async function importResource() {
            const url = document.getElementById('importUrl').value;
            const response = await fetch('/api/v1/tenant/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ import_url: url })
            });
            const data = await response.json();
            
            let html = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            if (data.flag) {
                html += `<div style="background: #d4edda; padding: 10px; margin-top: 10px;">🏆 FLAG: ${data.flag}</div>`;
            }
            document.getElementById('importResult').innerHTML = html;
        }
    </script>
</body>
</html>
'''

HTML_ADMIN = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel - MultiTenantCloud</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            margin: 0;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        button {
            background: #ff4757;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        input {
            padding: 8px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .sarcasm {
            background: #ff9800;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sarcasm">
            🚨 ADMIN PANEL - Only authorized personnel! (Or anyone who can hack 😏)
        </div>
        
        <div class="card">
            <h2>👑 User Management</h2>
            <p>Delete user (BFLA vulnerability):</p>
            <input type="number" id="deleteUserId" placeholder="User ID to delete">
            <button onclick="deleteUser()">Delete User</button>
        </div>
        
        <div class="card">
            <h2>⚡ Role Upgrade (Race Condition)</h2>
            <button onclick="upgradeRole()">Upgrade My Role</button>
            <p><small>Send multiple requests quickly to exploit race condition!</small></p>
        </div>
        
        <div class="card">
            <h2>🔍 Audit Logs</h2>
            <button onclick="viewAuditLogs()">View Logs</button>
            <div id="logs"></div>
        </div>
        
        <div class="card">
            <h2>🎯 Flags Found</h2>
            <div id="flags">None yet</div>
        </div>
    </div>
    
    <script>
        let flags = [];
        
        async function deleteUser() {
            const userId = document.getElementById('deleteUserId').value;
            const response = await fetch(`/api/v1/admin/delete-user/${userId}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.flag) {
                flags.push(data.flag);
                updateFlags();
                alert(`Flag found: ${data.flag}`);
            } else {
                alert(data.message);
            }
        }
        
        async function upgradeRole() {
            // Send 10 concurrent requests for race condition
            const promises = [];
            for (let i = 0; i < 10; i++) {
                promises.push(fetch('/api/v1/role/upgrade', { method: 'POST' }));
            }
            const results = await Promise.all(promises);
            for (const result of results) {
                const data = await result.json();
                if (data.flag && !flags.includes(data.flag)) {
                    flags.push(data.flag);
                    updateFlags();
                    alert(`Flag found: ${data.flag}`);
                }
            }
        }
        
        async function viewAuditLogs() {
            const response = await fetch('/api/v1/debug/audit-logs');
            const data = await response.json();
            if (data.flag && !flags.includes(data.flag)) {
                flags.push(data.flag);
                updateFlags();
            }
            document.getElementById('logs').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
        
        function updateFlags() {
            document.getElementById('flags').innerHTML = flags.map(f => `<div>🏆 ${f}</div>`).join('');
        }
    </script>
</body>
</html>
'''

HTML_DEBUG = '''
<!DOCTYPE html>
<html>
<head>
    <title>Debug Panel - MultiTenantCloud</title>
    <style>
        body {
            font-family: monospace;
            background: #0a0e27;
            color: #00ff00;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: rgba(0,0,0,0.8);
            border: 1px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        pre {
            background: #000;
            padding: 10px;
            overflow-x: auto;
            border-radius: 5px;
        }
        button {
            background: #00ff00;
            color: #000;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            font-weight: bold;
        }
        .flag {
            background: #ffff00;
            color: #000;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🐛 Debug Panel (Exposed!)</h1>
            <p>Configuration and sensitive data - No authentication required!</p>
            <button onclick="getConfig()">Load Config</button>
            <div id="config"></div>
        </div>
        
        <div class="card">
            <h1>📊 System Info</h1>
            <p><strong>App Secret:</strong> {{ app.secret_key }}</p>
            <p><strong>Stripe Key:</strong> sp_test_4eC39HqLyjWDarjtT1zdp7dc</p>
            <p><strong>AWS Key:</strong> AKIAIOSFODNN7EXAMPLE</p>
            <p><strong>Database:</strong> multitenant.db</p>
            <p><strong>Debug Mode:</strong> True</p>
        </div>
        
        <div class="card">
            <h1>🔑 GraphQL Introspection</h1>
            <button onclick="graphQL()">Query Schema</button>
            <div id="graphql"></div>
        </div>
        
        
        <div class="card">
            <h1>💉 NoSQL Injection Test</h1>
            <button onclick="nosqlInjection()">Test $ne Operator</button>
            <div id="nosql"></div>
        </div>
        
        <div class="card">
            <h1>🔓 JWT Algorithm Test</h1>
            <button onclick="jwtAttack()">Test 'none' Algorithm</button>
            <div id="jwt"></div>
        </div>
    </div>
    
    <script>
        async function getConfig() {
            const response = await fetch('/api/v1/config/debug');
            const data = await response.json();
            document.getElementById('config').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
        
        async function graphQL() {
            const response = await fetch('/graphql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: '{ __schema { types { name } } }' })
            });
            const data = await response.json();
            document.getElementById('graphql').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
        
        async function nosqlInjection() {
            const response = await fetch('/api/v1/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: { "$ne": null }, password: { "$regex": ".*" } })
            });
            const data = await response.json();
            document.getElementById('nosql').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
        
        async function jwtAttack() {
            // Create token with 'none' algorithm
            const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }));
            const payload = btoa(JSON.stringify({ user_id: 8, tenant_id: 4, username: 'master', role: 'master' }));
            const token = `${header}.${payload}.`;
            
            const response = await fetch('/api/v1/auth/refresh', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            document.getElementById('jwt').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
    </script>
</body>
</html>

''' 


@app.route('/admin-panel')
def admin_panel():
    """Hidden admin panel for CTF management"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CTF Admin Panel</title>
        <style>
            body {
                font-family: monospace;
                background: #1a1a2e;
                color: #00ff00;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .card {
                background: rgba(0,0,0,0.8);
                border: 1px solid #00ff00;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }
            button {
                background: #00ff00;
                color: #000;
                border: none;
                padding: 10px 20px;
                margin: 10px;
                cursor: pointer;
                font-weight: bold;
            }
            input {
                background: #000;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 8px;
                margin: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>🔧 CTF Admin Panel</h1>
                <p>Created by <strong>Asfahan</strong></p>
                <input type="password" id="adminKey" placeholder="Admin Key">
                <button onclick="authenticate()">Login</button>
            </div>
            <div id="adminContent" style="display: none;">
                <div class="card">
                    <h2>🔄 CTF Management</h2>
                    <button onclick="resetCTF()">Reset CTF (Clear All Flags)</button>
                    <button onclick="fixLeaderboard()">Fix Leaderboard</button>
                    <button onclick="addMissingFlags()">Add Missing Flags</button>
                    <button onclick="checkStatus()">Check CTF Status</button>
                </div>
            </div>
        </div>
        
        <script>
            let authenticated = false;
            
            function authenticate() {
                const key = document.getElementById('adminKey').value;
                if (key === 'CTF_MASTER_2024') {
                    authenticated = true;
                    document.getElementById('adminContent').style.display = 'block';
                    alert('✅ Authenticated! Welcome, Admin!');
                } else {
                    alert('❌ Invalid Admin Key!');
                }
            }
            
            async function resetCTF() {
                if (!authenticated) return;
                const response = await fetch('/api/v1/admin/ctf/reset', {
                    method: 'POST',
                    headers: { 'X-Admin-Key': 'CTF_MASTER_2024' }
                });
                const data = await response.json();
                alert(JSON.stringify(data, null, 2));
                location.reload();
            }
            
            async function fixLeaderboard() {
                if (!authenticated) return;
                const response = await fetch('/api/v1/admin/ctf/fix-leaderboard', {
                    method: 'POST',
                    headers: { 'X-Admin-Key': 'CTF_MASTER_2024' }
                });
                const data = await response.json();
                alert(JSON.stringify(data, null, 2));
            }
            
            async function addMissingFlags() {
                if (!authenticated) return;
                const response = await fetch('/api/v1/admin/ctf/add-missing-flags', {
                    method: 'POST',
                    headers: { 'X-Admin-Key': 'CTF_MASTER_2024' }
                });
                const data = await response.json();
                alert(JSON.stringify(data, null, 2));
            }
            
            async function checkStatus() {
                const response = await fetch('/api/v1/admin/ctf/status');
                const data = await response.json();
                alert(JSON.stringify(data, null, 2));
            }
        </script>
    </body>
    </html>
    '''


@app.route('/api/doc')
def api_documentation():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MultiTenantCloud - API Documentation</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .signature {
                margin-top: 10px;
                font-size: 12px;
                opacity: 0.8;
            }
            .content {
                padding: 30px;
            }
            .section {
                margin-bottom: 40px;
            }
            .section h2 {
                color: #667eea;
                margin-bottom: 15px;
                border-bottom: 2px solid #667eea;
                padding-bottom: 5px;
            }
            .endpoint {
                background: #f8f9fa;
                border-left: 4px solid #ff4757;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
            .method {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
                margin-right: 10px;
            }
            .GET { background: #28a745; color: white; }
            .POST { background: #007bff; color: white; }
            .PUT { background: #ffc107; color: black; }
            .DELETE { background: #dc3545; color: white; }
            .url {
                font-family: monospace;
                font-size: 14px;
                font-weight: bold;
            }
            .description {
                margin: 10px 0;
                color: #666;
            }
            .hint {
                background: #e8f4fd;
                border-left: 4px solid #2196f3;
                padding: 8px 12px;
                margin-top: 8px;
                font-size: 12px;
                font-family: monospace;
                color: #0c5460;
            }
            pre {
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                font-size: 12px;
                margin: 10px 0;
            }
            .note {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                font-size: 14px;
            }
            .badge {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                margin-left: 8px;
            }
            .auth { background: #28a745; color: white; }
            .no-auth { background: #dc3545; color: white; }
            .debug-section {
                background: #f0f0f0;
                border-left: 4px solid #ff9800;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 MultiTenantCloud API</h1>
                <p>Enterprise SaaS Platform API Documentation</p>
                <div class="signature">Created by Asfahan | Security Research Lab</div>
            </div>
            
            <div class="content">
                <div class="note">
                    <strong>📖 API Overview:</strong> This API provides access to the MultiTenantCloud platform.
                    All endpoints require authentication via JWT token except where noted.
                </div>
                
                <!-- Authentication Section -->
                <div class="section">
                    <h2>🔐 Authentication</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/auth/login</span>
                        <span class="badge no-auth">No Auth</span>
                        <div class="description">Authenticate user and receive JWT token.</div>
                        <pre>curl -X POST http://localhost:5000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"john_doe","password":"Password123!"}'</pre>
                        <div class="hint">💡 HINT: SQL injection might work here - try single quotes</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/auth/refresh</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Refresh expired JWT token.</div>
                        <div class="hint">💡 HINT: Try changing the algorithm to 'none'</div>
                    </div>
                </div>
                
                <!-- User Operations Section -->
                <div class="section">
                    <h2>👤 User Operations</h2>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/user/profile/{user_id}</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Retrieve user profile information by ID.</div>
                        <div class="hint">💡 HINT: Try changing the ID to access other users (1-8)</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method PUT">PUT</span>
                        <span class="url">/api/v1/user/profile</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Update user profile information.</div>
                        <div class="hint">💡 HINT: Try adding "role":"admin" to the request</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/user/update-role</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Update user roles in the system.</div>
                        <div class="hint">💡 HINT: Regular users might upgrade themselves</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/user/role/update</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Special role update endpoint with hidden parameters.</div>
                        <div class="hint">💡 HINT: Try secret: "i_am_the_ultimate_hacker"</div>
                    </div>
                </div>
                
                <!-- Project System Section -->
                <div class="section">
                    <h2>📁 Project System</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/projects/create</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Create a new project. Limit: 5 projects per user.</div>
                        <pre>curl -X POST http://localhost:5000/api/v1/projects/create \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"My Project"}'</pre>
                        <div class="hint">💡 HINT: Send multiple requests at once to bypass limit. Flag at uid-111project</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/projects/list</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">List all projects with their UIDs.</div>
                        <div class="hint">💡 HINT: UIDs follow pattern uid-1project, uid-2project...</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/projects/view/{uid}</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">View project details by UID.</div>
                        <div class="hint">💡 HINT: Try uid-111project</div>
                    </div>
                </div>
                
                <!-- Reports System Section -->
                <div class="section">
                    <h2>📈 Reports System</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/reports/generate</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Generate a new financial report.</div>
                        <pre>curl -X POST http://localhost:5000/api/v1/reports/generate \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"title":"Q1 Report"}'</pre>
                        <div class="hint">💡 HINT: Flag at uid-111report</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/reports/list</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">List all generated reports.</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/reports/view/{uid}</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">View report details by UID.</div>
                        <div class="hint">💡 HINT: Try uid-111report</div>
                    </div>
                </div>
                
                <!-- Strategy Section -->
                <div class="section">
                    <h2>📄 Company Strategy</h2>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/strategy/view</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">View the company's strategic roadmap document.</div>
                        <div class="hint">💡 HINT: Look at the document footer for encoded information</div>
                    </div>
                </div>
                
                <!-- Master Secrets Section -->
                <div class="section">
                    <h2>🔐 Master Secrets</h2>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/secrets/generate</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Generate a master secret based on your name.</div>
                        <pre>curl -X GET "http://localhost:5000/api/v1/secrets/generate?name=john"</pre>
                        <div class="hint">💡 HINT: Try SQL injection payloads like ' OR '1'='1'--</div>
                    </div>
                </div>
                
                <!-- Search & Query Section -->
                <div class="section">
                    <h2>🔍 Search & Query</h2>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/search/users</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Search for users by username.</div>
                        <pre>curl "http://localhost:5000/api/v1/search/users?q=john"</pre>
                        <div class="hint">💡 HINT: Try ' UNION SELECT id,username,password_hash,role FROM users--</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/query</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Custom query endpoint.</div>
                        <div class="hint">💡 HINT: Try {"username": {"$ne": null}}</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/graphql</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">GraphQL API endpoint.</div>
                        <div class="hint">💡 HINT: Try { __schema { types { name } } }</div>
                    </div>
                </div>
                
                <!-- Invite System Section -->
                <div class="section">
                    <h2>🎁 Invite System</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/invite/generate</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Generate invitation codes.</div>
                        <div class="hint">💡 HINT: Hidden codes in page source: INVITE_OWNER_f529c5de, INVITE_ADMIN_8f3a9b2c, INVITE_MASTER_7e1d4c8f</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/invite/redeem</span>
                        <span class="badge no-auth">No Auth</span>
                        <div class="description">Redeem invitation codes.</div>
                        <pre>curl -X POST http://localhost:5000/api/invite/redeem -d '{"code":"INVITE_OWNER_f529c5de"}'</pre>
                        <div class="hint">💡 HINT: Redeem hidden codes for flags</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/invite/list</span>
                        <span class="badge no-auth">No Auth</span>
                        <div class="description">List all active invites.</div>
                        <div class="hint">💡 HINT: Exposes all invite codes</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/invite/check</span>
                        <span class="badge no-auth">No Auth</span>
                        <div class="description">Check if an invite code is valid.</div>
                        <div class="hint">💡 HINT: Try INVITE_MASTER_7e1d4c8f</div>
                    </div>
                </div>
                
                <!-- Administration Section -->
                <div class="section">
                    <h2>⚙️ Administration</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/admin/delete-user/{user_id}</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Administrative user deletion.</div>
                        <div class="hint">💡 HINT: Try this as a regular user</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/debug/audit-logs</span>
                        <span class="badge no-auth">No Auth</span>
                        <div class="description">View system audit logs.</div>
                        <div class="hint">💡 HINT: No authentication required</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/config/debug</span>
                        <span class="badge no-auth">No Auth</span>
                        <div class="description">Debug configuration endpoint.</div>
                        <div class="hint">💡 HINT: Leaks API keys and secrets!</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/tenant/settings</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Get tenant configuration settings.</div>
                        <div class="hint">💡 HINT: Try changing X-Tenant-ID header</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/tenant/import</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Import resources from external URLs.</div>
                        <div class="hint">💡 HINT: Try http://localhost:5000/api/v1/config/debug</div>
                    </div>
                </div>
                
                <!-- Team Management Section -->
                <div class="section">
                    <h2>👥 Team Management</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/team/import</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Import team data from URL.</div>
                        <div class="hint">💡 HINT: SSRF vulnerability - try internal URLs</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/team/export</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Export all team member data.</div>
                        <div class="hint">💡 HINT: Exposes sensitive data like salaries and SSNs</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/team/update</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Update team member information.</div>
                        <div class="hint">💡 HINT: Try mass assignment to escalate privileges</div>
                    </div>
                </div>
                
                <!-- Race Condition Section -->
                <div class="section">
                    <h2>⚡ Race Condition</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/role/upgrade</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Upgrade role for eligible users.</div>
                        <div class="hint">💡 HINT: Send multiple requests at once</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/submit-flag-race</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Submit flags for scoring (vulnerable endpoint).</div>
                        <div class="hint">💡 HINT: After 8 flags, you can exploit race condition. Reach 10,000 points for ultimate flag!</div>
                    </div>
                </div>
                
                <!-- Hidden Endpoints Section -->
                <div class="section">
                    <h2>🔍 Hidden Endpoints</h2>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/special/secret</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Secret endpoint with special flag.</div>
                        <div class="hint">💡 HINT: Try header X-Secret-Key: clap_if_you_find_this</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/admin-panel</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">CTF Admin Control Panel.</div>
                        <div class="hint">💡 HINT: Needs key CTF_MASTER_2024 (revealed after 8 flags)</div>
                    </div>
                </div>
                
                <!-- Debug Endpoints Section -->
                <div class="section">
                    <h2>🐛 Debug Endpoints</h2>
                    
                    <div class="debug-section">
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method GET">GET</span>
                            <span class="url">/api/v1/debug/create-test-user</span>
                            <div class="description">Create a test user for debugging.</div>
                            <div class="hint">💡 Creates user: test_user / test123 (admin role)</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method GET">GET</span>
                            <span class="url">/api/v1/debug/create-demo-users</span>
                            <div class="description">Create all demo users (john_doe, jane_smith, bob_wilson).</div>
                            <div class="hint">💡 Run this first to populate database with users</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method GET">GET</span>
                            <span class="url">/api/v1/debug/list-all-users</span>
                            <div class="description">List all users in database.</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method POST">POST</span>
                            <span class="url">/api/v1/debug/clear-projects</span>
                            <div class="description">Clear all user-created projects.</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method GET">GET</span>
                            <span class="url">/api/v1/debug/check-users</span>
                            <div class="description">Check users in database with password hashes.</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method POST">POST</span>
                            <span class="url">/api/v1/debug/reset-db</span>
                            <div class="description">⚠️ WARNING: Delete and recreate database.</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method GET">GET</span>
                            <span class="url">/api/v1/debug/table-schema</span>
                            <div class="description">Check the users table schema.</div>
                        </div>
                        
                        <div class="endpoint" style="border-left-color: #ff9800;">
                            <span class="method GET">GET</span>
                            <span class="url">/api/v1/debug/list-projects</span>
                            <div class="description">List all projects for debugging.</div>
                        </div>
                    </div>
                </div>
                
                <!-- Scoring System Section -->
                <div class="section">
                    <h2>🏆 Scoring System</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/submit-flag</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Submit discovered flags for scoring.</div>
                        <pre>curl -X POST http://localhost:5000/api/v1/submit-flag \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"flag":"FLAG{...}"}'</pre>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/leaderboard</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">View the hacker leaderboard.</div>
                    </div>
                </div>
                
                <!-- CTF Admin Section -->
                <div class="section">
                    <h2>🔧 CTF Admin Endpoints</h2>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/admin/ctf/reset</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Reset entire CTF (clears all flags).</div>
                        <div class="hint">💡 HINT: Needs X-Admin-Key: CTF_MASTER_2024</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method POST">POST</span>
                        <span class="url">/api/v1/admin/ctf/fix-leaderboard</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Recalculate leaderboard scores.</div>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method GET">GET</span>
                        <span class="url">/api/v1/admin/ctf/status</span>
                        <span class="badge auth">Auth Required</span>
                        <div class="description">Check CTF status and statistics.</div>
                    </div>
                </div>
                
                <div class="note">
                    <strong>🔑 Authentication:</strong> Most endpoints require a JWT token. Include it in the Authorization header:<br>
                    <code>Authorization: Bearer &lt;your_token&gt;</code><br><br>

                    <strong>💡 Pro Tips:</strong>
                    <ul>
                        <li>Check the page source (Ctrl+U) for hidden comments with invite codes</li>
                        <li>Some endpoints have rate limits that can be bypassed with concurrent requests</li>
                        <li>IDs and UIDs follow predictable patterns (uid-1project, uid-2project, etc.)</li>
                        <li>After finding 8 flags, a special admin key is revealed on the dashboard</li>
                        <li>Flags are hidden from GET requests - you must submit them via POST to /api/v1/submit-flag</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/api/v1/debug/create-demo-users', methods=['GET'])
def create_demo_users():
    """Create demo users with correct column count (22 columns)"""
    import hashlib
    
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # First, let's see what columns exist
    c.execute("PRAGMA table_info(users)")
    columns = c.fetchall()
    column_count = len(columns)
    print(f"Users table has {column_count} columns")
    
    # Check if tenants exist
    c.execute("SELECT COUNT(*) FROM tenants")
    tenant_count = c.fetchone()[0]
    
    if tenant_count == 0:
        now = datetime.now().isoformat()
        tenants_data = [
            (1, 'Acme Corp', 'acme', 'tenant_api_key_12345', 'enterprise', '{"theme": "dark"}', now, 1, 'acme_secret_2024'),
            (2, 'Globex Inc', 'globex', 'tenant_api_key_67890', 'business', '{"theme": "light"}', now, 1, 'globex_secret_2024'),
            (3, 'Initech', 'initech', 'tenant_api_key_11111', 'starter', '{"theme": "default"}', now, 1, 'initech_backdoor_secret'),
            (4, 'Admin Tenant', 'admin', 'master_api_key_99999', 'master', '{"is_master": true}', now, 1, 'FLAG{15: MASTER_TENANT_SECRET}')
        ]
        for tenant in tenants_data:
            try:
                c.execute('INSERT INTO tenants VALUES (?,?,?,?,?,?,?,?,?)', tenant)
            except Exception as e:
                print(f"Error inserting tenant: {e}")
    
    now = datetime.now().isoformat()
    
    # Demo users data with 22 columns (based on your CREATE TABLE statement)
    # Columns: id, tenant_id, username, email, password_hash, role, api_key, reset_token, mfa_secret, department, manager_id, salary, ssn, credit_card, is_deleted, failed_login, account_locked, internal_notes, last_login, created_at, user_metadata, backup_codes
    demo_users = [
        (1, 1, 'john_doe', 'john@acme.com', hashlib.sha256(b'Password123!').hexdigest(), 'admin', None, None, None, 'Engineering', 1, 95000, '123-45-6789', '4111111111111111', 0, 0, 0, 'FLAG{8: INTERNAL_USER_NOTE}', now, now, None, None),
        (2, 1, 'jane_smith', 'jane@acme.com', hashlib.sha256(b'Password456!').hexdigest(), 'owner', None, None, None, 'Sales', 1, 120000, '987-65-4321', '5500000000000004', 0, 0, 0, 'FLAG{9: OWNER_NOTES}', now, now, None, None),
        (3, 1, 'bob_wilson', 'bob@acme.com', hashlib.sha256(b'Password789!').hexdigest(), 'viewer', None, None, None, 'IT', 1, 65000, '555-55-5555', '378282246310005', 0, 0, 0, 'Regular user', now, now, None, None),
    ]
    
    created_users = []
    errors = []
    
    for user in demo_users:
        try:
            # Check if user already exists
            c.execute("SELECT id FROM users WHERE username=?", (user[2],))
            existing = c.fetchone()
            if existing:
                print(f"User {user[2]} already exists, skipping")
                continue
            
            # Insert with exactly 22 columns
            c.execute('''INSERT INTO users 
                (id, tenant_id, username, email, password_hash, role, api_key, reset_token, mfa_secret, 
                 department, manager_id, salary, ssn, credit_card, is_deleted, failed_login, account_locked, 
                 internal_notes, last_login, created_at, user_metadata, backup_codes) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', user)
            conn.commit()
            created_users.append(user[2])
            print(f"Created user: {user[2]}")
        except Exception as e:
            error_msg = f"Error creating user {user[2]}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    conn.close()
    
    # Verify users after creation
    verify_conn = sqlite3.connect('multitenant.db')
    verify_c = verify_conn.cursor()
    verify_c.execute("SELECT id, username FROM users")
    all_users = verify_c.fetchall()
    verify_conn.close()
    
    return jsonify({
        'message': 'Demo users creation attempted',
        'created_users': created_users,
        'errors': errors,
        'total_users_in_db': len(all_users),
        'users_in_db': [{'id': u[0], 'username': u[1]} for u in all_users],
        'demo_credentials': [
            {'username': 'john_doe', 'password': 'Password123!', 'role': 'admin'},
            {'username': 'jane_smith', 'password': 'Password456!', 'role': 'owner'},
            {'username': 'bob_wilson', 'password': 'Password789!', 'role': 'viewer'}
        ]
    })


def update_db_schema():
    """Update database schema to add missing columns"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Check if is_hidden column exists in invites table
    try:
        c.execute("SELECT is_hidden FROM invites LIMIT 1")
    except sqlite3.OperationalError:
        # Add the column if it doesn't exist
        c.execute("ALTER TABLE invites ADD COLUMN is_hidden INTEGER DEFAULT 0")
        print("Added is_hidden column to invites table")
    
    # Check if secret_flag column exists
    try:
        c.execute("SELECT secret_flag FROM invites LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE invites ADD COLUMN secret_flag TEXT")
        print("Added secret_flag column to invites table")
    
    conn.commit()
    conn.close()

# Call this function after init_db()
init_db()
update_db_schema()

@app.route('/api/v1/debug/table-schema', methods=['GET'])
def table_schema():
    """Check the users table schema"""
    conn = sqlite3.connect('multitenant.db')
    c = conn.cursor()
    
    # Get the table schema
    c.execute("PRAGMA table_info(users)")
    columns = c.fetchall()
    
    conn.close()
    
    return jsonify({
        'columns': [{'cid': col[0], 'name': col[1], 'type': col[2]} for col in columns],
        'column_count': len(columns)
    })

@app.route('/api/v1/config/debug', methods=['GET'])
def debug_config():
    return jsonify({
        'app_secret_key': app.secret_key,
        'stripe_secret': STRIPE_SECRET_KEY,
        'aws_access_key': AWS_ACCESS_KEY,
        'jwt_secret': JWT_SECRET,
        'master_api_key': MASTER_API_KEY,
        'admin_backdoor': ADMIN_BACKDOOR,
        'flag': 'FLAG{5: SECRET_EXPOSURE}'
    })


# Also add the missing HTML templates from previous response
# [Insert all the HTML templates from the previous response here]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
