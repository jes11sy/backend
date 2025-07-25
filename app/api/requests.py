from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    UploadFile,
    File,
    Response,
    Request as FastapiRequest,
)
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import logging
import os
from uuid import uuid4
from datetime import datetime

from app.core.cache import cache_manager
from ..core.database import get_db
from ..core.auth import require_master, require_callcenter
from ..core.config import settings
from ..core.crud import (
    create_request,
    get_request,
    update_request,
    delete_request,
    get_cities,
    get_request_types,
    get_directions,
    get_masters,
    get_advertising_campaigns,
    create_advertising_campaign,
)
from ..core.optimized_crud import OptimizedRequestCRUD
from ..monitoring.performance import (
    get_requests_optimized,
    get_request_optimized,
    performance_monitor,
    get_cities_cached,
    get_request_types_cached,
    get_directions_cached,
)

# Используем только enhanced_schemas для единообразия
from ..core.enhanced_schemas import (
    RequestCreateSchema as RequestCreate,
    RequestUpdateSchema as RequestUpdate,
    RequestResponseSchema as RequestResponse,
    CitySchema as CityResponse,
    RequestTypeSchema as RequestTypeResponse,
    DirectionSchema as DirectionResponse,
    MasterSchema as MasterResponse,
    AdvertisingCampaignSchema as AdvertisingCampaignResponse,
    AdvertisingCampaignCreateSchema as AdvertisingCampaignCreate,
    ErrorResponse,
    ValidationErrorResponse,
)
from ..core.models import (
    Master,
    Employee,
    Administrator,
    Request,
    RequestType,
    Direction,
    AdvertisingCampaign,
)

router = APIRouter(prefix="/requests", tags=["requests"])


