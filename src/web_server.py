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


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )


# ============================================================
# AUTHENTICATION
# ============================================================

from src.auth import (
    authenticate_user,
    login_user,
    logout_user,
    login_required,
    role_required
)


# ============================================================
# DATABASE
# ============================================================

from src.database import (

    # Database initialization
    init_db,
    create_default_admin,

    # Students
    add_student,
    get_all_students,
    get_student,
    delete_student_db,

    # Attendance
    get_attendance_records,
    check_face_punch_exists,
    mark_subject_attendance,
    get_student_subject_summary,
    get_student_attendance_matrix,

    # Database connection
    get_db_connection,

    # Departments
    create_department,
    get_all_departments,
    get_department,
    update_department,
    delete_department,

    # Courses
    create_course,
    get_all_courses,
    get_courses_by_department,
    get_course,
    update_course,
    delete_course
)


# ============================================================
# FACE REGISTRATION
# ============================================================

from src.register_student import (
    validate_and_save_frame,
    get_student_dir
)


# ============================================================
# FACE ENCODINGS
# ============================================================

from src.generate_encodings import (
    train_system,
    ENCODINGS_PATH
)


# ============================================================
# FACE RECOGNITION
# ============================================================

from src.face_recognition_module import (
    load_known_faces,
    process_and_recognize_frame,
    TOLERANCE
)


# ============================================================
# ATTENDANCE
# ============================================================

from src.attendance import (
    load_today_attendance_cache,
    log_attendance_for_student,
    get_current_date_str
)


# ============================================================
# EXPORT
# ============================================================

from src.export import (
    export_attendance_to_csv
)


# ============================================================
# FLASK APPLICATION
# ============================================================

SRC_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

app = Flask(
    __name__,
    template_folder=os.path.join(
        SRC_DIR,
        "templates"
    ),
    static_folder=os.path.join(
        SRC_DIR,
        "static"
    ),
    static_url_path="/static"
)


app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key-change-this"
)


# ============================================================
# GLOBAL CAMERA VARIABLES
# ============================================================

global_cap = None

latest_frame = None

reg_id = ""

reg_name = ""

reg_count = 0


# ============================================================
# CAMERA FUNCTIONS
# ============================================================

def get_camera():

    global global_cap

    if global_cap is None:

        global_cap = cv2.VideoCapture(
            0
        )

        global_cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        global_cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

    return global_cap


def release_camera():

    global global_cap

    if global_cap is not None:

        global_cap.release()

        global_cap = None


# ============================================================
# VIDEO REGISTRATION STREAM
# ============================================================

def generate_registration_frames():

    global latest_frame

    cap = get_camera()

    while True:

        time.sleep(
            0.015
        )

        ret, frame = cap.read()

        if not ret:

            break

        latest_frame = frame.copy()

        h, w, _ = frame.shape

        cv2.ellipse(
            frame,
            (
                int(w / 2),
                int(h / 2)
            ),
            (
                120,
                160
            ),
            0,
            0,
            360,
            (
                255,
                82,
                59
            ),
            2
        )

        cv2.putText(
            frame,
            "Align Face Here",
            (
                int(w / 2) - 80,
                int(h / 2) - 180
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (
                255,
                82,
                59
            ),
            2
        )

        ret_enc, jpeg = cv2.imencode(
            ".jpg",
            frame
        )

        if not ret_enc:

            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg.tobytes()
            + b"\r\n"
        )


# ============================================================
# VIDEO ATTENDANCE STREAM
# ============================================================

