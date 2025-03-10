# File: app/auth/middleware.py
from fastapi import Request

async def tenant_middleware(request: Request, call_next):
    subdomain = request.headers.get('X-Tenant-ID')
    request.state.tenant = get_tenant(subdomain)
    response = await call_next(request)
    return response
