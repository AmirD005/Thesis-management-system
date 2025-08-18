import datetime
import hashlib
import secrets
from database import load_db, save_db

DEFAULT_PBKDF2_ITERS = 150_000


def hash_password(password: str, iterations: int = DEFAULT_PBKDF2_ITERS):
  
    
    if password is None:
        raise ValueError("Password cannot be None")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), dk.hex(), iterations

def verify_password(password: str, salt_hex: str, hash_hex: str, iterations: int = DEFAULT_PBKDF2_ITERS):
   
    
    if password is None:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(dk, expected)


def _next_user_id(db):
    if not db.get("users"):
        return 1
    return max(u.get("id", 0) for u in db.get("users", [])) + 1

def get_user_by_id(user_id, db_path="db.json"):
    db = load_db(db_path)
    for u in db.get("users", []):
        if u.get("id") == user_id:
            return u
    return None

def get_user_by_name(name, db_path="db.json"):
    if not isinstance(name, str):
        return None
    db = load_db(db_path)
    name_norm = name.strip().casefold()
    for u in db.get("users", []):
        uname = u.get("name")
        if isinstance(uname, str) and uname.strip().casefold() == name_norm:
            return u
    return None

def list_users(db_path="db.json"):
    db = load_db(db_path)
    return list(db.get("users", []))



def add_user(name, role, password,
             advisor_id=None, defense_date=None,
             advisee_capacity=None, jury_capacity=None,
             db_path="db.json"):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string.")
    name = name.strip()
    if role not in ("student", "teacher"):
        raise ValueError("role must be 'student' or 'teacher'.")
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string.")
    if defense_date is not None:
        try:
            dd = datetime.date.fromisoformat(defense_date.strip())
            defense_date = dd.isoformat()
        except Exception:
            raise ValueError("defense_date must be in YYYY-MM-DD format.")
    db = load_db(db_path)
    new_id = _next_user_id(db)
    salt_hex, hash_hex, iters = hash_password(password)
    now_iso = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    user_record = {
        "id": new_id,
        "name": name,
        "role": role,
        "advisor_id": advisor_id,
        "defense_date": defense_date,
        "password_salt": salt_hex,
        "password_hash": hash_hex,
        "password_iterations": iters,
        "created_at": now_iso,
        "last_login": None,
        "is_active": True
    }
    
    if role == "teacher":
        if advisee_capacity is not None and int(advisee_capacity) < 0:
            raise ValueError("advisee_capacity must be >= 0")
        if jury_capacity is not None and int(jury_capacity) < 0:
            raise ValueError("jury_capacity must be >= 0")
        user_record["advisee_capacity"] = int(advisee_capacity) if advisee_capacity is not None else 5
        user_record["jury_capacity"] = int(jury_capacity) if jury_capacity is not None else 10
    if role == "student" and advisor_id is not None:
        advisor = get_user_by_id(advisor_id, db_path)
        if not advisor or advisor.get("role") != "teacher":
            raise ValueError(f"advisor_id {advisor_id} not found or not a teacher.")
        current_advisees = sum(
            1 for u in db.get("users", [])
            if u.get("role") == "student" and u.get("advisor_id") == advisor_id
        )
        
        cap = int(advisor.get("advisee_capacity", 5))
        if current_advisees >= cap:
            raise ValueError(f"Advisor {advisor_id} has no remaining advisee slots (used {current_advisees} / cap {cap}).")
   
    db["users"].append(user_record)
    save_db(db, db_path)
    return new_id


def authenticate_user(identifier, password, db_path="db.json"):
   
    
    db = load_db(db_path)
    user = None
    if isinstance(identifier, int):
        user = get_user_by_id(identifier, db_path)
    else:
        user = get_user_by_name(str(identifier), db_path)

    if not user:
        return None
    if not user.get("is_active", True):
        return None

    salt = user.get("password_salt")
    hash_hex = user.get("password_hash")
    iters = user.get("password_iterations", DEFAULT_PBKDF2_ITERS)

    if not salt or not hash_hex:
        return None

    if verify_password(password, salt, hash_hex, iters):
        
        for u in db["users"]:
            if u["id"] == user["id"]:
                u["last_login"] = datetime.datetime.utcnow().isoformat() + "Z"
                break
        save_db(db, db_path)
        return get_user_by_id(user["id"], db_path)  # return fresh copy
    return None

def change_password(user_id, old_password, new_password, db_path="db.json"):
    
    
    db = load_db(db_path)
    user = get_user_by_id(user_id, db_path)
    if not user:
        raise ValueError("User not found")
    if not verify_password(old_password, user["password_salt"], user["password_hash"], user.get("password_iterations", DEFAULT_PBKDF2_ITERS)):
        raise ValueError("Old password does not match")

    salt_hex, hash_hex, iters = hash_password(new_password)
    for u in db["users"]:
        if u["id"] == user_id:
            u["password_salt"] = salt_hex
            u["password_hash"] = hash_hex
            u["password_iterations"] = iters
            break
    save_db(db, db_path)
    return True


