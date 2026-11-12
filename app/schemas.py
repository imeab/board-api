import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ----- 회원 -----
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64, description="8자 이상")
    name: str = Field(min_length=2, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("이름은 공백 제외 2자 이상이어야 합니다.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="만료까지 남은 초")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    role: str
    created_at: datetime


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


# ----- 게시글 -----
class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return v.strip()


class PostUpdate(BaseModel):
    """PATCH: 보낸 필드만 수정"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return v.strip() if v else v


class PostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: AuthorResponse
    view_count: int
    created_at: datetime


class PostDetail(PostSummary):
    content: str
    updated_at: datetime | None


class PostListResponse(BaseModel):
    items: list[PostSummary]
    total: int
    page: int
    size: int


# ----- 댓글 -----
class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return v.strip()


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    content: str
    author: AuthorResponse
    created_at: datetime
