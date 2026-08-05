from pathlib import Path
import tempfile
import unittest

from app.audit import list_audit_events
from app.db import (
    connect,
    create_mobility_profile,
    create_routing_policy,
    get_mobility_profile,
    get_routing_policy,
    list_mobility_profiles,
    list_routing_policies,
    update_mobility_profile,
    update_routing_policy,
    validate_stored_journey_configuration,
)
from app.journey_contract import JourneyMode, PolicyKind
from tests.database_test_support import initialise_test_database


class JourneyConfigurationPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "journey-config.sqlite3"
        initialise_test_database(self.database_path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_profile_and_policy_keep_stable_user_owned_identity_across_revisions(self) -> None:
        with connect(self.database_path) as connection:
            profile = create_mobility_profile(
                connection,
                "fictional-regular-walk",
                "Fictional regular walk",
                JourneyMode.WALK,
                {
                    "speed_metres_per_second": 1.2,
                    "source": "fictional repeated measurement",
                    "effective_date": "2026-08-05",
                },
            )
            policy = create_routing_policy(
                connection,
                "fictional-avoid-stairs",
                "Fictional avoid stairs",
                PolicyKind.SOFT_AVOIDANCE,
                {"modes": ["walk"], "attribute": "stairs"},
            )
            revised_profile = update_mobility_profile(
                connection,
                profile.profile_key,
                display_name=profile.display_name,
                primary_mode=profile.primary_mode,
                definition={
                    "speed_metres_per_second": 1.3,
                    "source": "fictional repeated measurement",
                    "effective_date": "2026-08-06",
                },
            )
            revised_policy = update_routing_policy(
                connection,
                policy.policy_key,
                display_name=policy.display_name,
                kind=PolicyKind.HARD_EXCLUSION,
                definition={"modes": ["walk"], "attribute": "stairs"},
                is_enabled=False,
            )
            errors = validate_stored_journey_configuration(connection)
            profile_audit = list_audit_events(
                connection, "mobility_profile", profile.id
            )
            policy_audit = list_audit_events(
                connection, "routing_policy", policy.id
            )

        self.assertEqual(profile.id, revised_profile.id)
        self.assertEqual(profile.profile_key, revised_profile.profile_key)
        self.assertEqual(2, revised_profile.revision)
        self.assertEqual(1.3, revised_profile.definition["speed_metres_per_second"])
        self.assertEqual(policy.id, revised_policy.id)
        self.assertEqual(policy.policy_key, revised_policy.policy_key)
        self.assertEqual(2, revised_policy.revision)
        self.assertFalse(revised_policy.is_enabled)
        self.assertEqual([], errors)
        self.assertEqual(["edit", "create"], [item.event_type for item in profile_audit])
        self.assertEqual(["edit", "create"], [item.event_type for item in policy_audit])

    def test_configuration_is_deterministic_and_rejects_provider_owned_or_invalid_values(self) -> None:
        with connect(self.database_path) as connection:
            profile = create_mobility_profile(
                connection,
                "fictional-walk",
                "Fictional walk",
                JourneyMode.WALK,
                {"b": 2, "a": 1},
            )
            policy = create_routing_policy(
                connection,
                "fictional-policy",
                "Fictional policy",
                PolicyKind.PREFERENCE,
                {"modes": ["walk"], "weights": {"shade": 2}},
            )
            profile_json = connection.execute(
                "SELECT definition_json FROM mobility_profiles WHERE id=?",
                (profile.id,),
            ).fetchone()[0]
            policy_json = connection.execute(
                "SELECT definition_json FROM routing_policies WHERE id=?",
                (policy.id,),
            ).fetchone()[0]
            with self.assertRaisesRegex(ValueError, "positive number"):
                create_mobility_profile(
                    connection,
                    "invalid-distance",
                    "Invalid distance",
                    JourneyMode.WALK,
                    {"maximum_contiguous_distance_metres": 0},
                )
            with self.assertRaisesRegex(ValueError, "unsupported journey mode"):
                create_routing_policy(
                    connection,
                    "invalid-mode",
                    "Invalid mode",
                    PolicyKind.PREFERENCE,
                    {"modes": ["provider-scooter"]},
                )

        self.assertEqual('{"a":1,"b":2}', profile_json)
        self.assertEqual(
            '{"modes":["walk"],"weights":{"shade":2}}', policy_json
        )

    def test_lists_and_lookups_return_only_canonical_configuration_database_rows(self) -> None:
        with connect(self.database_path) as connection:
            create_mobility_profile(
                connection,
                "z-profile",
                "Zulu profile",
                JourneyMode.DRIVE,
                {},
            )
            create_mobility_profile(
                connection,
                "a-profile",
                "Alpha profile",
                JourneyMode.CYCLE,
                {},
            )
            create_routing_policy(
                connection,
                "z-policy",
                "Zulu policy",
                PolicyKind.ADDED_COST,
                {},
            )
            create_routing_policy(
                connection,
                "a-policy",
                "Alpha policy",
                PolicyKind.ADDED_BUFFER,
                {},
            )

            profiles = list_mobility_profiles(connection)
            policies = list_routing_policies(connection)
            selected_profile = get_mobility_profile(connection, "a-profile")
            selected_policy = get_routing_policy(connection, "a-policy")

        self.assertEqual(["a-profile", "z-profile"], [item.profile_key for item in profiles])
        self.assertEqual(["a-policy", "z-policy"], [item.policy_key for item in policies])
        self.assertEqual(JourneyMode.CYCLE, selected_profile.primary_mode)
        self.assertEqual(PolicyKind.ADDED_BUFFER, selected_policy.kind)


if __name__ == "__main__":
    unittest.main()
