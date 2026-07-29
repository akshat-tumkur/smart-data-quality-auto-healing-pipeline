from ingestion.csv_loader import CSVLoader


class IngestionManager:
    def __init__(self, config: dict) -> None:
        self.config = config

    def ingest(self):
        source = self.config["pipeline"]["source"]
        if source == "csv":
            loader = CSVLoader()
            dataset_config = self.config.get("dataset", {})
            file_path = dataset_config.get(
                "path",
                self.config["pipeline"]["csv"]["file_path"],
            )
            return loader.load(
                file_path,
                delimiter=dataset_config.get("delimiter", ","),
                encoding=dataset_config.get("encoding", "utf-8"),
                has_header=dataset_config.get("has_header", True),
            )
        else:
            raise ValueError(f"Unsupported source: {source}")
