from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


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
    cookie: str = Field(..., title="115账号cookie")
    name: str = Field(..., title="115账号名称")
    created_at: Optional[str] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updated_at: Optional[str] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status: Optional[int] = 0
    key: Optional[str] = ""

class TaskItem(BaseModel):
    id_of_115: str = Field("", title="115账号标识")
    # key: Optional[str] = Field("", title="同步目录标识")
    cloud_type: str = Field("115", title="网盘类型")
    name: str = Field("任务1", title="任务名称")
    path: str = Field("Media/电视剧/儿童", title="网盘资源路径")
    strm_root_path: str = Field("./data/config/strm", title="strm根目录")
    mount_path: Optional[str] = Field("", title="alist挂载根文件夹")
    alist_server: Optional[str] = Field("", title="alist服务器地址")
    alist_115_path: Optional[str] = Field("", title="alist中115路径")
    type: str = Field("本地路径", title="同步类型") # 同步类型，'本地路径' | 'WebDAV' | 'alist302'
    path_of_115: str = Field("/mnt/115", title="115挂载根目录")
    copy_meta_file: int = Field(1, title="元数据选项") # 元数据选项：1-关闭，2-复制，3-软链接
    copy_delay: int = Field(1, title="元数据复制间隔") 
    webdav_url: Optional[str] = Field("", title="webdav服务器链接")
    webdav_username: Optional[str] = Field("", title="webdav服务器用户名")
    webdav_password: Optional[str] = Field("", title="webdav服务器密码")
    sync_type: str = Field("手动", title="同步类型")
    cron_str: Optional[str] = Field("", title="定时同步规则")
    strm_ext: List[str] = Field(None, title="strm扩展名", examples=[".mkv", ".mp4"])
    meta_ext: List[str] = Field(None, title="元数据扩展名", examples=[".jpg", ".jpeg", ".png"])
    extra: Optional[dict] = Field(None, title="额外配置")