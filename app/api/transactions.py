from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_db
from ..core.auth import require_master, get_current_active_user, require_callcenter
from ..core.config import settings
from ..core.crud import (
    create_transaction,
    get_transaction,
    update_transaction,
    delete_transaction,
    get_cities,
    get_transaction_types,
    create_transaction_type,
    update_transaction_type,
    delete_transaction_type,
)
from ..core.optimized_crud import OptimizedTransactionCRUD
from ..core.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    CityResponse,
    TransactionTypeResponse,
    TransactionTypeCreate,
    TransactionTypeUpdate,
)
from ..core.models import (
    Master,
    Employee,
    Administrator,
    TransactionType,
    Transaction,
    File as FileModel,
)
from ..utils.file_security import validate_and_save_file
from ..core.config import settings
import os

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionResponse)
async def create_new_transaction(
    transaction: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Создание новой транзакции
    """
    new_transaction = await create_transaction(db=db, transaction=transaction)
    # --- Инвалидация кэша после создания транзакции ---
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("transactions:*")
    # --- Конец инвалидации кэша ---
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/transactions")
    await cache_manager.invalidate_http_cache(
        f"/api/v1/transactions/{new_transaction.id}"
    )  # если есть id
    await cache_manager.invalidate_http_cache("/api/v1/transaction-types")
    await cache_manager.invalidate_http_cache("/api/transactions")
    await cache_manager.invalidate_http_cache("/api/transaction-types")
    return new_transaction


@router.get("/", response_model=List[TransactionResponse])
async def read_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Получение списка транзакций (временно упрощенная версия)"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    from sqlalchemy.orm import selectinload
    from ..core.models import Transaction

    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.city),
            selectinload(Transaction.transaction_type),
            selectinload(Transaction.files),
        )
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    transactions = result.scalars().all()

    # Преобразуем в простые словари
    return [
        {
            "id": trans.id,
            "city_id": trans.city_id,
            "transaction_type_id": trans.transaction_type_id,
            "amount": float(trans.amount) if trans.amount is not None else 0,
            "notes": trans.notes,
            "file_path": trans.file_path,
            "specified_date": (
                trans.specified_date.isoformat()
                if trans.specified_date is not None
                else None
            ),
            "payment_reason": trans.payment_reason,
            "expense_receipt_path": trans.expense_receipt_path,
            "created_at": (
                trans.created_at.isoformat() if trans.created_at is not None else None
            ),
            "city": (
                {"id": trans.city.id, "name": trans.city.name} if trans.city else None
            ),
            "transaction_type": (
                {"id": trans.transaction_type.id, "name": trans.transaction_type.name}
                if trans.transaction_type
                else None
            ),
        }
        for trans in transactions
    ]


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def read_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Получение транзакции по ID"""
    transaction = await get_transaction(db=db, transaction_id=transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_existing_transaction(
    transaction_id: int,
    transaction: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Обновление транзакции
    """
    updated_transaction = await update_transaction(
        db=db, transaction_id=transaction_id, transaction=transaction
    )
    if updated_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # --- Инвалидация кэша после обновления транзакции ---
    from app.core.cache import cache_manager

    await cache_manager.delete(f"transaction:{transaction_id}")
    await cache_manager.clear_pattern("transactions:*")
    # --- Конец инвалидации кэша ---
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/transactions")
    await cache_manager.invalidate_http_cache(
        f"/api/v1/transactions/{transaction_id}"
    )  # если есть id
    await cache_manager.invalidate_http_cache("/api/v1/transaction-types")
    await cache_manager.invalidate_http_cache("/api/transactions")
    await cache_manager.invalidate_http_cache("/api/transaction-types")
    return updated_transaction


@router.delete("/{transaction_id}")
async def delete_existing_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Удаление транзакции
    """
    success = await delete_transaction(db=db, transaction_id=transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # --- Инвалидация кэша после удаления транзакции ---
    from app.core.cache import cache_manager

    await cache_manager.delete(f"transaction:{transaction_id}")
    await cache_manager.clear_pattern("transactions:*")
    # --- Конец инвалидации кэша ---
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/transactions")
    await cache_manager.invalidate_http_cache(
        f"/api/v1/transactions/{transaction_id}"
    )  # если есть id
    await cache_manager.invalidate_http_cache("/api/v1/transaction-types")
    await cache_manager.invalidate_http_cache("/api/transactions")
    await cache_manager.invalidate_http_cache("/api/transaction-types")
    return {"message": "Transaction deleted successfully"}


# Дополнительные эндпоинты для получения справочных данных
@router.get("/cities/")
async def get_cities_list(
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """Получение списка городов"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    from ..core.models import City
    from fastapi.responses import JSONResponse

    result = await db.execute(select(City))
    cities = result.scalars().all()

    # Преобразуем в простые словари
    cities_data = [{"id": city.id, "name": city.name} for city in cities]

    return JSONResponse(
        content=cities_data,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Credentials": "true",
        },
    )


@router.get("/transaction-types/")
async def get_transaction_types_list(
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_callcenter),
):
    """Получение типов транзакций"""
    # Временно возвращаем простые словари, минуя Pydantic валидацию
    from fastapi.responses import JSONResponse

    result = await db.execute(select(TransactionType))
    transaction_types = result.scalars().all()

    # Преобразуем в простые словари
    types_data = [{"id": tt.id, "name": tt.name} for tt in transaction_types]

    return JSONResponse(
        content=types_data,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Credentials": "true",
        },
    )


@router.post("/transaction-types/", response_model=TransactionTypeResponse)
async def create_transaction_type_endpoint(
    transaction_type: TransactionTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Создание нового типа транзакции
    """
    new_transaction_type = await create_transaction_type(
        db=db, transaction_type=transaction_type
    )
    from app.core.cache import cache_manager

    await cache_manager.clear_pattern("transaction_types:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/transaction-types")
    await cache_manager.invalidate_http_cache("/api/transactions")
    await cache_manager.invalidate_http_cache("/api/transaction-types")
    return new_transaction_type


@router.put("/transaction-types/{type_id}", response_model=TransactionTypeResponse)
async def update_transaction_type_endpoint(
    type_id: int,
    transaction_type: TransactionTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Обновление типа транзакции по ID
    """
    updated_transaction_type = await update_transaction_type(
        db=db, type_id=type_id, transaction_type=transaction_type
    )
    if updated_transaction_type is None:
        raise HTTPException(status_code=404, detail="Transaction type not found")
    from app.core.cache import cache_manager

    await cache_manager.delete(f"transaction_type:{type_id}")
    await cache_manager.clear_pattern("transaction_types:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/transaction-types")
    await cache_manager.invalidate_http_cache("/api/transactions")
    await cache_manager.invalidate_http_cache("/api/transaction-types")
    return updated_transaction_type


@router.delete("/transaction-types/{type_id}")
async def delete_transaction_type_endpoint(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(require_master),
):
    """
    Удаление типа транзакции по ID
    """
    success = await delete_transaction_type(db=db, type_id=type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction type not found")
    from app.core.cache import cache_manager

    await cache_manager.delete(f"transaction_type:{type_id}")
    await cache_manager.clear_pattern("transaction_types:*")
    # Инвалидация кэша GET-запросов (middleware)
    await cache_manager.invalidate_http_cache("/api/v1/transaction-types")
    await cache_manager.invalidate_http_cache("/api/transactions")
    await cache_manager.invalidate_http_cache("/api/transaction-types")
    return {"message": "Transaction type deleted successfully"}


@router.post("/{transaction_id}/upload-file/")
async def upload_transaction_file(
    transaction_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Master | Employee | Administrator = Depends(get_current_active_user),
):
    """Загрузка файла к транзакции"""

    # Проверяем существование транзакции
    query = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        # Используем функцию безопасной загрузки файлов
        file_path, original_name, file_hash = await validate_and_save_file(
            file=file,
            upload_dir=settings.UPLOAD_DIR,
            subfolder="transactions",
            user_id=getattr(current_user, "id", None),
        )

        # Создаем запись в БД
        new_file = FileModel(
            filename=original_name,
            file_path=file_path,
            file_type="expense_receipt",
            transaction_id=transaction_id,
            uploaded_by=current_user.id,
        )
        db.add(new_file)
        await db.commit()

        return JSONResponse(
            content={
                "message": "Файл успешно загружен",
                "filename": original_name,
                "file_path": file_path,
            },
            headers={
                "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
                "Access-Control-Allow-Credentials": "true",
            },
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки файла: {str(e)}")
