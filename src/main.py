import os
import sys

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# IMPORT DATABASE
# ============================================================

from src.database import init_db


# ============================================================
# CREATE REQUIRED PROJECT DIRECTORIES
# ============================================================

def create_project_directories():
    directories = [
        "dataset",
        "encodings",
        "database",
        "exports",
    ]

    for directory in directories:
        directory_path = os.path.join(
            PROJECT_ROOT,
            directory
        )

        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            print(f"Created system directory: {directory_path}")


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    try:
        print("=" * 60)
        print("SMART ATTENDANCE UNIVERSITY PORTAL")
        print("=" * 60)

        # Create required folders
        create_project_directories()

        # Initialize database and default admin
        init_db()

        # Import Flask app after initialization
        from src.web_server import app

        print()
        print("Launching Smart Attendance Local Web Server...")
        print("Dashboard: http://127.0.0.1:5000")
        print("=" * 60)
        print()

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False
        )

    except Exception as e:
        print(f"\nStartup crash: {e}")
        sys.exit(1)


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()