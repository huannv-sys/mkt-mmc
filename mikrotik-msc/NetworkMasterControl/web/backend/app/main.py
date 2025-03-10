from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routes import devices, auth
from app.utils.security import verify_token

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with JWT protection
app.include_router(
    devices.router,
    prefix="/api/devices",
    dependencies=[Depends(verify_token)]
)
app.include_router(auth.router, prefix="/api/auth")

@app.get("/")
def read_root():
    return {"status": "CMS Backend Running"}
