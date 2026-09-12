import os
import sys
import time
import cv2
import sqlite3
import shutil
import pickle
from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    send_file,
    redirect,
    url_for,
    session,
    flash
)
from src.auth import (
    authenticate_user,
    login_user,
    logout_user,
    login_required,
    role_required
)

# Add project root directory to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database import (
    init_db, add_student, get_all_students, get_student, get_attendance_records,
    check_face_punch_exists, mark_subject_attendance, get_student_subject_summary,
    get_student_attendance_matrix, delete_student_db, SUBJECTS, get_db_connection
)
from src.register_student import validate_and_save_frame, get_student_dir
from src.generate_encodings import train_system, ENCODINGS_PATH
from src.face_recognition_module import load_known_faces, process_and_recognize_frame, TOLERANCE
from src.attendance import load_today_attendance_cache, log_attendance_for_student, get_current_date_str
from src.export import export_attendance_to_csv

# Directory where web_server.py is located
SRC_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(SRC_DIR, "templates"),
    static_folder=os.path.join(SRC_DIR, "static"),
    static_url_path="/static"
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key-change-this"
)

# Global camera and registration variables
global_cap = None
latest_frame = None

reg_id = ""
reg_name = ""
reg_count = 0

def get_camera():
    """
    Acquires camera connection. Reuses or opens it.
    """
    global global_cap
    if global_cap is None:
        global_cap = cv2.VideoCapture(0)
        global_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        global_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return global_cap

def release_camera():
    """
    Releases camera connection.
    """
    global global_cap
    if global_cap is not None:
        global_cap.release()
        global_cap = None

# =========================================================================
# VIDEO ENCODING STREAMS
# =========================================================================
def generate_registration_frames():
    global latest_frame
    cap = get_camera()
    
    while True:
        time.sleep(0.015)
        ret, frame = cap.read()
        if not ret:
            break
            
        latest_frame = frame.copy()
        
        # Draw registration guidance guide
        h, w, _ = frame.shape
        cv2.ellipse(frame, (int(w/2), int(h/2)), (120, 160), 0, 0, 360, (255, 82, 59), 2)
        cv2.putText(frame, "Align Face Here", (int(w/2) - 80, int(h/2) - 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 82, 59), 2)
        
        ret_enc, jpeg = cv2.imencode('.jpg', frame)
        if not ret_enc:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

