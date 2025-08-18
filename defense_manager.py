import datetime
from database import load_db , save_db
from pathlib import Path

def _next_defense_id(db):
    defs_ = db.get("defenses") or []
    if not defs_:
        return 1
    return max(d.get("id" , 0) for d in defs_) + 1

"""convert to datetime.date"""
def _parse_date(d):
    if d is None:
        raise ValueError("Date is required")
    if isinstance(d, datetime.date) and not isinstance(d, datetime.datetime):
        return d
    if isinstance(d,datetime.datetime):
        return d.date()
    if isinstance(d, str):
        s = d.strip()
        try:
            return datetime.date.fromisoformat(s)
        except Exception:
            try:
                return datetime.datetime.strptime(s, "%Y-%m-%d").date()
            except Exception:
                raise ValueError(f"Cannot parse date '{d}'. Expected YYYY-MM-DD.")
    raise ValueError(f"Unsupported date type: {type(d)}")
        
    
    """normalize committee members for database"""
def _normalize_committee(members, db_path="db.json"):
    if not isinstance(members, (list, tuple)):
        raise ValueError("committee_members must be a list")
    normalized = []
    from user_manager import get_user_by_id
    for item in members:
        if isinstance(item, (int)):
            u = get_user_by_id(item , db_path = "db.json")
            if not u:
                raise ValueError(f"Committee member with id {item} not found.")
            if u.get("role") != "teacher":
                raise ValueError(f"Committee member id {item} is not a teacher.")
            normalized.append({"id": u["id"],
                               "name": u.get("name"),
                               "role": "teacher"})
                
        elif isinstance(item, str):
            name = item.strip()
            if not name:
                continue
            normalized.append({"id": None,
                               "name": name,
                               "role": "external"})    
                
        elif isinstance(item, dict):
            if "id" in item and item["id"] is not None:
                uid = item["id"]
                u = get_user_by_id(uid, db_path)
                if not u:
                    raise ValueError(f"Committee member with id {uid} not found.")
                if u.get("role") != "teacher":
                    raise ValueError(f"Committee member id {uid} is not a teacher.")
                normalized.append({
                    "id": u["id"],
                    "name": u.get("name"),
                    "role": "teacher"
                })
            
            elif "name" in item:
                name = str(item.get("name", "")).strip()
                role = item.get("role", "external")
                normalized.append({
                    "id": None,
                    "name": name,
                    "role": role
                })
            else:
                raise ValueError("Committee member dict must contain 'id' or 'name'.")
        else:
            raise ValueError(f"Unsupported committee member type: {type(item)}")    
                
                
    has_teacher = any(m.get("role") == "teacher" for m in normalized)
    if not has_teacher:
        raise ValueError("Committee must include at least one member with role 'teacher'.")
    return normalized                

def count_jury_assignments(teacher_id , db_path = "db.json"):
    db = load_db(db_path)
    cnt = 0
    for d in db.get("defenses" , []):
        for m in d.get("committee_members" , []):
            if m.get("id") == teacher_id and m.get("role") == "teacher":
                cnt +=1
    return cnt
"""new defense for student"""
def record_defense (student_id , date , committee_members , final_score , notes = None , recorded_by=None, db_path="db.json"):
    db = load_db(db_path)
    db.setdefault("defenses" , [])
    
    from user_manager import get_user_by_id
    student = get_user_by_id(student_id , db_path)
    
    if not student or student.get("role") != "student":
        raise ValueError(f"Student with id {student_id} not found or not a student.")

    for d in db.get("defenses" , []):
        if d.get("student_id") == student_id:
            raise ValueError(f"A defense record already exists for student id {student_id} (id={d.get('id')}).")    

    defense_date = _parse_date(date)
    """conver id/string/dict to list of it"""
    normalized_committee = _normalize_committee(committee_members, db_path=db_path)
    
    teachers_in_new = {}
    for cm in normalized_committee:
        if cm.get("role") == "teacher" and cm.get("id") is not None:
            teachers_in_new[cm["id"]] = teachers_in_new.get(cm["id"] , 0) + 1

    for tid,add_count in teachers_in_new.items():
        teacher = get_user_by_id(tid , db_path) 
        if not teacher:
            raise ValueError(f"Teacher id {tid} not found.")
        current = count_jury_assignments(tid, db_path)   
        cap = int(teacher.get("jury_capacity" , 10))         
        if current + add_count > cap:
            raise ValueError(f"Teacher id {tid} would exceed jury capacity ({current} + {add_count} > {cap}).")
                    
        if final_score is not None:
            try:
                fs = float(final_score)
            except Exception:
                raise ValueError("final score must be a number")
            if fs < 0 or fs > 20:
                raise ValueError("final score must be between 0 and 20")
            final_score = fs
        else:
            final_score = None

        if recorded_by is not None:
            rb = get_user_by_id(recorded_by , db_path)
            if not rb:
               raise ValueError(f"Recorded by user id {recorded_by} not found.") 

        new_id = _next_defense_id(db)
        now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        record = {
            "id": new_id,
            "student_id": student_id,
            "date": defense_date.isoformat(),
            "committee_members": normalized_committee,
            "final_score": final_score,
            "notes": notes,
            "recorded_by": recorded_by,
            "recorded_at": now
        }
        
        db["defenses"].append(record)
        save_db(db, db_path)
        return record


def list_defenses(db_path="db.json"):
    db = load_db(db_path)
    defs_ = db.get("defenses" , [])
    def _key_fn(d):
        try:
            return _parse_date(d.get("date"))
        except Exception:
            return datetime.date.min
    return sorted(defs_, key=_key_fn, reverse=True)
        
def get_defense_by_id (defense_id , db_path = "db.json"):
    db = load_db(db_path)
    for d in db.get("defenses" , []):
        if d.get("id") == defense_id:
            return d
        return None

def list_defenses_by_student(student_id, db_path="db.json"):
    db = load_db(db_path)
    return [d for d in db.get("defenses", []) if d.get("student_id") == student_id]

"""edit defense for student"""
def update_defense(defense_id, final_score=None, notes=None, committee_members=None, db_path="db.json"):
    db = load_db(db_path)
    found = None
    for d in db.get("defenses" , []):
        if d.get("id") == defense_id:
            found = d
            break
    if not found:
        raise ValueError(f"Defense with id {defense_id} not found.")
        
    if committee_members is not None:
        normalize = _normalize_committee(committee_members , db_path = db_path)
        teachers_in_new = {}
        for cm in normalize:
            if cm.get("role") == "teacher" and cm.get("id") is not None:
                teachers_in_new[cm["id"]] = teachers_in_new.get(cm["id"], 0) + 1        
        
        from user_manager import get_user_by_id
        for tid,add_count in teachers_in_new.items():
            teacher = get_user_by_id(tid,db_path)
            if not teacher:
                raise ValueError(f"Teacher id {tid} not found.")
            current = count_jury_assignments(tid , db_path) 
            cap = int(teacher.get("jury_capacity", 10))
            if current + add_count > cap:
                raise ValueError(f"Teacher id {tid} would exceed jury capacity ({current} + {add_count} > {cap}).")
            found["committee_members"] = normalize
        if final_score is not None:
            try:
                fs = float(final_score)
            except Exception:
                if fs < 0 or fs > 20:
                    raise ValueError("final score must be between 0 and 20")
                found["final_score"] = fs
            if notes is not None:
                found["notes"]= notes
            save_db(db , db_path)
            return found