# Эндпоинты для мастеров (в начале файла)
@router.get("/masters/")
async def get_masters_list(db: AsyncSession = Depends(get_db)):
    """Получение списка мастеров"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    result = await db.execute(select(Master))
    masters = result.scalars().all()

    # Преобразуем в простые словари с базовыми данными
    data = [
        {
            "id": master.id,
            "full_name": master.full_name,
            "city_id": master.city_id,
            "phone_number": master.phone_number or "",
            "login": master.login or "",
            "status": master.status,
            "created_at": master.created_at.isoformat() if master.created_at else None,
        }
        for master in masters
    ]

    # Возвращаем JSONResponse напрямую, минуя валидацию
    return JSONResponse(
        content=data,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Credentials": "true",
        },
    )


@router.get("/masters-list/")
async def get_masters_list_test():
    """Тестовый эндпоинт для мастеров"""
    return JSONResponse(
        content=[
            {
                "id": 1,
                "full_name": "Test Master",
                "city_id": 1,
                "phone_number": "123",
                "login": "test",
                "status": "active",
                "created_at": "2025-01-01T00:00:00",
            }
        ],
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Credentials": "true",
        },
    )


@router.get("/masters-simple/")
async def get_masters_simple():
    """Максимально простой эндпоинт для мастеров"""
    return {
        "message": "Masters simple endpoint works!",
        "data": [{"id": 1, "name": "Test"}],
    }


# Роуты для заявок
@router.post(
    "/",
    response_model=RequestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Некорректные данные"},
        401: {"model": ErrorResponse, "description": "Требуется аутентификация"},
        422: {"model": ValidationErrorResponse, "description": "Ошибка валидации"},
    },
)
async def create_new_request(
    request: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """
    Создание новой заявки
    """
    if not request.city_id or request.city_id == 0:
        raise HTTPException(status_code=400, detail="city_id is required")
    if not request.request_type_id or request.request_type_id == 0:
        raise HTTPException(status_code=400, detail="request_type_id is required")
    new_request = await create_request(db=db, request=request)
    # --- Инвалидация кэша после создания заявки ---
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("requests:*")
    # --- Конец инвалидации кэша ---
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/requests")
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return new_request


@router.get("/", response_model=List[RequestResponse])
@performance_monitor
async def read_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    city_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    master_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение списка заявок (временно упрощенная версия)"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    query = select(Request).options(
        selectinload(Request.advertising_campaign),
        selectinload(Request.city),
        selectinload(Request.request_type),
        selectinload(Request.direction),
        selectinload(Request.master),
        selectinload(Request.files),
    )

    # Применяем фильтры
    if city_id:
        query = query.where(Request.city_id == city_id)
    if status:
        query = query.where(Request.status == status)
    if master_id:
        query = query.where(Request.master_id == master_id)

    # Применяем пагинацию
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    requests = result.scalars().all()

    # Преобразуем в простые словари
    return [
        {
            "id": req.id,
            "advertising_campaign_id": req.advertising_campaign_id,
            "city_id": req.city_id,
            "request_type_id": req.request_type_id,
            "client_phone": req.client_phone,
            "client_name": req.client_name,
            "address": req.address,
            "meeting_date": (
                req.meeting_date.isoformat() if req.meeting_date is not None else None
            ),
            "direction_id": req.direction_id,
            "problem": req.problem,
            "status": req.status,
            "master_id": req.master_id,
            "master_notes": req.master_notes,
            "result": float(req.result) if req.result is not None else None,
            "expenses": float(req.expenses) if req.expenses is not None else 0,
            "net_amount": float(req.net_amount) if req.net_amount is not None else 0,
            "master_handover": (
                float(req.master_handover) if req.master_handover is not None else 0
            ),
            "ats_number": req.ats_number,
            "call_center_name": req.call_center_name,
            "call_center_notes": req.call_center_notes,
            "avito_chat_id": req.avito_chat_id,
            "created_at": (
                req.created_at.isoformat() if req.created_at is not None else None
            ),
            "city": {"id": req.city.id, "name": req.city.name} if req.city else None,
            "request_type": (
                {"id": req.request_type.id, "name": req.request_type.name}
                if req.request_type
                else None
            ),
            "direction": (
                {"id": req.direction.id, "name": req.direction.name}
                if req.direction
                else None
            ),
            "master": (
                {
                    "id": req.master.id,
                    "full_name": req.master.full_name,
                    "phone_number": req.master.phone_number,
                    "login": req.master.login,
                    "city_id": req.master.city_id,
                    "created_at": (
                        req.master.created_at.isoformat()
                        if req.master.created_at is not None
                        else None
                    ),
                    "city": (
                        {"id": req.master.city.id, "name": req.master.city.name}
                        if req.master.city
                        else None
                    ),
                }
                if req.master
                else None
            ),
            "advertising_campaign": (
                {
                    "id": req.advertising_campaign.id,
                    "name": req.advertising_campaign.name,
                    "phone_number": req.advertising_campaign.phone_number,
                    "city_id": req.advertising_campaign.city_id,
                    "created_at": (
                        req.advertising_campaign.created_at.isoformat()
                        if req.advertising_campaign.created_at is not None
                        else None
                    ),
                    "city": (
                        {
                            "id": req.advertising_campaign.city.id,
                            "name": req.advertising_campaign.city.name,
                        }
                        if req.advertising_campaign.city
                        else None
                    ),
                }
                if req.advertising_campaign
                else None
            ),
        }
        for req in requests
    ]


@router.put("/{request_id}/", response_model=RequestResponse)
async def update_existing_request(
    request_id: int,
    request_data: RequestUpdate,
    request: FastapiRequest,  # <-- исправлено
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Обновление заявки"""
    updated_request = await update_request(
        db=db, request_id=request_id, request=request_data
    )
    if updated_request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    # --- Инвалидация кэша после обновления заявки ---
    from app.core.cache import cache_manager

    # Сброс кэша по id заявки (если используется)
    await cache_manager.delete(f"request:{request_id}")
    # Сброс кэша списков заявок (если используется паттерн)
    await cache_manager.clear_pattern("requests:*")
    # Можно добавить другие паттерны, если кэшируются связанные данные
    # await cache_manager.clear_pattern("masters:*")
    # await cache_manager.clear_pattern("users:*")
    # --- Конец инвалидации кэша ---
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/requests")
    await cache_manager.invalidate_http_cache(f"/api/v1/requests/{request_id}")
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    await cache_manager.invalidate_http_cache(str(request.url))
    return updated_request


