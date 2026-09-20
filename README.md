# DigRecSys

数码商品交易项目，包含 Django REST API 和微信原生小程序。后端可独立运行；商品采集、数据导入和小程序均为可选部分。

## 快速开始

以下命令适用于 Windows PowerShell。

### 前置环境

- Git
- Python 3.11
- MySQL 8

### 1. 下载并安装

```powershell
git clone https://github.com/HurricaneEd/DigRecSys.git
cd DigRecSys

python -m pip install -r requirements.txt
```

### 2. 初始化 MySQL

在 MySQL 客户端中创建数据库：

```sql
CREATE DATABASE digrecsys1
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 3. 迁移并启动

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 4. 验证

| 入口 | 地址 |
| --- | --- |
| Swagger | <http://127.0.0.1:8000/swagger/> |
| ReDoc | <http://127.0.0.1:8000/redoc/> |
| 商品 API | <http://127.0.0.1:8000/api/products/> |

需要管理员账号时运行：

```powershell
python manage.py createsuperuser
```

## 导入商品数据（可选）

仓库中有一份爬取脚本（crawl/）可供参考，以及一份导入脚本（/database）用于将数据导入数据库
```powershe

## 启动微信小程序（可选）

保持后端运行，然后安装小程序依赖：

```powershell
cd miniapp
npm ci
```

在微信开发者工具中导入 `miniapp/`，选择“工具 → 构建 npm”。API 地址配置在 `miniapp/utils/config.js`，默认指向：

```text
http://127.0.0.1:8000/api
```

真机调试时需改为电脑的局域网地址或已备案的 HTTPS 域名。其他说明见 [miniapp/README.md](miniapp/README.md)。

## 开发检查

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