def generate_attendance_frames():

    cap = get_camera()

    known_encodings, known_ids, known_names = (
        load_known_faces()
    )

    today_cache = (
        load_today_attendance_cache()
    )

    while True:

        time.sleep(
            0.01
        )

        ret, frame = cap.read()

        if not ret:

            break

        recognized_faces = (
            process_and_recognize_frame(
                frame,
                known_encodings,
                known_ids,
                known_names,
                tolerance=TOLERANCE
            )
        )

        for face in recognized_faces:

            top, right, bottom, left = (
                face["box"]
            )

            name = face["name"]

            student_id = face["id"]

            match_pct = face["match_pct"]

            if student_id:

                logged, message = (
                    log_attendance_for_student(
                        student_id,
                        name,
                        today_cache
                    )
                )

                box_color = (
                    0,
                    255,
                    16
                )

                text_label = (
                    f"{name} ({match_pct:.0f}%)"
                )

                sub_text = (
                    f"ID: {student_id}"
                )

                if student_id in today_cache:

                    sub_text += (
                        " [MARKED]"
                    )

            else:

                box_color = (
                    0,
                    0,
                    239
                )

                text_label = (
                    "Unknown"
                )

                sub_text = (
                    "Not Registered"
                )

            cv2.rectangle(
                frame,
                (
                    left,
                    top
                ),
                (
                    right,
                    bottom
                ),
                box_color,
                2
            )

            cv2.rectangle(
                frame,
                (
                    left,
                    bottom
                ),
                (
                    right,
                    bottom + 40
                ),
                box_color,
                cv2.FILLED
            )

            cv2.putText(
                frame,
                text_label,
                (
                    left + 6,
                    bottom + 18
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (
                    0,
                    0,
                    0
                ),
                1,
                cv2.LINE_AA
            )

            cv2.putText(
                frame,
                sub_text,
                (
                    left + 6,
                    bottom + 34
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (
                    0,
                    0,
                    0
                ),
                1,
                cv2.LINE_AA
            )

        ret_enc, jpeg = cv2.imencode(
            ".jpg",
            frame
        )

        if not ret_enc:

            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg.tobytes()
            + b"\r\n"
        )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if session.get(
        "user_id"
    ):

        return redirect(
            url_for(
                "dashboard"
            )
        )

    return render_template(
        "role_selection.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login/<role>",
    methods=[
        "GET",
        "POST"
    ]
)
def login(role):

    role = role.upper()

    allowed_roles = [
        "ADMIN",
        "FACULTY",
        "STUDENT"
    ]

    if role not in allowed_roles:

        return redirect(
            url_for(
                "home"
            )
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

        login_user(
            user
        )

        return redirect(
            url_for(
                "dashboard"
            )
        )

    return render_template(
        "login.html",
        role=role
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    logout_user()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for(
            "home"
        )
    )


# ============================================================
# DASHBOARD ROUTER
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    role = session.get(
        "role"
    )

    if role == "ADMIN":

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )

    elif role == "FACULTY":

        return redirect(
            url_for(
                "faculty_dashboard"
            )
        )

    elif role == "STUDENT":

        return redirect(
            url_for(
                "student_dashboard"
            )
        )

    logout_user()

    return redirect(
        url_for(
            "home"
        )
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
@role_required("ADMIN")
def admin_dashboard():

    return render_template(
        "admin_dashboard.html",
        username=session.get(
            "username"
        )
    )


# ============================================================
# FACULTY DASHBOARD
# ============================================================

@app.route("/faculty/dashboard")
@role_required("FACULTY")
def faculty_dashboard():

    return render_template(
        "faculty_dashboard.html",
        username=session.get(
            "username"
        )
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student/dashboard")
@role_required("STUDENT")
def student_dashboard():

    return render_template(
        "student_dashboard.html",
        username=session.get(
            "username"
        )
    )


# ============================================================
# ATTENDANCE SYSTEM
# ============================================================

@app.route("/attendance-system")
@role_required(
    "ADMIN",
    "FACULTY"
)
def attendance_system():

    return render_template(
        "index.html"
    )


# ============================================================
# ADMIN ACADEMIC MANAGEMENT
# ============================================================

@app.route("/admin/academic")
@role_required("ADMIN")
def admin_academic():

    return render_template(
        "admin_academic.html",
        username=session.get(
            "username"
        )
    )


# ============================================================
# ADMIN COURSES PAGE
# ============================================================

@app.route("/admin/courses")
@role_required("ADMIN")
def admin_courses():

    departments = (
        get_all_departments()
    )

    return render_template(
        "admin_courses.html",
        username=session.get(
            "username"
        ),
        departments=departments
    )


# ============================================================
# DEPARTMENT API
# ============================================================

@app.route(
    "/api/admin/departments",
    methods=["GET"]
)
@role_required("ADMIN")
def admin_departments_list():

    try:

        return jsonify({
            "success": True,
            "departments": (
                get_all_departments()
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e),
            "departments": []
        }), 500


@app.route(
    "/api/admin/departments",
    methods=["POST"]
)
@role_required("ADMIN")
def admin_departments_create():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    code = str(
        data.get(
            "department_code",
            ""
        )
    ).strip()

    name = str(
        data.get(
            "department_name",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    if not code or not name:

        return jsonify({
            "success": False,
            "message": (
                "Department code and department name are required."
            )
        }), 400

    try:

        department_id = (
            create_department(
                code,
                name,
                description
            )
        )

        return jsonify({
            "success": True,
            "message": (
                "Department created successfully."
            ),
            "department_id": department_id
        }), 201

    except sqlite3.IntegrityError:

        return jsonify({
            "success": False,
            "message": (
                "Department code or department name already exists."
            )
        }), 409

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route(
    "/api/admin/departments/<int:department_id>",
    methods=["GET"]
)
@role_required("ADMIN")
def admin_department_detail(
    department_id
):

    department = (
        get_department(
            department_id
        )
    )

    if not department:

        return jsonify({
            "success": False,
            "message": (
                "Department not found."
            )
        }), 404

    return jsonify({
        "success": True,
        "department": department
    })


@app.route(
    "/api/admin/departments/<int:department_id>",
    methods=["PUT"]
)
@role_required("ADMIN")
def admin_department_update(
    department_id
):

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    code = str(
        data.get(
            "department_code",
            ""
        )
    ).strip()

    name = str(
        data.get(
            "department_name",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    status = str(
        data.get(
            "status",
            "ACTIVE"
        )
    ).strip().upper()

    if not code or not name:

        return jsonify({
            "success": False,
            "message": (
                "Department code and name are required."
            )
        }), 400

    if status not in (
        "ACTIVE",
        "INACTIVE"
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid department status."
            )
        }), 400

    if not get_department(
        department_id
    ):

        return jsonify({
            "success": False,
            "message": (
                "Department not found."
            )
        }), 404

    try:

        update_department(
            department_id,
            code,
            name,
            description,
            status
        )

        return jsonify({
            "success": True,
            "message": (
                "Department updated successfully."
            )
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "success": False,
            "message": (
                "Department code or name already exists."
            )
        }), 409

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route(
    "/api/admin/departments/<int:department_id>",
    methods=["DELETE"]
)
@role_required("ADMIN")
def admin_department_delete(
    department_id
):

    try:

        if not get_department(
            department_id
        ):

            return jsonify({
                "success": False,
                "message": (
                    "Department not found."
                )
            }), 404

        delete_department(
            department_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Department deleted successfully."
            )
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "success": False,
            "message": (
                "Department cannot be deleted because courses are assigned to it."
            )
        }), 409


# ============================================================
# COURSE API - LIST
# ============================================================

@app.route(
    "/api/admin/courses",
    methods=["GET"]
)
@role_required("ADMIN")
def admin_courses_list():

    department_id = (
        request.args.get(
            "department_id",
            type=int
        )
    )

    try:

        if department_id:

            courses = (
                get_courses_by_department(
                    department_id
                )
            )

        else:

            courses = (
                get_all_courses()
            )

        return jsonify({
            "success": True,
            "courses": courses
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e),
            "courses": []
        }), 500


# ============================================================
# COURSE API - CREATE
# ============================================================

@app.route(
    "/api/admin/courses",
    methods=["POST"]
)
@role_required("ADMIN")
def admin_courses_create():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    department_id = (
        data.get(
            "department_id"
        )
    )

    course_code = str(
        data.get(
            "course_code",
            ""
        )
    ).strip()

    course_name = str(
        data.get(
            "course_name",
            ""
        )
    ).strip()

    degree_type = str(
        data.get(
            "degree_type",
            "B.Tech"
        )
    ).strip()

    duration_years = (
        data.get(
            "duration_years",
            4
        )
    )

    year = (
        data.get(
            "year"
        )
    )

    semester = (
        data.get(
            "semester"
        )
    )

    if not department_id:

        return jsonify({
            "success": False,
            "message": (
                "Department is required."
            )
        }), 400

    if not course_code:

        return jsonify({
            "success": False,
            "message": (
                "Course code is required."
            )
        }), 400

    if not course_name:

        return jsonify({
            "success": False,
            "message": (
                "Course name is required."
            )
        }), 400

    if year is None:

        return jsonify({
            "success": False,
            "message": (
                "Year is required."
            )
        }), 400

    if semester is None:

        return jsonify({
            "success": False,
            "message": (
                "Semester is required."
            )
        }), 400

    try:

        department_id = int(
            department_id
        )

        duration_years = int(
            duration_years
        )

        year = int(
            year
        )

        semester = int(
            semester
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid department, duration, year or semester."
            )
        }), 400

    if duration_years < 1 or duration_years > 10:

        return jsonify({
            "success": False,
            "message": (
                "Duration must be between 1 and 10."
            )
        }), 400

    if year < 1 or year > duration_years:

        return jsonify({
            "success": False,
            "message": (
                "Year must be within the course duration."
            )
        }), 400

    if semester < 1 or semester > (
        duration_years * 2
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid semester."
            )
        }), 400

    department = (
        get_department(
            department_id
        )
    )

    if not department:

        return jsonify({
            "success": False,
            "message": (
                "Selected department does not exist."
            )
        }), 404

    try:

        course_id = (
            create_course(
                department_id,
                course_code,
                course_name,
                degree_type,
                duration_years,
                year,
                semester
            )
        )

        return jsonify({
            "success": True,
            "message": (
                "Course created successfully."
            ),
            "course_id": course_id
        }), 201

    except sqlite3.IntegrityError:

        return jsonify({
            "success": False,
            "message": (
                "Course code already exists."
            )
        }), 409

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# COURSE API - DETAIL
# ============================================================

