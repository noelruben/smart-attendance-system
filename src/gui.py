import os
import cv2
import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from datetime import datetime

# Import modules from our project
from src.database import init_db, add_student, get_all_students, get_attendance_records
from src.register_student import validate_and_save_frame, get_student_dir
from src.generate_encodings import train_system
from src.face_recognition_module import load_known_faces, process_and_recognize_frame, TOLERANCE
from src.attendance import load_today_attendance_cache, log_attendance_for_student, get_current_date_str
from src.export import export_attendance_to_csv

class SmartAttendanceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Attendance System")
        self.root.geometry("1050x680")
        self.root.minsize(950, 600)
        
        # Initialize Database tables
        init_db()

        # State Variables
        self.cap = None  # cv2.VideoCapture object
        self.camera_active = False
        self.current_frame = None
        self.attendance_mode = False  # True when live attendance is running
        self.registration_mode = False  # True when capturing faces for registration
        
        # Registration details
        self.reg_id = ""
        self.reg_name = ""
        self.captured_count = 0
        self.max_captures = 5  # Capture 5 images per student
        
        # Live recognition variables
        self.known_encodings = []
        self.known_ids = []
        self.known_names = []
        self.today_cache = set()
        
        # Styling / Theme Colors (Modern Dark Slate theme)
        self.bg_color = "#0F172A"       # Deep Dark Slate Blue
        self.panel_color = "#1E293B"    # Slate Blue
        self.text_color = "#F8FAFC"     # Off-White
        self.accent_color = "#3B82F6"   # Electric Blue
        self.accent_hover = "#2563EB"   # Darker Blue
        self.success_color = "#10B981"  # Emerald Green
        self.warning_color = "#F59E0B"  # Amber
        self.danger_color = "#EF4444"   # Red

        self.root.configure(bg=self.bg_color)
        
        # Set up custom styles
        self.setup_styles()
        
        # Main Layout: Sidebar & Main Workspace Panel
        self.create_layout()

        # Load Welcome View on startup
        self.show_welcome_view()

    def setup_styles(self):
        """Configures ttk styles for a modern, professional look."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Global Styles
        self.style.configure(".", bg=self.bg_color, foreground=self.text_color)
        
        # Frame styles
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Panel.TFrame", background=self.panel_color)
        
        # Label styles
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=self.text_color)
        self.style.configure("Subheader.TLabel", font=("Segoe UI", 12), foreground=self.text_color)
        self.style.configure("PanelHeader.TLabel", background=self.panel_color, font=("Segoe UI", 13, "bold"), foreground=self.accent_color)
        self.style.configure("PanelLabel.TLabel", background=self.panel_color, foreground=self.text_color)
        
        # Button styles (Standard and Accent)
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8, background=self.panel_color, foreground=self.text_color, borderwidth=0)
        self.style.map("TButton", background=[("active", self.bg_color)])
        
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8, background=self.accent_color, foreground=self.text_color, borderwidth=0)
        self.style.map("Accent.TButton", background=[("active", self.accent_hover)])
        
        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), padding=8, background=self.success_color, foreground=self.text_color, borderwidth=0)
        self.style.map("Success.TButton", background=[("active", "#059669")])
        
        self.style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=8, background=self.danger_color, foreground=self.text_color, borderwidth=0)
        self.style.map("Danger.TButton", background=[("active", "#DC2626")])

        # Entry Style
        self.style.configure("TEntry", fieldbackground=self.panel_color, foreground=self.text_color, font=("Segoe UI", 11), padding=5)
        
        # Treeview Style (Tables)
        self.style.configure("Treeview", 
            background=self.panel_color, 
            foreground=self.text_color, 
            fieldbackground=self.panel_color,
            font=("Segoe UI", 9),
            rowheight=26
        )
        self.style.configure("Treeview.Heading", 
            background=self.bg_color, 
            foreground=self.text_color, 
            font=("Segoe UI", 10, "bold")
        )
        self.style.map("Treeview", background=[("selected", self.accent_color)])

    def create_layout(self):
        """Creates the sidebar navigation and main workspace container."""
        # Top Header Bar
        header_bar = ttk.Frame(self.root, height=70)
        header_bar.pack(fill=tk.X, side=tk.TOP, padx=20, pady=10)
        
        title_lbl = ttk.Label(header_bar, text="SMART ATTENDANCE SYSTEM", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT)
        
        subtitle_lbl = ttk.Label(header_bar, text="Computer Vision & Biometrics Project", style="Subheader.TLabel")
        subtitle_lbl.pack(side=tk.RIGHT, pady=10)

        # Separator Line
        separator = tk.Frame(self.root, height=2, bg=self.panel_color)
        separator.pack(fill=tk.X, side=tk.TOP, padx=20, pady=0)

        # Main Body Container
        body_frame = ttk.Frame(self.root)
        body_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, padx=20, pady=15)

        # Sidebar Panel (Left)
        self.sidebar = ttk.Frame(body_frame, style="Panel.TFrame", width=220)
        self.sidebar.pack(fill=tk.Y, side=tk.LEFT, padx=(0, 15))
        self.sidebar.pack_propagate(False)

        # Workspace Panel (Right - dynamically switched)
        self.workspace = ttk.Frame(body_frame, style="Panel.TFrame")
        self.workspace.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Sidebar Buttons
        lbl_nav = ttk.Label(self.sidebar, text="NAVIGATION", style="PanelHeader.TLabel", justify=tk.CENTER)
        lbl_nav.pack(pady=15, padx=10)

        btn_reg = ttk.Button(self.sidebar, text="1. Register Student", command=self.show_register_view)
        btn_reg.pack(fill=tk.X, padx=15, pady=8)

        btn_train = ttk.Button(self.sidebar, text="2. Train Encodings", command=self.trigger_training)
        btn_train.pack(fill=tk.X, padx=15, pady=8)

        btn_attend = ttk.Button(self.sidebar, text="3. Start Attendance", command=self.show_attendance_view)
        btn_attend.pack(fill=tk.X, padx=15, pady=8)

        btn_view = ttk.Button(self.sidebar, text="4. View Records", command=self.show_records_view)
        btn_view.pack(fill=tk.X, padx=15, pady=8)

        btn_export = ttk.Button(self.sidebar, text="5. Export CSV", command=self.trigger_direct_export)
        btn_export.pack(fill=tk.X, padx=15, pady=8)
        
        btn_exit = ttk.Button(self.sidebar, text="6. Exit", command=self.confirm_exit, style="Danger.TButton")
        btn_exit.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=20)

    def clear_workspace(self):
        """Cleans up the active webcam and clears the right-side workspace frame."""
        self.stop_webcam_capture()
        self.attendance_mode = False
        self.registration_mode = False
        
        for widget in self.workspace.winfo_children():
            widget.destroy()

    def confirm_exit(self):
        """Confirms closure and safely releases resources."""
        if messagebox.askyesno("Exit Application", "Are you sure you want to exit?"):
            self.stop_webcam_capture()
            self.root.quit()

    def start_webcam_capture(self):
        """Initializes OpenCV video capture."""
        self.stop_webcam_capture()
        self.cap = cv2.VideoCapture(0)
        
        # Set resolution to 640x480 for fast, standard operations
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.cap.isOpened():
            messagebox.showerror("Webcam Error", "Webcam could not be started. Check connection and permissions.")
            return False
            
        self.camera_active = True
        return True

    def stop_webcam_capture(self):
        """Releases the camera resource safely."""
        self.camera_active = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    # =========================================================================
    # VIEW 1: WELCOME SCREEN
    # =========================================================================
    def show_welcome_view(self):
        self.clear_workspace()
        
        welcome_frame = ttk.Frame(self.workspace, style="Panel.TFrame")
        welcome_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        welcome_title = ttk.Label(
            welcome_frame, 
            text="Welcome to the Smart Attendance System", 
            font=("Segoe UI", 16, "bold"), 
            foreground=self.accent_color,
            background=self.panel_color
        )
        welcome_title.pack(anchor=tk.W, pady=(10, 5))

        welcome_desc = ttk.Label(
            welcome_frame, 
            text="This project uses computer vision and face embeddings to automate attendance logging.\nFollow the stages in the sidebar to register students, train the recognition database, and start attendance.",
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            background=self.panel_color
        )
        welcome_desc.pack(anchor=tk.W, pady=(0, 20))

        # Show list of registered students
        lbl_list_header = ttk.Label(
            welcome_frame, 
            text="Currently Registered Students:", 
            font=("Segoe UI", 12, "bold"), 
            background=self.panel_color
        )
        lbl_list_header.pack(anchor=tk.W, pady=(10, 5))

        # Table showing students
        list_frame = ttk.Frame(welcome_frame, style="Panel.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "date")
        self.student_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.student_tree.heading("id", text="Student ID")
        self.student_tree.heading("name", text="Student Name")
        self.student_tree.heading("date", text="Registration Date")
        
        self.student_tree.column("id", width=120, anchor=tk.CENTER)
        self.student_tree.column("name", width=250, anchor=tk.W)
        self.student_tree.column("date", width=180, anchor=tk.CENTER)
        
        # Scrollbar for list
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.student_tree.yview)
        self.student_tree.configure(yscrollcommand=scrollbar.set)
        
        self.student_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_student_list()

    def refresh_student_list(self):
        """Fetches registered students from database and populates the table."""
        # Clear treeview
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)
            
        try:
            students = get_all_students()
            for s in students:
                self.student_tree.insert("", tk.END, values=(s["student_id"], s["student_name"], s["created_at"]))
        except Exception as e:
            print("Error loading students list:", e)

    # =========================================================================
    # VIEW 2: REGISTER STUDENT
    # =========================================================================
    def show_register_view(self):
        self.clear_workspace()
        self.registration_mode = True
        
        reg_frame = ttk.Frame(self.workspace, style="Panel.TFrame")
        reg_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Top Form Area
        form_frame = ttk.Frame(reg_frame, style="Panel.TFrame")
        form_frame.pack(fill=tk.X, side=tk.TOP, pady=5)

        lbl_title = ttk.Label(form_frame, text="STUDENT REGISTRATION", style="PanelHeader.TLabel")
        lbl_title.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(form_frame, text="Student ID / Roll No:", style="PanelLabel.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.entry_id = ttk.Entry(form_frame, width=25)
        self.entry_id.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(form_frame, text="Student Full Name:", style="PanelLabel.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.entry_name = ttk.Entry(form_frame, width=25)
        self.entry_name.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Webcam + Capture Controls Side-by-Side
        cam_and_controls = ttk.Frame(reg_frame, style="Panel.TFrame")
        cam_and_controls.pack(fill=tk.BOTH, expand=True, pady=10)

        # Camera Panel Frame
        self.cam_panel_frame = ttk.Frame(cam_and_controls, style="Panel.TFrame", borderwidth=1, relief="solid")
        self.cam_panel_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        self.label_reg_cam = tk.Label(self.cam_panel_frame, bg="#1E293B", text="Click 'Start Camera' after entering details.", font=("Segoe UI", 10), fg="#F8FAFC")
        self.label_reg_cam.pack(fill=tk.BOTH, expand=True)

        # Controls Panel Frame
        ctrl_frame = ttk.Frame(cam_and_controls, style="Panel.TFrame", width=220)
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.Y)
        ctrl_frame.pack_propagate(False)

        self.btn_start_cam = ttk.Button(ctrl_frame, text="Start Camera", command=self.start_registration_cam, style="Accent.TButton")
        self.btn_start_cam.pack(fill=tk.X, pady=8)

        self.btn_capture = ttk.Button(ctrl_frame, text="Capture Image", command=self.capture_face_frame, state=tk.DISABLED, style="Success.TButton")
        self.btn_capture.pack(fill=tk.X, pady=8)

        self.lbl_progress = ttk.Label(ctrl_frame, text="Captured: 0 / 5", font=("Segoe UI", 12, "bold"), background=self.panel_color, justify=tk.CENTER)
        self.lbl_progress.pack(fill=tk.X, pady=15)

        self.txt_status_box = tk.Text(ctrl_frame, height=8, bg=self.bg_color, fg=self.text_color, font=("Segoe UI", 9), borderwidth=0, wrap=tk.WORD)
        self.txt_status_box.pack(fill=tk.BOTH, expand=True, pady=5)
        self.txt_status_box.insert(tk.END, "Status Logs:\n")
        self.txt_status_box.config(state=tk.DISABLED)

    def log_reg_status(self, message):
        """Appends log text to the status display box."""
        if hasattr(self, "txt_status_box") and self.txt_status_box.winfo_exists():
            self.txt_status_box.config(state=tk.NORMAL)
            self.txt_status_box.insert(tk.END, f"- {message}\n")
            self.txt_status_box.see(tk.END)
            self.txt_status_box.config(state=tk.DISABLED)

    def start_registration_cam(self):
        """Prepares directory, validates user entries, and starts the capture camera loop."""
        self.reg_id = self.entry_id.get().strip()
        self.reg_name = self.entry_name.get().strip()

        if not self.reg_id or not self.reg_name:
            messagebox.showerror("Input Error", "Please provide both Student ID and Full Name.")
            return

        # Check if student ID already registered in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?;", (self.reg_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            messagebox.showerror("Duplicate ID", f"A student with ID '{self.reg_id}' is already registered as '{row['student_name']}'.")
            return

        # Lock inputs
        self.entry_id.config(state=tk.DISABLED)
        self.entry_name.config(state=tk.DISABLED)
        self.btn_start_cam.config(state=tk.DISABLED)
        self.btn_capture.config(state=tk.NORMAL)

        # Reset counts
        self.captured_count = 0
        self.lbl_progress.config(text=f"Captured: 0 / {self.max_captures}")
        self.log_reg_status(f"Starting registration for ID {self.reg_id} ({self.reg_name}).")

        # Start Camera
        if self.start_webcam_capture():
            self.registration_camera_loop()

    def registration_camera_loop(self):
        """Displays webcam frame in real-time for registration."""
        if not self.camera_active or not self.registration_mode:
            return
            
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame.copy()
            # Draw visual guidance grid/ellipse on screen to help alignment
            h, w, _ = frame.shape
            # BGR frame color conversion to RGB for Tkinter display
            cv2.ellipse(frame, (int(w/2), int(h/2)), (120, 160), 0, 0, 360, (255, 255, 0), 2)
            cv2.putText(frame, "Align Face Here", (int(w/2) - 80, int(h/2) - 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            img_tk = ImageTk.PhotoImage(image=img)
            self.label_reg_cam.configure(image=img_tk, text="")
            self.label_reg_cam.img_tk = img_tk
            
        self.root.after(10, self.registration_camera_loop)

    def capture_face_frame(self):
        """Validates face in current frame and saves image to dataset if valid."""
        if self.current_frame is None:
            messagebox.showerror("Camera Error", "No active frame captured. Wait for webcam to start.")
            return

        # Use our helper module function to validate face
        success, message = validate_and_save_frame(
            self.current_frame, 
            self.reg_id, 
            self.reg_name, 
            self.captured_count + 1
        )
        
        self.log_reg_status(message)
        
        if success:
            self.captured_count += 1
            self.lbl_progress.config(text=f"Captured: {self.captured_count} / {self.max_captures}")
            
            if self.captured_count >= self.max_captures:
                # Disable capture button, stop camera, and save student to DB
                self.btn_capture.config(state=tk.DISABLED)
                self.stop_webcam_capture()
                
                try:
                    add_student(self.reg_id, self.reg_name)
                    self.log_reg_status("Database updated. Registration successful!")
                    messagebox.showinfo("Success", f"Registration complete for {self.reg_name}.\nPlease train encodings next!")
                    self.show_welcome_view()
                except Exception as e:
                    self.log_reg_status(f"DB Error: {e}")
                    messagebox.showerror("Database Error", f"Failed to save student details: {e}")
                    # Release fields
                    self.entry_id.config(state=tk.NORMAL)
                    self.entry_name.config(state=tk.NORMAL)
                    self.btn_start_cam.config(state=tk.NORMAL)

    # =========================================================================
    # MODULE 2 LOGIC: TRAIN ENCODINGS
    # =========================================================================
    def trigger_training(self):
        """Triggers the generation of face encodings on demand."""
        self.clear_workspace()
        
        train_frame = ttk.Frame(self.workspace, style="Panel.TFrame")
        train_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        lbl_header = ttk.Label(train_frame, text="FACE EMBEDDINGS GENERATION", style="PanelHeader.TLabel")
        lbl_header.pack(anchor=tk.W, pady=10)

        lbl_info = ttk.Label(
            train_frame,
            text="Generating encodings translates saved face images into 128-dimensional mathematical embeddings.\nThe live webcam scanner compares face shapes using these math vectors.\nIncremental training will only process newly registered students.",
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            background=self.panel_color
        )
        lbl_info.pack(anchor=tk.W, pady=(0, 20))

        # Status output window
        self.txt_train_log = tk.Text(train_frame, height=12, bg=self.bg_color, fg=self.text_color, font=("Consolas", 10))
        self.txt_train_log.pack(fill=tk.BOTH, expand=True, pady=10)
        self.txt_train_log.insert(tk.END, "Ready for face training operations...\n")

        # Action Buttons
        btn_box = ttk.Frame(train_frame, style="Panel.TFrame")
        btn_box.pack(fill=tk.X, pady=10)

        self.btn_run_train = ttk.Button(btn_box, text="Run Incremental Training", command=lambda: self.run_training_flow(force=False), style="Accent.TButton")
        self.btn_run_train.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_force_train = ttk.Button(btn_box, text="Regenerate All Encodings (Force Build)", command=lambda: self.run_training_flow(force=True))
        self.btn_force_train.pack(side=tk.LEFT)

    def run_training_flow(self, force=False):
        """Runs the training system and displays logs in the GUI text widget."""
        self.btn_run_train.config(state=tk.DISABLED)
        self.btn_force_train.config(state=tk.DISABLED)
        
        self.txt_train_log.insert(tk.END, f"\n--- Training Started: {'Force Rebuild' if force else 'Incremental Update'} ---\n")
        self.txt_train_log.see(tk.END)
        self.root.update_idletasks()

        def log_progress(msg):
            self.txt_train_log.insert(tk.END, f"{msg}\n")
            self.txt_train_log.see(tk.END)
            self.root.update_idletasks()

        success, result_msg = train_system(force_rebuild=force, progress_callback=log_progress)
        
        self.txt_train_log.insert(tk.END, f"\nResult: {result_msg}\n")
        self.txt_train_log.insert(tk.END, "--- Training Process Complete ---\n")
        self.txt_train_log.see(tk.END)
        
        if success:
            messagebox.showinfo("Success", "Face embeddings generated and saved successfully!")
        else:
            messagebox.showwarning("Training Info", result_msg)
            
        self.btn_run_train.config(state=tk.NORMAL)
        self.btn_force_train.config(state=tk.NORMAL)

    # =========================================================================
    # VIEW 3: LIVE ATTENDANCE MODE
    # =========================================================================
    def show_attendance_view(self):
        self.clear_workspace()
        
        # Load encodings first
        self.known_encodings, self.known_ids, self.known_names = load_known_faces()
        if len(self.known_encodings) == 0:
            messagebox.showwarning(
                "No Encodings Found", 
                "No registered student encodings were found.\nPlease register a student and click 'Train Encodings' first!"
            )
            self.show_welcome_view()
            return

        # Load today's marked cache
        self.today_cache = load_today_attendance_cache()
        self.attendance_mode = True

        # GUI layout for attendance scanning
        att_frame = ttk.Frame(self.workspace, style="Panel.TFrame")
        att_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header Info
        header_grid = ttk.Frame(att_frame, style="Panel.TFrame")
        header_grid.pack(fill=tk.X, side=tk.TOP, pady=5)

        lbl_title = ttk.Label(header_grid, text="LIVE ATTENDANCE SCANNER", style="PanelHeader.TLabel")
        lbl_title.pack(side=tk.LEFT)

        self.lbl_tolerance_info = ttk.Label(
            header_grid, 
            text=f"Matching Sensitivity Tolerance: {TOLERANCE} (stricter)", 
            font=("Segoe UI", 9, "italic"),
            background=self.panel_color
        )
        self.lbl_tolerance_info.pack(side=tk.RIGHT, pady=5)

        # Camera Panel + Logs Panel side-by-side
        cam_and_logs = ttk.Frame(att_frame, style="Panel.TFrame")
        cam_and_logs.pack(fill=tk.BOTH, expand=True, pady=10)

        # Video Panel
        self.cam_panel_frame = ttk.Frame(cam_and_logs, style="Panel.TFrame", borderwidth=1, relief="solid")
        self.cam_panel_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        self.label_att_cam = tk.Label(self.cam_panel_frame, bg="#1E293B", text="Initializing camera...", font=("Segoe UI", 11), fg="#F8FAFC")
        self.label_att_cam.pack(fill=tk.BOTH, expand=True)

        # Log Listbox Pane
        log_panel = ttk.Frame(cam_and_logs, style="Panel.TFrame", width=250)
        log_panel.pack(side=tk.RIGHT, fill=tk.Y)
        log_panel.pack_propagate(False)

        ttk.Label(log_panel, text="Today's Session Activity Log:", font=("Segoe UI", 11, "bold"), background=self.panel_color).pack(anchor=tk.W, pady=5)

        # Log Listbox
        self.listbox_logs = tk.Listbox(
            log_panel, 
            bg=self.bg_color, 
            fg=self.text_color, 
            selectbackground=self.accent_color,
            font=("Segoe UI", 9), 
            borderwidth=0
        )
        self.listbox_logs.pack(fill=tk.BOTH, expand=True, pady=5)

        # Stop Camera button
        self.btn_stop_att = ttk.Button(log_panel, text="Stop Attendance Mode", command=self.show_welcome_view, style="Danger.TButton")
        self.btn_stop_att.pack(fill=tk.X, pady=(10, 0))

        # Start Camera and open Loop
        if self.start_webcam_capture():
            self.attendance_camera_loop()

    def log_attendance_message(self, message):
        """Inserts tracking message to GUI attendance listbox."""
        if hasattr(self, "listbox_logs") and self.listbox_logs.winfo_exists():
            self.listbox_logs.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def attendance_camera_loop(self):
        """Captures frame, runs recognition, logs attendance, draws visual boxes and renders."""
        if not self.camera_active or not self.attendance_mode:
            return

        ret, frame = self.cap.read()
        if ret:
            # Send frame to the recognition module
            recognized_faces = process_and_recognize_frame(
                frame, 
                self.known_encodings, 
                self.known_ids, 
                self.known_names, 
                tolerance=TOLERANCE
            )

            # Draw recognition widgets overlay on frame
            for face in recognized_faces:
                top, right, bottom, left = face["box"]
                name = face["name"]
                student_id = face["id"]
                match_pct = face["match_pct"]

                if student_id:
                    # Face is matched. Try logging attendance.
                    logged_success, log_msg = log_attendance_for_student(student_id, name, self.today_cache)
                    
                    if logged_success:
                        self.log_attendance_message(log_msg)
                    elif student_id in self.today_cache:
                        # Log warning message locally to display once inside lists
                        pass
                    
                    # Colors: Green for recognized registered students
                    box_color = (0, 255, 0)
                    text_label = f"{name} ({match_pct:.0f}%)"
                    sub_text = f"ID: {student_id}"
                    
                    # If attendance was already logged today, display label
                    if student_id in self.today_cache:
                        sub_text += " [MARKED]"
                else:
                    # Unrecognized face: Red box and label
                    box_color = (0, 0, 255)
                    text_label = "Unknown"
                    sub_text = "Not Registered"

                # Draw bounding box
                cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
                
                # Draw filled label backgrounds below box or above
                cv2.rectangle(frame, (left, bottom), (right, bottom + 40), box_color, cv2.FILLED)
                cv2.putText(frame, text_label, (left + 6, bottom + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
                cv2.putText(frame, sub_text, (left + 6, bottom + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

            # Color convert frame to display in Tkinter
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            img_tk = ImageTk.PhotoImage(image=img)
            
            if hasattr(self, "label_att_cam") and self.label_att_cam.winfo_exists():
                self.label_att_cam.configure(image=img_tk, text="")
                self.label_att_cam.img_tk = img_tk

        self.root.after(10, self.attendance_camera_loop)

    # =========================================================================
    # VIEW 4: ATTENDANCE RECORDS VIEW & SEARCH
    # =========================================================================
    def show_records_view(self):
        self.clear_workspace()

        records_frame = ttk.Frame(self.workspace, style="Panel.TFrame")
        records_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        lbl_title = ttk.Label(records_frame, text="ATTENDANCE LOGS HISTORY", style="PanelHeader.TLabel")
        lbl_title.pack(anchor=tk.W, pady=5)

        # Filters toolbar
        filter_bar = ttk.Frame(records_frame, style="Panel.TFrame")
        filter_bar.pack(fill=tk.X, pady=10)

        ttk.Label(filter_bar, text="Search (ID/Name):", style="PanelLabel.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(filter_bar, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(filter_bar, text="Date (DD-MM-YYYY):", style="PanelLabel.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.date_entry = ttk.Entry(filter_bar, width=12)
        self.date_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Helper button to insert today's date easily
        btn_today = ttk.Button(filter_bar, text="Today", command=self.insert_today_date_filter)
        btn_today.pack(side=tk.LEFT, padx=(0, 15))

        btn_search = ttk.Button(filter_bar, text="Search", command=self.load_filtered_records, style="Accent.TButton")
        btn_search.pack(side=tk.LEFT, padx=(0, 5))

        btn_reset = ttk.Button(filter_bar, text="Reset Filters", command=self.reset_record_filters)
        btn_reset.pack(side=tk.LEFT)

        # Records Table View (Treeview)
        table_frame = ttk.Frame(records_frame, style="Panel.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("id", "student_id", "student_name", "date", "time", "status")
        self.records_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.records_tree.heading("id", text="Record ID")
        self.records_tree.heading("student_id", text="Student ID")
        self.records_tree.heading("student_name", text="Student Name")
        self.records_tree.heading("date", text="Date")
        self.records_tree.heading("time", text="Time")
        self.records_tree.heading("status", text="Status")

        self.records_tree.column("id", width=80, anchor=tk.CENTER)
        self.records_tree.column("student_id", width=120, anchor=tk.CENTER)
        self.records_tree.column("student_name", width=220, anchor=tk.W)
        self.records_tree.column("date", width=120, anchor=tk.CENTER)
        self.records_tree.column("time", width=120, anchor=tk.CENTER)
        self.records_tree.column("status", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=scrollbar.set)
        
        self.records_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom export toolbar inside views
        bottom_bar = ttk.Frame(records_frame, style="Panel.TFrame")
        bottom_bar.pack(fill=tk.X, pady=(10, 0))

        self.lbl_records_count = ttk.Label(bottom_bar, text="Records displayed: 0", font=("Segoe UI", 9, "italic"), background=self.panel_color)
        self.lbl_records_count.pack(side=tk.LEFT)

        btn_export = ttk.Button(bottom_bar, text="Export Filtered List to CSV", command=self.trigger_filtered_export, style="Success.TButton")
        btn_export.pack(side=tk.RIGHT)

        # Load initial unfiltered records
        self.load_filtered_records()

    def insert_today_date_filter(self):
        """Auto-fills today's date in filter input."""
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, get_current_date_str())

    def reset_record_filters(self):
        """Clears all filters and reloads database table."""
        self.search_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.load_filtered_records()

    def load_filtered_records(self):
        """Loads records from sqlite DB applying date and search text filters."""
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
            
        search_q = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        date_q = self.date_entry.get().strip() if hasattr(self, "date_entry") else ""
        
        # If inputs are empty, evaluate as None
        search_q = search_q if search_q != "" else None
        date_q = date_q if date_q != "" else None
        
        try:
            records = get_attendance_records(filter_date=date_q, search_query=search_q)
            for r in records:
                self.records_tree.insert(
                    "", 
                    tk.END, 
                    values=(r["id"], r["student_id"], r["student_name"], r["date"], r["time"], r["status"])
                )
            self.lbl_records_count.config(text=f"Records displayed: {len(records)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch records: {e}")

    # =========================================================================
    # CSV EXPORTS CONTROLLERS
    # =========================================================================
    def trigger_direct_export(self):
        """Triggered from sidebar button 5. Exports all database rows to CSV using file dialog."""
        # Open save dialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Attendance Records",
            initialfile=f"attendance_all_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not filepath:
            return  # Cancelled

        success, message = export_attendance_to_csv(target_filepath=filepath)
        if success:
            messagebox.showinfo("Export Successful", f"Records exported successfully to:\n{message}")
        else:
            messagebox.showerror("Export Failed", message)

    def trigger_filtered_export(self):
        """Triggered from the records view button. Exports only filtered results to CSV."""
        date_q = self.date_entry.get().strip()
        date_q = date_q if date_q != "" else None
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Filtered Attendance Records",
            initialfile=f"attendance_filtered_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not filepath:
            return  # Cancelled

        success, message = export_attendance_to_csv(target_filepath=filepath, filter_date=date_q)
        if success:
            messagebox.showinfo("Export Successful", f"Filtered records exported to:\n{message}")
        else:
            messagebox.showerror("Export Failed", message)

if __name__ == "__main__":
    # Test script launches interface directly
    root = tk.Tk()
    app = SmartAttendanceGUI(root)
    
    # Handle window close button (X) safely
    root.protocol("WM_DELETE_WINDOW", app.confirm_exit)
    root.mainloop()
