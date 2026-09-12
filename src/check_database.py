import sqlite3
import os

DB_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "database",
        "attendance.db"
    )
)

print("=" * 60)
print("DATABASE:", DB_PATH)
print("=" * 60)

conn = sqlite3.connect(DB_PATH)

# ---------------------------------------------------------
# TABLES
# ---------------------------------------------------------

print("\nTABLES:")

tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

for table in tables:
    print("  -", table[0])


# ---------------------------------------------------------
# FACULTY
# ---------------------------------------------------------

print("\nFACULTY COLUMNS:")

faculty_columns = conn.execute("""
    PRAGMA table_info(faculty)
""").fetchall()

if faculty_columns:
    for column in faculty_columns:
        print(
            f"  - {column[1]} ({column[2]})"
        )
else:
    print("  Faculty table does not exist.")


# ---------------------------------------------------------
# STUDENTS
# ---------------------------------------------------------

print("\nSTUDENT COLUMNS:")

student_columns = conn.execute("""
    PRAGMA table_info(students)
""").fetchall()

if student_columns:
    for column in student_columns:
        print(
            f"  - {column[1]} ({column[2]})"
        )
else:
    print("  Students table does not exist.")


# ---------------------------------------------------------
# COURSES
# ---------------------------------------------------------

print("\nCOURSE COLUMNS:")

course_columns = conn.execute("""
    PRAGMA table_info(courses)
""").fetchall()

if course_columns:
    for column in course_columns:
        print(
            f"  - {column[1]} ({column[2]})"
        )
else:
    print("  Courses table does not exist.")


# ---------------------------------------------------------
# DEPARTMENTS
# ---------------------------------------------------------

print("\nDEPARTMENT COLUMNS:")

department_columns = conn.execute("""
    PRAGMA table_info(departments)
""").fetchall()

if department_columns:
    for column in department_columns:
        print(
            f"  - {column[1]} ({column[2]})"
        )
else:
    print("  Departments table does not exist.")


# ---------------------------------------------------------
# SUBJECTS
# ---------------------------------------------------------

print("\nSUBJECT COLUMNS:")

subject_columns = conn.execute("""
    PRAGMA table_info(subjects)
""").fetchall()

if subject_columns:
    for column in subject_columns:
        print(
            f"  - {column[1]} ({column[2]})"
        )
else:
    print("  Subjects table does not exist.")


conn.close()

print("\n" + "=" * 60)
print("DATABASE CHECK COMPLETE")
print("=" * 60)