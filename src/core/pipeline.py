class Pipeline:
    def __init__(self, validation_manager):
        self.validation_manager = validation_manager
    def run(self, dataframe):
        results = self.validation_manager.run_validations(dataframe)
        return results