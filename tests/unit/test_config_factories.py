import yaml

from config.config_loader import ConfigLoader
from validation.validator_factory import ValidatorFactory


def test_config_loader_normalizes_dataset_and_yaml_null_key(tmp_path):
    (tmp_path / "pipeline_config.yaml").write_text(
        yaml.safe_dump(
            {
                "dataset": {
                    "path": "data/raw/example.csv",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "validation_rules.yaml").write_text(
        "validation:\n  null:\n    enabled: true\n",
        encoding="utf-8",
    )

    config = ConfigLoader(tmp_path).load()

    assert config["dataset"]["path"] == "data/raw/example.csv"
    assert config["dataset"]["delimiter"] == ","
    assert config["validation"]["null"]["enabled"] is True
    assert config["healing"]["missing"]["enabled"] is False


def test_validator_factory_resolves_enabled_plugins_and_regex_aliases():
    validators = ValidatorFactory(
        {
            "null": {"enabled": True},
            "duplicate": {"enabled": True, "subset": ["employee_id"]},
            "datatype": {
                "enabled": True,
                "columns": {"salary": "float"},
            },
            "regex": [
                {
                    "column": "email",
                    "pattern": "EMAIL",
                }
            ],
        }
    ).build()

    assert [type(validator).__name__ for validator in validators] == [
        "NullValidator",
        "DuplicateValidator",
        "DataTypeValidator",
        "RegexValidator",
    ]
    assert validators[1].subset == ["employee_id"]
    assert validators[3].pattern != "EMAIL"
