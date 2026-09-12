import os
import sqlite3
from datetime import datetime


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DB_DIR = os.path.join(
    PROJECT_ROOT,
    "database"
)

DB_PATH = os.path.join(
    DB_DIR,
    "attendance.db"
)


# ============================================================
# LEGACY SUBJECTS
# Kept for compatibility with the existing attendance system.
# ============================================================

SUBJECTS = {
    "INF45011": "Computer Vision (CV)",
    "INF45021": "AI & Machine Learning",
    "INF45022": "Deep Learning (DL)",
    "INF45112": "Data Science & NLP",
    "CVLAB": "Computer Vision Lab (CVLAB)"
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    os.makedirs(DB_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA foreign_keys = ON;")

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# HELPER
# ============================================================

def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def column_exists(conn, table_name, column_name):

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def add_column_if_missing(
    conn,
    table_name,
    column_name,
    column_definition
):

    if not column_exists(
        conn,
        table_name,
        column_name
    ):

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# ============================================================
# INITIAL DATABASE SETUP
# ============================================================

def init_db():

    conn = get_db_connection()

    try:

        # ----------------------------------------------------
        # 1. Create legacy tables
        # ----------------------------------------------------
        create_legacy_tables(conn)

        # ----------------------------------------------------
        # 2. Create core system tables
        # ----------------------------------------------------
        create_core_system_tables(conn)

        # ----------------------------------------------------
        # 3. Create academic structure tables
        # ----------------------------------------------------
        create_academic_tables(conn)

        # ----------------------------------------------------
        # 4. Create relationship tables
        # ----------------------------------------------------
        create_relationship_tables(conn)

        # ----------------------------------------------------
        # 5. Migrate existing databases
        #
        # IMPORTANT:
        # Existing databases may have been created using
        # an older schema. Migration MUST happen before
        # indexes are created.
        # ----------------------------------------------------
        migrate_existing_tables(conn)

        # ----------------------------------------------------
        # 6. Create indexes
        # ----------------------------------------------------
        create_indexes(conn)

        # ----------------------------------------------------
        # 7. Commit everything
        # ----------------------------------------------------
        conn.commit()

        print(
            "Database initialized successfully at:",
            DB_PATH
        )

    except Exception as e:

        # ----------------------------------------------------
        # Roll back if anything fails
        # ----------------------------------------------------
        conn.rollback()

        print(
            "Database initialization failed:",
            str(e)
        )

        raise

    finally:

        # ----------------------------------------------------
        # Always close database connection
        # ----------------------------------------------------
        conn.close()

# ============================================================
# LEGACY TABLES
# Keep these because your existing application uses them.
# ============================================================

def create_legacy_tables(conn):

    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (

            student_id TEXT PRIMARY KEY,

            student_name TEXT NOT NULL,

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    # --------------------------------------------------------
    # OLD DAILY ATTENDANCE
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            student_name TEXT NOT NULL,

            date TEXT NOT NULL,

            time TEXT NOT NULL,

            status TEXT NOT NULL,

            FOREIGN KEY (
                student_id
            )
            REFERENCES students(student_id)

            ON DELETE CASCADE
        );
        """
    )


    # --------------------------------------------------------
    # OLD SUBJECT ATTENDANCE
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            subject_code TEXT NOT NULL,

            date TEXT NOT NULL,

            status TEXT NOT NULL,

            FOREIGN KEY (
                student_id
            )
            REFERENCES students(student_id)

            ON DELETE CASCADE
        );
        """
    )


# ============================================================
# CORE SYSTEM TABLES
# ============================================================

def create_core_system_tables(conn):

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL UNIQUE,

            password_hash TEXT NOT NULL,

            role TEXT NOT NULL
                CHECK (
                    role IN (
                        'ADMIN',
                        'FACULTY',
                        'STUDENT'
                    )
                ),

            is_active INTEGER NOT NULL DEFAULT 1,

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    # --------------------------------------------------------
    # FACULTY
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS faculty (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER UNIQUE,

            faculty_id TEXT NOT NULL UNIQUE,

            name TEXT NOT NULL,

            email TEXT UNIQUE,

            phone TEXT,

            designation TEXT,

            department_id INTEGER,

            status TEXT NOT NULL DEFAULT 'ACTIVE',

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                user_id
            )
            REFERENCES users(id)

            ON DELETE SET NULL,

            FOREIGN KEY (
                department_id
            )
            REFERENCES departments(id)

            ON DELETE SET NULL
        );
        """
    )


# ============================================================
# ACADEMIC STRUCTURE
# ============================================================

def create_academic_tables(conn):

    # --------------------------------------------------------
    # DEPARTMENTS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            department_code TEXT NOT NULL UNIQUE,

            department_name TEXT NOT NULL UNIQUE,

            description TEXT,

            status TEXT NOT NULL DEFAULT 'ACTIVE',

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    # --------------------------------------------------------
    # COURSES
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            department_id INTEGER NOT NULL,

            course_code TEXT NOT NULL UNIQUE,

            course_name TEXT NOT NULL,

            degree_type TEXT,

            duration_years INTEGER,

            status TEXT NOT NULL DEFAULT 'ACTIVE',

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                department_id
            )
            REFERENCES departments(id)

            ON DELETE RESTRICT
        );
        """
    )


    # --------------------------------------------------------
    # SEMESTERS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS semesters (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            course_id INTEGER NOT NULL,

            semester_number INTEGER NOT NULL,

            semester_name TEXT,

            academic_year TEXT,

            status TEXT NOT NULL DEFAULT 'ACTIVE',

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (
                course_id,
                semester_number
            ),

            FOREIGN KEY (
                course_id
            )
            REFERENCES courses(id)

            ON DELETE CASCADE
        );
        """
    )


    # --------------------------------------------------------
    # SUBJECTS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            semester_id INTEGER NOT NULL,

            subject_code TEXT NOT NULL UNIQUE,

            subject_name TEXT NOT NULL,

            subject_type TEXT DEFAULT 'THEORY',

            credits REAL DEFAULT 0,

            weekly_lectures INTEGER DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'ACTIVE',

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                semester_id
            )
            REFERENCES semesters(id)

            ON DELETE CASCADE
        );
        """
    )


