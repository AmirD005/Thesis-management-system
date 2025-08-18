import json
import traceback

from database import load_db, save_db
from user_manager import add_user, list_users, get_user_by_id, change_advisor, set_teacher_capacity
from file_manager import register_file, list_files, get_file_by_id, find_files, delete_file
from message_system import send_message, list_messages
from defense_manager import record_defense, list_defenses, get_defense_by_id, update_defense
from report_generator import generate_teacher_report, generate_student_report, generate_overall_report, report_to_text, export_report

DB_DEFAULT = "db.json"


def _print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _input_int(prompt, allow_empty=False):
    v = input(prompt).strip()
    if v == "" and allow_empty:
        return None
    try:
        return int(v)
    except Exception:
        print("invalid integer")
        return _input_int(prompt, allow_empty=allow_empty)


def pause():
    input("\nPress Enter to continue...")


def show_users():
    users = list_users(db_path=DB_DEFAULT)
    _print_json(users)
    pause()


def get_user():
    uid = _input_int("user id: ")
    u = get_user_by_id(uid, db_path=DB_DEFAULT)
    _print_json(u)
    pause()


def create_user():
    name = input("name: ").strip()
    role = input("role (student/teacher): ").strip()
    password = input("password: ").strip()
    advisor = None
    defense_date = None
    advisee_capacity = None
    jury_capacity = None
    if role == "student":
        aid = input("advisor id (enter for none): ").strip()
        advisor = int(aid) if aid else None
        dd = input("defense_date (YYYY-MM-DD) (enter for none): ").strip()
        defense_date = dd if dd else None
    else:
        ac = input("advisee_capacity (enter for default 5): ").strip()
        jc = input("jury_capacity (enter for default 10): ").strip()
        advisee_capacity = int(ac) if ac else None
        jury_capacity = int(jc) if jc else None
    uid = add_user(name, role, password, advisor_id=advisor, defense_date=defense_date,
                   advisee_capacity=advisee_capacity, jury_capacity=jury_capacity, db_path=DB_DEFAULT)
    print("created user id:", uid)
    pause()


def change_user_advisor():
    sid = _input_int("student id: ")
    tid = _input_int("new teacher id: ")
    changed_by = _input_int("changed by (admin id) (enter for none): ", allow_empty=True)
    change_advisor(sid, tid, db_path=DB_DEFAULT)
    print("advisor changed")
    pause()


def set_capacity():
    tid = _input_int("teacher id: ")
    ac = input("advisee_capacity (enter to skip): ").strip()
    jc = input("jury_capacity (enter to skip): ").strip()
    advisee_capacity = int(ac) if ac else None
    jury_capacity = int(jc) if jc else None
    set_teacher_capacity(tid, advisee_capacity=advisee_capacity, jury_capacity=jury_capacity, db_path=DB_DEFAULT)
    print("capacities updated")
    pause()


def show_files():
    files = list_files(db_path=DB_DEFAULT)
    _print_json(files)
    pause()


def register_file_interactive():
    path = input("file path: ").strip()
    ft = input("file type (pdf/jpg): ").strip()
    desc = input("description (optional): ").strip()
    uploader = input("uploader id (enter for none): ").strip()
    uploader_id = int(uploader) if uploader else None
    uploads_dir = input("uploads dir (enter for default behavior): ").strip() or None
    fid = register_file(path, ft, description=desc, uploader_id=uploader_id, db_path=DB_DEFAULT, uploads_dir=uploads_dir)
    print("registered file id:", fid)
    pause()


def find_files_interactive():
    ft = input("file type filter (pdf/jpg or enter): ").strip() or None
    uid = input("uploader id filter (enter for none): ").strip()
    uid = int(uid) if uid else None
    namec = input("original name contains (enter for none): ").strip() or None
    res = find_files(db_path=DB_DEFAULT, file_type=ft, uploader_id=uid, original_name_contains=namec)
    _print_json(res)
    pause()


def delete_file_interactive():
    fid = _input_int("file id to delete: ")
    remove = input("also remove physical file? (y/N): ").strip().lower() == "y"
    delete_file(fid, db_path=DB_DEFAULT, remove_file=remove)
    print("deleted (or marked)")
    pause()


def send_message_interactive():
    sid = _input_int("sender id: ")
    rid = _input_int("receiver id: ")
    text = input("text: ").strip()
    mid = send_message(sid, rid, text, db_path=DB_DEFAULT)
    print("message id:", mid)
    pause()


