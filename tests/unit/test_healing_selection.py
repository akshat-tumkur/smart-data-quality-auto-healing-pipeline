import pandas as pd

from auto_healing.base_healer import BaseHealer
from auto_healing.healer_manager import HealerManager
from auto_healing.healing_result import HealingResult
from validation.validation_result import ValidationResult


class RecordingHealer(BaseHealer):
    def __init__(self, name, validation_types):
        self.display_name = name
        self.validation_types = frozenset(validation_types)
        self.calls = 0

    def heal(self, dataframe):
        self.calls += 1
        return dataframe, self.build_result(
            status="success",
            message="Healer executed.",
            rows_affected=1,
            execution_time=0.0,
        )


def validation_result(name, status):
    return ValidationResult(
        validator_name=name,
        status=status,
        metadata={},
    )


def test_healer_manager_runs_only_compatible_failed_validations():
    missing_healer = RecordingHealer("missing", {"missing"})
    duplicate_healer = RecordingHealer("duplicate", {"duplicate"})
    regex_healer = RecordingHealer("regex", {"regex"})
    manager = HealerManager([missing_healer, duplicate_healer, regex_healer])

    _, results = manager.heal(
        pd.DataFrame({"value": [1]}),
        validation_results=[
            validation_result("Null Validator", False),
            validation_result("Duplicate Validator", True),
        ],
    )

    assert missing_healer.calls == 1
    assert duplicate_healer.calls == 0
    assert regex_healer.calls == 0
    assert [result.healer_name for result in results] == ["missing"]


def test_healer_manager_preserves_legacy_direct_execution():
    missing_healer = RecordingHealer("missing", {"missing"})
    duplicate_healer = RecordingHealer("duplicate", {"duplicate"})
    manager = HealerManager([missing_healer, duplicate_healer])

    manager.heal(pd.DataFrame({"value": [1]}))

    assert missing_healer.calls == 1
    assert duplicate_healer.calls == 1


def test_healing_result_contains_standard_metadata_without_losing_details():
    healer = RecordingHealer("missing", {"missing"})

    _, result = healer.heal(pd.DataFrame({"value": [1]}))

    assert result.metadata["summary"]["operation"] == "missing"
    assert result.metadata["summary"]["rows_affected"] == 1
    assert result.metadata["metrics"]["rows_affected"] == 1


def test_base_healer_only_reports_success_when_action_is_truthful():
    assert BaseHealer.summarize_status(
        attempted=2,
        changed=2,
        unresolved=0,
        default_message="Repaired values." ,
    ) == ("success", "Repaired values. (2 repaired)")
    assert BaseHealer.summarize_status(
        attempted=2,
        changed=0,
        unresolved=1,
        default_message="Repaired values.",
    ) == ("failed", "Repaired values. (1 unresolved)")


def test_datatype_healer_safely_normalizes_dirty_numeric_strings_and_tracks_failures():
    df = pd.DataFrame({"salary": ["$54,764", "59,716", "39,382,547", "abc", " "]})

    _, result = __import__("auto_healing.healers.datatype_healer", fromlist=["DatatypeHealer"]).DatatypeHealer({"salary": "float"}).heal(df)

    assert result.status in {"success", "partial"}
    assert list(df["salary"][:3]) == [54764.0, 59716.0, 39382547.0]
    assert result.rows_affected == 3
    assert result.metadata["failed_conversions"]["salary"]["invalid_conversion_count"] == 2


def test_missing_value_healer_reports_effective_strategy_and_rows_vs_cells():
    df = pd.DataFrame(
        {
            "salary": [None, 100.0, None, 200.0],
            "department": [None, "IT", None, "HR"],
        }
    )

    _, result = __import__("auto_healing.healers.missing_value_healer", fromlist=["MissingValueHealer"]).MissingValueHealer(strategy="median").heal(df)

    assert result.metadata["filled_columns"]["salary"]["strategy"] == "median"
    assert result.metadata["filled_columns"]["department"]["strategy"] == "mode"
    assert result.metadata["strategy"] == "per_column"
    assert result.metadata["configured_strategy"] == "median"
    assert result.rows_affected == 2
    assert result.metadata["cells_changed"] == 4


def test_regex_healer_reports_partial_success_when_unresolved_values_remain():
    df = pd.DataFrame({"email": ["  Alice@Example.com ", "bad-email", "maria@company"]})

    _, result = __import__("auto_healing.healers.regex_healer", fromlist=["RegexHealer"]).RegexHealer(columns=["email"]).heal(df)

    assert result.status == "partial"
    assert result.rows_affected == 1
    assert result.metadata["transformed_columns"]["email"]["changed_count"] == 1
    assert result.metadata["unresolved_count"] == 2


def test_duplicate_healer_rows_affected_is_not_greater_than_dataset_rows():
    df = pd.DataFrame({"value": [1, 1, 2, 3, 3]})

    _, result = __import__("auto_healing.healers.duplicate_healer", fromlist=["DuplicateHealer"]).DuplicateHealer().heal(df)

    assert result.rows_affected <= len(df)
    assert result.rows_affected == 2
