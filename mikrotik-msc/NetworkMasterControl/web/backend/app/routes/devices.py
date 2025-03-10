from fastapi import APIRouter, HTTPException
from app.services.mikrotik_service import MikroTikService
from app.models.device_model import DeviceResponse

router = APIRouter()

@router.get("/", response_model=list[DeviceResponse])
async def get_devices():
    try:
        # Example: Get first device from DB
        devices = await MikroTikService.get_all_devices()
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
