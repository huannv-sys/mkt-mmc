from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional, Dict, Any
from app.schemas.ip import IPAddress, IPAddressCreate, AddressList, AddressListCreate
from app.services.ip_service import IPService
from app.core.security import get_current_user

router = APIRouter()

@router.get("/addresses", response_model=List[IPAddress])
async def get_ip_addresses(
    address: Optional[str] = Query(None, description="Lọc theo địa chỉ IP hoặc subnet"),
    network: Optional[str] = Query(None, description="Lọc theo mạng"),
    interface: Optional[str] = Query(None, description="Lọc theo interface"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (active, disabled)"),
    limit: int = Query(100, ge=1, le=1000, description="Số lượng tối đa kết quả"),
    current_user = Depends(get_current_user)
):
    """
    Lấy danh sách các địa chỉ IP đã được cấu hình
    """
    try:
        return await IPService.get_ip_addresses(address, network, interface, status, limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách địa chỉ IP: {str(e)}"
        )

@router.post("/addresses", response_model=IPAddress, status_code=status.HTTP_201_CREATED)
async def add_ip_address(
    ip_data: IPAddressCreate,
    current_user = Depends(get_current_user)
):
    """
    Thêm địa chỉ IP mới
    """
    try:
        return await IPService.add_ip_address(ip_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi thêm địa chỉ IP: {str(e)}"
        )

@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_ip_address(
    address_id: str,
    current_user = Depends(get_current_user)
):
    """
    Xóa địa chỉ IP
    """
    try:
        result = await IPService.remove_ip_address(address_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa chỉ IP"
            )
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa địa chỉ IP: {str(e)}"
        )

@router.get("/address-lists", response_model=List[AddressList])
async def get_address_lists(
    name: Optional[str] = Query(None, description="Lọc theo tên address list"),
    current_user = Depends(get_current_user)
):
    """
    Lấy danh sách các address list
    """
    try:
        return await IPService.get_address_lists(name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách address list: {str(e)}"
        )

@router.post("/address-lists", response_model=AddressList, status_code=status.HTTP_201_CREATED)
async def create_address_list(
    list_data: AddressListCreate,
    current_user = Depends(get_current_user)
):
    """
    Tạo address list mới
    """
    try:
        return await IPService.create_address_list(list_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo address list: {str(e)}"
        )

@router.post("/address-lists/{list_name}/add", status_code=status.HTTP_200_OK)
async def add_to_address_list(
    list_name: str,
    address: str = Body(..., embed=True),
    comment: Optional[str] = Body(None, embed=True),
    timeout: Optional[str] = Body(None, embed=True),
    current_user = Depends(get_current_user)
):
    """
    Thêm địa chỉ vào address list
    """
    try:
        result = await IPService.add_to_address_list(list_name, address, comment, timeout)
        if result:
            return {"success": True, "message": "Đã thêm địa chỉ vào address list"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể thêm địa chỉ vào address list"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi thêm địa chỉ vào address list: {str(e)}"
        )

@router.post("/address-lists/{list_name}/remove", status_code=status.HTTP_200_OK)
async def remove_from_address_list(
    list_name: str,
    address: str = Body(..., embed=True),
    current_user = Depends(get_current_user)
):
    """
    Xóa địa chỉ khỏi address list
    """
    try:
        result = await IPService.remove_from_address_list(list_name, address)
        if result:
            return {"success": True, "message": "Đã xóa địa chỉ khỏi address list"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể xóa địa chỉ khỏi address list"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa địa chỉ khỏi address list: {str(e)}"
        )

@router.get("/arp-table", response_model=List[Dict[str, Any]])
async def get_arp_table(
    ip: Optional[str] = Query(None, description="Lọc theo địa chỉ IP"),
    mac: Optional[str] = Query(None, description="Lọc theo địa chỉ MAC"),
    interface: Optional[str] = Query(None, description="Lọc theo interface"),
    current_user = Depends(get_current_user)
):
    """
    Lấy bảng ARP
    """
    try:
        return await IPService.get_arp_table(ip, mac, interface)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy bảng ARP: {str(e)}"
        )

@router.get("/dns-cache", response_model=List[Dict[str, Any]])
async def get_dns_cache(
    name: Optional[str] = Query(None, description="Lọc theo tên miền"),
    current_user = Depends(get_current_user)
):
    """
    Lấy bộ nhớ đệm DNS
    """
    try:
        return await IPService.get_dns_cache(name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy bộ nhớ đệm DNS: {str(e)}"
        )

@router.post("/dns-cache/flush", status_code=status.HTTP_200_OK)
async def flush_dns_cache(current_user = Depends(get_current_user)):
    """
    Xóa bộ nhớ đệm DNS
    """
    try:
        result = await IPService.flush_dns_cache()
        if result:
            return {"success": True, "message": "Đã xóa bộ nhớ đệm DNS"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể xóa bộ nhớ đệm DNS"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa bộ nhớ đệm DNS: {str(e)}"
        )