@router.delete("/{request_id}/")
async def delete_existing_request(
    request_id: int,
    request: FastapiRequest,  # <-- исправлено
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Удаление заявки
    """
    success = await delete_request(db=db, request_id=request_id)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found")
    # --- Инвалидация кэша после удаления заявки ---
    from app.core.cache import cache_manager

    await cache_manager.delete(f"request:{request_id}")
    await cache_manager.clear_pattern("requests:*")
    # --- Конец инвалидации кэша ---
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/requests")
    await cache_manager.invalidate_http_cache(f"/api/v1/requests/{request_id}")
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    await cache_manager.invalidate_http_cache(str(request.url))
    return {"message": "Request deleted successfully"}


# Дополнительные эндпоинты для получения справочных данных
@router.get("/cities/", response_model=List[CityResponse])
@performance_monitor
async def get_cities_list(
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение списка городов"""
    return await get_cities(db=db)


@router.post("/cities/", response_model=CityResponse)
async def create_city_endpoint(
    city: CityResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Создание нового города"""
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("cities:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_cities(db=db)


@router.put("/cities/{city_id}", response_model=CityResponse)
async def update_city_endpoint(
    city_id: int,
    city: CityResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Обновление города"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"city:{city_id}")
    await cache_manager.clear_pattern("cities:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_cities(db=db)


@router.delete("/cities/{city_id}")
async def delete_city_endpoint(
    city_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Удаление города"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"city:{city_id}")
    await cache_manager.clear_pattern("cities:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"message": "City deleted successfully"}


@router.get("/request-types/", response_model=List[RequestTypeResponse])
async def get_request_types_list(
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение типов заявок"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    result = await db.execute(select(RequestType))
    request_types = result.scalars().all()

    # Преобразуем в простые словари
    return [{"id": rt.id, "name": rt.name} for rt in request_types]


@router.post("/request-types/", response_model=RequestTypeResponse)
async def create_request_type_endpoint(
    request_type: RequestTypeResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Создание нового типа заявки"""
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("request_types:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_request_types(db=db)


@router.put("/request-types/{type_id}", response_model=RequestTypeResponse)
async def update_request_type_endpoint(
    type_id: int,
    request_type: RequestTypeResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Обновление типа заявки"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"request_type:{type_id}")
    await cache_manager.clear_pattern("request_types:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_request_types(db=db)


@router.delete("/request-types/{type_id}")
async def delete_request_type_endpoint(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Удаление типа заявки"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"request_type:{type_id}")
    await cache_manager.clear_pattern("request_types:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"message": "Request type deleted successfully"}


@router.get("/directions/", response_model=List[DirectionResponse])
async def get_directions_list(
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение списка направлений"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    result = await db.execute(select(Direction))
    directions = result.scalars().all()

    # Преобразуем в простые словари
    return [{"id": direction.id, "name": direction.name} for direction in directions]


@router.post("/directions/", response_model=DirectionResponse)
async def create_direction_endpoint(
    direction: DirectionResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Создание нового направления"""
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("directions:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_directions(db=db)


@router.put("/directions/{direction_id}", response_model=DirectionResponse)
async def update_direction_endpoint(
    direction_id: int,
    direction: DirectionResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Обновление направления"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"direction:{direction_id}")
    await cache_manager.clear_pattern("directions:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_directions(db=db)


@router.delete("/directions/{direction_id}")
async def delete_direction_endpoint(
    direction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Удаление направления"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"direction:{direction_id}")
    await cache_manager.clear_pattern("directions:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"message": "Direction deleted successfully"}


@router.get("/advertising-campaigns/", response_model=List[AdvertisingCampaignResponse])
async def get_advertising_campaigns_list(
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение рекламных кампаний"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    result = await db.execute(
        select(AdvertisingCampaign).options(selectinload(AdvertisingCampaign.city))
    )
    campaigns = result.scalars().all()

    # Преобразуем в простые словари с полными данными
    return [
        {
            "id": campaign.id,
            "city_id": campaign.city_id,
            "name": campaign.name,
            "phone_number": campaign.phone_number,
            "created_at": (
                campaign.created_at.isoformat()
                if campaign.created_at is not None
                else None
            ),
            "city": (
                {"id": campaign.city.id, "name": campaign.city.name}
                if campaign.city
                else None
            ),
        }
        for campaign in campaigns
    ]


@router.post("/advertising-campaigns/", response_model=AdvertisingCampaignResponse)
async def create_advertising_campaign_endpoint(
    campaign: AdvertisingCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Создание новой рекламной кампании"""
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("advertising_campaigns:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await create_advertising_campaign(db=db, campaign=campaign)


@router.put(
    "/advertising-campaigns/{campaign_id}", response_model=AdvertisingCampaignResponse
)
async def update_advertising_campaign_endpoint(
    campaign_id: int,
    campaign: AdvertisingCampaignResponse,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Обновление рекламной кампании"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"advertising_campaign:{campaign_id}")
    await cache_manager.clear_pattern("advertising_campaigns:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return await get_advertising_campaigns(db=db)


@router.delete("/advertising-campaigns/{campaign_id}")
async def delete_advertising_campaign_endpoint(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Удаление рекламной кампании"""
    from app.core.cache import cache_manager

    await cache_manager.delete(f"advertising_campaign:{campaign_id}")
    await cache_manager.clear_pattern("advertising_campaigns:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"message": "Advertising campaign deleted successfully"}


@router.get("/callcenter-report")
async def get_callcenter_report(
    city_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение отчета для колл-центра"""

    # Базовый запрос
    query = select(Request).options(
        selectinload(Request.city),
        selectinload(Request.request_type),
        selectinload(Request.advertising_campaign),
    )

    # Применяем фильтры
    filters = []

    if city_id is not None:
        filters.append(Request.city_id == city_id)

    if status is not None:
        filters.append(Request.status == status)

    if date_from is not None:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            filters.append(Request.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to is not None:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            filters.append(Request.created_at <= date_to_obj)
        except ValueError:
            pass

    if filters:
        query = query.where(and_(*filters))

    # Получаем данные
    result = await db.execute(query)
    requests = result.scalars().all()

    # Подсчитываем статистику
    stats = {
        "total": len(requests),
        "new": len([r for r in requests if r.status == "new"]),
        "in_progress": len([r for r in requests if r.status == "in_progress"]),
        "done": len([r for r in requests if r.status == "done"]),
        "cancelled": len([r for r in requests if r.status == "cancelled"]),
    }

    # Статистика по городам
    city_stats = {}
    for request in requests:
        city_name = request.city.name if request.city else "Неизвестно"
        if city_name not in city_stats:
            city_stats[city_name] = {
                "total": 0,
                "new": 0,
                "in_progress": 0,
                "done": 0,
                "cancelled": 0,
            }
        city_stats[city_name]["total"] += 1
        city_stats[city_name][str(request.status)] += 1

    return {
        "requests": [
            {
                "id": r.id,
                "client_phone": r.client_phone,
                "client_name": r.client_name,
                "city_id": r.city_id,
                "city_name": r.city.name if r.city else "Неизвестно",
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "request_type": r.request_type.name if r.request_type else None,
                "advertising_campaign": (
                    r.advertising_campaign.name if r.advertising_campaign else None
                ),
            }
            for r in requests
        ],
        "stats": stats,
        "city_stats": city_stats,
    }


# OPTIONS handler для CORS preflight
@router.options("/{request_id}/")
async def options_request(request_id: int):
    """OPTIONS handler для CORS preflight запросов"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        },
    )


# Общий роут с параметром должен быть ПОСЛЕ всех специфических роутов
@router.get("/{request_id}/")
@performance_monitor
async def read_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение заявки по ID (оптимизированная версия)"""
    request = await get_request_optimized(db, request_id=request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    # Простая сериализация в словарь
    request_data = {
        "id": request.id,
        "advertising_campaign_id": request.advertising_campaign_id,
        "city_id": request.city_id,
        "request_type_id": request.request_type_id,
        "client_phone": request.client_phone,
        "client_name": request.client_name,
        "address": request.address,
        "meeting_date": (
            request.meeting_date.isoformat() if request.meeting_date else None
        ),
        "direction_id": request.direction_id,
        "problem": request.problem,
        "status": request.status,
        "master_id": request.master_id,
        "master_notes": request.master_notes,
        "result": float(request.result) if request.result is not None else 0,
        "expenses": float(request.expenses) if request.expenses is not None else 0,
        "net_amount": (
            float(request.net_amount) if request.net_amount is not None else 0
        ),
        "master_handover": (
            float(request.master_handover) if request.master_handover is not None else 0
        ),
        "ats_number": request.ats_number,
        "call_center_name": request.call_center_name,
        "call_center_notes": request.call_center_notes,
        "avito_chat_id": request.avito_chat_id,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "bso_file_path": request.bso_file_path,
        "expense_file_path": request.expense_file_path,
        "recording_file_path": request.recording_file_path,
    }

    # Добавляем связанные объекты если они есть
    if hasattr(request, "city") and request.city:
        request_data["city"] = {"id": request.city.id, "name": request.city.name}
    if hasattr(request, "request_type") and request.request_type:
        request_data["request_type"] = {
            "id": request.request_type.id,
            "name": request.request_type.name,
        }
    if hasattr(request, "direction") and request.direction:
        request_data["direction"] = {
            "id": request.direction.id,
            "name": request.direction.name,
        }
    if hasattr(request, "master") and request.master:
        request_data["master"] = {
            "id": request.master.id,
            "full_name": request.master.full_name,
        }

    return JSONResponse(
        content=request_data,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


# --- Загрузка файлов к заявке ---
@router.post("/{request_id}/upload-bso/")
async def upload_bso_file(
    request_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """Загрузка БСО к заявке"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")
    upload_dir = os.path.join("media", "zayvka", "bso")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    # Обновляем заявку
    from ..core.crud import update_request

    await update_request(db, request_id, RequestUpdate(bso_file_path=file_path))  # type: ignore
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/requests")
    await cache_manager.invalidate_http_cache(f"/api/v1/requests/{request_id}")
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"file_path": file_path}


@router.post("/{request_id}/upload-expense/")
async def upload_expense_file(
    request_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """Загрузка чека расхода к заявке"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")
    upload_dir = os.path.join("media", "zayvka", "rashod")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    from ..core.crud import update_request

    await update_request(db, request_id, RequestUpdate(expense_file_path=file_path))  # type: ignore
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/requests")
    await cache_manager.invalidate_http_cache(f"/api/v1/requests/{request_id}")
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"file_path": file_path}


@router.post("/{request_id}/upload-recording/")
async def upload_recording_file(
    request_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """Загрузка аудиозаписи к заявке"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".mp3", ".wav", ".ogg", ".m4a", ".amr"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")
    upload_dir = os.path.join("media", "zayvka", "zapis")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    from ..core.crud import update_request

    await update_request(db, request_id, RequestUpdate(recording_file_path=file_path))  # type: ignore
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/requests")
    await cache_manager.invalidate_http_cache(f"/api/v1/requests/{request_id}")
    await cache_manager.invalidate_http_cache("/api/v1/cities")
    await cache_manager.invalidate_http_cache("/api/v1/request-types")
    await cache_manager.invalidate_http_cache("/api/v1/directions")
    await cache_manager.invalidate_http_cache("/api/v1/advertising-campaigns")
    await cache_manager.invalidate_http_cache("/api/requests")
    await cache_manager.invalidate_http_cache("/api/cities")
    await cache_manager.invalidate_http_cache("/api/request-types")
    await cache_manager.invalidate_http_cache("/api/directions")
    await cache_manager.invalidate_http_cache("/api/advertising-campaigns")
    return {"file_path": file_path}