def list_messages_interactive():
    uid = _input_int("user id: ")
    lim = input("limit (enter for none): ").strip()
    lim = int(lim) if lim else None
    msgs = list_messages(uid, db_path=DB_DEFAULT, limit=lim)
    _print_json(msgs)
    pause()


def show_defenses():
    ds = list_defenses(db_path=DB_DEFAULT)
    _print_json(ds)
    pause()


def record_defense_interactive():
    sid = _input_int("student id: ")
    date = input("date (YYYY-MM-DD): ").strip()
    committee = input("committee members (space-separated ids or names): ").strip().split()
    cm = []
    for x in committee:
        try:
            cm.append(int(x))
        except Exception:
            cm.append(x)
    final_score = input("final_score (enter for none): ").strip()
    final_score = float(final_score) if final_score else None
    notes = input("notes (enter for none): ").strip() or None
    recorded_by = input("recorded_by id (enter for none): ").strip()
    recorded_by = int(recorded_by) if recorded_by else None
    rec = record_defense(sid, date, cm, final_score, notes=notes, recorded_by=recorded_by, db_path=DB_DEFAULT)
    _print_json(rec)
    pause()


def update_defense_interactive():
    did = _input_int("defense id: ")
    fs = input("final_score (enter to skip): ").strip()
    fs = float(fs) if fs else None
    notes = input("notes (enter to skip): ").strip() or None
    cm_raw = input("committee members (space-separated ids or names) (enter to skip): ").strip()
    cm = None
    if cm_raw:
        cm = []
        for x in cm_raw.split():
            try:
                cm.append(int(x))
            except Exception:
                cm.append(x)
    upd = update_defense(did, final_score=fs, notes=notes, committee_members=cm, db_path=DB_DEFAULT)
    _print_json(upd)
    pause()


def teacher_report_interactive():
    tid = _input_int("teacher id: ")
    rpt = generate_teacher_report(tid, db_path=DB_DEFAULT)
    print(report_to_text(rpt))
    out = input("save to file? (enter path or leave empty): ").strip()
    if out:
        export_report(rpt, format="text", out_path=out) if False else open(out, "w", encoding="utf-8").write(report_to_text(rpt))
        print("written to", out)
    pause()


def student_report_interactive():
    sid = _input_int("student id: ")
    rpt = generate_student_report(sid, db_path=DB_DEFAULT)
    print(report_to_text(rpt))
    out = input("save to file? (enter path or leave empty): ").strip()
    if out:
        open(out, "w", encoding="utf-8").write(report_to_text(rpt))
        print("written to", out)
    pause()


def overall_report_interactive():
    rpt = generate_overall_report(db_path=DB_DEFAULT)
    print(report_to_text(rpt))
    out = input("save to file? (enter path or leave empty): ").strip()
    if out:
        open(out, "w", encoding="utf-8").write(report_to_text(rpt))
        print("written to", out)
    pause()


def main():
    while True:
        try:
            print("\n=== Project Interactive Menu ===")
            print("1) list users")
            print("2) get user by id")
            print("3) add user")
            print("4) change student's advisor")
            print("5) set teacher capacities")
            print("6) list files")
            print("7) register file")
            print("8) find files")
            print("9) delete file")
            print("10) send message")
            print("11) list messages for user")
            print("12) list defenses")
            print("13) record defense")
            print("14) update defense")
            print("15) teacher report (text)")
            print("16) student report (text)")
            print("17) overall report (text)")
            print("0) exit")
            choice = input("choose: ").strip()
            if choice == "1":
                show_users()
            elif choice == "2":
                get_user()
            elif choice == "3":
                create_user()
            elif choice == "4":
                change_user_advisor()
            elif choice == "5":
                set_capacity()
            elif choice == "6":
                show_files()
            elif choice == "7":
                register_file_interactive()
            elif choice == "8":
                find_files_interactive()
            elif choice == "9":
                delete_file_interactive()
            elif choice == "10":
                send_message_interactive()
            elif choice == "11":
                list_messages_interactive()
            elif choice == "12":
                show_defenses()
            elif choice == "13":
                record_defense_interactive()
            elif choice == "14":
                update_defense_interactive()
            elif choice == "15":
                teacher_report_interactive()
            elif choice == "16":
                student_report_interactive()
            elif choice == "17":
                overall_report_interactive()
            elif choice == "0":
                print("bye")
                break
            else:
                print("unknown choice")
        except Exception as e:
            print("ERROR:", str(e))
            traceback.print_exc()
            pause()


if __name__ == "__main__":
    main()
