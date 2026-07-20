import pandas as pd
from src.validation.validators.null_validator import NullValidator
from src.validation.validator_manager import ValidatorManager
from src.core.pipeline import Pipeline

df = pd.read_csv("data/sample_data/employees.csv")
null_validator = NullValidator()
validator_manager = ValidatorManager(validators=[
        null_validator
    ])

results = Pipeline(validation_manager=validator_manager).run(df)
        
for result in results: 
    print(result)