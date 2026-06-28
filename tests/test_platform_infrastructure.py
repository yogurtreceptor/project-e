import tempfile
import unittest
from pathlib import Path
from app.db import connect, initialise_database, create_entity
from app.entities import DEFINITIONS_BY_TYPE
from app.audit import list_audit_events, get_provenance
from app.data_quality import registry, resolve_finding
from app.discovery_repository import search_entities
from app.timeline import registry as timeline_registry
class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'e.db'; initialise_database(self.path); self.c=connect(self.path)
    def tearDown(self): self.c.close(); self.tmp.cleanup()
    def test_platform_services(self):
        eid=create_entity(self.c,DEFINITIONS_BY_TYPE['person'],{'display_name':'Ada','given_name':'Ada','family_name':'Lovelace','birthday':'1815-12-10'})
        self.assertEqual('create',list_audit_events(self.c,'entity',eid)[0].event_type)
        self.assertEqual('manual',get_provenance(self.c,'entity',eid)['birthday'])
        result=search_entities(self.c,'has:birthday')[0]['entity']; self.assertEqual(eid,result.id)
        findings=registry.evaluate(self.c); self.assertTrue(any(f.category=='orphan_detection' for f in findings))
        resolve_finding(self.c,findings[0].key,'reviewed'); self.assertEqual('reviewed',next(f for f in registry.evaluate(self.c) if f.key==findings[0].key).status)
        events=timeline_registry.derive(result,[]); self.assertEqual('Birth',events[0].title); self.assertNotIn('create',[e.category for e in events])
if __name__=='__main__': unittest.main()