def require_role(user_obj, role):
   
    
    if not user_obj:
        raise ValueError("No user provided")
    if user_obj.get("role") != role:
        raise PermissionError(f"User must have role '{role}'")

def list_students_of_teacher(teacher_id, db_path="db.json"):
    
    
    db = load_db(db_path)
    return [u for u in db["users"] if u.get("role") == "student" and u.get("advisor_id") == teacher_id]


def change_advisor(student_id, new_teacher_id, db_path="db.json", changed_by=None):
    import datetime
    db = load_db(db_path)

    student = get_user_by_id(student_id, db_path)
    teacher = get_user_by_id(new_teacher_id, db_path)

    if not student or student.get("role") != "student":
        raise ValueError("Student not found.")
    if not teacher or teacher.get("role") != "teacher":
        raise ValueError("Teacher not found.")

    current_advisor = student.get("advisor_id")
    if current_advisor == new_teacher_id:
        return True  # no-op

    # prevent change after defense date
    if student.get("defense_date"):
        defense_date = datetime.datetime.strptime(student["defense_date"], "%Y-%m-%d").date()
        if datetime.date.today() >= defense_date:
            raise ValueError("after defense date you cant change teacher")

    # check remaining advisee slots (exclude this student from count)
    advisee_count = sum(
        1 for u in db.get("users", [])
        if u.get("role") == "student" and u.get("advisor_id") == new_teacher_id and u.get("id") != student_id
    )
    advisee_capacity = int(teacher.get("advisee_capacity", 5))
    if advisee_count >= advisee_capacity:
        raise ValueError(f"Teacher id {new_teacher_id} has no remaining advisee slots (used {advisee_count} / cap {advisee_capacity}).")

    # apply change and record history
    changed_at = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    history_entry = {
        "old_advisor": current_advisor,
        "new_advisor": new_teacher_id,
        "changed_by": changed_by,
        "changed_at": changed_at
    }

    for u in db["users"]:
        if u["id"] == student_id:
            u["advisor_id"] = new_teacher_id
            hist = u.get("advisor_history")
            if not isinstance(hist, list):
                u["advisor_history"] = []
                hist = u["advisor_history"]
            hist.append(history_entry)
            break

    save_db(db, db_path)
    return True

"""Several active students under advisor teacher"""
def count_advisees(teacher_id, db_path="db.json"):
    db = load_db(db_path)
    return sum(1 for u in db.get("users", []) if u.get("role") == "student" and u.get("advisor_id") == teacher_id)

"""Number of remaining capacities of advisor teacher"""
def get_remaining_advisee_slots(teacher_id, db_path="db.json"):
    teacher = get_user_by_id(teacher_id, db_path)
    if not teacher:
        raise ValueError("Teacher not found")
    cap = teacher.get("advisee_capacity", 5)  
    used = count_advisees(teacher_id, db_path)
    return cap - used

def set_teacher_capacity(teacher_id, advisee_capacity=None, jury_capacity=None, db_path="db.json"):
    db = load_db(db_path)
    for u in db.get("users", []):
        if u.get("id") == teacher_id and u.get("role") == "teacher":
            if advisee_capacity is not None:
                u["advisee_capacity"] = int(advisee_capacity)
            if jury_capacity is not None:
                u["jury_capacity"] = int(jury_capacity)
            save_db(db, db_path)
            return True
    return False


if __name__ == "__main__":
    from database import reset_db
    reset_db()

    print("=== Add teacher and students (with passwords) ===")
    tid = add_user("Dr.Rasooli", "teacher", password="TeachPass123")
    sid = add_user("Amir Mohamad Davoudi", "student", password="S1mpl3Pass!", advisor_id=tid, defense_date="2025-09-10")
    sid2 = add_user("Karim Qasemi", "student", password="AnotherPass", advisor_id=tid, defense_date="2025-09-10")
    sid3 = add_user("Mohsen Mohamadi", "student", password="Pass3", advisor_id=tid, defense_date="2025-09-15")

    print("Users after add:")
    for u in list_users():
        print(u)

    
    print("\n=== Authenticate Amir with correct password ===")
    user = authenticate_user("Amir Mohamad Davoudi", "S1mpl3Pass!")
    print("Auth success:", bool(user), "User id:", user["id"] if user else None)

   
    print("\n=== Change password for Amir ===")
    try:
        change_password(sid, "S1mpl3Pass!", "NewStrongPass!")
        print("Password changed successfully")
    except Exception as e:
        print("Password change failed:", e)

    
    print("\n=== Authenticate with new password ===")
    user = authenticate_user(sid, "NewStrongPass!")
    print("Auth success:", bool(user), "User id:", user["id"] if user else None)


    print("\n=== Students of teacher id", tid, "===")
    studs = list_students_of_teacher(tid)
    for s in studs:
        print(s["id"], s["name"])