def generate_attendance_frames():
    cap = get_camera()
    
    # Load known face encodings and session cache at start of stream
    known_encodings, known_ids, known_names = load_known_faces()
    today_cache = load_today_attendance_cache()
    
    while True:
        time.sleep(0.01)
        ret, frame = cap.read()
        if not ret:
            break
            
        recognized_faces = process_and_recognize_frame(
            frame, 
            known_encodings, 
            known_ids, 
            known_names, 
            tolerance=TOLERANCE
        )
        
        for face in recognized_faces:
            top, right, bottom, left = face["box"]
            name = face["name"]
            student_id = face["id"]
            match_pct = face["match_pct"]
            
            if student_id:
                # Log attendance (Face Punch)
                logged, msg = log_attendance_for_student(student_id, name, today_cache)
                box_color = (0, 255, 16)
                text_label = f"{name} ({match_pct:.0f}%)"
                sub_text = f"ID: {student_id}"
                if student_id in today_cache:
                    sub_text += " [MARKED]"
            else:
                box_color = (0, 0, 239)
                text_label = "Unknown"
                sub_text = "Not Registered"
                
            cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
            cv2.rectangle(frame, (left, bottom), (right, bottom + 40), box_color, cv2.FILLED)
            cv2.putText(frame, text_label, (left + 6, bottom + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(frame, sub_text, (left + 6, bottom + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            
        ret_enc, jpeg = cv2.imencode('.jpg', frame)
        if not ret_enc:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

# =========================================================================
# AUTHENTICATION & ROLE BASED ROUTES
# =========================================================================

@app.route("/")
def home():

    if session.get("user_id"):
        return redirect(
            url_for("dashboard")
        )

    return render_template("role_selection.html")


@app.route("/login/<role>", methods=["GET", "POST"])
def login(role):

    role = role.upper()

    allowed_roles = [
        "ADMIN",
        "FACULTY",
        "STUDENT"
    ]

    if role not in allowed_roles:
        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = authenticate_user(
            username,
            password,
            expected_role=role
        )

        if not user:

            flash(
                "Invalid username, password, or account role.",
                "danger"
            )

            return render_template(
                "login.html",
                role=role
            )

        login_user(user)

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "login.html",
        role=role
    )


@app.route("/logout")
def logout():

    logout_user()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )


@app.route("/dashboard")
@login_required
def dashboard():

    role = session.get("role")

    if role == "ADMIN":

        return redirect(
            url_for("admin_dashboard")
        )

    elif role == "FACULTY":

        return redirect(
            url_for("faculty_dashboard")
        )

    elif role == "STUDENT":

        return redirect(
            url_for("student_dashboard")
        )

    logout_user()

    return redirect(
        url_for("home")
    )


@app.route("/admin/dashboard")
@role_required("ADMIN")
def admin_dashboard():

    return render_template(
        "admin_dashboard.html",
        username=session.get("username")
    )


@app.route("/faculty/dashboard")
@role_required("FACULTY")
def faculty_dashboard():

    return render_template(
        "faculty_dashboard.html",
        username=session.get("username")
    )


@app.route("/student/dashboard")
@role_required("STUDENT")
def student_dashboard():

    return render_template(
        "student_dashboard.html",
        username=session.get("username")
    )


@app.route("/attendance-system")
@role_required("ADMIN", "FACULTY")
def attendance_system():

    return render_template("index.html")

@app.route("/api/stats")
def stats():
    try:
        students = get_all_students()
        logs = get_attendance_records(filter_date=get_current_date_str())
        return jsonify({
            "registered_count": len(students),
            "present_today": len(logs)
        })
    except Exception as e:
        return jsonify({"registered_count": 0, "present_today": 0, "error": str(e)})

@app.route("/api/students")
def students():
    try:
        students = get_all_students()
        return jsonify(students)
    except Exception as e:
        return jsonify([])

@app.route("/api/register/start", methods=["POST"])
def register_start():
    global reg_id, reg_name, reg_count
    data = request.json
    
    reg_id = str(data.get("student_id", "")).strip()
    reg_name = str(data.get("student_name", "")).strip()
    
    if not reg_id or not reg_name:
        return jsonify({"success": False, "message": "ID and name are required."})
        
    try:
        students_list = get_all_students()
        if any(s["student_id"] == reg_id for s in students_list):
            return jsonify({"success": False, "message": f"Student ID '{reg_id}' is already registered."})
            
        reg_count = 0
        get_camera()
        return jsonify({"success": True, "message": "Camera initialized successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database check failed: {e}"})

@app.route("/api/register/capture", methods=["POST"])
def register_capture():
    global reg_id, reg_name, reg_count, latest_frame
    
    if latest_frame is None:
        return jsonify({"success": False, "message": "Webcam frame not available."})
        
    success, message = validate_and_save_frame(
        latest_frame, 
        reg_id, 
        reg_name, 
        reg_count + 1
    )
    
    if success:
        reg_count += 1
        return jsonify({"success": True, "message": f"Frame {reg_count}/5 captured successfully!"})
    else:
        return jsonify({"success": False, "message": message})

@app.route("/api/register/save", methods=["POST"])
def register_save():
    global reg_id, reg_name, reg_count
    
    if reg_count < 5:
        return jsonify({"success": False, "message": "Please capture at least 5 frames."})
        
    try:
        add_student(reg_id, reg_name)
        release_camera()
        return jsonify({"success": True, "message": f"Successfully registered {reg_name} in database."})
    except Exception as e:
        return jsonify({"success": False, "message": f"DB Write Failed: {e}"})

@app.route("/api/video_feed/register")
def video_feed_register():
    return Response(
        generate_registration_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/api/video_feed/attendance")
def video_feed_attendance():
    return Response(
        generate_attendance_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/api/camera/release", methods=["POST"])
def camera_release():
    release_camera()
    return jsonify({"success": True})

@app.route("/api/train", methods=["POST"])
def train():
    data = request.json or {}
    force = data.get("force", False)
    try:
        success, message = train_system(force_rebuild=force)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/logs")
def logs():
    search = request.args.get("search", None)
    date = request.args.get("date", None)
    try:
        records = get_attendance_records(filter_date=date, search_query=search)
        return jsonify(records)
    except Exception as e:
        return jsonify([])

# =========================================================================
# V1.1 TEACHER & STUDENT ERP EXTENDED ROUTE APIS
# =========================================================================
@app.route("/api/teacher/students")
def teacher_students():
    """
    Returns the student list for a specific subject and date, indicating
    whether each student has punched their face today, and their saved status.
    """
    subject = request.args.get("subject")
    date = request.args.get("date")
    
    if not date:
        return jsonify([])
        
    try:
        students_list = get_all_students()
        result = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for s in students_list:
            student_id = s["student_id"]
            
            # 1. Check if daily face punch gate entry exists
            has_punched = check_face_punch_exists(student_id, date)
            
            # 2. Check if subject attendance has been previously saved
            cursor.execute("""
                SELECT status FROM subject_attendance 
                WHERE student_id = ? AND subject_code = ? AND date = ?;
            """, (student_id, subject, date))
            row = cursor.fetchone()
            saved_status = row["status"] if row else None
            
            result.append({
                "student_id": student_id,
                "student_name": s["student_name"],
                "has_punched": has_punched,
                "saved_status": saved_status
            })
            
        conn.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error loading teacher class list: {e}")
        return jsonify([])

@app.route("/api/teacher/submit", methods=["POST"])
def teacher_submit():
    """
    Submits subject-wise attendance logs from the teacher panel.
    """
    data = request.json or {}
    subject = data.get("subject_code")
    date = data.get("date")
    records = data.get("attendance", [])
    
    if not subject or not date or not records:
        return jsonify({"success": False, "message": "Missing required fields."})
        
    try:
        for r in records:
            student_id = r["student_id"]
            status = r["status"]
            
            # Enforce gate punch validation check
            has_punched = check_face_punch_exists(student_id, date)
            if status == "Present" and not has_punched:
                return jsonify({
                    "success": False, 
                    "message": f"Student {student_id} cannot be marked Present without a daily Face Punch!"
                })
                
            mark_subject_attendance(student_id, subject, date, status)
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/student/erp")
def student_erp():
    """
    Returns student data, subject summaries, and date-wise matrix logs
    for the Student ERP view dashboard.
    """
    student_id = request.args.get("student_id")
    if not student_id:
        return jsonify({"error": "Missing student ID"}), 400
        
    student = get_student(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
        
    # Generate 12-digit simulated PRN number: 240105 + padded student ID
    # e.g., student ID 23 -> 240105131223 (replicating screenshots format)
    # Ensure it maps nicely to a unique 12-digit string
    padded_id = f"{int(student_id):06d}" if student_id.isdigit() else student_id.zfill(6)
    prn_no = f"240105{padded_id}"
    
    try:
        summaries = get_student_subject_summary(student_id)
        matrix = get_student_attendance_matrix(student_id)
        
        return jsonify({
            "student_id": student_id,
            "student_name": student["student_name"],
            "prn_no": prn_no,
            "summaries": summaries,
            "matrix": matrix
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/student/delete", methods=["POST"])
def student_delete():
    """
    Deletes a student record from the database, deletes their biometric image dataset folder,
    and removes their face encodings from the pickle file.
    """
    data = request.json or {}
    student_id = data.get("student_id")
    
    if not student_id:
        return jsonify({"success": False, "message": "Missing Student ID."})
        
    try:
        student = get_student(student_id)
        if not student:
            return jsonify({"success": False, "message": f"Student with ID '{student_id}' not found."})
            
        student_name = student["student_name"]
        
        # 1. Delete student records from DB (cascades gate entry and subject logs)
        delete_student_db(student_id)
        
        # 2. Delete raw image dataset folder
        student_dir = get_student_dir(student_id, student_name)
        if os.path.exists(student_dir):
            shutil.rmtree(student_dir)
            print(f"Deleted dataset directory: {student_dir}")
            
        # 3. Delete face encodings from pickling file
        if os.path.exists(ENCODINGS_PATH):
            with open(ENCODINGS_PATH, "rb") as f:
                encoding_records = pickle.load(f)
            
            if isinstance(encoding_records, list):
                # Filter out deleted student
                updated_records = [r for r in encoding_records if r["student_id"] != student_id]
                with open(ENCODINGS_PATH, "wb") as f:
                    pickle.dump(updated_records, f)
                print(f"Updated encodings file, removed ID: {student_id}")

        return jsonify({"success": True, "message": f"Successfully deleted student {student_name} (ID: {student_id})."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Deletion failed: {e}"})

@app.route("/api/export", methods=["POST"])
def export():
    data = request.json or {}
    search = data.get("search", None)
    date = data.get("date", None)
    
    try:
        success, filepath = export_attendance_to_csv(filter_date=date)
        if success:
            filename = os.path.basename(filepath)
            return jsonify({"success": True, "filepath": filepath, "filename": filename})
        else:
            return jsonify({"success": False, "message": filepath})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/download")
def download():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
