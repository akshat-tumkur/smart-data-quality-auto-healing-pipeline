from abc import ABC, abstractmethod

class BaseValidator(ABC):
    def __init__(self, validator_name: str):
        self.validator_name = validator_name

    @abstractmethod
    def validate(self, df):
        """Run the validation logic on the provided DataFrame and return a ValidationResult."""
        pass