# ============================================================
# RELATIONSHIP TABLES
# ============================================================

def create_relationship_tables(conn):

    # --------------------------------------------------------
    # FACULTY ↔ SUBJECT
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS faculty_subjects (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            faculty_id INTEGER NOT NULL,

            subject_id INTEGER NOT NULL,

            academic_year TEXT,

            assigned_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (
                faculty_id,
                subject_id,
                academic_year
            ),

            FOREIGN KEY (
                faculty_id
            )
            REFERENCES faculty(id)

            ON DELETE CASCADE,

            FOREIGN KEY (
                subject_id
            )
            REFERENCES subjects(id)

            ON DELETE CASCADE
        );
        """
    )


    # --------------------------------------------------------
    # STUDENT COURSE ENROLLMENT
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS student_courses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            course_id INTEGER NOT NULL,

            semester_id INTEGER,

            division TEXT,

            roll_number TEXT,

            academic_year TEXT,

            enrollment_status TEXT
                DEFAULT 'ACTIVE',

            enrolled_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (
                student_id,
                course_id,
                academic_year
            ),

            FOREIGN KEY (
                student_id
            )
            REFERENCES students(student_id)

            ON DELETE CASCADE,

            FOREIGN KEY (
                course_id
            )
            REFERENCES courses(id)

            ON DELETE RESTRICT,

            FOREIGN KEY (
                semester_id
            )
            REFERENCES semesters(id)

            ON DELETE SET NULL
        );
        """
    )


    # --------------------------------------------------------
    # FACE EMBEDDINGS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS face_embeddings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            embedding BLOB NOT NULL,

            model_version TEXT NOT NULL
                DEFAULT 'face_recognition_128d',

            is_active INTEGER NOT NULL DEFAULT 1,

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                student_id
            )
            REFERENCES students(student_id)

            ON DELETE CASCADE
        );
        """
    )


    # --------------------------------------------------------
    # LECTURE SESSIONS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            subject_id INTEGER,

            subject_code TEXT,

            faculty_id INTEGER NOT NULL,

            division TEXT,

            session_date TEXT NOT NULL,

            start_time TEXT NOT NULL,

            end_time TEXT NOT NULL,

            attendance_start_time TEXT,

            attendance_end_time TEXT,

            status TEXT NOT NULL DEFAULT 'SCHEDULED',

            created_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                subject_id
            )
            REFERENCES subjects(id)

            ON DELETE SET NULL,

            FOREIGN KEY (
                faculty_id
            )
            REFERENCES faculty(id)

            ON DELETE RESTRICT
        );
        """
    )


    # --------------------------------------------------------
    # SESSION ATTENDANCE
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            session_id INTEGER NOT NULL,

            student_id TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'PRESENT',

            marked_at
                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            face_distance REAL,

            method TEXT NOT NULL DEFAULT 'FACE',

            UNIQUE (
                session_id,
                student_id
            ),

            FOREIGN KEY (
                session_id
            )
            REFERENCES sessions(id)

            ON DELETE CASCADE,

            FOREIGN KEY (
                student_id
            )
            REFERENCES students(student_id)

            ON DELETE CASCADE
        );
        """
    )


# ============================================================
# MIGRATE EXISTING TABLES
# ============================================================

def migrate_existing_tables(conn):

    # --------------------------------------------------------
    # STUDENT ADDITIONAL INFORMATION
    # --------------------------------------------------------

    add_column_if_missing(
        conn,
        "students",
        "email",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "students",
        "phone",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "students",
        "roll_number",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "students",
        "department_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "students",
        "course_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "students",
        "semester_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "students",
        "division",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "students",
        "user_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "students",
        "status",
        "TEXT DEFAULT 'ACTIVE'"
    )


    # --------------------------------------------------------
    # FACULTY ADDITIONAL INFORMATION
    # --------------------------------------------------------

    add_column_if_missing(
        conn,
        "faculty",
        "department_id",
        "INTEGER"
    )


    # --------------------------------------------------------
    # SESSION SUBJECT RELATION
    # --------------------------------------------------------

    add_column_if_missing(
        conn,
        "sessions",
        "subject_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "sessions",
        "division",
        "TEXT"
    )


# ============================================================
# INDEXES
# ============================================================

def create_indexes(conn):

    # --------------------------------------------------------
    # LEGACY ATTENDANCE
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_attendance_student_date
        ON attendance (
            student_id,
            date
        );
        """
    )


    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_subject_attendance_unique
        ON subject_attendance (
            student_id,
            subject_code,
            date
        );
        """
    )


    # --------------------------------------------------------
    # ACADEMIC
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_courses_department
        ON courses(department_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_semesters_course
        ON semesters(course_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_subjects_semester
        ON subjects(semester_id);
        """
    )


    # --------------------------------------------------------
    # FACULTY
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_faculty_department
        ON faculty(department_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_faculty_subjects_faculty
        ON faculty_subjects(faculty_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_faculty_subjects_subject
        ON faculty_subjects(subject_id);
        """
    )


    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_student_courses_student
        ON student_courses(student_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_student_courses_course
        ON student_courses(course_id);
        """
    )


    # --------------------------------------------------------
    # BIOMETRICS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_face_embeddings_student
        ON face_embeddings(student_id);
        """
    )


    # --------------------------------------------------------
    # SESSIONS
    # --------------------------------------------------------

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sessions_date
        ON sessions(session_date);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sessions_faculty
        ON sessions(faculty_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sessions_subject
        ON sessions(subject_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_session_attendance_session
        ON session_attendance(session_id);
        """
    )


    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_session_attendance_student
        ON session_attendance(student_id);
        """
    )


# ============================================================
# USER MANAGEMENT
# ============================================================

def create_user(
    username,
    password_hash,
    role
):

    username = str(username).strip()

    role = str(role).strip().upper()

    if role not in (
        "ADMIN",
        "FACULTY",
        "STUDENT"
    ):

        raise ValueError(
            "Invalid user role."
        )

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role
            )
            VALUES (?, ?, ?)
            """,
            (
                username,
                password_hash,
                role
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_user_by_username(username):

    conn = get_db_connection()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (str(username).strip(),)
        ).fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