@app.route(
    "/api/admin/courses/<int:course_id>",
    methods=["GET"]
)
@role_required("ADMIN")
def admin_course_detail(
    course_id
):

    course = get_course(
        course_id
    )

    if not course:

        return jsonify({
            "success": False,
            "message": (
                "Course not found."
            )
        }), 404

    return jsonify({
        "success": True,
        "course": course
    })


# ============================================================
# COURSE API - UPDATE
# ============================================================

@app.route(
    "/api/admin/courses/<int:course_id>",
    methods=["PUT"]
)
@role_required("ADMIN")
def admin_course_update(
    course_id
):

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    if not get_course(
        course_id
    ):

        return jsonify({
            "success": False,
            "message": (
                "Course not found."
            )
        }), 404

    try:

        department_id = int(
            data.get(
                "department_id"
            )
        )

        course_code = str(
            data.get(
                "course_code",
                ""
            )
        ).strip()

        course_name = str(
            data.get(
                "course_name",
                ""
            )
        ).strip()

        degree_type = str(
            data.get(
                "degree_type",
                "B.Tech"
            )
        ).strip()

        duration_years = int(
            data.get(
                "duration_years",
                4
            )
        )

        year = int(
            data.get(
                "year"
            )
        )

        semester = int(
            data.get(
                "semester"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid course data."
            )
        }), 400

    if not course_code or not course_name:

        return jsonify({
            "success": False,
            "message": (
                "Course code and name are required."
            )
        }), 400

    if not get_department(
        department_id
    ):

        return jsonify({
            "success": False,
            "message": (
                "Department does not exist."
            )
        }), 404

    try:

        update_course(
            course_id,
            department_id,
            course_code,
            course_name,
            degree_type,
            duration_years,
            year,
            semester
        )

        return jsonify({
            "success": True,
            "message": (
                "Course updated successfully."
            )
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "success": False,
            "message": (
                "Course code already exists."
            )
        }), 409

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# COURSE API - DELETE
# ============================================================

