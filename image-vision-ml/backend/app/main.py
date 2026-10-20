
from fastapi import FastAPI

from backend.app.api.satellite import router as satellite_router

app = FastAPI(
    title="Image Vision ML API",
    description=(
        "Machine Learning and Computer Vision API "
        "for geospatial image processing and forecasting."
    ),
    version="0.1.0",
    docs_url="/api",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(
    satellite_router,
    prefix="/api/v1/satellite",
    tags=["satellite"],
)


@app.get("/")
def root():
    return {
        "application": "image-vision-ml",
        "version": "0.1.0",
        "message": "Image Vision ML API is running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "application": "image-vision-ml",
    }
