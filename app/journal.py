from dataclasses import dataclass


@dataclass(frozen=True)
class JournalEntry:
    id: int
    entity_type: str
    entity_id: int
    body: str
    created_at: str
    updated_at: str
    archived_at: str

    @property
    def is_edited(self) -> bool:
        return self.updated_at != self.created_at

    @property
    def is_archived(self) -> bool:
        return bool(self.archived_at)
