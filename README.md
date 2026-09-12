# Smart Attendance System Using Face Recognition and Face Embeddings (Web Application)

A complete, working 3rd-year Computer Science and Engineering micro-project based on Image Processing and Computer Vision. This system operates entirely locally/offline and automates student attendance tracking using face embeddings. It runs in the web browser at `http://127.0.0.1:5000` via a local Flask web server.

---

## 1. Project Title
**Smart Attendance System Using Face Recognition and Face Embeddings**

## 2. Problem Statement
Traditional attendance systems (such as manual roll calls or paper sheets) are slow, error-prone, and susceptible to proxy attendance (where students mark attendance for absent peers). While biometric systems like fingerprint scanners solve proxy issues, they require physical contact, creating bottlenecks and hygiene concerns. This project provides a contact-free, automated, and secure alternative using face recognition via a standard computer webcam.

## 3. Objective
To design and build a lightweight, offline, web-based webcam attendance system that:
1. Registers students by capturing face images from a live webcam stream in the browser.
2. Validates registration data to ensure clear, single-face images.
3. Generates 128-dimensional face embedding vectors using pre-trained computer vision models.
4. Matches live faces in real-time against stored embeddings using MJPEG streams.
5. Automatically logs attendance in an SQLite database, preventing duplicate entries for the same day.
6. Allows searching, filtering, and exporting attendance history to CSV.

## 4. Features
* **Modern Web Interface Dashboard**: A sleek dark-slate SPA (Single Page Application) design with glassmorphic layouts, statistics cards, and sidebar tabs.
* **Server-Driven Camera Streams**: Streams camera feeds directly to browser `<img>` elements using MJPEG multipart boundaries (`/api/video_feed/register` and `/api/video_feed/attendance`).
* **Smart Student Registration**: Captures 5 face images per student, validates that exactly one face is present, and organizes them in a directory-based dataset structure.
* **Incremental Training**: Avoids redundant processing by only generating face encodings for newly registered students.
* **Real-time Bounding Box Overlay**: Draws bounding boxes in real-time with student name, ID, and match percentage directly on the video stream.
* **Double-Attendance Prevention**: Restricts student marking to once per day. An in-memory cache prevents redundant database operations.
* **Comprehensive Search & Filter**: View records sorted by date, search by student name/ID, or filter by date.
* **CSV Export Module**: Clean data exports to CSV files using Pandas, triggered from the browser.
* **100% Local Processing**: No external cloud APIs, internet connections, or paid services are used, ensuring absolute biometric privacy.

---

## 5. Technologies Used
1. **Programming Language**: Python 3.14+
2. **Web Framework**: Flask (handles routing, REST APIs, and MJPEG video streaming).
3. **Computer Vision & Image Processing**: OpenCV (for frame acquisition, color space conversions, image resizing, and drawing overlays).
4. **Face Recognition**: `face_recognition` library (wraps the dlib pre-trained ResNet model to detect face locations and extract 128-dimensional face embeddings).
5. **Numerical Data Handling**: NumPy (for distance calculation and array operations) and Pandas (for data structuring and CSV exporting).
6. **Database**: SQLite3 (built-in relational SQL database for storing student metadata and attendance logs).
7. **Frontend Design**: HTML5, Vanilla CSS3 (custom dark theme), and Vanilla JavaScript (Fetch API AJAX and DOM router).
8. **Hardware**: Any standard laptop or desktop USB webcam.

---

## 6. System Architecture
The application runs as a modular system split into presentation (Web Frontend), backend (Flask API & SQLite), and computer vision layers:

```
Smart-Attendance/
│
├── dataset/                    # Stores captured raw BGR face images in ID_Name folders
│   └── 23_Lakshmi/
│       ├── image_1.jpg
│       └── ...
│
├── encodings/
│   └── encodings.pkl           # Serialized 128-dimensional face embedding vectors
│
├── database/
│   └── attendance.db           # SQLite3 database (stores students and attendance tables)
│
├── exports/
│   └── attendance_*.csv        # Exported CSV spreadsheets
│
├── templates/
│   └── index.html              # Main HTML web page template
│
├── static/
│   ├── style.css               # Premium CSS dark theme stylesheet
│   └── app.js                  # Frontend Javascript application logic
│
├── src/
│   ├── main.py                 # Application entry point launcher
│   ├── web_server.py           # Flask web routes and video streaming APIs
│   ├── database.py             # SQLite schema and query operations
│   ├── register_student.py     # Image validation & dataset file saving
│   ├── generate_encodings.py   # Embedding extraction using face_recognition
│   ├── face_recognition_module.py # Frame resizing, conversion, distance comparison
│   ├── attendance.py           # Day cache checks and attendance registration
│   └── export.py               # Database to CSV converter using Pandas
│
└── requirements.txt            # System dependencies
```

---

