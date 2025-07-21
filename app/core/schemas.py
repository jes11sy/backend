# Обратная совместимость - реэкспорт из enhanced_schemas
from .enhanced_schemas import (
    # Статусы и энумы
    RequestStatus, UserStatus, UserRole,
    
    # Основные схемы
    CitySchema as CityBase,
    RequestTypeSchema as RequestTypeBase,
    DirectionSchema as DirectionBase,
    RoleSchema as RoleBase,
    TransactionTypeSchema as TransactionTypeBase,
    AdvertisingCampaignSchema as AdvertisingCampaignBase,
    MasterSchema as MasterBase,
    EmployeeSchema as EmployeeBase,
    AdministratorSchema as AdministratorBase,
    FileSchema as FileBase,
    
    # Create схемы
    RequestCreateSchema as RequestCreate,
    TransactionCreateSchema as TransactionCreate,
    AdvertisingCampaignCreateSchema as AdvertisingCampaignCreate,
    MasterCreateSchema as MasterCreate,
    EmployeeCreateSchema as EmployeeCreate,
    
    # Update схемы
    RequestUpdateSchema as RequestUpdate,
    TransactionUpdateSchema as TransactionUpdate,
    
    # Response схемы
    RequestResponseSchema as RequestResponse,
    TransactionResponseSchema as TransactionResponse,
    CitySchema as CityResponse,
    RequestTypeSchema as RequestTypeResponse,
    DirectionSchema as DirectionResponse,
    RoleSchema as RoleResponse,
    TransactionTypeSchema as TransactionTypeResponse,
    AdvertisingCampaignSchema as AdvertisingCampaignResponse,
    MasterSchema as MasterResponse,
    EmployeeSchema as EmployeeResponse,
    AdministratorSchema as AdministratorResponse,
    FileSchema as FileResponse,
    
    # Auth схемы
    UserLogin, Token, TokenData, TokenResponse
)

# Для обратной совместимости с pydantic
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

# Дополнительные схемы, которых нет в enhanced_schemas (если нужны)
class CityCreate(CityBase):
    pass

class CityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)

class RequestTypeCreate(RequestTypeBase):
    pass

class RequestTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)

class DirectionCreate(DirectionBase):
    pass

class DirectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)

class TransactionTypeCreate(TransactionTypeBase):
    pass

class TransactionTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)

class AdvertisingCampaignUpdate(BaseModel):
    city_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=200)
    phone_number: Optional[str] = Field(None, max_length=20)

class MasterUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    city_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    login: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    role_id: Optional[int] = None
    city_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    login: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)

class AdministratorCreate(AdministratorBase):
    pass

class AdministratorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    role_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    login: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)

class FileCreate(FileBase):
    pass

class FileUpdate(BaseModel):
    file_type: Optional[str] = Field(None, max_length=50)
    file_path: Optional[str] = Field(None, max_length=500)

 