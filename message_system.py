import datetime
from pathlib import Path
from database import load_db, save_db

MAX_MESSAGE_LENGTH = 20000

def _next_messsage_id(db):
    msgs = db.get("message") or []
    if not msgs:
        return 1
    return max(m["id"] for m in msgs) + 1

"""convert time input types to standard objects"""
def _parse_iso(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime.datetime):
        return dt
    s = str(dt).rstrip("Z")
    
    try:
       return datetime.datetime.fromisoformat(s)
    except Exception:
       try:
           return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
       except Exception:
           raise ValueError(f"Cannot parse datetime: {dt}")
         
           
def send_message(sender_id, receiver_id, text, db_path="db.json"):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text should be string and non-empty")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"its too long max character is {MAX_MESSAGE_LENGTH}")
        
    db = load_db(db_path)
    db.setdefault("messages" , [])    
    
    from user_manager import get_user_by_id
    sender = get_user_by_id(sender_id , db_path)
    receiver = get_user_by_id(receiver_id , db_path)
    
    if not sender:
        raise ValueError("sender with id {sender_id} not found")
    if not receiver:
        raise ValueError("receiver with id {receiver_id} not found")   
    if not sender.get("is_active" , True):
        raise ValueError("sender with id {sender_id} isnt active")
    if not receiver.get("is_active" , True):
        raise ValueError("receiver with id {receiver_id} isnt active")
        """now in world clock"""
    new_id = _next_messsage_id(db)
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    record = {
        "id": new_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "text": text,
        "created_at": now,
        "is_read": False,
        "read_at": None
    }
    db["message"].append(record)
    save_db(db , db_path)
    return record

def list_messages(user_id = None , db_path = "db.json" , limit = None , since = None):
    
    db = load_db(db_path)
    msgs = db("messages" , [])
    since_dt = _parse_iso(since) if since else None
    
    results = []
    for m in msgs:
        if user_id is not None:
            if not (m.get("sender_id") == user_id or m.get("receiver_id") == user_id):
                continue
        if since_dt is not None:
            m_dt = _parse_iso(m.get("craeted_at"))
            if m_dt is None or m_dt <= since_dt:
                continue
        results.append(m)
            
    results.sort(key=lambda x: _parse_iso(m.get("created_at")) or datetime.datetime.min , reverse = True)
    if limit is not None:
        return results[:limit]  
    return results     

def search_message(query , db_path = "db.json" , sender_id = None , receiver_id = None , since = None , until = None):
    
    if not isinstance(query, str) or not query.strip():
        raise ValueError("search should be non-empty string")
            
        
        """ casefold for convert lowercase"""
    q = query.strip().casefold()  
    since_dt = _parse_iso(since) if since else None
    until_dt = _parse_iso(until) if until else None
    db = load_db(db_path)
    results = []
            
    for m in db.get("message" , []):
        if sender_id is not None and m.get("sender_id") != sender_id:
            continue
        if receiver_id is not None and m.get("receiver_id") != receiver_id:
            continue    
            
        m_dt = _parse_iso(m.get("created_at"))  
        if since_dt and (m_dt is None or m_dt <= since_dt):
            continue
        if until_dt and (m_dt is None or m_dt >= until_dt):
          continue 
      
        text = (m.get("text") or "").casefold()
        if q in text:
            results.append(m)
        
        results.sort(key= lambda x: _parse_iso(x.get("created_at")) or datetime.datetime.min , reverse=True)
        return results
        
def mark_message_read(message_id , db_path = "db.json"):
    db = load_db(db_path)
    for m in db.get("message" , []):
        if m.get("id") == message_id:
            if not m.get("is_read" , False): 
                m["is_read"] = True
                m["read_at"] =  datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
                save_db(db , db_path)
            return True
        return False
"""this function didnt delete message just throw error"""
def delete_message_attempt(message_id, db_path="db.json"):     
    raise PermissionError("Messages are non-deletable in this system.")