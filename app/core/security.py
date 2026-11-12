import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


# ----- 비밀번호 -----
def hash_password(password: str) -> str:
    """비밀번호는 bcrypt로 해싱해서 저장 (원문 저장 X)"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ----- JWT -----
def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """토큰과 만료까지 남은 초를 반환"""
    now = datetime.now(timezone.utc)
    expires_in = settings.access_token_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),  # 만료 시간
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("토큰이 만료되었습니다. 다시 로그인해 주세요.")
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedException("유효하지 않은 토큰입니다.")
