from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt as PyJWT
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import os
import signal
from multiprocessing import Process
from collections import defaultdict
import json
from pathlib import Path

from job import StartJob
from lib import Libs, OO5List, Setting, TGBot

# JWT配置
SECRET_KEY = "your-secret-key-here"  # 生产环境应使用安全的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

# 用户token限制
MAX_TOKENS_PER_USER = 3
user_tokens = defaultdict(set)

# 黑名单文件路径
BLACKLIST_FILE = Path("./data/config/token_blacklist.json")
USER_TOKENS_FILE = Path("./data/config/user_tokens.json")

def load_blacklist():
    if not BLACKLIST_FILE.exists():
        return defaultdict(set)
    with open(BLACKLIST_FILE, 'r') as f:
        data = json.load(f)
        return defaultdict(set, {
            datetime.strptime(k, '%Y-%m-%d').date(): set(v) 
            for k, v in data.items()
        })

def load_user_tokens():
    if not USER_TOKENS_FILE.exists():
        return defaultdict(set)
    with open(USER_TOKENS_FILE, 'r') as f:
        data = json.load(f)
        return defaultdict(set, {k: set(v) for k, v in data.items()})

def save_blacklist(blacklist):
    # 将date对象转为字符串，将set转为list
    data = {
        k.strftime('%Y-%m-%d'): list(v)
        for k, v in blacklist.items()
    }
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump(data, f)

def save_user_tokens():
    data = {k: list(v) for k, v in user_tokens.items()}
    with open(USER_TOKENS_FILE, 'w') as f:
        json.dump(data, f)

# 初始化黑名单和用户token记录
token_blacklist = load_blacklist()
user_tokens = load_user_tokens()

# 初始化
app = FastAPI(
    title="115 Sync API",
    summary="115网盘同步工具API接口",
    version="1.0.0"
)

security = HTTPBearer()
LIBS = Libs()
o5List = OO5List()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模型定义
class Result(BaseModel):
    code: int
    msg: str
    data: dict | str | list | None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class SettingUpdate(BaseModel):
    username: str
    password: str
    telegram_bot_token: str
    telegram_user_id: str
class AccountCookie(BaseModel):
    cookie: str
    name: str

class TaskItem(BaseModel):
    id_of_115: str
    key: Optional[str] = ""
    cloud_type: str
    name: str
    path: str
    strm_root_path: str
    mount_path: Optional[str] = ""
    alist_server: Optional[str] = ""
    alist_115_path: Optional[str] = ""
    type: str
    path_of_115: str
    copy_meta_file: str
    copy_delay: int = 1
    webdav_url: Optional[str] = ""
    webdav_username: Optional[str] = ""
    webdav_password: Optional[str] = ""
    sync_type: str
    cron_str: Optional[str] = ""
    # 默认值
    strm_ext: List[str] = [
        ".mkv", ".mp4", ".ts", ".avi", ".mov", ".mpeg", ".mpg", ".wmv", 
        ".3gp", ".m4v", ".flv", ".m2ts", ".f4v", ".tp", ".iso"
    ]
    meta_ext: List[str] = [
        ".jpg", ".jpeg", ".png", ".webp", ".nfo", ".srt", ".ass", 
        ".svg", ".sup", ".lrc"
    ]

# JWT相关函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = PyJWT.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        # 检查token是否在黑名单中
        if credentials.credentials in token_blacklist[datetime.now(timezone.utc).date()]:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        payload = PyJWT.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except PyJWT.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except PyJWT.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# 路由定义
@app.post("/api/token", response_model=Token, summary="登录获取token", tags=["身份认证"])
async def login_for_access_token(user_data: UserLogin):
    settings = Setting()
    if user_data.username != settings.username or user_data.password != settings.password:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 检查用户当前token数量
    if len(user_tokens[user_data.username]) >= MAX_TOKENS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"已达到最大token数量限制({MAX_TOKENS_PER_USER}个)，请先注销其他登录"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    # 记录用户token
    user_tokens[user_data.username].add(access_token)
    save_user_tokens()
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/libs", response_model=Result, summary="获取同步目录列表", tags=["同步目录管理"])
async def get_libs(_: str = Depends(verify_token)) -> Result:
    data = [item.getJson() for item in LIBS.list()]
    return Result(code=200, msg="", data=data)

@app.post("/api/libs", response_model=Result, summary="添加同步目录", tags=["同步目录管理"])
async def add_lib(data: TaskItem, _: str = Depends(verify_token)) -> Result:
    rs, msg = LIBS.add(data)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@app.get("/api/lib/{key}", response_model=Result, summary="获取同步目录详情", tags=["同步目录管理"])
async def get_lib(key: str, _: str = Depends(verify_token)) -> Result:
    lib = LIBS.getLib(key)
    if lib is None:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    return {"code": 200, "msg": "", "data": lib.getJson()}

@app.delete("/api/lib/{key}", response_model=Result, summary="删除同步目录", tags=["同步目录管理"])
async def delete_lib(key: str, _: str = Depends(verify_token)) -> Result:
    rs, msg = LIBS.deleteLib(key)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return {"code": 200, "msg": "", "data": {}}

@app.put("/api/lib/{key}", response_model=Result, summary="更新同步目录", tags=["同步目录管理"])
async def update_lib(key: str, data: TaskItem, _: str = Depends(verify_token)) -> Result:
    rs, msg = LIBS.updateLib(key, data.model_dump(exclude_unset=True))
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return {"code": 200, "msg": "", "data": {}}

@app.post("/api/lib/sync/{key}", response_model=Result, summary="运行指定同步目录", tags=["同步目录管理"])
async def sync_lib(key: str, _: str = Depends(verify_token)) -> Result:
    lib = LIBS.getLib(key)
    if lib is None:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    if lib.extra.pid > 0:
        raise HTTPException(status_code=500, detail="该目录正在同步中...")
    p1 = Process(target=StartJob, kwargs={'key': key})
    p1.start()
    return {"code": 200, "msg": "已启动任务", "data": {}}

