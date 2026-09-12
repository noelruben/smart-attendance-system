import os
import cv2
import face_recognition

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))

def get_student_dir(student_id, student_name):
    """
    Returns the path to the directory for a specific student's images.
    Cleans up names to prevent invalid characters in directory paths.
    """
    # Sanitize inputs for directory name
    clean_id = str(student_id).strip().replace("/", "_").replace("\\", "_")
    clean_name = str(student_name).strip().replace("/", "_").replace("\\", "_")
    dir_name = f"{clean_id}_{clean_name}"
    return os.path.join(DATASET_DIR, dir_name)

def validate_and_save_frame(frame, student_id, student_name, img_index):
    """
    Validates that a frame contains exactly one clear face and saves it.
    
    Parameters:
      frame: OpenCV BGR image frame
      student_id: String representing Student ID
      student_name: String representing Student Name
      img_index: Integer representing image capture index (e.g. 1 to 5)
      
    Returns:
      (success_status (bool), message (str))
    """
    if frame is None:
        return False, "Invalid frame data"

    # Image acquisition & Color Conversion (BGR to RGB)
    # OpenCV loads images in BGR format, but face_recognition uses RGB format.
    # Color space conversion is necessary to match the features expected by the detector.
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Face Detection & Face Localization
    # We locate faces in the frame. Using default HOG-based model for fast CPU execution.
    face_locations = face_recognition.face_locations(rgb_frame)
    num_faces = len(face_locations)

    if num_faces == 0:
        return False, "No face detected"
    elif num_faces > 1:
        return False, "Multiple faces detected"

    # Exactly 1 face is present, proceed to save the image
    student_dir = get_student_dir(student_id, student_name)
    os.makedirs(student_dir, exist_ok=True)
    
    filename = f"image_{img_index}.jpg"
    filepath = os.path.join(student_dir, filename)
    
    # Save the original BGR frame using OpenCV
    cv2.imwrite(filepath, frame)
    return True, f"Face detected! Image {img_index} captured and saved."

if __name__ == "__main__":
    # Test directory path creation
    print("Test student directory:", get_student_dir("23", "Lakshmi"))
