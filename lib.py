import datetime, pytz
import json
import hashlib, os
from typing import List, Mapping
from crontab import CronTab

def GetNow():
    # 获取当前时间
    now = datetime.datetime.now()
    # 创建一个表示北京时区的对象
    beijing = pytz.timezone('Asia/Shanghai')
    # 将当前时间转换为北京时区
    now_beijing = now.astimezone(beijing)
    print(now_beijing)
    return now_beijing.strftime("%Y-%m-%d %H:%M:%S")

class LibExtra:
    pid: str # 正在运行的进程ID
    status: int # 运行状态: 1-正常，2-运行中，3-中断
    last_sync_at: str # 最后运行时间
    last_sync_result: Mapping[str, List[int]]

    def __init__(self, pid: int = 0, status: int = 1, last_sync_at: str = '', last_sync_result: Mapping[str, List[int]] = {'strm': [0,0], 'meta': [0,0],'delete': [0,0]}):
        self.pid = pid
        self.status = status
        self.last_sync_at = last_sync_at
        self.last_sync_result = last_sync_result

    def getJson(self):
        dict = self.__dict__
        return dict

class LibBase:
    key: str # 标识
    name: str # 名称
    path: str # 路径
    type: str # strm类型，'本地路径' | 'WebDAV'
    strm_root_path: str # strm根目录
    path_of_115: str # 115挂载根目录
    copy_meta_file: int # 元数据选项：1-关闭，2-复制，3-软链接
    copy_delay: int | float # 元数据复制间隔
    webdav_url: str # webdav服务器链接
    webdav_username: str # webdav服务器用户名
    webdav_password: str # webdav服务器密码
    sync_type: str # 同步类型，'定时' | '监控变更'
    cron_str: str # 定时同步规则
    id_of_115: str # 115账号标识
    strm_ext: list[str] # strm扩展名
    meta_ext: list[str] # 元数据扩展名

    def __init__(self, data: None | dict):
        if data is not None:
            self.key = data['key']
            self.name = data['name']
            self.path = data['path']
            self.type = data['type']
            self.strm_root_path = data['strm_root_path']
            self.path_of_115 = data['path_of_115']
            self.copy_meta_file = data['copy_meta_file']
            self.copy_delay = data['copy_delay']
            self.webdav_url = data['webdav_url']
            self.webdav_username = data['webdav_username']
            self.webdav_password = data['webdav_password']
            self.sync_type = data['sync_type']
            self.cron_str = data['cron_str']
            self.id_of_115 = data.get('id_of_115')
            self.strm_ext = data.get('strm_ext')
            self.meta_ext = data.get('meta_ext')
            if self.key == '':
                m = hashlib.md5()
                m.update(self.path.encode(encoding='UTF-8'))
                self.key = m.hexdigest()


class Lib(LibBase):
    extra: LibExtra

    def __init__(self, data: None | dict):
        super().__init__(data)
        hasExtra = False
        if data is not None:
            extra = data.get('extra')
            if extra is not None:
                hasExtra = True
                self.extra = LibExtra(
                    pid=data['extra']['pid'],
                    status=data['extra']['status'],
                    last_sync_at=data['extra']['last_sync_at'],
                    last_sync_result=data['extra']['last_sync_result']
                )
        if hasExtra == False:
            self.extra = LibExtra()


    def validate(self) -> tuple[bool, str]:
        # 验证路径是否存在

        # 验证STRM根目录是否存在
        # if not os.path.exists(self.strm_root_path):
        #     return False, 'STRM根目录不存在'
        # # 验证115挂在根目录是否存在
        # if self.path_of_115 != '' and not os.path.exists(self.path_of_115):
        #     return False, '115挂载根目录不存在'
        return True, ''

    def cron(self):
        # 处理定时任务

        cron = CronTab(user='root')
        iter = cron.find_comment(self.key)
        existsJob = None
        for i in iter:
            existsJob = i
        if self.sync_type == '定时':
            if existsJob == None:
                jobFile = os.path.abspath('./job.py')
                job = cron.new(comment="%s" % self.key, command="python3 %s -k %s" % (jobFile, self.key))
                job.setall(self.cron_str)
                cron.write(user='root')
        else:
            if existsJob is not None:
                # 删除定时任务
                cron.remove(existsJob)
        pass

    def getJson(self):
        dict = self.__dict__
        if isinstance(self.extra, LibExtra):
            dict['extra'] = self.extra.getJson()
        else:
            dict['extra'] = self.extra
        return dict
        
    
def jsonHook(obj):
    return obj.getJson()

