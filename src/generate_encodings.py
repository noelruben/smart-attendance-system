import os
import pickle
import cv2
import face_recognition

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
ENCODINGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "encodings"))
ENCODINGS_PATH = os.path.join(ENCODINGS_DIR, "encodings.pkl")

def load_stored_encodings():
    """
    Loads stored face encodings from the pickle file.
    Returns:
      A list of dictionaries: [{"student_id": str, "student_name": str, "encodings": [numpy.ndarray]}]
      If file doesn't exist, returns an empty list.
    """
    if os.path.exists(ENCODINGS_PATH):
        try:
            with open(ENCODINGS_PATH, "rb") as f:
                data = pickle.load(f)
                # Verify that it is a list
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Error reading encoding file: {e}. Starting fresh.")
    return []

def save_encodings(data):
    """
    Saves the list of encodings to the pickle file.
    """
    os.makedirs(ENCODINGS_DIR, exist_ok=True)
    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump(data, f)
    print(f"Encodings saved successfully at: {ENCODINGS_PATH}")

def train_system(force_rebuild=False, progress_callback=None):
    """
    Scans the dataset directory, extracts face encodings, and updates the local pickle file.
    
    Parameters:
      force_rebuild: If True, regenerates all encodings. If False, processes only new students.
      progress_callback: A function to report progress updates (e.g. for Tkinter GUI)
      
    Returns:
      (success_status (bool), message (str))
    """
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR, exist_ok=True)
        return False, "Dataset directory is empty. No students to train."

    existing_data = [] if force_rebuild else load_stored_encodings()
    # Map student_id to its record for easy lookups
    processed_ids = {item["student_id"] for item in existing_data}
    
    # Get all student subdirectories
    student_dirs = []
    for name in os.listdir(DATASET_DIR):
        path = os.path.join(DATASET_DIR, name)
        if os.path.isdir(path):
            student_dirs.append((name, path))

    if not student_dirs:
        return False, "No student folders found in dataset/."

    new_records = []
    skipped_count = 0
    total_folders = len(student_dirs)

    for i, (dir_name, dir_path) in enumerate(student_dirs):
        # Parse student_id and student_name from folder name (format: ID_Name)
        if "_" not in dir_name:
            # Skip invalid folder formats but print a warning
            print(f"Warning: Folder '{dir_name}' does not follow 'ID_Name' format. Skipping.")
            skipped_count += 1
            continue

        parts = dir_name.split("_", 1)
        student_id = parts[0].strip()
        student_name = parts[1].strip()

        if student_id in processed_ids:
            skipped_count += 1
            continue

        if progress_callback:
            progress_callback(f"Processing student {i+1}/{total_folders}: {student_name} (ID: {student_id})...")

        print(f"Generating encodings for: {student_name} (ID: {student_id})")
        student_encodings = []

        # Read images in directory
        for img_name in os.listdir(dir_path):
            if img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(dir_path, img_name)
                # Load image
                image = cv2.imread(img_path)
                if image is None:
                    print(f"Warning: Could not read image {img_name} for student {student_name}. Skipping.")
                    continue

                # Image color conversion (BGR to RGB)
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                # Face Detection & Face Localization
                # Locate face bounding box
                face_locations = face_recognition.face_locations(rgb_image)
                
                if len(face_locations) == 0:
                    print(f"Warning: No face detected in {img_name} for student {student_name}. Skipping.")
                    continue

                # Face encoding (Feature Representation)
                # Generate 128-dimensional face encoding
                encodings = face_recognition.face_encodings(rgb_image, face_locations)
                if encodings:
                    student_encodings.append(encodings[0])

        if student_encodings:
            new_records.append({
                "student_id": student_id,
                "student_name": student_name,
                "encodings": student_encodings
            })
            print(f"Successfully generated {len(student_encodings)} encodings for {student_name}.")
        else:
            print(f"Warning: No valid encodings found for {student_name}. Skipping record creation.")

    # Combine existing records with new records
    combined_data = existing_data + new_records
    
    if new_records:
        save_encodings(combined_data)
        msg = f"Training complete! Processed {len(new_records)} new student(s). Skipped {skipped_count} already encoded. Total registered students: {len(combined_data)}."
        return True, msg
    else:
        msg = f"Training complete. No new student directories to encode. Skipped {skipped_count} already encoded. Total registered students: {len(combined_data)}."
        return True, msg

if __name__ == "__main__":
    # Test runner
    status, msg = train_system()
    print(status, "-", msg)
