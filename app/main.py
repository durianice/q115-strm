import json
from multiprocessing import Process
import random
import signal
import string
import os, sys
import time
from sys import path
from os.path import dirname
path.append(dirname(dirname(__file__)))

from app.utils.common import md5_str

cronProcess: Process | None = None
watchProcess: Process | None = None
webProcess: Process | None = None

def stop(sig, frame):
    global cronProcess
    global watchProcess
    global webProcess
    print("收到终止信号：{0}".format(sig))
    try:
        if watchProcess is not None:
            watchProcess.terminate()
            print("等待停止监控服务")
            watchProcess.join()
            print("监控服务已停止")
            watchProcess = None
    except Exception as e:
        print("监控服务停止出错：{0}".format(e))
    try:
        if cronProcess is not None:
            cronProcess.terminate()
            print("等待停止定时任务服务")
            cronProcess.join()
            print("定时任务服务已停止")
            cronProcess = None
    except Exception as e:
        print("定时任务服务停止出错：{0}".format(e))
    try:
        if webProcess is not None:
            webProcess.terminate()
            print("等待停止Web服务")
            webProcess.join()
            print("Web服务已停止")
            webProcess = None
    except Exception as e:
        print("Web服务停止出错：{0}".format(e))
    sys.exit(0)

if not os.path.exists('./data/logs'):
    os.makedirs('./data/logs')
if not os.path.exists('./data/config'):
    os.makedirs('./data/config')
if not os.path.exists('./data/config/setting.json'):
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    md5_password = md5_str(password)
    print("初始化setting.json，密码：{0}".format(password))
    setting = {"username": "admin", "password": md5_password, "telegram_bot_token": "", "telegram_user_id": ""}
    with open('./data/config/setting.json', mode='w', encoding='utf-8') as f:
        json.dump(setting, f)

from modules import StartCron, StartWatch
from api import APIServer

if __name__ == '__main__':
    # 启动监控服务
    watchProcess = Process(target=StartWatch)
    watchProcess.start()
    cronProcess = Process(target=StartCron)
    cronProcess.start()
    webProcess = Process(target=APIServer)
    webProcess.start()
    print("所有服务启动完毕，阻塞主进程并等待其他信号")
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    while(True):
        try:
            time.sleep(2)
        except:
            break
    stop(None, None)
    