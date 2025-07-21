from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..core.database import get_db
from ..core import crud, schemas
from ..core.config import settings
from datetime import datetime
import logging
import json
import urllib.parse
import hmac
import hashlib

router = APIRouter()


# Функция для проверки безопасности webhook
async def verify_webhook_security(
    request: Request, x_signature: Optional[str] = Header(None, alias="X-Signature")
):
    """Проверка безопасности webhook - IP whitelist и подпись"""
    # Получаем реальный IP через прокси заголовки
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Проверка IP адреса (если настроен whitelist)
    allowed_ips = settings.get_mango_allowed_ips
    if allowed_ips and client_ip not in allowed_ips:
        logging.warning(
            f"MANGO WEBHOOK: Blocked request from unauthorized IP: {client_ip}"
        )
        raise HTTPException(status_code=403, detail=f"IP {client_ip} not allowed")

    # Проверка подписи (если настроен секрет)
    if settings.MANGO_WEBHOOK_SECRET:
        if not x_signature:
            logging.warning("MANGO WEBHOOK: Missing signature header")
            raise HTTPException(status_code=403, detail="Missing signature")

        # Здесь должна быть проверка подписи по алгоритму Mango
        # Пока просто базовая проверка
        expected_signature = (
            x_signature  # TODO: Implement actual signature verification
        )

    logging.info(f"MANGO WEBHOOK: Accepted request from IP: {client_ip}")
    return True


@router.post("/webhook")
async def mango_webhook_root(
    request: Request,
    db: AsyncSession = Depends(get_db),
    security_check: bool = Depends(verify_webhook_security),
):
    return await mango_webhook(request, db, subpath="", security_check=security_check)


@router.post("/webhook/{subpath:path}")
async def mango_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    subpath: str = "",
    security_check: bool = Depends(verify_webhook_security),
):
    # Логируем сырое тело
    raw_body = await request.body()
    logging.warning(f"MANGO RAW BODY: {raw_body}")

    # Пробуем получить form-data и распарсить JSON
    try:
        form = await request.form()
        json_str = form.get("json")
        if json_str and isinstance(json_str, str):
            json_str = urllib.parse.unquote_plus(json_str)
            data = json.loads(json_str)
        else:
            data = {}
    except Exception as e:
        logging.warning(f"FORM PARSE ERROR: {e}")
        data = {}

    logging.warning(f"MANGO PARSED DATA: {data}")

    # Получаем информацию о звонке
    from_number = data.get("from", {}).get("number")
    to_number = data.get("to", {}).get("number")
    call_id = data.get("call_id")
    seq = data.get("seq")
    call_state = data.get("call_state")

    logging.warning(
        f"MANGO CALL INFO: CallID={call_id}, Seq={seq}, State={call_state}, From={from_number}, To={to_number}"
    )

    # Проверяем базовые данные
    if not from_number or not to_number or not call_id:
        logging.warning("MANGO SKIP: Missing basic call data")
        return {"ok": True, "detail": "Missing call data"}

    # ВАЖНО: Обрабатываем заявку только для завершенных звонков
    # Игнорируем промежуточные события, чтобы избежать дублей
    if call_state not in ["Disconnected", "Completed", "Finished"]:
        logging.warning(
            f"MANGO SKIP: Call state '{call_state}' not final, waiting for completion"
        )
        return {"ok": True, "detail": f"Ignoring intermediate state: {call_state}"}

    # Получаем номер, на который позвонили (line_number)
    phone_number = None
    if "to" in data and isinstance(data["to"], dict):
        phone_number = data["to"].get("line_number")
    if not phone_number:
        logging.warning("MANGO SKIP: No line_number found")
        return {"ok": True, "detail": "Нет номера для поиска РК"}

    # ДВОЙНАЯ ПРОВЕРКА на дубликаты: по телефону И по call_id

    # 1. Проверка по номеру телефона (за последние 30 минут)
    existing_by_phone = await crud.get_existing_new_request_by_phone(db, from_number)
    if existing_by_phone:
        logging.warning(
            f"MANGO DUPLICATE BLOCKED BY PHONE: Phone {from_number}, existing request ID {existing_by_phone.id}, created at {existing_by_phone.created_at}"
        )
        return {
            "ok": True,
            "detail": f"Заявка уже существует по телефону (ID: {existing_by_phone.id})",
        }

    # 2. Проверка по call_id (если есть запись в примечаниях)
    try:
        from sqlalchemy import select
        from ..core.models import Request

        existing_by_call_id = await db.execute(
            select(Request).where(
                Request.call_center_notes.like(f"%call_id:{call_id}%")
            )
        )
        existing_call = existing_by_call_id.scalar_one_or_none()
        if existing_call:
            logging.warning(
                f"MANGO DUPLICATE BLOCKED BY CALL_ID: CallID {call_id}, existing request ID {existing_call.id}"
            )
            return {
                "ok": True,
                "detail": f"Заявка уже существует по call_id (ID: {existing_call.id})",
            }
    except Exception as e:
        logging.warning(f"MANGO CALL_ID CHECK ERROR: {e}")

    # Найти рекламную кампанию по номеру
    campaign = await crud.get_advertising_campaign_by_phone(db, phone_number)
    if not campaign:
        logging.warning(f"MANGO SKIP: No campaign found for phone {phone_number}")
        return {"ok": True, "detail": "Не найдена РК для номера"}

    city_id = campaign.city_id

    # Определяем тип заявки: 'Впервые' или 'Повтор'
    # ВАЖНО: Проверяем ВСЕ заявки, не только за последние 30 минут
    is_first_time = await crud.check_client_first_time(db, from_number)
    if is_first_time:
        request_type = await crud.get_request_type_by_name(db, "Впервые")
        logging.warning(
            f"MANGO TYPE DECISION: Phone {from_number} - FIRST TIME (Впервые)"
        )
    else:
        request_type = await crud.get_request_type_by_name(db, "Повтор")
        logging.warning(f"MANGO TYPE DECISION: Phone {from_number} - REPEAT (Повтор)")
    request_type_id = request_type.id if request_type else None

    # ФИНАЛЬНАЯ ПРОВЕРКА перед созданием (защита от race condition)
    final_check = await crud.get_existing_new_request_by_phone(db, from_number)
    if final_check:
        logging.warning(
            f"MANGO FINAL CHECK BLOCKED: Phone {from_number}, existing request ID {final_check.id}"
        )
        return {
            "ok": True,
            "detail": f"Заявка уже существует (финальная проверка, ID: {final_check.id})",
        }

    request_in = schemas.RequestCreate(
        advertising_campaign_id=campaign.id,
        city_id=campaign.city_id,
        request_type_id=request_type_id,
        client_phone=from_number,
        status="Новая",
        ats_number=phone_number,
        result=None,
        call_center_name=None,
        call_center_notes=None,
        avito_chat_id=None,
    )

    try:
        new_request = await crud.create_request(db, request_in)
        request_type_name = request_type.name if request_type else "Unknown"

        logging.warning(
            f"MANGO REQUEST CREATED: Phone {from_number}, Type: {request_type_name}, ID: {new_request.id}, Campaign: {campaign.name}, CallID: {call_id}"
        )

        return {
            "ok": True,
            "request_id": new_request.id,
            "type": request_type_name,
            "call_id": call_id,
        }
    except Exception as e:
        logging.error(
            f"MANGO REQUEST CREATION ERROR: Phone {from_number}, CallID {call_id}, Error: {e}"
        )
        # Возможно, заявка уже была создана другим процессом
        await db.rollback()
        return {"ok": True, "detail": f"Ошибка создания заявки: {str(e)}"}
