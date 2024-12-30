from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
import jwt as PyJWT
from app.api.models import Result, Token, UserLogin
from app.core.lib import Setting
from app.utils.common import md5_str
from app.utils.jwt import security, MAX_TOKENS_PER_USER, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, user_tokens, token_blacklist, save_blacklist, save_user_tokens

router = APIRouter(
    prefix="/api"
)

# 路由定义
@router.post("/login", response_model=Token, summary="登录", tags=["身份认证"])
async def login_for_access_token(user_data: UserLogin):
    settings = Setting()
    if user_data.username != settings.username or md5_str(user_data.password) != settings.password:
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
    # 生成token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    # 记录用户token
    user_tokens[user_data.username].add(access_token)
    save_user_tokens()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout", response_model=Result, summary="注销", tags=["身份认证"])
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