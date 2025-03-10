from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ClientBase(BaseModel):
    ip_address: Optional[str] = Field(None, description="Địa chỉ IP của client")
    mac_address: Optional[str] = Field(None, description="Địa chỉ MAC của client")
    hostname: Optional[str] = Field(None, description="Tên máy chủ của client")
    comment: Optional[str] = Field(None, description="Ghi chú về client")
    
class ClientCreate(ClientBase):
    """Schema cho việc tạo client mới"""
    pass
    
class ClientUpdate(ClientBase):
    """Schema cho việc cập nhật client"""
    pass
    
class Client(ClientBase):
    """Schema đầy đủ cho client, bao gồm dữ liệu bổ sung từ hệ thống"""
    id: str = Field(..., description="ID duy nhất của client")
    connection_type: Optional[str] = Field(None, description="Loại kết nối (wired, wireless)")
    interface: Optional[str] = Field(None, description="Interface mà client kết nối tới")
    uptime: Optional[str] = Field(None, description="Thời gian kết nối")
    last_activity: Optional[datetime] = Field(None, description="Thời gian hoạt động cuối cùng")
    tx_rate: Optional[int] = Field(None, description="Tốc độ truyền dữ liệu (kbps)")
    rx_rate: Optional[int] = Field(None, description="Tốc độ nhận dữ liệu (kbps)")
    tx_bytes: Optional[int] = Field(None, description="Tổng số bytes đã truyền")
    rx_bytes: Optional[int] = Field(None, description="Tổng số bytes đã nhận")
    signal_strength: Optional[int] = Field(None, description="Cường độ tín hiệu (dBm, chỉ áp dụng cho kết nối wireless)")
    status: str = Field("active", description="Trạng thái của client (active, blocked, disconnected)")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Thông tin bổ sung về client")
    
    class Config:
        orm_mode = True
        
class ClientFilter(BaseModel):
    """Schema cho việc lọc danh sách client"""
    ip: Optional[str] = None
    mac: Optional[str] = None
    hostname: Optional[str] = None
    connection_type: Optional[str] = None
    status: Optional[str] = None