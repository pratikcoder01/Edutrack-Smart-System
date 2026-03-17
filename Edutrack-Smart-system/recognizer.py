from deepface import DeepFace
import os

def get_present_rolls(frame):
    try:
        # DeepFace scans the 'dataset' folder created during registration
        results = DeepFace.find(img_path=frame, db_path="dataset", 
                                model_name="Facenet", enforce_detection=False, silent=True)
        found = {}
        for df in results:
            if not df.empty:
                # Extract best match from the DataFrame
                top_match = df.iloc[0]
                path = top_match['identity']
                distance = top_match['distance'] # Facenet cosine distance threshold defaults ~0.40
                
                # Normalize distance to ~100% confidence scale (0.4 dist = low conf, 0.0 dist = high conf)
                confidence = max(1, min(100, int((1 - (distance / 0.40)) * 100)))
                
                # Extracts the Roll Number from the folder name (e.g., dataset/67/0.jpg -> 67)
                roll = os.path.basename(os.path.dirname(path))
                
                # Store highest confidence if roll detected multiple times in same frame
                found[roll] = max(confidence, found.get(roll, 0))
        return list(found.items())
    except Exception as e:
        print(f"Recognition Error: {e}")
        return []