import hashlib
from pathlib import Path

def resolve_path(file_path: str) -> Path:
    """
    确保目标目录存在，并返回规范化的绝对路径。

    参数:
        file_path (str): 目标文件的路径，可以是相对路径或绝对路径。

    返回:
        Path: 规范化后的绝对路径。
    """
    # 获取当前脚本所在的目录
    script_dir = Path(__file__).parent

    # 将相对路径基于脚本目录解析为绝对路径
    path = Path(file_path)
    if not path.is_absolute():
        path = (script_dir / path).resolve()

    # 确保目标目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    # 返回规范化的绝对路径
    return path

def md5_str(text: str) -> str:
    """
    将字符串转换为md5值
    :param text: 字符串
    :return: md5值
    """
    if text == '':
        return ''
    return hashlib.md5(text.encode()).hexdigest()
