from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config.config_loader import load_config
from ingestion.ingestion_manager import IngestionManager
from src.validation.validators.datatype_validator import DataTypeValidator
from src.validation.validators.duplicate_validator import DuplicateValidator
from src.validation.validators.null_validator import NullValidator
from src.validation.validators.regex_validator import RegexValidator
from src.validation.validator_manager import ValidatorManager
from src.core.pipeline import Pipeline


def load_runtime_config() -> dict:
    config = load_config(str(PROJECT_ROOT / "config" / "pipeline_config.yaml"))
    validation_rules = load_config(str(PROJECT_ROOT / "config" / "validation_rules.yaml"))
    config["validation_rules"] = validation_rules.get("validation_rules", {})
    return config


def build_validators(config) -> list:
    validation_rules = config.get("validation_rules", {})
    validators = []

    null_rules = validation_rules.get("null", {})
    if null_rules.get("enabled", False):
        validators.append(NullValidator())

    duplicate_rules = validation_rules.get("duplicate", {})
    if duplicate_rules.get("enabled", False):
        validators.append(DuplicateValidator())

    for rule in validation_rules.get("regex", []):
        column_name = rule.get("column")
        pattern = rule.get("pattern")
        if column_name and pattern:
            validators.append(RegexValidator(column_name, pattern))

    for rule in validation_rules.get("datatype", []):
        column_name = rule.get("column")
        expected_type = rule.get("type")
        if column_name and expected_type:
            validators.append(DataTypeValidator(column_name, expected_type))

    return validators


def main() -> None:
    config = load_runtime_config()

    manager = IngestionManager(config)
    data = manager.ingest()

    validators = build_validators(config)
    validator_manager = ValidatorManager(validators=validators)
    results = Pipeline(validation_manager=validator_manager).run(data)

    for result in results:
        print(result)


if __name__ == "__main__":
    main()