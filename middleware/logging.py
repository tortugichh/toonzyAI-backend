from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        logging.info(f"Request: {request.method} {request.url} Body: {body}")
        response = await call_next(request)
        logging.info(f"Response status: {response.status_code}")
        return response 