def get_user_by_id(user_id):

    conn = get_db_connection()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


# ============================================================
# DEPARTMENT FUNCTIONS
# ============================================================

def create_department(
    department_code,
    department_name,
    description=""
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO departments (
                department_code,
                department_name,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                department_code.strip().upper(),
                department_name.strip(),
                description.strip()
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_all_departments():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM departments
            ORDER BY department_name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


def get_department(department_id):

    conn = get_db_connection()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM departments
            WHERE id = ?
            """,
            (department_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


def update_department(
    department_id,
    department_code,
    department_name,
    description="",
    status="ACTIVE"
):

    conn = get_db_connection()

    try:

        conn.execute(
            """
            UPDATE departments

            SET
                department_code = ?,
                department_name = ?,
                description = ?,
                status = ?

            WHERE id = ?
            """,
            (
                department_code.strip().upper(),
                department_name.strip(),
                description.strip(),
                status,
                department_id
            )
        )

        conn.commit()

    finally:

        conn.close()


def delete_department(
    department_id
):

    conn = get_db_connection()

    try:

        conn.execute(
            """
            DELETE FROM departments
            WHERE id = ?
            """,
            (department_id,)
        )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# COURSE FUNCTIONS
# ============================================================

def create_course(
    department_id,
    course_code,
    course_name,
    degree_type="B.Tech",
    duration_years=4
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO courses (
                department_id,
                course_code,
                course_name,
                degree_type,
                duration_years
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                department_id,
                course_code.strip().upper(),
                course_name.strip(),
                degree_type.strip(),
                duration_years
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_all_courses():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                c.*,
                d.department_name,
                d.department_code

            FROM courses c

            JOIN departments d
                ON d.id = c.department_id

            ORDER BY
                d.department_name,
                c.course_name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


def get_courses_by_department(
    department_id
):

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM courses

            WHERE department_id = ?

            ORDER BY course_name
            """,
            (department_id,)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# SEMESTER FUNCTIONS
# ============================================================

def create_semester(
    course_id,
    semester_number,
    semester_name=None,
    academic_year=None
):

    if not semester_name:

        semester_name = (
            f"Semester {semester_number}"
        )

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO semesters (
                course_id,
                semester_number,
                semester_name,
                academic_year
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                course_id,
                semester_number,
                semester_name,
                academic_year
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_semesters_by_course(
    course_id
):

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM semesters

            WHERE course_id = ?

            ORDER BY semester_number
            """,
            (course_id,)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# SUBJECT FUNCTIONS
# ============================================================

def create_subject(
    semester_id,
    subject_code,
    subject_name,
    subject_type="THEORY",
    credits=0,
    weekly_lectures=0
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO subjects (
                semester_id,
                subject_code,
                subject_name,
                subject_type,
                credits,
                weekly_lectures
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                semester_id,
                subject_code.strip().upper(),
                subject_name.strip(),
                subject_type.strip().upper(),
                credits,
                weekly_lectures
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_all_subjects():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                s.*,
                sem.semester_number,
                c.course_name,
                c.course_code,
                d.department_name

            FROM subjects s

            JOIN semesters sem
                ON sem.id = s.semester_id

            JOIN courses c
                ON c.id = sem.course_id

            JOIN departments d
                ON d.id = c.department_id

            ORDER BY
                d.department_name,
                c.course_name,
                sem.semester_number,
                s.subject_name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


def get_subjects_by_semester(
    semester_id
):

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM subjects

            WHERE semester_id = ?

            ORDER BY subject_name
            """,
            (semester_id,)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# STUDENT FUNCTIONS
# ============================================================

def add_student(
    student_id,
    student_name,
    email=None,
    phone=None,
    roll_number=None,
    department_id=None,
    course_id=None,
    semester_id=None,
    division=None,
    user_id=None
):

    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO students (
                student_id,
                student_name,
                email,
                phone,
                roll_number,
                department_id,
                course_id,
                semester_id,
                division,
                user_id,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
            (
                student_id.strip(),
                student_name.strip(),
                email,
                phone,
                roll_number,
                department_id,
                course_id,
                semester_id,
                division,
                user_id
            )
        )

        conn.commit()

        return True

    finally:

        conn.close()


def get_student(student_id):

    conn = get_db_connection()

    try:

        row = conn.execute(
            """
            SELECT
                s.*,

                d.department_name,

                c.course_name,
                c.course_code,

                sem.semester_number

            FROM students s

            LEFT JOIN departments d
                ON d.id = s.department_id

            LEFT JOIN courses c
                ON c.id = s.course_id

            LEFT JOIN semesters sem
                ON sem.id = s.semester_id

            WHERE s.student_id = ?
            """,
            (
                student_id.strip(),
            )
        ).fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


def get_all_students():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                s.*,

                d.department_name,

                c.course_name,
                c.course_code,

                sem.semester_number

            FROM students s

            LEFT JOIN departments d
                ON d.id = s.department_id

            LEFT JOIN courses c
                ON c.id = s.course_id

            LEFT JOIN semesters sem
                ON sem.id = s.semester_id

            ORDER BY
                s.student_id
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


def delete_student_db(
    student_id
):

    conn = get_db_connection()

    try:

        conn.execute(
            """
            DELETE FROM students
            WHERE student_id = ?
            """,
            (
                student_id.strip(),
            )
        )

        conn.commit()

        return True

    finally:

        conn.close()


# ============================================================
# STUDENT ENROLLMENT
# ============================================================

def enroll_student(
    student_id,
    course_id,
    semester_id=None,
    division=None,
    roll_number=None,
    academic_year=None
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO student_courses (
                student_id,
                course_id,
                semester_id,
                division,
                roll_number,
                academic_year
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                course_id,
                semester_id,
                division,
                roll_number,
                academic_year
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_student_enrollments(
    student_id
):

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                sc.*,

                c.course_name,
                c.course_code,

                d.department_name,

                sem.semester_number

            FROM student_courses sc

            JOIN courses c
                ON c.id = sc.course_id

            JOIN departments d
                ON d.id = c.department_id

            LEFT JOIN semesters sem
                ON sem.id = sc.semester_id

            WHERE sc.student_id = ?

            ORDER BY
                sc.academic_year DESC
            """,
            (
                student_id,
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# FACE EMBEDDING FUNCTIONS
# ============================================================

def save_face_embedding(
    student_id,
    embedding,
    model_version="face_recognition_128d"
):

    conn = get_db_connection()

    try:

        conn.execute(
            """
            UPDATE face_embeddings

            SET is_active = 0

            WHERE student_id = ?
            """,
            (
                student_id,
            )
        )


        conn.execute(
            """
            INSERT INTO face_embeddings (
                student_id,
                embedding,
                model_version
            )
            VALUES (?, ?, ?)
            """,
            (
                student_id,
                embedding,
                model_version
            )
        )

        conn.commit()

    finally:

        conn.close()


def get_active_face_embeddings():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                fe.*,
                s.student_name

            FROM face_embeddings fe

            JOIN students s
                ON s.student_id = fe.student_id

            WHERE fe.is_active = 1
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# FACULTY FUNCTIONS
# ============================================================

def create_faculty(
    faculty_id,
    name,
    email=None,
    phone=None,
    designation=None,
    department_id=None,
    user_id=None
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO faculty (
                faculty_id,
                name,
                email,
                phone,
                designation,
                department_id,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                faculty_id.strip(),
                name.strip(),
                email,
                phone,
                designation,
                department_id,
                user_id
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_all_faculty():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                f.*,
                d.department_name

            FROM faculty f

            LEFT JOIN departments d
                ON d.id = f.department_id

            ORDER BY
                f.name
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# FACULTY SUBJECT ASSIGNMENT
# ============================================================

def assign_subject_to_faculty(
    faculty_id,
    subject_id,
    academic_year=None
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO faculty_subjects (
                faculty_id,
                subject_id,
                academic_year
            )
            VALUES (?, ?, ?)
            """,
            (
                faculty_id,
                subject_id,
                academic_year
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_faculty_subjects(
    faculty_id
):

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                fs.*,

                s.subject_code,
                s.subject_name,

                sem.semester_number,

                c.course_name,

                d.department_name

            FROM faculty_subjects fs

            JOIN subjects s
                ON s.id = fs.subject_id

            JOIN semesters sem
                ON sem.id = s.semester_id

            JOIN courses c
                ON c.id = sem.course_id

            JOIN departments d
                ON d.id = c.department_id

            WHERE fs.faculty_id = ?

            ORDER BY
                c.course_name,
                sem.semester_number,
                s.subject_name
            """,
            (
                faculty_id,
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# LECTURE SESSION FUNCTIONS
# ============================================================

def create_session(
    subject_id,
    faculty_id,
    session_date,
    start_time,
    end_time,
    attendance_start_time=None,
    attendance_end_time=None,
    division=None
):

    conn = get_db_connection()

    try:

        subject = conn.execute(
            """
            SELECT subject_code
            FROM subjects
            WHERE id = ?
            """,
            (
                subject_id,
            )
        ).fetchone()


        subject_code = (
            subject["subject_code"]
            if subject
            else None
        )


        cursor = conn.execute(
            """
            INSERT INTO sessions (
                subject_id,
                subject_code,
                faculty_id,
                division,
                session_date,
                start_time,
                end_time,
                attendance_start_time,
                attendance_end_time,
                status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED'
            )
            """,
            (
                subject_id,
                subject_code,
                faculty_id,
                division,
                session_date,
                start_time,
                end_time,
                attendance_start_time,
                attendance_end_time
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_session(
    session_id
):

    conn = get_db_connection()

    try:

        row = conn.execute(
            """
            SELECT

                se.*,

                s.subject_name,
                s.subject_code,

                f.faculty_id,
                f.name AS faculty_name

            FROM sessions se

            LEFT JOIN subjects s
                ON s.id = se.subject_id

            JOIN faculty f
                ON f.id = se.faculty_id

            WHERE se.id = ?

            """,
            (
                session_id,
            )
        ).fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


# ============================================================
# SESSION ATTENDANCE
# ============================================================

def mark_session_attendance(
    session_id,
    student_id,
    status="PRESENT",
    face_distance=None,
    method="FACE"
):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            INSERT INTO session_attendance (
                session_id,
                student_id,
                status,
                face_distance,
                method
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT (
                session_id,
                student_id
            )
            DO UPDATE SET

                status = excluded.status,

                marked_at =
                    CURRENT_TIMESTAMP,

                face_distance =
                    excluded.face_distance,

                method =
                    excluded.method
            """,
            (
                session_id,
                student_id,
                status,
                face_distance,
                method
            )
        )

        conn.commit()

        return cursor.lastrowid

    finally:

        conn.close()


def get_session_attendance(
    session_id
):

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                sa.*,

                s.student_name,

                s.roll_number,

                sc.division

            FROM session_attendance sa

            JOIN students s
                ON s.student_id = sa.student_id

            LEFT JOIN student_courses sc
                ON sc.student_id = s.student_id

            WHERE sa.session_id = ?

            ORDER BY
                sa.marked_at
            """,
            (
                session_id,
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# LEGACY ATTENDANCE FUNCTIONS
# These remain for your existing application.
# ============================================================

def mark_attendance(
    student_id,
    student_name,
    date_str,
    time_str,
    status="Present"
):

    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO attendance (
                student_id,
                student_name,
                date,
                time,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                student_id.strip(),
                student_name.strip(),
                date_str,
                time_str,
                status
            )
        )

        conn.commit()

        return True

    finally:

        conn.close()


def get_attendance_records(
    filter_date=None,
    search_query=None
):

    conn = get_db_connection()

    try:

        query = """
            SELECT *
            FROM attendance
            WHERE 1 = 1
        """

        params = []


        if filter_date:

            query += """
                AND date = ?
            """

            params.append(
                filter_date.strip()
            )


        if search_query:

            query += """
                AND (
                    student_id LIKE ?
                    OR student_name LIKE ?
                )
            """

            search_like = (
                f"%{search_query.strip()}%"
            )

            params.extend([
                search_like,
                search_like
            ])


        query += """
            ORDER BY id DESC
        """


        rows = conn.execute(
            query,
            params
        ).fetchall()


        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


def check_face_punch_exists(
    student_id,
    date_str
):

    conn = get_db_connection()

    try:

        row = conn.execute(
            """
            SELECT 1
            FROM attendance

            WHERE student_id = ?
            AND date = ?

            LIMIT 1
            """,
            (
                student_id,
                date_str
            )
        ).fetchone()

        return row is not None

    finally:

        conn.close()


def mark_subject_attendance(
    student_id,
    subject_code,
    date_str,
    status
):

    if (
        status == "Present"
        and
        not check_face_punch_exists(
            student_id,
            date_str
        )
    ):

        raise ValueError(
            f"Student ID {student_id} "
            f"has not punched their face today!"
        )


    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO subject_attendance (
                student_id,
                subject_code,
                date,
                status
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT (
                student_id,
                subject_code,
                date
            )
            DO UPDATE SET
                status = excluded.status
            """,
            (
                student_id,
                subject_code,
                date_str,
                status
            )
        )

        conn.commit()

        return True

    finally:

        conn.close()


# ============================================================
# STUDENT ATTENDANCE REPORT
# ============================================================

def get_student_subject_summary(
    student_id
):

    conn = get_db_connection()

    try:

        summary = []


        rows = conn.execute(
            """
            SELECT

                s.id,
                s.subject_code,
                s.subject_name

            FROM subjects s

            JOIN semesters sem
                ON sem.id = s.semester_id

            JOIN student_courses sc
                ON sc.semester_id = sem.id

            WHERE sc.student_id = ?

            ORDER BY s.subject_name
            """,
            (
                student_id,
            )
        ).fetchall()


        for subject in rows:

            total = conn.execute(
                """
                SELECT COUNT(*)

                FROM session_attendance sa

                JOIN sessions se
                    ON se.id = sa.session_id

                WHERE
                    sa.student_id = ?
                    AND se.subject_id = ?
                """,
                (
                    student_id,
                    subject["id"]
                )
            ).fetchone()[0]


            present = conn.execute(
                """
                SELECT COUNT(*)

                FROM session_attendance sa

                JOIN sessions se
                    ON se.id = sa.session_id

                WHERE
                    sa.student_id = ?
                    AND se.subject_id = ?

                    AND sa.status = 'PRESENT'
                """,
                (
                    student_id,
                    subject["id"]
                )
            ).fetchone()[0]


            percentage = (
                round(
                    (present / total) * 100,
                    2
                )
                if total
                else 0
            )


            summary.append({

                "subject_code":
                    subject["subject_code"],

                "subject_name":
                    subject["subject_name"],

                "total_lectures":
                    total,

                "present_lectures":
                    present,

                "attendance_percentage":
                    percentage
            })


        return summary

    finally:

        conn.close()


# ============================================================
# UTILITY
# ============================================================

def get_day_name(
    date_str
):

    try:

        dt = datetime.strptime(
            date_str,
            "%d-%m-%Y"
        )

        return dt.strftime("%a")

    except Exception:

        return "Day"


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    init_db()