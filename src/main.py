import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config_loader import load_config
from ingestion.ingestion_manager import IngestionManager
config=load_config("config/pipeline_config.yaml")
print(config)
manager=IngestionManager(config)
data=manager.ingest()
print(data.head())