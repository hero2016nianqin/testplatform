from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.response import ApiResponse


class BusinessException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


class AuthError(BusinessException):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(code=401, message=message, status_code=401)


class ForbiddenError(BusinessException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(code=403, message=message, status_code=403)


class NotFoundError(BusinessException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message, status_code=404)


class ConflictError(BusinessException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(code=409, message=message, status_code=409)


async def _business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(code=exc.code, message=exc.message).model_dump(),
    )


async def _generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ApiResponse(code=500, message=f"服务器内部错误: {str(exc)}").model_dump(),
    )


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(BusinessException, _business_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
