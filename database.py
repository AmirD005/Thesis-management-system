import json
import os

DEFAULT_DB_PATH = "db.json"

def load_db(file_path=DEFAULT_DB_PATH):
    """
    load data
    if file didnt exist ,return empty structure
    """
    if not os.path.exists(file_path):
        return {
            "users": [],
            "files": [],
            "messages": [],
            "defenses": []
        }
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data, file_path=DEFAULT_DB_PATH):
    """save data as json"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def reset_db(file_path=DEFAULT_DB_PATH):
    """reset database """
    data = {
        "users": [],
        "files": [],
        "messages": [],
        "defenses": []
    }
    save_db(data, file_path)


if __name__ == "__main__":
    reset_db()
    print("DB initialized:", load_db())