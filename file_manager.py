import shutil
import datetime
from pathlib import Path
from database import load_db, save_db

ALLOWED_EXTS = {".pdf", ".jpg", ".jpeg"}
UPLOADS_DIR = Path("uploads")

def _next_file_id(db):
    if not db["files"]:
        return 1
    return max(f["id"] for f in db["files"]) + 1

def register_file(file_path, description="", uploader_id=None, db_path="db.json"):
    
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"Invalid file type: {ext}. Allowed: {ALLOWED_EXTS}")

    db = load_db(db_path)

 
    if uploader_id is not None:
        from user_manager import get_user_by_id
        uploader = get_user_by_id(uploader_id, db_path)
        if uploader is None:
            raise ValueError(f"Uploader with id {uploader_id} not found.")
        if not uploader.get("is_active", True):
            raise ValueError(f"Uploader with id {uploader_id} is not active.")

    new_id = _next_file_id(db)
    stored_name = f"file_{new_id}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}{ext}"
    stored_path = UPLOADS_DIR / stored_name
    UPLOADS_DIR.mkdir(exist_ok=True)

    shutil.copy2(p, stored_path)
    size_bytes = stored_path.stat().st_size

    record = {
        "id": new_id,
        "original_name": p.name,
        "stored_path": str(stored_path),
        "file_type": ext.lstrip("."),
        "description": description,
        "uploader_id": uploader_id,
        "size_bytes": size_bytes,
        "registered_at": datetime.datetime.utcnow().isoformat() + "Z",
        "metadata": {}  
    }

    db["files"].append(record)
    save_db(db, db_path)
    return new_id

def list_files(db_path="db.json"):
    db = load_db(db_path)
    return db["files"]

def find_files(db_path="db.json", file_type=None, uploader_id=None, original_name_contains=None):
    db = load_db(db_path)
    files = db.get("files", []) or []
    results = []
    for f in files:
        if file_type is not None and f.get("file_type") != file_type:
            continue
        if uploader_id is not None and f.get("uploader_id") != uploader_id:
            continue
        if original_name_contains is not None:
            name = f.get("original_name") or ""
            if original_name_contains.lower() not in name.lower():
                continue
        results.append(f)
    return results

def get_file_by_id(file_id, db_path="db.json"):
    db = load_db(db_path)
    for f in db["files"]:
        if f["id"] == file_id:
            return f
    return None

def delete_file(file_id, db_path="db.json", delete_from_disk=False):
    db = load_db(db_path)
    for i, f in enumerate(db["files"]):
        if f["id"] == file_id:
            if delete_from_disk:
                try:
                    Path(f["stored_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
            del db["files"][i]
            save_db(db, db_path)
            return True
    return False

if __name__ == "__main__":
    from database import reset_db
    reset_db()
    fid = register_file("example.pdf", "Test file", uploader_id=None)
    print("Files:", list_files())