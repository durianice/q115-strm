from fastapi import FastAPI
from app.api.routes import router
from app.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="115 Sync API",
    summary="115网盘同步工具API接口",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)

def APIServer(host: str = "0.0.0.0", port: int = 11566):
    import uvicorn
    uvicorn.run(app, host=host, port=port) 