import pandas as pd
from src.validation.null_validator import NullValidator
from src.validation.validator_manager import ValidatorManager

df = pd.read_csv("data/sample_data/employees.csv")
null_validator = NullValidator()
manager = ValidatorManager(validators=[
        null_validator
    ])

results = manager.run_validations(df)

for result in results: 
    print(result)