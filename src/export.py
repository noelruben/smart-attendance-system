import os
import pandas as pd
from datetime import datetime
from src.database import get_db_connection

EXPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports"))

def export_attendance_to_csv(target_filepath=None, filter_date=None):
    """
    Exports attendance records from the SQLite database to a CSV file.
    
    Parameters:
      target_filepath: Absolute file path where the CSV will be saved.
                       If None, default to exports/attendance_YYYY-MM-DD_HHMMSS.csv.
      filter_date: String in DD-MM-YYYY format to export only a specific day's attendance.
      
    Returns:
      (success_status (bool), filepath_saved (str) or error_msg (str))
    """
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    
    conn = get_db_connection()
    try:
        # Build query
        query = "SELECT id, student_id, student_name, date, time, status FROM attendance"
        params = []
        if filter_date:
            query += " WHERE date = ?"
            params.append(filter_date.strip())
        
        # Order by most recent first
        query += " ORDER BY id DESC"
        
        # Read SQL query directly into a Pandas DataFrame
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            return False, "No attendance records found to export."

        # Rename columns for a clean presentation
        df.columns = ["Record ID", "Student ID", "Student Name", "Date", "Time", "Status"]

        # Determine target file path
        if not target_filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_{timestamp}.csv"
            target_filepath = os.path.join(EXPORTS_DIR, filename)

        # Ensure directory of target path exists
        parent_dir = os.path.dirname(target_filepath)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # Export to CSV (omit index for cleaner output)
        df.to_csv(target_filepath, index=False)
        return True, target_filepath

    except Exception as e:
        return False, f"Failed to export: {str(e)}"
    finally:
        conn.close()

if __name__ == "__main__":
    # Test export (will print warning/error if database is empty, but checks logic)
    status, result = export_attendance_to_csv()
    print("Export Status:", status, "| Result:", result)
