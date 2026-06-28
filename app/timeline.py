from dataclasses import dataclass
@dataclass(frozen=True)
class TimelineEvent:date:str;title:str;category:str;entity_ids:tuple
class TimelineRegistry:
 def __init__(self):self.derivers=[]
 def register(self,fn):self.derivers.append(fn);return fn
 def derive(self,record,relationships):return sorted([e for fn in self.derivers for e in fn(record,relationships)],key=lambda e:e.date,reverse=True)
registry=TimelineRegistry()
@registry.register
def entity_dates(record,relationships):
 mapping={"birthday":"Birth","started_at":"Project started","document_date":"Document dated","acquisition_date":"Asset acquired"}
 return [TimelineEvent(record.metadata[k],v,"entity",(record.id,)) for k,v in mapping.items() if record.metadata.get(k)]
@registry.register
def relationship_dates(record,relationships):
 out=[]
 for rel in relationships:
  other=rel.other_entity(record.id);label=rel.label_from(record.id)
  if rel.started_at:out.append(TimelineEvent(rel.started_at,f"{label}: {other.title}","relationship",(record.id,other.id)))
  if rel.ended_at:out.append(TimelineEvent(rel.ended_at,f"{label} ended: {other.title}","relationship",(record.id,other.id)))
 return out
