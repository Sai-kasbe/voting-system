import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import os

# ====== CONFIGURATION ======
st.set_page_config(page_title="KGRCET ONLINE ELECTION SYSTEM", layout="wide")

st.markdown("""
    <style>
    body {
        background-color: #0D1B2A;
        color: white;
    }
    .stButton>button {
        background-color: #1B263B;
        color: white;
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        margin-top: 10px;
    }
    h1, h2, h3, h4 {
        color: #E0E1DD;
    }
    </style>
""", unsafe_allow_html=True)

# ====== UTILS ======
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_connection():
    conn = sqlite3.connect("voting_app.db", check_same_thread=False)
    return conn, conn.cursor()

def authenticate_user(roll_no, password):
    conn, cursor = get_connection()
    cursor.execute("SELECT * FROM users WHERE roll_no=? AND password=?", (roll_no, hash_password(password)))
    row = cursor.fetchone()
    if row:
        return {
            "roll_no": row[0],
            "name": row[1],
            "email": row[3],
            "phone": row[4],
            "image": row[5],
            "has_voted": row[6]
        }
    return None

# ====== INIT DB ======
def create_tables():
    conn, cursor = get_connection()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        roll_no TEXT PRIMARY KEY,
        name TEXT,
        password TEXT,
        email TEXT,
        phone TEXT,
        image TEXT,
        has_voted INTEGER DEFAULT 0
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates (
        candidate_name TEXT,
        roll_no TEXT PRIMARY KEY,
        department TEXT,
        year_sem TEXT,
        role TEXT,
        image TEXT,
        votes INTEGER DEFAULT 0
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS result_schedule (
        id INTEGER PRIMARY KEY,
        result_date TEXT,
        is_announced INTEGER DEFAULT 0
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS blockchain (
        vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        candidate TEXT,
        vote_hash TEXT,
        timestamp TEXT
    )''')

    conn.commit()
    conn.close()

def record_vote_hash(roll_no, candidate):
    vote_string = roll_no + candidate + datetime.now().isoformat()
    vote_hash = hashlib.sha256(vote_string.encode()).hexdigest()
    conn, cursor = get_connection()
    cursor.execute("INSERT INTO blockchain (roll_no, candidate, vote_hash, timestamp) VALUES (?, ?, ?, ?)",
                   (roll_no, candidate, vote_hash, datetime.now().isoformat()))
    conn.commit()

# ====== ADMIN CREDENTIALS ======
ADMIN_ID = "22QM1A6721"
ADMIN_PASS = hash_password("Sai7@99499")

# ====== USER LOGIN ======
def user_login():
    st.subheader("👨‍🎓 User Login")
    roll_no = st.text_input("Roll Number")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = authenticate_user(roll_no, password)
        if user:
            st.session_state.user_logged_in = True
            st.session_state.user_data = user
        else:
            st.error("Invalid credentials!")

def user_dashboard(user):
    st.header("🗳️ Vote Dashboard")
    if user['has_voted']:
        st.success("Status: ✅ VOTED")
    else:
        st.warning("Status: ❌ NOT VOTED")
        conn, cursor = get_connection()
        candidates = pd.read_sql("SELECT * FROM candidates", conn)
        selected = st.radio("Choose your candidate:", candidates['candidate_name'])
        if st.button("Cast Vote"):
            cursor.execute("UPDATE candidates SET votes = votes + 1 WHERE candidate_name=?", (selected,))
            cursor.execute("UPDATE users SET has_voted=1 WHERE roll_no=?", (user['roll_no'],))
            conn.commit()
            record_vote_hash(user['roll_no'], selected)
            st.success("Vote Cast Successfully!")

# ====== ADMIN LOGIN ======
def admin_login():
    st.subheader("🔐 Admin Login")
    username = st.text_input("Admin ID")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == ADMIN_ID and hash_password(password) == ADMIN_PASS:
            st.session_state.admin_logged_in = True
        else:
            st.error("Invalid admin credentials!")

def admin_dashboard():
    st.header("📊 Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["➕ Add Candidate", "🧑‍💼 Registered Users", "📢 Result Settings"])

    with tab1:
        st.subheader("Add New Candidate (Party)")
        name = st.text_input("Candidate Name")
        roll_no = st.text_input("Roll No (roll_no)")
        dept = st.text_input("Department")
        year_sem = st.text_input("Year/Sem")
        role = st.selectbox("Role", ["President", "Vice-President", "Secretary", "Treasurer"])
        image_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

        if st.button("Add Candidate"):
            if not all([name, roll_no, dept, year_sem, role, image_file]):
                st.error("Please fill in all fields and upload an image.")
            else:
                try:
                    os.makedirs("images", exist_ok=True)
                    image_path = os.path.join("images", image_file.name)
                    with open(image_path, "wb") as f:
                        f.write(image_file.getbuffer())

                    conn, cursor = get_connection()
                    cursor.execute(
                        "INSERT INTO candidates (candidate_name, roll_no, department, year_sem, role, image, votes) VALUES (?, ?, ?, ?, ?, ?, 0)",
                        (name, roll_no, dept, year_sem, role, image_path)
                    )
                    conn.commit()
                    st.success("Candidate Added Successfully!")
                except sqlite3.IntegrityError:
                    st.error("Candidate with this roll number already exists!")
                except Exception as e:
                    st.error(f"Error while adding candidate: {e}")
                finally:
                    conn.close()

    with tab2:
        st.subheader("All Registered Users")
        conn, cursor = get_connection()
        try:
            df = pd.read_sql("SELECT roll_no, name, email, phone, has_voted FROM users", conn)
            st.dataframe(df)
        except Exception as e:
            st.error(f"Failed to load users: {e}")
        finally:
            conn.close()

    with tab3:
        conn, cursor = get_connection()
        st.subheader("Schedule or Announce Result")
        new_date = st.date_input("Result Date")
        if st.button("Schedule Result"):
            cursor.execute("INSERT OR REPLACE INTO result_schedule (id, result_date, is_announced) VALUES (1, ?, 0)", (str(new_date),))
            conn.commit()
            st.success("Result Scheduled!")
        if st.button("Announce Now"):
            cursor.execute("UPDATE result_schedule SET is_announced=1 WHERE id=1")
            conn.commit()
            st.success("Result Announced!")
        result = cursor.execute("SELECT * FROM result_schedule").fetchone()
        if result:
            st.info(f"Scheduled Date: {result[1]} | Announced: {'Yes' if result[2] else 'No'}")
        conn.close()

# ====== REGISTRATION ======
def user_registration():
    st.subheader("📝 New User Registration")
    name = st.text_input("Full Name")
    roll_no = st.text_input("Roll Number (roll_no)")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    password = st.text_input("Password", type="password")
    image = st.file_uploader("Upload Image")

    if st.button("Register"):
        if not all([name, roll_no, email, phone, password, image]):
            st.error("All fields including image are required.")
            return

        image_path = "images/" + image.name
        try:
            os.makedirs("images", exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(image.getbuffer())

            from database import add_user  # Import the correct function
            success = add_user(roll_no, name, password, email, phone, image_path)
            if success:
                st.success("Registered successfully!")
            else:
                st.error("User with this roll number already exists!")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            pass
            

# ====== FORGOT PASSWORD ======
def forgot_password():
    st.subheader("🔑 Forgot Password")
    roll_no = st.text_input("Enter your registered Roll Number")
    email = st.text_input("Enter your registered Email")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Reset Password"):
        conn, cursor = get_connection()
        cursor.execute("SELECT * FROM users WHERE roll_no=? AND email=?", (roll_no, email))
        if cursor.fetchone():
            cursor.execute("UPDATE users SET password=? WHERE roll_no=?", (hash_password(new_pass), roll_no))
            conn.commit()
            st.success("Password updated successfully!")
        else:
            st.error("Invalid roll number or email!")

# ====== MAIN ======
def main():
    st.title("🏛️ KGRCET ONLINE ELECTION SYSTEM")
    create_tables()

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False

    if st.session_state.user_logged_in:
        user_dashboard(st.session_state.user_data)
        if st.button("Logout"):
            st.session_state.user_logged_in = False
            st.session_state.user_data = None
            st.success("User logged out!")

    elif st.session_state.admin_logged_in:
        admin_dashboard()
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.success("Admin logged out!")

    else:
        page = st.sidebar.selectbox("Choose Page", ["Home", "User Login", "Admin Login", "Register", "Forgot Password"])

        if page == "User Login":
            user_login()
        elif page == "Admin Login":
            admin_login()
        elif page == "Register":
            user_registration()
        elif page == "Forgot Password":
            forgot_password()
        else:
            st.markdown("Welcome to KGRCET's transparent, secure, blockchain-based Online Voting System.")
            st.markdown("Please use the sidebar to navigate.")

if __name__ == "__main__":
    main()
