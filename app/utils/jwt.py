from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
from typing import Optional
import jwt as PyJWT
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.utils.common import resolve_path


SECRET_KEY = "bt2n7fMZ1Ss5aYxncpaNmbrTZBTwi8wj"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080
security = HTTPBearer()

# 用户token限制
MAX_TOKENS_PER_USER = 3
user_tokens = defaultdict(set)

# 黑名单文件路径
BLACKLIST_FILE = resolve_path("../../data/config/token_blacklist.json")
USER_TOKENS_FILE = resolve_path("../../data/config/user_tokens.json")

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
        if username is None or username == "":
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except PyJWT.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except PyJWT.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")