## 7. Workflow
1. **Enrollment**: User opens `http://127.0.0.1:5000/` and goes to Register Student. Enters ID and name, starts camera, and clicks "Capture Face" 5 times under a guided webcam boundary.
2. **Training**: User navigates to Train Encodings and clicks "Run Incremental Training". The server processes images, extracts 128-D embeddings, and writes to `encodings.pkl`.
3. **Scanning**: User opens Live Scanner. Flask starts the camera and streams the feed with bounding box overlays. The matching engine compares live faces against the database.
4. **Logging**: Recognized faces (distance <= 0.5) trigger SQLite insertions (marked only once per day using in-memory set cache check).
5. **Logs & Export**: User visits Attendance Logs to search/filter records and export them to a CSV spreadsheet.

---

## 8. Installation
Since dlib is complex to compile on Windows without Visual Studio C++ Build Tools, this project uses a precompiled community wheel.

Run the following commands in your terminal (Command Prompt or PowerShell) inside the project directory:

```bash
# 1. Install pre-compiled dlib wheel for Python 3.14 on Windows
pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-20.0.99-cp314-cp314-win_amd64.whl

# 2. Downgrade setuptools to restore pkg_resources (required for face_recognition compatibility)
pip install "setuptools<=80.10.2"

# 3. Install remaining dependencies from requirements.txt
pip install -r requirements.txt
```

## 9. How to Run
Launch the local web server:
```bash
python src/main.py
```
Then, open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 10. Student Registration Procedure
1. Enter a unique **Student ID / Roll No** (e.g., `23`) and **Full Name** (e.g., `Lakshmi`).
2. Click **Start Camera** to activate the webcam stream inside the browser.
3. Position your head inside the red alignment guide.
4. Click **Capture Face** 5 times in slightly different angles/expressions.
5. The console log displays if a single face was detected and saved. Multiple/zero faces will be rejected.
6. Once 5 photos are captured, the camera closes and the student is recorded in the database.

## 11. Encoding Generation Procedure
1. Go to the **Train Encodings** tab on the navigation sidebar.
2. Click **Run Incremental Training**.
3. The system scans the `dataset/` folder, processes folders not yet in `encodings.pkl`, detects the face in each image, extracts the 128-dimensional embedding, and updates the local pickle file.
4. You can also run **Force Regenerate All** to rebuild from scratch.

## 12. Attendance Procedure
1. Click **Live Scanner** on the navigation sidebar.
2. Click **Start Scanning** to open the webcam stream.
3. When a registered student appears before the camera, a green bounding box will surround their face, displaying their name, ID, and match confidence.
4. The side Activity Log panel shows real-time check-in logs ("Checked in at: 10:35:20 | Present").
5. If the student remains in front of the camera, the overlay displays `[MARKED]` next to their ID, and no duplicate records are generated.
6. Pointing at an unregistered face draws a red bounding box labeled "Unknown".

## 13. Database Structure
The system uses SQLite3 with two relational tables:

### `students` Table
Stores student enrollment metadata.
* `student_id` (TEXT, PRIMARY KEY): Unique identifier.
* `student_name` (TEXT, NOT NULL): Full name.
* `created_at` (TIMESTAMP): Date and time of registration.

### `attendance` Table
Logs daily attendance records.
* `id` (INTEGER, PRIMARY KEY AUTOINCREMENT): Unique record ID.
* `student_id` (TEXT, NOT NULL, FOREIGN KEY): Links to `students.student_id`.
* `student_name` (TEXT, NOT NULL): Name copy for denormalized viewing.
* `date` (TEXT, NOT NULL): Date in `DD-MM-YYYY` format.
* `time` (TEXT, NOT NULL): Time in `HH:MM:SS` format.
* `status` (TEXT, NOT NULL): Typically `"Present"`.

*A Unique Composite Index `idx_attendance_student_date` is created on `(student_id, date)` to prevent duplicate marking.*

---

## 14. Image Processing Concepts Used
This project applies fundamental computer vision concepts in a real-world pipeline:
* **Image Acquisition**: Grabbing sequential video frames (NumPy arrays) from a hardware camera sensor using OpenCV's `VideoCapture` API.
* **Image Resizing**: Scaling the incoming frame down by 75% (`fx=0.25, fy=0.25`). Resizing reduces pixel count by a factor of 16, which significantly speeds up face localization and embedding extraction.
* **Color Space Conversion**: Converting BGR (Blue-Green-Red) matrices captured by OpenCV into RGB (Red-Green-Blue) matrices. This is mandatory because the underlying dlib HOG detector and neural network are trained on RGB channel sequences.
* **Face Detection & Localization**: Finding coordinates of faces in the frame using Histograms of Oriented Gradients (HOG) combined with a linear SVM classifier.
* **Feature Representation**: Converting the localized face region into a standard feature space (a 128-dimensional vector) using a pre-trained deep residual network (ResNet).
* **Face Distance**: Measuring vector similarity by calculating the Euclidean distance between two 128-dimensional vectors.
* **Thresholding / Matching Decision**: Classifying a face as matching if the Euclidean distance is less than or equal to a configured threshold parameter (`TOLERANCE = 0.5`).