@app.post("/api/lib/stop/{key}", response_model=Result, summary="停止指定同步目录", tags=["同步目录管理"])
async def stop_lib(key: str, _: str = Depends(verify_token)) -> Result:
    lib = LIBS.getLib(key)
    if lib is None:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    if lib.extra.pid > 0:
        try:
            os.kill(lib.extra.pid, signal.SIGILL)
            lib.extra.status = 3
        except:
            lib.extra.status = 1
        lib.extra.pid = 0
        LIBS.saveExtra(lib)
    return {"code": 200, "msg": "已停止", "data": {}}

@app.get("/api/lib/log/{key}", response_model=Result, summary="获取指定同步目录的日志", tags=["同步目录管理"])
async def get_lib_log(key: str, _: str = Depends(verify_token)) -> Result:
    logFile = os.path.abspath(f"./data/logs/{key}.log")
    if not os.path.exists(logFile):
        return Result(code=200, msg="", data="")
    with open(logFile, mode='r', encoding='utf-8') as logfd:
        content = logfd.read()
    content = content.replace("\n", "<br />")
    return {"code": 200, "msg": "", "data": content}

@app.get("/api/oo5list", response_model=Result, summary="获取115账号列表", tags=["115账号管理"])
async def get_oo5_list(_: str = Depends(verify_token)) -> Result:
    data = [item.getJson() for item in o5List.getList()]
    return Result(code=200, msg="", data=data)

@app.post("/api/oo5list", response_model=Result, summary="添加115账号", tags=["115账号管理"])
async def add_oo5(data: AccountCookie, _: str = Depends(verify_token)) -> Result:
    rs, msg = o5List.add(data)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@app.get("/api/oo5/{key}", response_model=Result, summary="获取115账号详情", tags=["115账号管理"])
async def get_oo5(key: str, _: str = Depends(verify_token)) -> Result:
    oo5 = o5List.getLib(key)
    if oo5 is None:
        raise HTTPException(status_code=404, detail="115账号不存在")
    return Result(code=200, msg="", data=oo5)

@app.delete("/api/oo5/{key}", summary="删除115账号", tags=["115账号管理"])
async def delete_oo5(key: str, _: str = Depends(verify_token)) -> Result:
    rs, msg = o5List.delOO5(key)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@app.put("/api/oo5/{key}", response_model=Result, summary="更新115账号", tags=["115账号管理"])
async def update_oo5(key: str, data: dict, _: str = Depends(verify_token)) -> Result:
    rs, msg = o5List.updateOO5(key, data)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@app.get("/api/settings", response_model=Result, summary="获取配置", tags=["配置管理"])
async def get_settings(_: str = Depends(verify_token)) -> Result:
    settings = Setting()
    return Result(code=200, msg="", data=settings.__dict__)

@app.post("/api/settings", response_model=Result, summary="更新配置", tags=["配置管理"])
async def update_settings(data: SettingUpdate, _: str = Depends(verify_token)) -> Result:
    if data.username == '' or data.password == '':
        raise HTTPException(status_code=500, detail="用户名密码不能为空")
    
    settings = Setting()
    settings.username = data.username
    settings.password = data.password
    settings.telegram_bot_token = data.telegram_bot_token
    settings.telegram_user_id = data.telegram_user_id
    settings.save()
    
    if settings.telegram_bot_token and settings.telegram_user_id:
        bot = TGBot()
        rs, msg = bot.sendMsg("通知配置成功，稍后您将在此收到运行通知")
        if not rs:
            raise HTTPException(
                status_code=500, 
                detail=f'保存成功，但是Telegram通知配置出错：{msg}'
            )
    return Result(code=200, msg="", data=settings.__dict__)

@app.post("/api/dir", response_model=Result, summary="获取目录列表", tags=["目录管理"])
async def get_dirs(data: dict = {}, _: str = Depends(verify_token)) -> Result:
    base_dir = data.get('base_dir', '/')
    dirs = []
    for dir in os.listdir(base_dir):
        item = os.path.join(base_dir, dir)
        if not os.path.isfile(item):
            dirs.append(dir)
    return Result(code=200, msg="", data=dirs)

@app.get("/api/job", response_model=Result, summary="获取任务列表", tags=["任务管理"])
async def start_job(path: str, _: str = Depends(verify_token)) -> Result:
    if not path:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    
    lib = LIBS.getByPath(path)
    if lib is None:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    if lib.extra.pid > 0:
        raise HTTPException(status_code=500, detail="该目录正在同步中...")
    
    p1 = Process(target=StartJob, kwargs={'key': lib.key})
    p1.start()
    return Result(
        code=200, 
        msg=f'已启动任务，可调用API查询状态：/api/lib/{lib.key}', 
        data={}
    )

@app.post("/api/logout", response_model=Result, summary="注销", tags=["身份认证"])
async def logout(credentials: HTTPAuthorizationCredentials = Security(security)) -> Result:
    try:
        # 解码token获取用户名
        payload = PyJWT.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username:
            # 从用户token记录中移除
            user_tokens[username].discard(credentials.credentials)
            save_user_tokens()
    except:
        pass  # 即使token解码失败也继续处理
    
    # 将token加入黑名单
    today = datetime.now(timezone.utc)
    token_blacklist[today.date()].add(credentials.credentials)
    save_blacklist(token_blacklist)
    
    return Result(code=200, msg="已注销", data={})

def APIServer(host: str = "0.0.0.0", port: int = 11566):
    import uvicorn
    uvicorn.run(app, host=host, port=port) 