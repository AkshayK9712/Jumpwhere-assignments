from fastapi import APIRouter

from app.api.v1 import admin, auth, health, readings, sensors, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sensors.router, prefix="/sensors", tags=["sensors"])
api_router.include_router(readings.router, tags=["readings"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Added on later days:
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
# api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