## 15. Face Embedding Explanation
A **face embedding** is a vector representation of a face's features. The `face_recognition` library uses a pre-trained deep learning model (trained on millions of faces) to map a face image to a 128-dimensional space. The coordinates represent abstract facial measurements (e.g., distance between eyes, nose bridge height, jawline curves). A key property of embeddings is that images of the same person will cluster close together in this 128-dimensional space, while images of different people will be far apart.

## 16. Face Distance Explanation
To recognize a face, the system calculates the **Euclidean distance** (the straight-line distance between two points in a multi-dimensional space) between the live face embedding and all registered embeddings:
$$\text{Distance} = \sqrt{\sum_{i=1}^{128} (x_i - y_i)^2}$$
A distance of `0.0` represents a perfect identical match. As the distance increases, the facial features differ. We classify the face as recognized if the minimum distance is below our configured tolerance threshold of `0.5`.

## 17. Limitations
* **Lighting Sensitivity**: Drastic changes in lighting (extremely dark rooms, strong backlight) can alter facial shadow features, leading to false negatives.
* **Pose Limitations**: The system is designed for frontal or near-frontal face views. Extreme side profiles may fail to match.
* **Hardware Dependence**: Requires an active, connected USB/internal webcam. Low-quality camera sensors degrade detection accuracy.
* **Simple Spoor/Spoofing Vulnerability**: Can be fooled by displaying a high-resolution photograph of a registered student in front of the camera (liveness detection is not implemented).

## 18. Future Enhancements
* **Liveness Detection**: Integrate texture analysis or blink detection to prevent photo-spoofing.
* **Multi-Camera Support**: Allow administrators to switch between multiple connected camera feeds.
* **Cloud Sync**: Allow automatic synchronization of database records with a cloud service while keeping face embeddings stored locally.
* **Deep CNN Model Acceleration**: Utilize GPU acceleration (CUDA) to process high-resolution frames or multiple faces concurrently.

## 19. Privacy Considerations
Biometric information (face data) is sensitive. This system operates **100% offline**. Raw images and mathematical embeddings are saved locally in the user's workspace directory (`dataset/` and `encodings/`). The software does not transmit data over the internet or communicate with external servers. It is strictly intended for local educational demonstrations.

## 20. Screenshots Section Placeholders
* **Dashboard Tab**: Main home interface displaying statistics cards and enrolled student registry table.
* **Registration Tab**: Active camera feed showing the oval alignment guide during enrollment.
* **Live Scanner Tab**: Bounding boxes enclosing faces on stream with real-time session logs.
* **Attendance Logs Tab**: Filtered table displaying historical logs database and export controls.

---

## PROJECT PRESENTATION / VIVA PREPARATION GUIDE

### A. Project Overview Summary
* **Title**: Smart Attendance System Using Face Recognition and Face Embeddings
* **Goal**: Automate class roll-calls using real-time face embeddings via a standard laptop webcam.
* **Language**: Python (Flask Backend) & Javascript (AJAX Frontend).
* **Key Libraries**: OpenCV, face_recognition, NumPy, Pandas, SQLite3, Flask.

### B. Why These Technologies?
* **Python** is used for rapid prototyping, rich scientific libraries (NumPy, Pandas), and high-level wrappers for C++ computer vision tools (OpenCV, dlib).
* **Flask** is a micro-framework selected to build a responsive browser application that streams video feeds using standard web protocols.
* **OpenCV** handles heavy video processing (acquiring frames, resizing, drawing graphic boxes, converting color channels).
* **face_recognition** wraps a pre-trained ResNet model that is highly accurate on faces, saving us from training a deep neural network from scratch.
* **SQLite3** is a lightweight, zero-configuration relational SQL database that stores records locally without needing a separate server process.

### C. Embedding & Matching Science
* **128-Dimensional Vector**: A series of 128 numbers generated by a deep neural network representing unique facial landmarks.
* **Euclidean Distance**: Calculates the distance between two vectors. A distance of `0` is a perfect match. We use a threshold of `0.5` (lower is stricter).
* **Double-Marking Prevention**: We use a composite index `UNIQUE(student_id, date)` in SQL. We also cache marked student IDs in a Python `set` in-memory. When a face is recognized, we check the set first before performing database writes.

---

## 20 Likely Viva Questions & Answers

**Q1: What is the core objective of your project?**  
**A:** To automate attendance logging by detecting and identifying registered students from a webcam feed using pre-trained 128-dimensional face embeddings, recording their attendance in an offline SQLite database once per day.

