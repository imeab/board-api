from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["회원"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="회원가입")
async def signup(body: SignupRequest, db: DbSession):
    email = body.email.lower()
    exists = await db.scalar(select(User.id).where(User.email == email))
    if exists:
        raise ConflictException("이미 가입된 이메일입니다.")

    user = User(email=email, password_hash=hash_password(body.password), name=body.name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse, summary="로그인 (JWT 발급)")
async def login(body: LoginRequest, db: DbSession):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))

    # 이메일이 없는지 비밀번호가 틀린지 구분하지 않음 (계정 존재 여부 노출 방지)
    if user is None or not verify_password(body.password, user.password_hash):
        raise UnauthorizedException("이메일 또는 비밀번호가 올바르지 않습니다.")

    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse, summary="내 정보")
async def me(user: CurrentUser):
    return user
