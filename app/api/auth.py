from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.auth import authenticate_user, create_access_token, get_current_active_user
from ..core.schemas import UserLogin, Token
from ..core.enhanced_schemas import (
    UserLogin as EnhancedUserLogin,
    TokenResponse,
    ErrorResponse,
)
from ..core.models import Master, Employee, Administrator
from ..core.config import settings
from ..core.security import LoginAttemptTracker, get_client_ip, CSRFProtection
import secrets
from app.core.cache import cache_manager

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.options("/login")
async def login_options():
    """Обработчик OPTIONS запросов для CORS"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@router.options("/me")
async def me_options():
    """Обработчик OPTIONS запросов для /me эндпоинта"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": settings.get_cors_origin_header(),
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Неверный логин или пароль"},
        400: {"model": ErrorResponse, "description": "Пользователь неактивен"},
        423: {"model": ErrorResponse, "description": "Аккаунт заблокирован"},
    },
)
async def login(
    user_credentials: EnhancedUserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Аутентификация пользователя с улучшенной безопасностью"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # Проверяем блокировку аккаунта
    if LoginAttemptTracker.is_account_locked(client_ip, user_credentials.login):
        remaining_time = LoginAttemptTracker.get_lockout_time_remaining(
            client_ip, user_credentials.login
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again in {remaining_time} seconds",
        )

    user = await authenticate_user(
        user_credentials.login, user_credentials.password, db
    )

    if not user:
        # Записываем неудачную попытку
        LoginAttemptTracker.record_login_attempt(
            client_ip, user_credentials.login, False, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if str(user.status) != "active":
        # Записываем неудачную попытку (неактивный пользователь)
        LoginAttemptTracker.record_login_attempt(
            client_ip, user_credentials.login, False, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Записываем успешную попытку
    LoginAttemptTracker.record_login_attempt(
        client_ip, user_credentials.login, True, user_agent
    )

    # Определяем тип пользователя и роль
    if isinstance(user, Master):
        user_type = "master"
        role = "master"
    elif isinstance(user, Employee):
        user_type = user.role.name
        role = user.role.name
    elif isinstance(user, Administrator):
        user_type = user.role.name
        role = user.role.name
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unknown user type",
        )

    # Создаем токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.login,
            "user_type": user_type,
            "user_id": user.id,
            "role": role,
        },
        expires_delta=access_token_expires,
    )

    # Генерируем session_id для CSRF защиты
    session_id = secrets.token_urlsafe(32)
    csrf_token = CSRFProtection.generate_csrf_token(session_id)

    # Устанавливаем токен в httpOnly cookie для безопасности
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # Включаем httpOnly для безопасности
        secure=False,  # Для разработки отключаем secure
        samesite="lax",  # Lax для работы с localhost
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # в секундах
        path="/",
        domain=None,  # Явно убираем domain
    )

    # Устанавливаем session_id cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain=None,
    )

    # Добавляем CORS заголовки
    response.headers["Access-Control-Allow-Origin"] = settings.get_cors_origin_header()
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": user_type,
        "role": role,
        "user_id": user.id,
        "city_id": getattr(user, "city_id", None),
        "csrf_token": csrf_token,
    }


@router.post("/logout")
async def logout(response: Response):
    """Выход из системы — удаление httpOnly cookie"""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,  # Включаем httpOnly для безопасности
        secure=False,  # Для разработки отключаем secure
        samesite="lax",
        domain=None,  # Явно убираем domain
    )

    # Удаляем session_id cookie
    response.delete_cookie(
        key="session_id",
        path="/",
        httponly=True,
        secure=False,
        samesite="lax",
        domain=None,
    )

    await cache_manager.invalidate_http_cache("/api/v1/users/me")
    await cache_manager.invalidate_http_cache("/api/v1/auth/status")
    await cache_manager.invalidate_http_cache("/api/users/me")
    await cache_manager.invalidate_http_cache("/api/auth/status")

    return {"message": "Logged out successfully"}


@router.get("/csrf-token")
async def get_csrf_token(request: Request):
    """Получение CSRF токена для защиты форм"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found"
        )

    csrf_token = CSRFProtection.generate_csrf_token(session_id)
    return {"csrf_token": csrf_token}


@router.get("/me")
async def read_users_me(
    current_user: Master | Employee | Administrator = Depends(get_current_active_user),
):
    """Получение информации о текущем пользователе"""
    base = {
        "id": current_user.id,
        "login": current_user.login,
        "status": current_user.status,
        "user_type": type(current_user).__name__.lower(),
        "role": (
            current_user.role.name
            if hasattr(current_user, "role") and current_user.role is not None
            else "master"
        ),
    }
    # Добавляем city_id для Employee и Master
    if hasattr(current_user, "city_id") and current_user.city_id is not None:
        base["city_id"] = current_user.city_id

    # Добавляем CORS заголовки
    response = JSONResponse(content=base)
    response.headers["Access-Control-Allow-Origin"] = settings.get_cors_origin_header()
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@router.get("/test")
async def test_endpoint():
    """Тестовый эндпоинт для проверки CORS"""
    return {"message": "CORS test successful", "status": "ok"}


# Debug endpoints защищены - доступны только в development
if settings.ENVIRONMENT == "development":

    @router.get("/debug")
    async def debug_endpoint(request: Request):
        """Отладочный эндпоинт для проверки cookie - ТОЛЬКО ДЛЯ DEVELOPMENT"""
        cookies = dict(request.cookies)
        headers = dict(request.headers)
        return {
            "environment": settings.ENVIRONMENT,
            "warning": "This endpoint is only available in development",
            "cookies": cookies,
            "headers": headers,
            "access_token": cookies.get("access_token"),
        }

    @router.get("/test-masters/")
    async def test_masters():
        """Тестовый эндпоинт для мастеров в auth роутере - ТОЛЬКО ДЛЯ DEVELOPMENT"""
        return {
            "environment": settings.ENVIRONMENT,
            "message": "Masters test endpoint works!",
            "data": [{"id": 1, "name": "Test Master"}],
        }
