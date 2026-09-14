import os
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "attendance.db"
)


# ============================================================
# SUBJECTS
# ============================================================

SUBJECTS = []


# ============================================================
# CONNECTION
# ============================================================

def get_db_connection():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# DATABASE MIGRATION HELPERS
# ============================================================

def table_has_column(
    cursor,
    table_name,
    column_name
):

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    return any(
        column["name"] == column_name
        for column in columns
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    conn = get_db_connection()

    cursor = conn.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            username TEXT
                NOT NULL UNIQUE,

            password_hash TEXT
                NOT NULL,

            role TEXT
                NOT NULL,

            is_active INTEGER
                NOT NULL DEFAULT 1,

            created_at TEXT
                DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # --------------------------------------------------------
    # DEPARTMENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (

            department_id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            department_code TEXT
                NOT NULL UNIQUE,

            department_name TEXT
                NOT NULL UNIQUE,

            description TEXT,

            status TEXT
                NOT NULL
                DEFAULT 'ACTIVE'
        )
    """)


    # --------------------------------------------------------
    # COURSES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (

            course_id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            department_id INTEGER
                NOT NULL,

            course_code TEXT
                NOT NULL UNIQUE,

            course_name TEXT
                NOT NULL,

            degree_type TEXT
                NOT NULL,

            duration_years INTEGER
                NOT NULL,

            year INTEGER
                NOT NULL DEFAULT 1,

            semester INTEGER
                NOT NULL DEFAULT 1,

            created_at TEXT
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (department_id)
                REFERENCES departments(department_id)
                ON DELETE RESTRICT
        )
    """)


    # --------------------------------------------------------
    # MIGRATE OLD COURSES TABLE
    # --------------------------------------------------------

    if not table_has_column(
        cursor,
        "courses",
        "year"
    ):

        cursor.execute("""
            ALTER TABLE courses
            ADD COLUMN year INTEGER
            NOT NULL DEFAULT 1
        """)


    if not table_has_column(
        cursor,
        "courses",
        "semester"
    ):

        cursor.execute("""
            ALTER TABLE courses
            ADD COLUMN semester INTEGER
            NOT NULL DEFAULT 1
        """)


    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            student_id TEXT
                PRIMARY KEY,

            student_name TEXT
                NOT NULL
        )
    """)


    # --------------------------------------------------------
    # ATTENDANCE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            student_id TEXT
                NOT NULL,

            student_name TEXT,

            date TEXT,

            time TEXT
        )
    """)


    # --------------------------------------------------------
    # SUBJECT ATTENDANCE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subject_attendance (

            id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            student_id TEXT
                NOT NULL,

            subject_code TEXT
                NOT NULL,

            date TEXT
                NOT NULL,

            status TEXT
                NOT NULL,

            UNIQUE(
                student_id,
                subject_code,
                date
            )
        )
    """)


    conn.commit()

    conn.close()

    create_default_admin()


# ============================================================
# USER / AUTHENTICATION FUNCTIONS
# ============================================================

def get_user_by_username(username):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            username,
            password_hash,
            role,
            is_active,
            created_at

        FROM users

        WHERE username = ?
        """,
        (
            username,
        )
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        user = dict(row)

        user["is_active"] = bool(
            user["is_active"]
        )

        return user

    return None


def get_user_by_id(user_id):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            username,
            password_hash,
            role,
            is_active,
            created_at

        FROM users

        WHERE id = ?
        """,
        (
            user_id,
        )
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        user = dict(row)

        user["is_active"] = bool(
            user["is_active"]
        )

        return user

    return None


def create_user(
    username,
    password,
    role,
    is_active=True
):

    username = str(
        username
    ).strip()

    password_hash = generate_password_hash(
        password
    )

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (

            username,
            password_hash,
            role,
            is_active

        )

        VALUES (?, ?, ?, ?)
        """,
        (
            username,
            password_hash,
            str(role).upper(),
            1 if is_active else 0
        )
    )

    user_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return user_id


