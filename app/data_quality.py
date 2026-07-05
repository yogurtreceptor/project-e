import hashlib
from dataclasses import dataclass
from app.audit import record_audit_event
from app.db_support import utc_now
from app.entity_repository import list_all_entities
from app.integrity import audit_relationships
@dataclass(frozen=True)
class Finding:
 key:str;category:str;severity:str;explanation:str;entity_ids:tuple;relationship_ids:tuple;status:str;actions:tuple
class RuleRegistry:
 def __init__(self):self.rules=[]
 def register(self,fn):self.rules.append(fn);return fn
 def evaluate(self,c):
  states={r[0]:r[1] for r in c.execute("SELECT finding_key,status FROM data_quality_finding_state")}
  findings=[f for rule in self.rules for f in rule(c)]
  return [Finding(f.key,f.category,f.severity,f.explanation,f.entity_ids,f.relationship_ids,states.get(f.key,"open"),f.actions) for f in findings]
registry=RuleRegistry()
def finding(category,severity,text,entities=(),relationships=(),actions=("review","open_record","ignore","mark_intentional")):
 raw=f"{category}|{entities}|{relationships}|{text}";return Finding(hashlib.sha256(raw.encode()).hexdigest()[:24],category,severity,text,tuple(entities),tuple(relationships),"open",actions)
@registry.register
def missing_and_coverage(c):
 out=[]
 for r in list_all_entities(c):
  important=[f.name for f in r.definition.fields if f.editable][:3];missing=[x for x in important if not r.metadata.get(x)]
  if missing:out.append(finding("missing_information","warning",f"{r.title} is missing: {', '.join(missing)}.",(r.id,)))
  filled=sum(bool(r.metadata.get(x)) for x in important);score=round(100*filled/max(1,len(important)))
  if score<50:out.append(finding("coverage","info",f"{r.title} completeness is {score}%.",(r.id,)))
 return out
@registry.register
def date_sanity(c):
 out=[]
 for r in list_all_entities(c):
  for name,value in r.metadata.items():
   if (name.endswith("date") or name in {"birthday","started_at","ended_at"}) and name!="expiry_date" and value>utc_now()[:10]:out.append(finding("date_sanity","warning",f"{r.title} has a future {name}.",(r.id,)))
 return out
@registry.register
def graph_health(c):return [finding("graph_consistency",w.severity,w.message,w.entity_ids,w.relationship_ids) for w in audit_relationships(c)]
@registry.register
def orphans(c):
 return [finding("orphan_detection","info",f"{r.title} has no relationships.",(r.id,)) for r in list_all_entities(c) if not c.execute("SELECT 1 FROM relationships WHERE source_entity_id=? OR target_entity_id=?",(r.id,r.id)).fetchone()]
def resolve_finding(c,key,status,notes=""):
 if status not in {"reviewed","ignored","intentional","resolved","accepted","rejected"}:raise ValueError("Invalid finding status.")
 c.execute("INSERT INTO data_quality_finding_state VALUES(?,?,?,?) ON CONFLICT(finding_key) DO UPDATE SET status=excluded.status,notes=excluded.notes,updated_at=excluded.updated_at",(key,status,notes,utc_now()))
 record_audit_event(c,"validation",[("finding",0)],after={"finding_key":key,"status":status},notes=notes);c.commit()
