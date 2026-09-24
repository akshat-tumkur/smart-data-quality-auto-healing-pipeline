from fastapi import APIRouter, File, HTTPException, UploadFile
import pandas as pd

from api.services.pipeline_service import (
    EmptyDatasetError,
    PipelineService,
    UnsupportedDatasetError,
)


router = APIRouter(prefix="/pipeline", tags=["pipeline"])
pipeline_service = PipelineService()


@router.post("/run", summary="Run the data quality pipeline")
async def run_pipeline(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    try:
        payload = pipeline_service.run_csv(file.filename or "dataset.csv", content)
    except UnsupportedDatasetError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except EmptyDatasetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded CSV is invalid.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Pipeline execution failed.") from exc

    if payload.get("status") == "schema_failed":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "The dataset is missing required schema columns.",
                "result": payload,
            },
        )
    return payload