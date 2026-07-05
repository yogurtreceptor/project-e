from dataclasses import dataclass

from app.entities import EntityRecord
from app.relationships import RelationshipRecord


@dataclass(frozen=True)
class TimelineEvent:
    date: str
    title: str
    category: str
    entity_ids: tuple[int, ...]
    href: str = ""
    origin_type: str = ""
    origin_title: str = ""
    entity_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimelineFilters:
    entity_type: str = ""
    date_from: str = ""
    date_to: str = ""
    related_person_id: int | None = None
    related_organisation_id: int | None = None
    related_project_id: int | None = None


class TimelineRegistry:
    """Registry of canonical entity fields that represent real-world dates."""

    def __init__(self) -> None:
        self.date_fields: dict[str, str] = {}

    def register_date_field(self, field_name: str, title: str) -> None:
        self.date_fields[field_name] = title

    def derive(
        self, record: EntityRecord, relationships: list[RelationshipRecord]
    ) -> list[TimelineEvent]:
        events = self._entity_events(record, relationships)
        events.extend(
            self._relationship_event(relationship, record.id, is_end=False)
            for relationship in relationships
            if relationship.started_at
        )
        events.extend(
            self._relationship_event(relationship, record.id, is_end=True)
            for relationship in relationships
            if relationship.ended_at
        )
        return sorted(events, key=lambda event: (event.date, event.title), reverse=True)

    def derive_all(
        self,
        records: list[EntityRecord],
        relationships: list[RelationshipRecord],
        filters: TimelineFilters | None = None,
    ) -> list[TimelineEvent]:
        relationships_by_entity: dict[int, list[RelationshipRecord]] = {
            record.id: [] for record in records
        }
        for relationship in relationships:
            for entity_id in (relationship.source.id, relationship.target.id):
                if entity_id in relationships_by_entity:
                    relationships_by_entity[entity_id].append(relationship)

        events: list[TimelineEvent] = []
        for record in records:
            events.extend(self._entity_events(record, relationships_by_entity[record.id]))
        for relationship in relationships:
            if relationship.started_at:
                events.append(self._relationship_event(relationship, None, is_end=False))
            if relationship.ended_at:
                events.append(self._relationship_event(relationship, None, is_end=True))

        selected = filters or TimelineFilters()
        return sorted(
            (event for event in events if _matches(event, selected)),
            key=lambda event: (event.date, event.title, event.href),
            reverse=True,
        )

    def _entity_events(
        self, record: EntityRecord, relationships: list[RelationshipRecord]
    ) -> list[TimelineEvent]:
        associated_ids = {record.id}
        for relationship in relationships:
            associated_ids.add(relationship.other_entity(record.id).id)
        return [
            TimelineEvent(
                date=record.metadata[field_name],
                title=title,
                category="entity",
                entity_ids=tuple(sorted(associated_ids)),
                href=f"/{record.slug}/{record.id}",
                origin_type=record.type,
                origin_title=record.title,
                entity_types=(record.type,),
            )
            for field_name, title in self.date_fields.items()
            if record.metadata.get(field_name)
        ]

    @staticmethod
    def _relationship_event(
        relationship: RelationshipRecord, perspective_id: int | None, is_end: bool
    ) -> TimelineEvent:
        if perspective_id is None:
            title = relationship.type.label
            origin_title = f"{relationship.source.title} and {relationship.target.title}"
        else:
            other = relationship.other_entity(perspective_id)
            title = f"{relationship.label_from(perspective_id)}: {other.title}"
            origin_title = other.title
        if is_end:
            title = f"{title} ended"
        return TimelineEvent(
            date=relationship.ended_at if is_end else relationship.started_at,
            title=title,
            category="relationship",
            entity_ids=tuple(sorted((relationship.source.id, relationship.target.id))),
            href=f"/relationships/{relationship.id}",
            origin_type="relationship",
            origin_title=origin_title,
            entity_types=tuple(sorted({relationship.source.type, relationship.target.type})),
        )


def _matches(event: TimelineEvent, filters: TimelineFilters) -> bool:
    if filters.entity_type and filters.entity_type not in event.entity_types:
        return False
    if filters.date_from and event.date < filters.date_from:
        return False
    if filters.date_to and event.date > filters.date_to:
        return False
    related_ids = (
        filters.related_person_id,
        filters.related_organisation_id,
        filters.related_project_id,
    )
    return all(entity_id is None or entity_id in event.entity_ids for entity_id in related_ids)


registry = TimelineRegistry()
registry.register_date_field("birthday", "Birth")
registry.register_date_field("started_at", "Project started")
registry.register_date_field("target_date", "Project target date")
registry.register_date_field("ended_at", "Project ended")
registry.register_date_field("document_date", "Document dated")
registry.register_date_field("expiry_date", "Document expires")
registry.register_date_field("acquisition_date", "Asset acquired")
