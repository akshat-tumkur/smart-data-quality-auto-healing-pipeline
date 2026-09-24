from fastapi import APIRouter, File, UploadFile

from api.services.pipeline_service import PipelineService


router = APIRouter(prefix="/pipeline", tags=["pipeline"])
pipeline_service = PipelineService()


@router.post("/run", summary="Run the data quality pipeline")
async def run_pipeline(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    return pipeline_service.run_csv(file.filename or "dataset.csv", content)