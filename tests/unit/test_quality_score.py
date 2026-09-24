from types import SimpleNamespace

from quality.quality_score import QualityScoreCalculator
from validation.validation_result import ValidationResult


def profile(rows=10, columns=2, missing=2, duplicates=1):
    return SimpleNamespace(
        row_count=rows,
        column_count=columns,
        total_missing_values=missing,
        duplicate_rows=duplicates,
    )


def result(status, rows_affected):
    return ValidationResult(
        validator_name="Test Validator",
        status=status,
        rows_affected=rows_affected,
    )


def indexed_result(status, rows_affected, indices):
    return ValidationResult(
        validator_name="Indexed Validator",
        status=status,
        rows_affected=rows_affected,
        metadata={"invalid_indices": indices},
    )


def test_quality_score_calculates_weighted_components():
    calculator = QualityScoreCalculator(
        {
            "enabled": True,
            "weights": {
                "completeness": 0.5,
                "validity": 0.25,
                "uniqueness": 0.25,
            },
        }
    )

    score = calculator.calculate(profile(), [result(False, 2)])

    assert score.enabled is True
    assert score.components == {
        "completeness": 90.0,
        "validity": 80.0,
        "uniqueness": 90.0,
    }
    assert score.score == 87.5
    assert sum(score.weights.values()) == 1.0


def test_quality_score_disabled_is_serializable_and_empty():
    score = QualityScoreCalculator().calculate(profile(), [])

    assert score.enabled is False
    assert score.score is None
    assert score.to_dict["enabled"] is False


def test_quality_score_compare_returns_delta():
    calculator = QualityScoreCalculator({"enabled": True})
    initial = calculator.calculate(profile(missing=10, duplicates=2), [result(False, 5)])
    final = calculator.calculate(profile(missing=0, duplicates=0), [result(True, 0)])

    comparison = calculator.compare(initial, final)

    assert comparison["enabled"] is True
    assert comparison["delta"] > 0
    assert comparison["initial"]["score"] == initial.score
    assert comparison["final"]["score"] == final.score


def test_quality_score_does_not_double_count_overlapping_invalid_rows():
    calculator = QualityScoreCalculator({"enabled": True})

    score = calculator.calculate(
        profile(rows=4, columns=1, missing=0, duplicates=0),
        [
            indexed_result(False, 2, [0, 1]),
            indexed_result(False, 2, [1, 2]),
        ],
    )

    assert score.components["validity"] == 25.0


def test_quality_score_uses_duplicate_validator_subset_metadata():
    calculator = QualityScoreCalculator({"enabled": True})
    duplicate_result = ValidationResult(
        validator_name="Duplicate Validator",
        status=False,
        rows_affected=2,
        metadata={
            "subset": ["email"],
            "duplicate_indices": [0, 1],
        },
    )

    score = calculator.calculate(
        profile(rows=3, columns=2, missing=0, duplicates=0),
        [duplicate_result],
    )

    assert score.metrics["duplicate_rows"] == 2
    assert score.components["uniqueness"] == 33.3333