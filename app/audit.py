import json
from dataclasses import dataclass
from app.db_support import utc_now
EVENT_TYPES={"create","edit","delete","restore","permanent_delete","relationship_change","inference","validation","merge","import","manual_override"}
PROVENANCE_TYPES={"manual","inferred","imported","document","contact_import","user_confirmed","unknown"}
@dataclass(frozen=True)
class AuditEvent:
    id:int; event_type:str; occurred_at:str; actor:str; notes:str; before:object; after:object; provenance:str; records:tuple
def record_audit_event(connection,event_type,records,before=None,after=None,notes="",actor="local_user",provenance="manual"):
    if event_type not in EVENT_TYPES: raise ValueError("Unknown audit event type.")
    if provenance not in PROVENANCE_TYPES: raise ValueError("Unknown provenance type.")
    cur=connection.execute("INSERT INTO audit_events(event_type,occurred_at,actor,notes,before_json,after_json,provenance) VALUES(?,?,?,?,?,?,?)",(event_type,utc_now(),actor,notes,json.dumps(before,sort_keys=True) if before is not None else "",json.dumps(after,sort_keys=True) if after is not None else "",provenance)); event_id=int(cur.lastrowid)
    connection.executemany("INSERT INTO audit_event_records VALUES(?,?,?)",[(event_id,k,i) for k,i in records]); return event_id
def list_audit_events(connection,record_kind=None,record_id=None):
    sql="SELECT DISTINCT a.* FROM audit_events a"; params=[]
    if record_kind is not None: sql+=" JOIN audit_event_records r ON r.event_id=a.id WHERE r.record_kind=? AND r.record_id=?"; params=[record_kind,record_id]
    result=[]
    for row in connection.execute(sql+" ORDER BY a.occurred_at DESC,a.id DESC",params):
        refs=tuple((r[0],r[1]) for r in connection.execute("SELECT record_kind,record_id FROM audit_event_records WHERE event_id=?",(row["id"],)))
        result.append(AuditEvent(row["id"],row["event_type"],row["occurred_at"],row["actor"],row["notes"],json.loads(row["before_json"]) if row["before_json"] else None,json.loads(row["after_json"]) if row["after_json"] else None,row["provenance"],refs))
    return result
def set_provenance(connection,kind,record_id,field_name,provenance):
    if provenance not in PROVENANCE_TYPES: raise ValueError("Unknown provenance type.")
    connection.execute("INSERT INTO provenance_metadata VALUES(?,?,?,?,?) ON CONFLICT(record_kind,record_id,field_name) DO UPDATE SET provenance=excluded.provenance,updated_at=excluded.updated_at",(kind,record_id,field_name,provenance,utc_now()))
def get_provenance(connection,kind,record_id): return {r[0]:r[1] for r in connection.execute("SELECT field_name,provenance FROM provenance_metadata WHERE record_kind=? AND record_id=?",(kind,record_id))}
