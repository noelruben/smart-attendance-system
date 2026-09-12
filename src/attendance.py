from datetime import datetime
from src.database import mark_attendance, get_db_connection

def get_current_date_str():
    """
    Returns current date in DD-MM-YYYY format.
    """
    return datetime.now().strftime("%d-%m-%Y")

def get_current_time_str():
    """
    Returns current time in HH:MM:SS format.
    """
    return datetime.now().strftime("%H:%M:%S")

def load_today_attendance_cache():
    """
    Queries the database and loads all student IDs that have already been
    marked present today into a set. This prevents redundant DB operations.
    """
    today_date = get_current_date_str()
    today_cache = set()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT student_id FROM attendance WHERE date = ?;", (today_date,))
        rows = cursor.fetchall()
        for row in rows:
            today_cache.add(row["student_id"])
    except Exception as e:
        print(f"Error loading attendance cache: {e}")
    finally:
        conn.close()
        
    return today_cache

def log_attendance_for_student(student_id, student_name, today_cache):
    """
    Logs attendance for a recognized student if not already marked today.
    
    Parameters:
      student_id: String representing Student ID
      student_name: String representing Student Name
      today_cache: Set containing student IDs already marked today (in-memory cache)
      
    Returns:
      (success_status (bool), message (str))
    """
    if not student_id:
        return False, "Invalid Student ID"

    # Quick check against in-memory cache to prevent database query on every frame
    if student_id in today_cache:
        return False, "Attendance already marked"

    # Get date and time strings
    date_str = get_current_date_str()
    time_str = get_current_time_str()
    
    try:
        # Write to SQLite database
        mark_attendance(student_id, student_name, date_str, time_str, status="Present")
        # Update the in-memory cache to prevent marking again
        today_cache.add(student_id)
        return True, f"Attendance marked: {student_name} (ID: {student_id}) at {time_str}"
    except Exception as e:
        # Database constraint violated or other DB issue
        # Even if DB write fails due to unique constraint, ensure the cache is updated
        today_cache.add(student_id)
        return False, "Attendance already marked"

if __name__ == "__main__":
    # Test caching and logging
    cache = load_today_attendance_cache()
    print("Today's marked students cache:", cache)
