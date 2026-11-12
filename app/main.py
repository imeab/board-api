import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text

from app.core.database import Base, engine
from app.core.exceptions import register_exception_handlers
from app.routers import auth, posts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("board-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 테이블이 없으면 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB 테이블 준비 완료")
    yield
    await engine.dispose()


app = FastAPI(
    title="게시판 API",
    description="회원가입 / 로그인(JWT) / 게시글 / 댓글 RESTful API",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 요청의 메서드, 경로, 상태코드, 처리 시간을 로그로 남김"""
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{ms:.1f}"
    logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, ms)
    return response


app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(posts.comment_router)


@app.get("/health", tags=["상태"], summary="서버 / DB 상태 확인")
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))
    return {"status": "ok"}
