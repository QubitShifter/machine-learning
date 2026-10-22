
from fastapi import FastAPI

from backend.app.api.aoi import router as aoi_router
from backend.app.api.integration import router as integration_router
from backend.app.api.satellite import router as satellite_router
from backend.app.api.soil import router as soil_router
from backend.app.api.weather import router as weather_router

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
app.include_router(
    weather_router,
    prefix="/api/v1/weather",
    tags=["weather"],
)
app.include_router(
    integration_router,
    prefix="/api/v1/integration",
    tags=["integration"],
)
app.include_router(
    soil_router,
    prefix="/api/v1/soil",
    tags=["soil"],
)
app.include_router(
    aoi_router,
    prefix="/api/v1/aoi",
    tags=["aoi"],
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
