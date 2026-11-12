from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    """서비스에서 던지는 예외. 핸들러가 공통 에러 형식으로 바꿔서 응답"""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFoundException(AppException):
    def __init__(self, message: str = "대상을 찾을 수 없습니다."):
        super().__init__(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "인증이 필요합니다."):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "권한이 없습니다."):
        super().__init__(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(status.HTTP_409_CONFLICT, "CONFLICT", message)


def error_body(code: str, message: str, details: list | None = None) -> dict:
    """모든 에러 응답을 같은 모양으로"""
    return {"success": False, "error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(error_body(exc.code, exc.message), exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # 어떤 필드가 왜 틀렸는지만 간단하게 정리
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            error_body("VALIDATION_ERROR", "입력값이 올바르지 않습니다.", details),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(error_body("HTTP_ERROR", str(exc.detail)), exc.status_code)
