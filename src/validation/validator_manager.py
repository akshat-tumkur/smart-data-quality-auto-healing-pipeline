"""Validation orchestration entry point."""
class ValidatorManager:
    def __init__(self, validators):
        self.validators = validators

    def run_validations(self, data):
        results = []
        for validator in self.validators:
            result = validator.validate(data)
            results.append(result)
        return results