from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class IPAddressBase(BaseModel):
    address: str = Field(..., description="Địa chỉ IP kèm theo netmask (ví dụ: 192.168.1.1/24)")
    interface: str = Field(..., description="Tên interface")
    comment: Optional[str] = Field(None, description="Ghi chú về địa chỉ IP")
    disabled: Optional[bool] = Field(False, description="Trạng thái vô hiệu hóa")
    
class IPAddressCreate(IPAddressBase):
    """Schema cho việc tạo địa chỉ IP mới"""
    network: Optional[str] = Field(None, description="Mạng mà địa chỉ IP thuộc về")
    
class IPAddressUpdate(BaseModel):
    """Schema cho việc cập nhật địa chỉ IP"""
    comment: Optional[str] = Field(None, description="Ghi chú về địa chỉ IP")
    disabled: Optional[bool] = Field(None, description="Trạng thái vô hiệu hóa")
    
class IPAddress(IPAddressBase):
    """Schema đầy đủ cho địa chỉ IP, bao gồm dữ liệu bổ sung từ hệ thống"""
    id: str = Field(..., description="ID duy nhất của địa chỉ IP")
    network: Optional[str] = Field(None, description="Mạng mà địa chỉ IP thuộc về")
    actual_interface: Optional[str] = Field(None, description="Interface thực tế mà địa chỉ IP được gán vào")
    creation_time: Optional[datetime] = Field(None, description="Thời gian tạo")
    last_updated: Optional[datetime] = Field(None, description="Thời gian cập nhật cuối cùng")
    dynamic: Optional[bool] = Field(False, description="Đánh dấu địa chỉ IP có phải là động hay không")
    
    class Config:
        orm_mode = True

class AddressListEntryBase(BaseModel):
    address: str = Field(..., description="Địa chỉ IP hoặc subnet")
    list: str = Field(..., description="Tên address list")
    comment: Optional[str] = Field(None, description="Ghi chú về address list entry")
    
class AddressListEntryCreate(AddressListEntryBase):
    """Schema cho việc tạo address list entry mới"""
    timeout: Optional[str] = Field(None, description="Thời gian timeout của entry này")
    
class AddressListEntry(AddressListEntryBase):
    """Schema đầy đủ cho address list entry, bao gồm dữ liệu bổ sung từ hệ thống"""
    id: str = Field(..., description="ID duy nhất của address list entry")
    dynamic: Optional[bool] = Field(False, description="Đánh dấu entry có phải là động hay không")
    timeout: Optional[str] = Field(None, description="Thời gian timeout của entry này")
    creation_time: Optional[datetime] = Field(None, description="Thời gian tạo")
    
    class Config:
        orm_mode = True

class AddressListBase(BaseModel):
    name: str = Field(..., description="Tên của address list")
    comment: Optional[str] = Field(None, description="Ghi chú về address list")
    
class AddressListCreate(AddressListBase):
    """Schema cho việc tạo address list mới"""
    entries: Optional[List[AddressListEntryCreate]] = Field(None, description="Danh sách các địa chỉ trong address list")
    
class AddressList(AddressListBase):
    """Schema đầy đủ cho address list, bao gồm dữ liệu bổ sung từ hệ thống"""
    id: str = Field(..., description="ID duy nhất của address list")
    entries: List[AddressListEntry] = Field([], description="Danh sách các địa chỉ trong address list")
    dynamic: Optional[bool] = Field(False, description="Đánh dấu address list có phải là động hay không")
    creation_time: Optional[datetime] = Field(None, description="Thời gian tạo")
    
    class Config:
        orm_mode = True