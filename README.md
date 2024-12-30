root/                         # 项目根目录
├── README.md                 # 项目说明文件（描述项目、安装方法、使用方法等）
├── setup.py                  # 安装、打包和部署脚本
├── requirements.txt          # 项目依赖列表
├── .gitignore                # Git 忽略规则文件
├── LICENSE                   # 项目许可证
├── pyproject.toml            # 项目配置文件（PEP 518，现代 Python 项目推荐）
├── app/             # 主应用程序代码目录（与项目同名）
│   ├── __init__.py           # 包初始化文件
│   ├── main.py               # 主模块
│   ├── utils/                # 工具模块目录
│   │   ├── __init__.py       # 工具模块初始化文件
│   │   └── helper.py         # 工具函数
│   └── ...                   # 其他模块
├── data/                     # 数据目录（可选，用于存放数据文件）
│   ├── raw/                  # 原始数据
│   ├── processed/            # 处理后的数据
│   └── ...                   # 其他数据
├── scripts/                  # 脚本目录（可选，用于存放辅助脚本）
│   ├── script1.py            # 辅助脚本 1
│   └── ...                   # 其他脚本
└── .vscode/                  # VS Code 配置目录（可选）
    ├── settings.json         # VS Code 设置
    └── ...                   # 其他配置
