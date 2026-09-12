import os
import sqlite3
import random
from datetime import datetime

# Path to the database file
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database"))
DB_PATH = os.path.join(DB_DIR, "attendance.db")

# Standard course subjects matching Sandip University B.Tech AI & ML curriculum
SUBJECTS = {
    "INF45011": "Computer Vision (CV)",
    "INF45021": "AI & Machine Learning",
    "INF45022": "Deep Learning (DL)",
    "INF45112": "Data Science & NLP",
    "CVLAB": "Computer Vision Lab (CVLAB)"
}

# Standard dates for historical simulation to populate the ERP matrix (from user screenshots)
HISTORICAL_DATES = [
    "06-07-2026", "08-07-2026", "09-07-2026", "10-07-2026", "13-07-2026",
    "14-07-2026", "15-07-2026", "16-07-2026", "17-07-2026", "20-07-2026",
    "21-07-2026", "22-07-2026", "23-07-2026", "24-07-2026", "27-07-2026"
]

def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    Enforces foreign keys support.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database by creating the required tables and indexes.
    This runs at application startup.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create daily gate entry / face punches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE
        );
    """)

    # Index to prevent duplicate daily gate face punches
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_student_date 
        ON attendance (student_id, date);
    """)

    # Create subject-wise attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subject_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_code TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE
        );
    """)

    # Composite unique index to restrict double marking for same subject/date
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_subject_att_uniq
        ON subject_attendance (student_id, subject_code, date);
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully at:", DB_PATH)

def add_student(student_id, student_name):
    """
    Adds a new student to the students table and seeds historical attendance logs
    to simulate a realistic ERP dashboard for demonstration.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Insert student record
        cursor.execute(
            "INSERT INTO students (student_id, student_name) VALUES (?, ?);",
            (student_id.strip(), student_name.strip())
        )
        conn.commit()
        
        # Seed historical attendance logs
        seed_historical_records(student_id, student_name)
        return True
    except sqlite3.IntegrityError as e:
        raise e
    finally:
        conn.close()

def delete_student_db(student_id):
    """
    Deletes a student from the database.
    Because of ON DELETE CASCADE, daily face punches and subject attendance
    records are automatically removed.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM students WHERE student_id = ?;", (student_id.strip(),))
        conn.commit()
        return True
    finally:
        conn.close()

def seed_historical_records(student_id, student_name):
    """
    Seeds historical logs for a student across standard dates, ensuring that
    if marked Present in a subject, a corresponding daily face punch is created.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        random.seed(int(student_id) if student_id.isdigit() else 42)
        
        for date_str in HISTORICAL_DATES:
            # Determine if the student entered campus today (80% probability)
            had_face_punch = random.random() < 0.8
            
            if had_face_punch:
                # Log a daily face punch
                punch_time = f"{random.randint(8, 9):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
                cursor.execute("""
                    INSERT OR IGNORE INTO attendance (student_id, student_name, date, time, status)
                    VALUES (?, ?, ?, ?, 'Present');
                """, (student_id, student_name, date_str, punch_time))

                # If on campus, they can be Present ('P') or Absent ('A') for each subject
                for sub_code in SUBJECTS.keys():
                    # 75% attendance probability if they entered campus
                    status = "Present" if random.random() < 0.75 else "Absent"
                    cursor.execute("""
                        INSERT OR IGNORE INTO subject_attendance (student_id, subject_code, date, status)
                        VALUES (?, ?, ?, ?);
                    """, (student_id, sub_code, date_str, status))
            else:
                # No face punch = Absent for all subjects (forced lockout)
                for sub_code in SUBJECTS.keys():
                    cursor.execute("""
                        INSERT OR IGNORE INTO subject_attendance (student_id, subject_code, date, status)
                        VALUES (?, ?, ?, 'Absent');
                    """, (student_id, sub_code, date_str))
                    
        conn.commit()
        print(f"Seeded historical ERP attendance logs for student ID: {student_id}")
    except Exception as e:
        print(f"Error seeding historical records: {e}")
    finally:
        conn.close()

