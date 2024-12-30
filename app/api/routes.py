from fastapi import APIRouter, Depends, HTTPException
from app.utils.common import md5_str
from app.utils.jwt import verify_token
from app.api.models import SettingUpdate, AccountCookie, TaskItem, Result
import os
import signal
from multiprocessing import Process

from app.modules.job import StartJob
from app.core.lib import Libs, OO5List, Setting, TGBot

LIBS = Libs()
o5List = OO5List()

router = APIRouter(
    prefix="/api", 
    dependencies=[Depends(verify_token)]
)

@router.get("/libs", response_model=Result, summary="获取同步目录列表", tags=["同步目录管理"])
async def get_libs(_: str = Depends(verify_token)) -> Result:
    data = [item.getJson() for item in LIBS.list()]
    return Result(code=200, msg="", data=data)

@router.post("/libs", response_model=Result, summary="添加同步目录", tags=["同步目录管理"])
async def add_lib(data: TaskItem, _: str = Depends(verify_token)) -> Result:
    rs, msg = LIBS.add(data.model_dump(exclude_unset=True))
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@router.get("/lib/{key}", response_model=Result, summary="获取同步目录详情", tags=["同步目录管理"])
async def get_lib(key: str, _: str = Depends(verify_token)) -> Result:
    lib = LIBS.getLib(key)
    if lib is None:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    return {"code": 200, "msg": "", "data": lib.getJson()}

@router.delete("/lib/{key}", response_model=Result, summary="删除同步目录", tags=["同步目录管理"])
async def delete_lib(key: str, _: str = Depends(verify_token)) -> Result:
    rs, msg = LIBS.deleteLib(key)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return {"code": 200, "msg": "", "data": {}}

@router.put("/lib/{key}", response_model=Result, summary="更新同步目录", tags=["同步目录管理"])
async def update_lib(key: str, data: TaskItem, _: str = Depends(verify_token)) -> Result:
    rs, msg = LIBS.updateLib(key, data.model_dump(exclude_unset=True))
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return {"code": 200, "msg": "", "data": {}}

@router.post("/lib/sync/{key}", response_model=Result, summary="运行指定同步目录", tags=["同步目录管理"])
async def sync_lib(key: str, _: str = Depends(verify_token)) -> Result:
    lib = LIBS.getLib(key)
    if lib is None:
        raise HTTPException(status_code=404, detail="同步目录不存在")
    if lib.extra.pid > 0:
        raise HTTPException(status_code=500, detail="该目录正在同步中...")
    p1 = Process(target=StartJob, kwargs={'key': key})
    p1.start()
    return {"code": 200, "msg": "已启动任务", "data": {}}

@router.post("/lib/stop/{key}", response_model=Result, summary="停止指定同步目录", tags=["同步目录管理"])
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

@router.get("/lib/log/{key}", response_model=Result, summary="获取指定同步目录的日志", tags=["同步目录管理"])
async def get_lib_log(key: str, _: str = Depends(verify_token)) -> Result:
    logFile = os.path.abspath(f"../../data/logs/{key}.log")
    if not os.path.exists(logFile):
        return Result(code=200, msg="", data="")
    with open(logFile, mode='r', encoding='utf-8') as logfd:
        content = logfd.read()
    content = content.replace("\n", "<br />")
    return {"code": 200, "msg": "", "data": content}

@router.get("/oo5list", response_model=Result, summary="获取115账号列表", tags=["115账号管理"])
async def get_oo5_list(_: str = Depends(verify_token)) -> Result:
    data = [item.getJson() for item in o5List.getList()]
    return Result(code=200, msg="", data=data)

@router.post("/oo5list", response_model=Result, summary="添加115账号", tags=["115账号管理"])
async def add_oo5(data: AccountCookie, _: str = Depends(verify_token)) -> Result:
    rs, msg = o5List.add(data.model_dump(exclude_unset=True))
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@router.get("/oo5/{key}", response_model=Result, summary="获取115账号详情", tags=["115账号管理"])
async def get_oo5(key: str, _: str = Depends(verify_token)) -> Result:
    oo5 = o5List.get(key)
    if oo5 is None:
        raise HTTPException(status_code=404, detail="115账号不存在")
    return Result(code=200, msg="", data=oo5.getJson())

@router.delete("/oo5/{key}", summary="删除115账号", tags=["115账号管理"])
async def delete_oo5(key: str, _: str = Depends(verify_token)) -> Result:
    rs, msg = o5List.delOO5(key)
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@router.put("/oo5/{key}", response_model=Result, summary="更新115账号", tags=["115账号管理"])
async def update_oo5(key: str, data: AccountCookie, _: str = Depends(verify_token)) -> Result:
    rs, msg = o5List.updateOO5(key, data.model_dump(exclude_unset=True))
    if not rs:
        raise HTTPException(status_code=500, detail=msg)
    return Result(code=200, msg="", data={})

@router.get("/settings", response_model=Result, summary="获取配置", tags=["配置管理"])
async def get_settings(_: str = Depends(verify_token)) -> Result:
    settings = Setting()
    return Result(code=200, msg="", data=settings.__dict__)

@router.post("/settings", response_model=Result, summary="更新配置", tags=["配置管理"])
async def update_settings(data: SettingUpdate, _: str = Depends(verify_token)) -> Result:
    if data.username == '' or data.password == '':
        raise HTTPException(status_code=500, detail="用户名密码不能为空")
    
    settings = Setting()
    settings.username = data.username
    settings.password = md5_str(data.password)
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

@router.post("/dir", response_model=Result, summary="获取目录列表", tags=["目录管理"])
async def get_dirs(data: dict = {}, _: str = Depends(verify_token)) -> Result:
    base_dir = data.get('base_dir', '/')
    dirs = []
    for dir in os.listdir(base_dir):
        item = os.path.join(base_dir, dir)
        if not os.path.isfile(item):
            dirs.append(dir)
    return Result(code=200, msg="", data=dirs)

@router.get("/job", response_model=Result, summary="获取任务列表", tags=["任务管理"])
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