"""CSV ingestion helpers."""
import pandas as pd
class CSVLoader:
    def load(self,file_path):
        print(f"Reading CSV file from: {file_path}")
        data=pd.read_csv(file_path)
        print("CSV loaded succesfully")
        return data