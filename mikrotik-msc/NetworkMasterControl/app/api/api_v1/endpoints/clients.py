from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.schemas.client import Client, ClientCreate, ClientUpdate, ClientFilter
from app.services.client_service import ClientService
from app.core.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Client])
async def get_clients(
    ip: Optional[str] = Query(None, description="Lọc theo địa chỉ IP"),
    mac: Optional[str] = Query(None, description="Lọc theo địa chỉ MAC"),
    hostname: Optional[str] = Query(None, description="Lọc theo hostname"),
    connection_type: Optional[str] = Query(None, description="Lọc theo loại kết nối (wired, wireless)"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (active, blocked)"),
    limit: int = Query(100, ge=1, le=1000, description="Số lượng tối đa kết quả"),
    current_user = Depends(get_current_user)
):
    """
    Lấy danh sách các client kết nối đến mạng
    """
    try:
        filters = ClientFilter(
            ip=ip,
            mac=mac,
            hostname=hostname,
            connection_type=connection_type,
            status=status
        )
        return await ClientService.get_all_clients(filters, limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách client: {str(e)}"
        )

@router.get("/wireless", response_model=List[Client])
async def get_wireless_clients(current_user = Depends(get_current_user)):
    """
    Lấy danh sách các client kết nối không dây
    """
    try:
        return await ClientService.get_wireless_clients()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách client không dây: {str(e)}"
        )

@router.get("/dhcp-leases", response_model=List[Client])
async def get_dhcp_leases(current_user = Depends(get_current_user)):
    """
    Lấy danh sách các DHCP leases
    """
    try:
        return await ClientService.get_dhcp_leases()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách DHCP leases: {str(e)}"
        )

@router.get("/blocked", response_model=List[Client])
async def get_blocked_clients(current_user = Depends(get_current_user)):
    """
    Lấy danh sách các client đã bị chặn
    """
    try:
        return await ClientService.get_blocked_clients()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách client bị chặn: {str(e)}"
        )

@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: str,
    current_user = Depends(get_current_user)
):
    """
    Lấy thông tin chi tiết của một client
    """
    client = await ClientService.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy client"
        )
    return client

@router.post("/block", status_code=status.HTTP_200_OK)
async def block_client(
    ip: Optional[str] = None,
    mac: Optional[str] = None,
    comment: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Chặn một client dựa trên địa chỉ IP hoặc MAC
    """
    if not ip and not mac:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phải cung cấp ít nhất một trong hai: địa chỉ IP hoặc MAC"
        )
    
    try:
        result = await ClientService.block_client(ip, mac, comment)
        if result:
            return {"success": True, "message": "Đã chặn client thành công"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể chặn client"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chặn client: {str(e)}"
        )

@router.post("/unblock", status_code=status.HTTP_200_OK)
async def unblock_client(
    ip: Optional[str] = None,
    mac: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Bỏ chặn một client dựa trên địa chỉ IP hoặc MAC
    """
    if not ip and not mac:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phải cung cấp ít nhất một trong hai: địa chỉ IP hoặc MAC"
        )
    
    try:
        result = await ClientService.unblock_client(ip, mac)
        if result:
            return {"success": True, "message": "Đã bỏ chặn client thành công"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể bỏ chặn client"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi bỏ chặn client: {str(e)}"
        )

@router.get("/{client_id}/traffic", response_model=dict)
async def get_client_traffic(
    client_id: str,
    period: Optional[str] = Query("hour", description="Khoảng thời gian (hour, day, week, month)"),
    current_user = Depends(get_current_user)
):
    """
    Lấy thông tin lưu lượng của một client cụ thể
    """
    try:
        traffic_data = await ClientService.get_client_traffic(client_id, period)
        if not traffic_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy dữ liệu lưu lượng cho client này"
            )
        return traffic_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy dữ liệu lưu lượng: {str(e)}"
        )