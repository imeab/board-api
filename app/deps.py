from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.models import User

# Swagger의 Authorize 버튼에 토큰을 넣으면 Authorization: Bearer <토큰> 헤더로 전달됨
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """토큰을 확인해서 로그인한 회원을 돌려줌 (없거나 틀리면 401)"""
    if credentials is None:
        raise UnauthorizedException("로그인이 필요합니다.")

    user_id = decode_access_token(credentials.credentials)
    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedException("존재하지 않는 회원입니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
