#FastAPI 入口

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import data

app = FastAPI(title="智能坐姿监测系统 API", version="1.0.0")

# 允许前端 Vue 开发服务器跨域访问

origins = [
    "http://localhost:5173",   #使用 Vue 开发默认端口
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由

app.include_router(data.router, prefix="/api/v1/data", tags=["data"])

@app.get("/")
def root():
    return {"message": "Smart Sitting Posture Monitor Backend"}