**Q2: Did you train a deep learning model from scratch in this project?**  
**A:** No. We used the pre-trained model provided by the `face_recognition` library (trained on dlib's ResNet-34). The model is already trained to extract facial feature vectors (embeddings). We utilize it to generate embeddings and compare them using distance metrics.

**Q3: What library is used to perform face detection and encoding?**  
**A:** The `face_recognition` library, which is a high-level wrapper around the `dlib` toolkit.

**Q4: What is a face embedding?**  
**A:** A face embedding is a 128-dimensional vector (a list of 128 floating-point numbers) that mathematically represents the unique facial features of a person.

**Q5: How does the system determine if a live face matches a registered student?**  
**A:** It computes the Euclidean distance between the 128-dimensional embedding of the live face and the stored embeddings of registered students. If the smallest distance is below our tolerance threshold (0.5), it classifies it as a match.

**Q6: What does the "Tolerance" parameter mean, and what is its default value?**  
**A:** Tolerance is the threshold distance for classification. The default is `0.5`. A lower tolerance (e.g. 0.4) is stricter, reducing false matches but requiring better alignment. A higher tolerance (e.g. 0.6) is more lenient, allowing matches in poor light but increasing the risk of false positives.

**Q7: Why do you resize the webcam frame to 1/4 size before processing?**  
**A:** Face detection and localization are computationally expensive and scale with image resolution. Downscaling the frame by 75% reduces the pixel count by 16 times, which significantly speeds up processing frames per second (FPS) and ensures smooth real-time execution.

**Q8: Why do we convert the BGR frame from OpenCV to RGB before face processing?**  
**A:** OpenCV reads image frames in BGR format by default. However, the pre-trained dlib neural network and face recognition libraries are trained on RGB images. Failing to convert the color channels will cause incorrect detection and poor feature mapping.

**Q9: How do you prevent a student from being marked present multiple times on the same day?**  
**A:** We implement two levels of protection:
1. **Database level**: An SQLite composite unique constraint `UNIQUE(student_id, date)` prevents duplicate records.
2. **Application level**: We load today's marked students into an in-memory Python `set` cache. When a student is recognized, we verify they aren't in the cache before querying the database, which prevents unnecessary database lag.

**Q10: What database is used, and what are its tables?**  
**A:** We use SQLite3. It has two tables: `students` (stores student metadata: ID, Name, registration timestamp) and `attendance` (logs daily records: ID, Student ID, Name, Date, Time, Status).

**Q11: Why is SQLite preferred over MySQL or PostgreSQL for this project?**  
**A:** SQLite is serverless, self-contained, and requires zero configuration. It stores the database in a single local file, making it perfect for lightweight, offline desktop micro-projects that need to run immediately without configuring a database server.

**Q12: How are the student face encodings saved locally?**  
**A:** They are saved inside `encodings/encodings.pkl` as a serialized list of dictionaries using Python's `pickle` module.

**Q13: What does the training/generate encodings phase do?**  
**A:** It scans the `dataset/` directory, checks if folders exist that are not in the pickle file, extracts face embeddings from the images in those folders, and appends them to `encodings.pkl`.

**Q14: How many images are captured per student during registration, and why?**  
**A:** We capture 5 images per student. This allows the system to store multiple embeddings representing slight variations in facial angle, head tilt, and expression, which improves real-time recognition accuracy.

**Q15: What happens if multiple faces appear during registration?**  
**A:** The registration module validates each frame using face detection. If more than one face is detected, it displays "Multiple faces detected" and rejects the capture to ensure clean data for that student's profile.

**Q16: What happens if an unregistered person appears in front of the camera?**  
**A:** The system calculates the Euclidean distance. Since the distance to all registered student embeddings will exceed the tolerance threshold (0.5), it labels the face as "Unknown" with a red bounding box and does not record attendance.

**Q17: How is the attendance data exported, and what format is used?**  
**A:** It is exported to a `.csv` (Comma-Separated Values) file using the Pandas library, which can be opened in Excel.

**Q18: How does the camera feed display in the browser window?**  
**A:** The Flask backend reads video frames, overlays graphic annotations, and yields them using MJPEG streaming (`multipart/x-mixed-replace` mimetype). The browser renders this stream inside standard `<img>` tags dynamically.

**Q19: What are the main limitations of this system?**  
**A:** 
1. It is sensitive to extreme lighting changes (darkness, backlight).
2. It does not perform liveness detection, so it can be spoofed using a high-quality photograph of a student.
3. Side-view face profiles are not recognized.

**Q20: How could you improve this system for commercial deployment?**  
**A:** By adding liveness detection (blink detection or depth sensing) to prevent photo spoofing, integrating with a central cloud database, and utilizing GPU acceleration (CUDA) to process higher resolution feeds with multiple concurrent faces.
