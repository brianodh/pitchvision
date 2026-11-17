from backend.app.api.routes.health import router as health_router
from fastapi import FastAPI


app = FastAPI(
    title="PitchVision API",
    description="Backend API for the PitchVision soccer action spotting system.",
    version="0.1.0",
)


app.include_router(
    health_router,
    prefix="/api/v1",
)


@app.get("/")
def root():
    return {
        "message": "PitchVision API is running",
        "version": "0.1.0",
    }