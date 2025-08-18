import datetime
import json
from database import load_db

def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def generate_teacher_report(teacher_id, db_path="db.json"):
    db = load_db(db_path)
    from user_manager import get_user_by_id
    
    teacher = get_user_by_id(teacher_id , db_path)
    if not teacher or teacher.get("role") != "teacher":
        raise ValueError("teacher not found")
        
    users = db.get("users" , [])
    defenses = db.get("defenses" , [])
    advisees = [u for u in users if u.get("role") == "student" 
                and u.get("advisor_id") == teacher_id]
    
    jury_assignments = []
    
    for d in defenses:
        for m in d.get("committee_members" , []):
            jury_assignments.append({"defense_id" : d.get("id"),
                             "student_id" : d.get("student_id"),
                             "date" : d.get("date"),
                             "final_score" : d.get("final_score")})
    """defenses list for students"""
    supervised_defenses = [d for d in defenses if any(u.get("id") == d.get("student_id") and u.get("advisor_id") == teacher_id for u in users)]
    """values of final score"""
    scores = [d.get("final_score") for d in supervised_defenses if isinstance(d.get("final_score"), (int, float))]
    """average of scores"""
    avg_score = (sum(scores) / len(scores)) if scores else None
    """capacity of teacher for advise"""
    cap = int(teacher.get("advisee_capacity", 5)) 
    """number of used for advise"""      
    used = len(advisees)
    """remaining number for advise"""
    remaining = cap - used
    
    return {
        "generated_at": _now_iso(),
        "type": "teacher_report",
        "teacher": {"id": teacher["id"], "name": teacher.get("name")},
        "advisee_capacity": cap,
        "advisees_count": used,
        "advisees_remaining": remaining,
        "advisees": [
            {"id": s["id"], "name": s.get("name"), "defense_date": s.get("defense_date")}
            for s in advisees
        ],
        "jury_assignments_count": len(jury_assignments),
        "jury_assignments": jury_assignments,
        "supervised_defenses_count": len(supervised_defenses),
        "supervised_avg_score": avg_score
    }

def generate_student_report(student_id, db_path="db.json"):
    db = load_db(db_path)
    from user_manager import get_user_by_id
    student = get_user_by_id(student_id, db_path)

    if not student or student.get("role") != "student":
        raise ValueError("student not found")
        
        advisor = None
        if student.get("advisor_id") is not None:
            advisor = get_user_by_id(student.get("advisor_id"), db_path)
        
        defense_record = next((d for d in db.get("defenses", []) if d.get("student_id") == student_id), None)
        student_files = [f for f in db.get("files", []) if f.get("uploader_id") == student_id]

        return {
        "generated_at": _now_iso(),
        "type": "student_report",
        "student": {"id": student["id"], "name": student.get("name")},
        "advisor": {"id": advisor.get("id"), "name": advisor.get("name")} if advisor else None,
        "defense": defense_record,
        "files": [{"id": f.get("id"), "original_name": f.get("original_name"), "file_type": f.get("file_type")} for f in student_files]
    }

def generate_overall_report(db_path="db.json"):
    db = load_db(db_path)
    users = db.get("users", [])
    defenses = db.get("defenses", [])
    total_users = len(users)
    total_teachers = sum(1 for u in users if u.get("role") == "teacher")
    total_students = sum(1 for u in users if u.get("role") == "student")
    total_defenses = len(defenses)
    scores = [d.get("final_score") for d in defenses if isinstance(d.get("final_score"), (int, float))]
    avg_score = (sum(scores) / len(scores)) if scores else None
    
    teacher_counts = {}
    for d in defenses:
        for m in d.get("committee_members"):
            if m.get("role") == "teacher" and m.get("id") is not None:
                teacher_counts[m["id"]] = teacher_counts.get(m["id"], 0) + 1
    top_teachers = sorted(teacher_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "generated_at": _now_iso(),
        "type": "overall_report",
        "total_users": total_users,
        "total_teachers": total_teachers,
        "total_students": total_students,
        "total_defenses": total_defenses,
        "average_defense_score": avg_score,
        "top_teachers_by_jury_assignments": [{"teacher_id": t, "assignments": c} for t, c in top_teachers]
    }
"""convert dictionary report to string"""
def report_to_text(report):
    t = []
    typ = report.get("type" , "report")
    t.append(f"report typ: {typ}")
    t.append(f"generated at: {report.get('generated_at')}")
    
    if typ == "teacher_report":
        t.append(f"teacher: {report['teacher']['name']} id: {report['teacher']['id']}")
        t.append(f"Advisees: {report.get('advisees_count')} (remaining: {report.get('advisees_remaining')})")
       
        for s in report.get("advisees", []):
            t.append(f" - {s.get('id')}: {s.get('name')} (defense_date: {s.get('defense_date')})")

        t.append(f"Jury assignments: {report.get('jury_assignments_count')}")
        for j in report.get("jury_assignments", []):
            t.append(f" - defense {j.get('defense_id')} student {j.get('student_id')} date {j.get('date')} score {j.get('final_score')}")
        t.append(f"Supervised defenses: {report.get('supervised_defenses_count')}")
        t.append(f"Supervised average score: {report.get('supervised_avg_score')}")
    elif typ == "student_report":
        st = report.get("student", {})
        t.append(f"Student: {st.get('name')} (id: {st.get('id')})")
        adv = report.get("advisor")
        if adv:
            t.append(f"Advisor: {adv.get('name')} (id: {adv.get('id')})")
        if report.get("defense"):
            d = report.get("defense")
            t.append(f"Defense id: {d.get('id')} date: {d.get('date')} final_score: {d.get('final_score')}")
        else:
            t.append("No defense recorded.")
        t.append("Files:")
        for f in report.get("files", []):
            t.append(f" - {f.get('id')} {f.get('original_name')} ({f.get('file_type')})")
    else:
        t.append(json.dumps(report, ensure_ascii=False, indent=2))
    return "\n".join(t)
        
def export_report(report, format="json", out_path=None):
    fmt = format.lower()
    if fmt == "json":
        s = json.dumps(report, ensure_ascii=False, indent=4)
    elif fmt == "text":
        s = report_to_text(report)
    else:
        raise ValueError("unsupported format, use 'json' or 'text'")

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(s)
        return out_path
    return s
        