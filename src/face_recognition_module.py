import os
import pickle
import cv2
import numpy as np
import face_recognition

# CONFIGURATION
# TOLERANCE sets the strictness of face recognition.
# Lower tolerance is stricter (reduces false positives but may fail to recognize under different lighting/angles).
# Default recommended is 0.5. The library default is 0.6.
TOLERANCE = 0.5

ENCODINGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "encodings"))
ENCODINGS_PATH = os.path.join(ENCODINGS_DIR, "encodings.pkl")

def load_known_faces():
    """
    Loads face encodings and maps them to lists of encodings, IDs, and names.
    Flattens multiple encodings per student to parallel lists.
    """
    known_encodings = []
    known_ids = []
    known_names = []

    if not os.path.exists(ENCODINGS_PATH):
        print(f"Warning: Encodings file not found at {ENCODINGS_PATH}")
        return known_encodings, known_ids, known_names

    try:
        with open(ENCODINGS_PATH, "rb") as f:
            students_data = pickle.load(f)
            
            for student in students_data:
                student_id = student["student_id"]
                student_name = student["student_name"]
                for enc in student["encodings"]:
                    known_encodings.append(enc)
                    known_ids.append(student_id)
                    known_names.append(student_name)
                    
            print(f"Loaded {len(known_encodings)} face encodings for {len(set(known_ids))} students.")
    except Exception as e:
        print(f"Error loading encodings: {e}")
        
    return known_encodings, known_ids, known_names

def process_and_recognize_frame(frame, known_encodings, known_ids, known_names, tolerance=TOLERANCE):
    """
    Performs face detection, localization, encoding, and recognition on a single webcam frame.
    
    Image Processing Concepts Used:
    1. Image Acquisition: Capturing live frames from the webcam.
    2. Image Resizing: Scaling the frame down to 25% of its size. Resizing is critical because
       computational complexity of face detection scales quadratically with image resolution.
       Smaller frames result in dramatically higher processing FPS.
    3. Color Space Conversion: OpenCV captures frames in BGR color space, whereas the dlib-based
       face_recognition library expects RGB color space. This conversion is required for correct feature detection.
    4. Face Localization: Detecting the bounding boxes of faces in the frame.
    5. Feature Representation: Generating a 128-dimensional face embedding representing facial features.
    6. Face Distance: Calculating Euclidean distance between the live embedding and known student embeddings.
    7. Thresholding / Decision Making: Matching a face if the distance is below the tolerance threshold.
    
    Parameters:
      frame: OpenCV BGR frame
      known_encodings: List of known 128-d face encodings
      known_ids: List of student IDs corresponding to the known encodings
      known_names: List of student names corresponding to the known encodings
      tolerance: Float, matching threshold
      
    Returns:
      A list of dicts: [{"name": str, "id": str, "match_pct": float, "box": (top, right, bottom, left)}]
    """
    recognized_faces = []
    
    if frame is None:
        return recognized_faces

    # 1. Resizing for faster processing (reducing image size to 1/4)
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

    # 2. Color Conversion (BGR to RGB)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # 3. Face Localization
    face_locations = face_recognition.face_locations(rgb_small_frame)
    
    if not face_locations:
        return recognized_faces

    # 4. Face Encoding / Feature Representation
    # Generate 128-dimensional face embeddings for all detected faces
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for face_encoding, face_loc in zip(face_encodings, face_locations):
        # Scale back face locations since we processed a 1/4 size image
        top, right, bottom, left = face_loc
        box = (top * 4, right * 4, bottom * 4, left * 4)

        name = "Unknown"
        student_id = None
        match_pct = 0.0

        if len(known_encodings) > 0:
            # 5. Face Distance Calculation
            # Calculate Euclidean distance between the live face encoding and all known encodings
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            # Find the best match index
            best_match_idx = np.argmin(distances)
            best_distance = distances[best_match_idx]

            # 6. Thresholding / Matching Decision
            if best_distance <= tolerance:
                name = known_names[best_match_idx]
                student_id = known_ids[best_match_idx]
                # Calculate match percentage (closer distance = higher percentage)
                # A distance of 0.0 is 100% match, a distance of tolerance is 50% match, etc.
                match_pct = (1.0 - best_distance) * 100

        recognized_faces.append({
            "name": name,
            "id": student_id,
            "match_pct": round(match_pct, 1),
            "box": box
        })

    return recognized_faces

if __name__ == "__main__":
    # Test loader
    enc, ids, names = load_known_faces()
    print("Test run complete. Encodings count:", len(enc))
