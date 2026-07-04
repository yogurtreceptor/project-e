import shlex
from datetime import date,datetime,timedelta,timezone
class QueryRegistry:
 def __init__(self):self.filters={}
 def register(self,key,predicate):self.filters[key]=predicate
 def apply(self,c,records,query):
  terms=[]
  for token in shlex.split(query):
   key,sep,value=token.partition(":")
   if sep and key in self.filters:records=[r for r in records if self.filters[key](c,r,value)]
   else:terms.append(token)
  return records," ".join(terms)
registry=QueryRegistry()
registry.register("missing",lambda c,r,v:not(r.metadata.get(v) or getattr(r,v,"")));registry.register("has",lambda c,r,v:bool(r.metadata.get(v) or getattr(r,v,"")))
registry.register("relationship",lambda c,r,v:bool(c.execute("SELECT 1 FROM relationships x JOIN entities e ON e.id=CASE WHEN x.source_entity_id=? THEN x.target_entity_id ELSE x.source_entity_id END WHERE x.type=? AND (x.source_entity_id=? OR x.target_entity_id=?) AND e.deleted_at=''",(r.id,v,r.id,r.id)).fetchone()))
def related(kind):return lambda c,r,v:bool(c.execute("SELECT 1 FROM relationships x JOIN entities e ON e.id=CASE WHEN x.source_entity_id=? THEN x.target_entity_id ELSE x.source_entity_id END WHERE (x.source_entity_id=? OR x.target_entity_id=?) AND e.type=? AND e.deleted_at='' AND lower(e.display_name) LIKE ?",(r.id,r.id,r.id,kind,"%"+v.lower()+"%")).fetchone())
registry.register("organisation",related("organisation"));registry.register("location",related("location"))
def recent(value,spec):
 days={"last30days":30,"last7days":7}.get(spec)
 try:return bool(days and datetime.fromisoformat(value.replace("Z","+00:00"))>=datetime.now(timezone.utc)-timedelta(days=days))
 except ValueError:return False
registry.register("created",lambda c,r,v:recent(r.created_at,v));registry.register("updated",lambda c,r,v:recent(r.updated_at,v))
def birthday(r,spec):
 value=r.metadata.get("birthday","");today=date.today()
 if len(value)<10:return False
 if spec=="this-month":return value[5:7]==today.strftime("%m")
 return spec=="next30days" and any(value[5:]==(today+timedelta(days=n)).strftime("%m-%d") for n in range(31))
registry.register("birthday",lambda c,r,v:birthday(r,v))
