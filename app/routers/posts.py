from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, or_, select

from app.core.exceptions import ForbiddenException, NotFoundException
from app.deps import CurrentUser, DbSession
from app.models import Comment, Post, User
from app.schemas import (
    CommentCreate,
    CommentResponse,
    PostCreate,
    PostDetail,
    PostListResponse,
    PostUpdate,
)

router = APIRouter(prefix="/api/v1/posts", tags=["게시글"])
comment_router = APIRouter(prefix="/api/v1/comments", tags=["댓글"])


def check_owner(author_id, user: User) -> None:
    """작성자 본인 또는 관리자만 수정/삭제 가능"""
    if author_id != user.id and user.role != "ADMIN":
        raise ForbiddenException("작성자만 수정하거나 삭제할 수 있습니다.")


async def get_post_or_404(db: DbSession, post_id: int) -> Post:
    post = await db.get(Post, post_id)
    if post is None:
        raise NotFoundException("게시글을 찾을 수 없습니다.")
    return post


# ----- 게시글 -----
@router.get("", response_model=PostListResponse, summary="게시글 목록")
async def list_posts(
    db: DbSession,
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=50, description="한 페이지 개수"),
    keyword: str | None = Query(None, max_length=50, description="제목/내용 검색"),
):
    query = select(Post)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(or_(Post.title.ilike(like), Post.content.ilike(like)))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = await db.scalars(
        query.order_by(Post.id.desc()).offset((page - 1) * size).limit(size)
    )
    return PostListResponse(items=list(rows), total=total or 0, page=page, size=size)


@router.get("/{post_id}", response_model=PostDetail, summary="게시글 상세 (조회수 +1)")
async def get_post(post_id: int, db: DbSession):
    post = await get_post_or_404(db, post_id)
    post.view_count += 1
    await db.commit()
    await db.refresh(post)
    return post


@router.post("", response_model=PostDetail, status_code=status.HTTP_201_CREATED, summary="게시글 작성")
async def create_post(body: PostCreate, user: CurrentUser, db: DbSession):
    post = Post(title=body.title, content=body.content, author_id=user.id)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.patch("/{post_id}", response_model=PostDetail, summary="게시글 수정 (작성자만)")
async def update_post(post_id: int, body: PostUpdate, user: CurrentUser, db: DbSession):
    post = await get_post_or_404(db, post_id)
    check_owner(post.author_id, user)

    # 보낸 필드만 바꾸기
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT, summary="게시글 삭제 (작성자만)")
async def delete_post(post_id: int, user: CurrentUser, db: DbSession):
    post = await get_post_or_404(db, post_id)
    check_owner(post.author_id, user)
    await db.delete(post)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- 댓글 -----
@router.get("/{post_id}/comments", response_model=list[CommentResponse], summary="댓글 목록")
async def list_comments(post_id: int, db: DbSession):
    await get_post_or_404(db, post_id)
    rows = await db.scalars(select(Comment).where(Comment.post_id == post_id).order_by(Comment.id))
    return list(rows)


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="댓글 작성",
)
async def create_comment(post_id: int, body: CommentCreate, user: CurrentUser, db: DbSession):
    await get_post_or_404(db, post_id)
    comment = Comment(post_id=post_id, content=body.content, author_id=user.id)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@comment_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="댓글 삭제 (작성자만)")
async def delete_comment(comment_id: int, user: CurrentUser, db: DbSession):
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise NotFoundException("댓글을 찾을 수 없습니다.")
    check_owner(comment.author_id, user)
    await db.delete(comment)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
