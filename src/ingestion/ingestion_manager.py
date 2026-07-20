from ingestion.csv_loader import CSVLoader
class IngestionManager:
    def __init__(self,config):
        self.config=config
    def ingest(self):
        source= self.config["pipeline"]["source"]
        if source=="csv":
            loader=CSVLoader()
            file_path=self.config["pipeline"]["csv"]["file_path"]
            return loader.load(file_path)
        else:
            raise Exception("Unsupported Source")
        