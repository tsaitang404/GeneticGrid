# GeneticGrid Django Project

这是一个最小的 Django 项目脚手架，用于开始开发 `GeneticGrid` 应用。

快速开始：

1. 创建并激活虚拟环境（推荐）：
```
python -m venv venv
source venv/bin/activate
```
2. 安装依赖：
```
pip install -r requirements.txt
```
3. 运行迁移并启动开发服务器：
```
python manage.py migrate
python manage.py runserver
```

项目结构核心文件：
- `manage.py` — Django 管理入口
- `geneticgrid/` — 项目包（settings, urls, wsgi, asgi）
- `core/` — 示例应用，包含一个首页视图

示例：访问 `http://127.0.0.1:8000/` 将显示欢迎信息。