@app.route(
    "/api/admin/courses/<int:course_id>",
    methods=["DELETE"]
)
@role_required("ADMIN")
def admin_course_delete(
    course_id
):

    try:

        if not get_course(
            course_id
        ):

            return jsonify({
                "success": False,
                "message": (
                    "Course not found."
                )
            }), 404

        delete_course(
            course_id
        )

        return jsonify({
            "success": True,
            "message": (
                "Course deleted successfully."
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# STATISTICS
# ============================================================

@app.route("/api/stats")
def stats():

    try:

        students = (
            get_all_students()
        )

        logs = (
            get_attendance_records(
                filter_date=get_current_date_str()
            )
        )

        return jsonify({
            "registered_count": len(
                students
            ),
            "present_today": len(
                logs
            )
        })

    except Exception as e:

        return jsonify({
            "registered_count": 0,
            "present_today": 0,
            "error": str(e)
        })


# ============================================================
# STUDENT API
# ============================================================

@app.route("/api/students")
def students():

    try:

        return jsonify(
            get_all_students()
        )

    except Exception:

        return jsonify([])


# ============================================================
# STUDENT REGISTRATION
# ============================================================

@app.route(
    "/api/register/start",
    methods=["POST"]
)
def register_start():

    global reg_id
    global reg_name
    global reg_count

    data = request.json or {}

    reg_id = str(
        data.get(
            "student_id",
            ""
        )
    ).strip()

    reg_name = str(
        data.get(
            "student_name",
            ""
        )
    ).strip()

    if not reg_id or not reg_name:

        return jsonify({
            "success": False,
            "message": (
                "ID and name are required."
            )
        })

    try:

        students_list = (
            get_all_students()
        )

        if any(
            s["student_id"] == reg_id
            for s in students_list
        ):

            return jsonify({
                "success": False,
                "message": (
                    f"Student ID '{reg_id}' "
                    "is already registered."
                )
            })

        reg_count = 0

        get_camera()

        return jsonify({
            "success": True,
            "message": (
                "Camera initialized successfully."
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": (
                f"Database check failed: {e}"
            )
        })


@app.route(
    "/api/register/capture",
    methods=["POST"]
)
def register_capture():

    global reg_count
    global latest_frame

    if latest_frame is None:

        return jsonify({
            "success": False,
            "message": (
                "Webcam frame not available."
            )
        })

    success, message = (
        validate_and_save_frame(
            latest_frame,
            reg_id,
            reg_name,
            reg_count + 1
        )
    )

    if success:

        reg_count += 1

        return jsonify({
            "success": True,
            "message": (
                f"Frame {reg_count}/5 captured successfully!"
            )
        })

    return jsonify({
        "success": False,
        "message": message
    })


@app.route(
    "/api/register/save",
    methods=["POST"]
)
def register_save():

    global reg_id
    global reg_name
    global reg_count

    if reg_count < 5:

        return jsonify({
            "success": False,
            "message": (
                "Please capture at least 5 frames."
            )
        })

    try:

        add_student(
            reg_id,
            reg_name
        )

        release_camera()

        return jsonify({
            "success": True,
            "message": (
                f"Successfully registered {reg_name}."
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": (
                f"Database write failed: {e}"
            )
        })


# ============================================================
# VIDEO FEEDS
# ============================================================

@app.route("/api/video_feed/register")
def video_feed_register():

    return Response(
        generate_registration_frames(),
        mimetype=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        )
    )


@app.route("/api/video_feed/attendance")
def video_feed_attendance():

    return Response(
        generate_attendance_frames(),
        mimetype=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        )
    )


@app.route(
    "/api/camera/release",
    methods=["POST"]
)
def camera_release():

    release_camera()

    return jsonify({
        "success": True
    })


# ============================================================
# TRAIN FACE SYSTEM
# ============================================================

@app.route(
    "/api/train",
    methods=["POST"]
)
def train():

    data = request.json or {}

    force = data.get(
        "force",
        False
    )

    try:

        success, message = (
            train_system(
                force_rebuild=force
            )
        )

        return jsonify({
            "success": success,
            "message": message
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# ============================================================
# ATTENDANCE LOGS
# ============================================================

@app.route("/api/logs")
def logs():

    search = request.args.get(
        "search"
    )

    date = request.args.get(
        "date"
    )

    try:

        records = (
            get_attendance_records(
                filter_date=date,
                search_query=search
            )
        )

        return jsonify(
            records
        )

    except Exception:

        return jsonify([])


# ============================================================
# TEACHER STUDENTS
# ============================================================

@app.route("/api/teacher/students")
def teacher_students():

    subject = request.args.get(
        "subject"
    )

    date = request.args.get(
        "date"
    )

    if not date:

        return jsonify([])

    try:

        students_list = (
            get_all_students()
        )

        result = []

        conn = (
            get_db_connection()
        )

        cursor = conn.cursor()

        for student in students_list:

            student_id = (
                student["student_id"]
            )

            has_punched = (
                check_face_punch_exists(
                    student_id,
                    date
                )
            )

            cursor.execute(
                """
                SELECT status
                FROM subject_attendance
                WHERE
                    student_id = ?
                    AND subject_code = ?
                    AND date = ?
                """,
                (
                    student_id,
                    subject,
                    date
                )
            )

            row = cursor.fetchone()

            saved_status = (
                row["status"]
                if row
                else None
            )

            result.append({
                "student_id": student_id,
                "student_name": (
                    student[
                        "student_name"
                    ]
                ),
                "has_punched": (
                    has_punched
                ),
                "saved_status": (
                    saved_status
                )
            })

        conn.close()

        return jsonify(
            result
        )

    except Exception as e:

        print(
            "Teacher student API error:",
            e
        )

        return jsonify([])


# ============================================================
# TEACHER ATTENDANCE SUBMIT
# ============================================================

@app.route(
    "/api/teacher/submit",
    methods=["POST"]
)
def teacher_submit():

    data = request.json or {}

    subject = data.get(
        "subject_code"
    )

    date = data.get(
        "date"
    )

    records = data.get(
        "attendance",
        []
    )

    if (
        not subject
        or not date
        or not records
    ):

        return jsonify({
            "success": False,
            "message": (
                "Missing required fields."
            )
        })

    try:

        for record in records:

            student_id = (
                record[
                    "student_id"
                ]
            )

            status = (
                record[
                    "status"
                ]
            )

            has_punched = (
                check_face_punch_exists(
                    student_id,
                    date
                )
            )

            if (
                status == "Present"
                and not has_punched
            ):

                return jsonify({
                    "success": False,
                    "message": (
                        f"Student {student_id} cannot be "
                        "marked Present without a Face Punch."
                    )
                })

            mark_subject_attendance(
                student_id,
                subject,
                date,
                status
            )

        return jsonify({
            "success": True
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# ============================================================
# STUDENT ERP
# ============================================================

@app.route("/api/student/erp")
def student_erp():

    student_id = request.args.get(
        "student_id"
    )

    if not student_id:

        return jsonify({
            "error": (
                "Missing student ID"
            )
        }), 400

    student = (
        get_student(
            student_id
        )
    )

    if not student:

        return jsonify({
            "error": (
                "Student not found"
            )
        }), 404

    if student_id.isdigit():

        padded_id = (
            f"{int(student_id):06d}"
        )

    else:

        padded_id = (
            student_id.zfill(6)
        )

    prn_no = (
        f"240105{padded_id}"
    )

    try:

        summaries = (
            get_student_subject_summary(
                student_id
            )
        )

        matrix = (
            get_student_attendance_matrix(
                student_id
            )
        )

        return jsonify({
            "student_id": (
                student_id
            ),
            "student_name": (
                student[
                    "student_name"
                ]
            ),
            "prn_no": prn_no,
            "summaries": summaries,
            "matrix": matrix
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# DELETE STUDENT
# ============================================================

@app.route(
    "/api/student/delete",
    methods=["POST"]
)
def student_delete():

    data = request.json or {}

    student_id = data.get(
        "student_id"
    )

    if not student_id:

        return jsonify({
            "success": False,
            "message": (
                "Missing Student ID."
            )
        })

    try:

        student = (
            get_student(
                student_id
            )
        )

        if not student:

            return jsonify({
                "success": False,
                "message": (
                    f"Student '{student_id}' "
                    "not found."
                )
            })

        student_name = (
            student[
                "student_name"
            ]
        )

        delete_student_db(
            student_id
        )

        student_dir = (
            get_student_dir(
                student_id,
                student_name
            )
        )

        if os.path.exists(
            student_dir
        ):

            shutil.rmtree(
                student_dir
            )

        if os.path.exists(
            ENCODINGS_PATH
        ):

            with open(
                ENCODINGS_PATH,
                "rb"
            ) as file:

                encoding_records = (
                    pickle.load(
                        file
                    )
                )

            if isinstance(
                encoding_records,
                list
            ):

                updated_records = [

                    record

                    for record
                    in encoding_records

                    if record.get(
                        "student_id"
                    )
                    != student_id

                ]

                with open(
                    ENCODINGS_PATH,
                    "wb"
                ) as file:

                    pickle.dump(
                        updated_records,
                        file
                    )

        return jsonify({
            "success": True,
            "message": (
                f"Successfully deleted "
                f"{student_name} "
                f"(ID: {student_id})."
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": (
                f"Deletion failed: {e}"
            )
        })


# ============================================================
# EXPORT ATTENDANCE
# ============================================================

@app.route(
    "/api/export",
    methods=["POST"]
)
def export():

    data = request.json or {}

    date = data.get(
        "date"
    )

    try:

        success, filepath = (
            export_attendance_to_csv(
                filter_date=date
            )
        )

        if success:

            filename = (
                os.path.basename(
                    filepath
                )
            )

            return jsonify({
                "success": True,
                "filepath": filepath,
                "filename": filename
            })

        return jsonify({
            "success": False,
            "message": filepath
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# ============================================================
# DOWNLOAD EXPORT
# ============================================================

@app.route("/api/download")
def download():

    path = request.args.get(
        "path"
    )

    if (
        not path
        or not os.path.exists(
            path
        )
    ):

        return (
            "File not found",
            404
        )

    return send_file(
        path,
        as_attachment=True
    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    init_db()

    create_default_admin()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )