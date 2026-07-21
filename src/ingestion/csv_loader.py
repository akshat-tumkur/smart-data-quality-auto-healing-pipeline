from ingestion.base_loader import BaseLoader
import pandas as pd

class CSVLoader(BaseLoader):
    def load(self, file_path):
        print(f"Reading CSV file from: {file_path}")
        data = pd.read_csv(file_path)
        print("CSV loaded succesfully")
        return data