class Libs:
    libs_file: str = os.path.abspath("./data/config/libs.json")
    libList: Mapping[str, List[Lib]] # 同步目录列表

    def __init__(self):
        self.libList = {}
        self.loadFromFile()
    
    def loadFromFile(self):
        libs = {}
        if os.path.exists(self.libs_file):
            with open(self.libs_file, mode='r', encoding='utf-8') as fd_libs:
                jsonLibs = json.load(fd_libs)
            for k in jsonLibs:
                libs[k] = Lib(jsonLibs[k])
        self.libList = libs
        return True
    
    def list(self) -> List[Lib]:
        self.loadFromFile()
        return self.libList.values()
    
    def save(self) -> bool:
        with open(self.libs_file, mode='w', encoding='utf-8') as fd_libs:
            json.dump(self.libList, fd_libs, default=jsonHook)
        return True
        
    def getLib(self, key: str) -> Lib | None:
        self.loadFromFile()
        return self.libList.get(key)
    
    def add(self, data: dict) -> tuple[bool, str]:
        for k, v in self.libList.items():
            if v.path == data['path']:
                return False, '同步目录已存在'
            if v.name == data['name']:
                return False, '同步目录名称已存在'
        data['extra'] = {
            'pid': 0,
            'status': 1,
            'last_sync_at': '',
            'last_sync_result': {
                'strm': [0, 0],
                'meta': [0, 0],
                'delete': [0, 0]
            }
        }
        lib = Lib(data)
        rs, msg = lib.validate()
        if rs is False:
            return rs, msg
        self.libList[lib.key] = lib
        self.save()
        lib.cron()
        return True, ''

    def updateLib(self, key: str, data: dict) -> tuple[bool, str]:
        lib = self.getLib(key)
        if lib is None:
            return False, '同步目录不存在'
        del data['extra']
        for k in data:
            lib.__setattr__(k, data[k])
        self.libList[key] = lib
        self.save()
        lib.cron()
        return True, ''

    def saveExtra(self, lib: Lib):
        self.libList[lib.key] = lib
        self.save()
        pass

    def deleteLib(self, key: str) -> tuple[bool, str]:
        del self.libList[key]
        self.save()
        return True, ''
    
class OO5:
    key: str
    name: str
    cookie: str
    status: int
    created_at: str
    updated_at: str

    def __init__(self, data: dict):
        self.name = data['name']
        self.cookie = data['cookie']
        self.status = data['status']
        self.created_at = data['created_at']
        self.updated_at = data['updated_at']
        self.key = data['key']
    
    def getJson(self):
        dict = self.__dict__
        return dict
    

class OO5List:
    oo5_files = os.path.abspath("./data/config/115.json")
    list: Mapping[str, List[OO5]] # 115账号列表

    def __init__(self):
        self.list = {}
        self.loadFromFile()
    
    def loadFromFile(self):
        list = {}
        if os.path.exists(self.oo5_files):
            with open(self.oo5_files, mode='r', encoding='utf-8') as fd_oo5:
                jsonList = json.load(fd_oo5)
            for k in jsonList:
                list[k] = OO5(jsonList[k])
        self.list = list
        return True

    def save(self) -> bool:
        with open(self.oo5_files, mode='w', encoding='utf-8') as o:
            json.dump(self.list, o, default=jsonHook)
        return True
    
    def get(self, key: str) -> OO5 | None:
        return self.list.get(key)
    
    def getList(self) -> List[OO5]:
        self.loadFromFile()
        return self.list.values()
    
    def add(self, data: dict) -> tuple[bool, str]:
        for key in self.list:
            if self.list[key].name == data['name'] or self.list[key].cookie == data['cookie']:
                return False, '名称或者cookie已存在'
        data['created_at'] = GetNow()
        data['updated_at'] = ''
        data['status'] = 0
        m = hashlib.md5()
        m.update(data['name'].encode(encoding='UTF-8'))
        data['key'] = m.hexdigest()
        oo5 = OO5(data)
        self.list[oo5.key] = oo5
        self.save()
        return True, ''
    
    def updateOO5(self, key: str, data: dict):
        oo5 = self.get(key)
        if oo5 is None:
            return False, '115账号不存在'
        oo5.name = data['name']
        oo5.cookie = data['cookie']
        oo5.updated_at = GetNow()
        self.list[key] = oo5
        self.save()
        return True, ''

    def delOO5(self, key: str):
        oo5 = self.get(key)
        if oo5 is None:
            return True, ''
        # 检查是否有在使用
        libs = Libs()
        libList = libs.list()
        for item in libList:
            if item.id_of_115 == key:
                return False, '该账号使用中'
        del self.list[key]
        self.save()
        return True, ''

if __name__ == '__main__':
    # with open('./data/config/libs.json', mode='r', encoding='utf-8') as fd_libs:
    #     jsonLibs = json.load(fd_libs)
    # newLibs = {}
    # for item in jsonLibs:
    #     newLibs[item['key']] = item
    # with open('./data/config/libs.json', mode='w', encoding='utf-8') as fd_libs:
    #     json.dump(newLibs, fd_libs)
    pass