def create_default_admin():

    existing_admin = get_user_by_username(
        "admin"
    )

    if existing_admin:

        return

    create_user(
        username="admin",
        password="admin123",
        role="ADMIN",
        is_active=True
    )

    print(
        "Default admin created: admin / admin123"
    )


# ============================================================
# DEPARTMENT FUNCTIONS
# ============================================================

def create_department(
    department_code,
    department_name,
    description=""
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO departments (

            department_code,
            department_name,
            description

        )

        VALUES (?, ?, ?)
        """,
        (
            department_code,
            department_name,
            description
        )
    )

    department_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return department_id


def get_all_departments():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            department_id,
            department_code,
            department_name,
            description,
            status

        FROM departments

        ORDER BY department_name
    """)

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_department(
    department_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *

        FROM departments

        WHERE department_id = ?
        """,
        (
            department_id,
        )
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        return dict(row)

    return None


def update_department(
    department_id,
    department_code,
    department_name,
    description,
    status
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE departments

        SET

            department_code = ?,

            department_name = ?,

            description = ?,

            status = ?

        WHERE department_id = ?
        """,
        (
            department_code,
            department_name,
            description,
            status,
            department_id
        )
    )

    conn.commit()

    conn.close()


def delete_department(
    department_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM departments

        WHERE department_id = ?
        """,
        (
            department_id,
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# COURSE FUNCTIONS
# ============================================================

def create_course(
    department_id,
    course_code,
    course_name,
    degree_type,
    duration_years,
    year,
    semester
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO courses (

            department_id,
            course_code,
            course_name,
            degree_type,
            duration_years,
            year,
            semester

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            department_id,
            course_code,
            course_name,
            degree_type,
            duration_years,
            year,
            semester
        )
    )

    course_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return course_id


def get_all_courses():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            c.course_id,

            c.department_id,

            d.department_code,

            d.department_name,

            c.course_code,

            c.course_name,

            c.degree_type,

            c.duration_years,

            c.year,

            c.semester,

            c.created_at

        FROM courses c

        INNER JOIN departments d

        ON c.department_id =
           d.department_id

        ORDER BY

            d.department_name,

            c.year,

            c.semester,

            c.course_name
    """)

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_courses_by_department(
    department_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            c.course_id,

            c.department_id,

            d.department_code,

            d.department_name,

            c.course_code,

            c.course_name,

            c.degree_type,

            c.duration_years,

            c.year,

            c.semester,

            c.created_at

        FROM courses c

        INNER JOIN departments d

        ON c.department_id =
           d.department_id

        WHERE c.department_id = ?

        ORDER BY

            c.year,

            c.semester,

            c.course_name
        """,
        (
            department_id,
        )
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_course(
    course_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *

        FROM courses

        WHERE course_id = ?
        """,
        (
            course_id,
        )
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        return dict(row)

    return None


def update_course(
    course_id,
    department_id,
    course_code,
    course_name,
    degree_type,
    duration_years,
    year,
    semester
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE courses

        SET

            department_id = ?,

            course_code = ?,

            course_name = ?,

            degree_type = ?,

            duration_years = ?,

            year = ?,

            semester = ?

        WHERE course_id = ?
        """,
        (
            department_id,
            course_code,
            course_name,
            degree_type,
            duration_years,
            year,
            semester,
            course_id
        )
    )

    conn.commit()

    conn.close()


def delete_course(
    course_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM courses

        WHERE course_id = ?
        """,
        (
            course_id,
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# STUDENT FUNCTIONS
# ============================================================

def add_student(
    student_id,
    student_name
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO students (

            student_id,
            student_name

        )

        VALUES (?, ?)
        """,
        (
            student_id,
            student_name
        )
    )

    conn.commit()

    conn.close()


def get_all_students():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            student_id,
            student_name

        FROM students

        ORDER BY student_name
    """)

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_student(
    student_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *

        FROM students

        WHERE student_id = ?
        """,
        (
            student_id,
        )
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        return dict(row)

    return None


def delete_student_db(
    student_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM subject_attendance

        WHERE student_id = ?
        """,
        (
            student_id,
        )
    )

    cursor.execute(
        """
        DELETE FROM attendance

        WHERE student_id = ?
        """,
        (
            student_id,
        )
    )

    cursor.execute(
        """
        DELETE FROM students

        WHERE student_id = ?
        """,
        (
            student_id,
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# ATTENDANCE FUNCTIONS
# ============================================================

def mark_attendance(student_id, student_name=None, date=None, time=None):
    from datetime import datetime

    date = date or datetime.now().strftime("%Y-%m-%d")
    time = time or datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Prevent duplicate attendance for the same student on the same date
    cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE student_id = ? AND date = ?
        LIMIT 1
        """,
        (student_id, date),
    )

    if cursor.fetchone():
        conn.close()
        return False

    # Get student name automatically if not supplied
    if not student_name:
        cursor.execute(
            "SELECT student_name FROM students WHERE student_id = ?",
            (student_id,),
        )
        student = cursor.fetchone()

        if student:
            student_name = student["student_name"]

    cursor.execute(
        """
        INSERT INTO attendance (
            student_id,
            student_name,
            date,
            time
        )
        VALUES (?, ?, ?, ?)
        """,
        (student_id, student_name, date, time),
    )

    conn.commit()
    conn.close()

    return True


def get_attendance_records(
    filter_date=None,
    search_query=None
):

    conn = get_db_connection()

    cursor = conn.cursor()

    query = """
        SELECT
            id,
            student_id,
            student_name,
            date,
            time

        FROM attendance

        WHERE 1 = 1
    """

    params = []

    if filter_date:

        query += """
            AND date = ?
        """

        params.append(
            filter_date
        )

    if search_query:

        query += """
            AND (
                student_id LIKE ?
                OR
                student_name LIKE ?
            )
        """

        search_value = (
            f"%{search_query}%"
        )

        params.append(
            search_value
        )

        params.append(
            search_value
        )

    query += """
        ORDER BY id DESC
    """

    cursor.execute(
        query,
        params
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def check_face_punch_exists(
    student_id,
    date
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id

        FROM attendance

        WHERE
            student_id = ?
            AND date = ?

        LIMIT 1
        """,
        (
            student_id,
            date
        )
    )

    row = cursor.fetchone()

    conn.close()

    return row is not None


# ============================================================
# SUBJECT ATTENDANCE FUNCTIONS
# ============================================================

def mark_subject_attendance(
    student_id,
    subject_code,
    date,
    status
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO
        subject_attendance (

            student_id,
            subject_code,
            date,
            status

        )

        VALUES (?, ?, ?, ?)
        """,
        (
            student_id,
            subject_code,
            date,
            status
        )
    )

    conn.commit()

    conn.close()


def get_student_subject_summary(
    student_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            subject_code,

            COUNT(*) AS total_classes,

            SUM(
                CASE
                    WHEN status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_count

        FROM subject_attendance

        WHERE student_id = ?

        GROUP BY subject_code
        """,
        (
            student_id,
        )
    )

    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:

        data = dict(
            row
        )

        total = data[
            "total_classes"
        ]

        present = (
            data[
                "present_count"
            ]
            or 0
        )

        percentage = (
            round(
                (
                    present / total
                ) * 100,
                2
            )
            if total > 0
            else 0
        )

        result.append({

            "subject_code":
                data["subject_code"],

            "total_classes":
                total,

            "present_count":
                present,

            "percentage":
                percentage
        })

    return result


def get_student_attendance_matrix(
    student_id
):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            subject_code,
            date,
            status

        FROM subject_attendance

        WHERE student_id = ?

        ORDER BY date DESC
        """,
        (
            student_id,
        )
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]
