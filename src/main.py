import os
import sys

# Add the project root directory to the python path to resolve imports correctly
# when running main.py directly from the command line.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database import init_db

def create_project_directories():
    """
    Creates the default directory structure for the application if they do not exist.
    """
    dirs = ["dataset", "encodings", "database", "exports"]
    for d in dirs:
        dir_path = os.path.join(PROJECT_ROOT, d)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"Created system directory: {dir_path}")

def main():
    """
    Application startup sequence:
    1. Creates necessary folder directories (dataset, encodings, database, exports)
    2. Initializes database schema
    3. Launches the Flask Local Web Server
    """
    try:
        # Step 1: Ensure system folders are initialized
        create_project_directories()

        # Step 2: Ensure database and tables are ready
        init_db()

        # Step 3: Run the web server
        # We import here to avoid circular imports during app startup
        from src.web_server import app
        
        print("\n" + "="*50)
        print("Launching Smart Attendance Local Web Server...")
        print("Access the dashboard at: http://127.0.0.1:5000")
        print("="*50 + "\n")
        
        app.run(host="127.0.0.1", port=5000, debug=False)
        
    except Exception as e:
        print(f"Startup crash: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
