import pandas as pd


from ingestion.base_loader import BaseLoader


class CSVLoader(BaseLoader):
    def load(
        self,
        file_path: str,
        delimiter: str = ",",
        encoding: str = "utf-8",
        has_header: bool = True,
    ) -> pd.DataFrame:
        print(f"Reading CSV file from: {file_path}")
        header = 0 if has_header else None
        data = pd.read_csv(
            file_path,
            delimiter=delimiter,
            encoding=encoding,
            header=header,
        )
        print("CSV loaded successfully")
        return data
