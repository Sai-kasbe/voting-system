import sqlite3
import hashlib

# ====== Database Connection ======
def get_connection():
    conn = sqlite3.connect("voting_app.db", check_same_thread=False)
    return conn, conn.cursor()

# ====== Hashing Function ======
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ====== Create Tables If Not Exist ======
def create_tables():
    conn, cursor = get_connection()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            roll_no TEXT PRIMARY KEY,
            name TEXT,
            password TEXT,
            email TEXT,
            phone TEXT,
            image TEXT,
            has_voted INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_name TEXT,
            roll_no TEXT PRIMARY KEY,
            department TEXT,
            year_sem TEXT,
            role TEXT,
            image TEXT,
            votes INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS result_schedule (
            id INTEGER PRIMARY KEY,
            result_date TEXT,
            is_announced INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blockchain (
            vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT,
            candidate TEXT,
            vote_hash TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()

# ====== Add New User ======
def add_user(roll_no, name, password, email, phone, image):
    conn, cursor = get_connection()
    try:
        cursor.execute("INSERT INTO users (roll_no, name, password, email, phone, image, has_voted) VALUES (?, ?, ?, ?, ?, ?, 0)",
                       (roll_no, name, hash_password(password), email, phone, image))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