def get_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?;", (student_id.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY student_id ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_attendance(student_id, student_name, date_str, time_str, status="Present"):
    """
    Records a daily face punch (gate entry) for a student.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO attendance (student_id, student_name, date, time, status)
            VALUES (?, ?, ?, ?, ?);
        """, (student_id.strip(), student_name.strip(), date_str, time_str, status))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        raise e
    finally:
        conn.close()

def get_attendance_records(filter_date=None, search_query=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM attendance WHERE 1=1"
    params = []
    if filter_date:
        query += " AND date = ?"
        params.append(filter_date.strip())
    if search_query:
        query += " AND (student_id LIKE ? OR student_name LIKE ?)"
        search_like = f"%{search_query.strip()}%"
        params.append(search_like)
        params.append(search_like)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# =========================================================================
# SUBJECT ATTENDANCE DATABASE QUERY METHODS
# =========================================================================
def check_face_punch_exists(student_id, date_str):
    """
    Checks if a student has a face punch on campus for a given date.
    Returns: Boolean
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM attendance WHERE student_id = ? AND date = ?;", (student_id, date_str))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_subject_attendance(student_id, subject_code, date_str, status):
    """
    Inserts or updates subject-wise attendance.
    Enforces the face punching prerequisite: raises exception if student hasn't punched in.
    """
    # Verify face punch gate entry exists first
    if status == "Present" and not check_face_punch_exists(student_id, date_str):
        raise ValueError(f"Student ID {student_id} has not punched their face today! Cannot mark Present.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO subject_attendance (student_id, subject_code, date, status)
            VALUES (?, ?, ?, ?);
        """, (student_id, subject_code, date_str, status))
        conn.commit()
        return True
    finally:
        conn.close()

def get_student_subject_summary(student_id):
    """
    Returns statistics summaries for all subjects (Total Lectures, Presents, Percentages)
    mimicking the Student Subject List page.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    summary = []
    
    try:
        for sub_code, sub_name in SUBJECTS.items():
            # Count total lectures recorded for this subject
            cursor.execute("""
                SELECT COUNT(*) FROM subject_attendance 
                WHERE student_id = ? AND subject_code = ?;
            """, (student_id, sub_code))
            total_lectures = cursor.fetchone()[0]

            # Count presents
            cursor.execute("""
                SELECT COUNT(*) FROM subject_attendance 
                WHERE student_id = ? AND subject_code = ? AND status = 'Present';
            """, (student_id, sub_code))
            present_lectures = cursor.fetchone()[0]

            pct = 0.0
            if total_lectures > 0:
                pct = round((present_lectures / total_lectures) * 100, 2)

            summary.append({
                "subject_code": sub_code,
                "subject_name": sub_name,
                "total_lectures": total_lectures,
                "present_lectures": present_lectures,
                "attendance_percentage": pct
            })
    finally:
        conn.close()
        
    return summary

def get_student_attendance_matrix(student_id):
    """
    Generates a list of date rows with subject columns, representing
    the View Attendance Matrix Grid in the ERP.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all unique dates this student has records for
    cursor.execute("""
        SELECT DISTINCT date FROM subject_attendance 
        WHERE student_id = ? ORDER BY date DESC;
    """, (student_id,))
    dates = [row["date"] for row in cursor.fetchall()]
    
    matrix = []
    try:
        for date_str in dates:
            row_data = {
                "date": date_str,
                "day": get_day_name(date_str)
            }
            
            # For each subject, fetch status
            for sub_code in SUBJECTS.keys():
                cursor.execute("""
                    SELECT status FROM subject_attendance 
                    WHERE student_id = ? AND subject_code = ? AND date = ?;
                """, (student_id, sub_code, date_str))
                row = cursor.fetchone()
                # Use 'P' for Present, 'A' for Absent, '-' if no lecture recorded
                if row:
                    row_data[sub_code] = 'P' if row["status"] == "Present" else 'A'
                else:
                    row_data[sub_code] = '-'
            
            matrix.append(row_data)
    finally:
        conn.close()
        
    return matrix

def get_day_name(date_str):
    """Converts DD-MM-YYYY to Day of week name (e.g. Mon, Wed)."""
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%a")
    except:
        return "Day"

if __name__ == "__main__":
    init_db()
