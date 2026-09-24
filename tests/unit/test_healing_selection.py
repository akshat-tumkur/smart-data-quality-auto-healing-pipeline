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
