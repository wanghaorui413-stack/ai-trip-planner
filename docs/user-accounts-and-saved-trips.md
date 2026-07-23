# 用户账户与攻略保存

本功能为旅行规划器增加了：

- 邮箱注册与登录
- PBKDF2-SHA256 密码哈希（不保存明文密码）
- 7 天有效的 HMAC 签名访问令牌
- 用户昵称与默认旅行偏好
- 当前攻略保存
- 历史攻略列表、打开与删除
- SQLite 本地持久化，数据按用户隔离

## 本地启动

后端：

```powershell
$env:AUTH_SECRET = "请替换成一段足够长的随机字符串"
.\.venv\Scripts\uvicorn.exe authenticated_main:app --host 0.0.0.0 --port 8000
```

前端：

```powershell
.\.venv\Scripts\streamlit.exe run authenticated_streamlit_app.py
```

浏览器打开 `http://localhost:8501`，首次使用选择“创建账户”。

## Docker Compose 启动

```powershell
$env:AUTH_SECRET = "请替换成一段足够长的随机字符串"
docker compose -f docker-compose.yml -f docker-compose.auth.yml up --build
```

`docker-compose.auth.yml` 会把 `./data` 挂载到后端容器，确保容器重建后用户和攻略仍然存在。

## 环境变量

| 名称 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_DB_PATH` | `data/trip_planner.db` | SQLite 数据库路径 |
| `AUTH_SECRET` | 开发默认值 | 生产环境必须设置为随机密钥 |
| `AUTH_TOKEN_TTL_SECONDS` | `604800` | 登录令牌有效期（秒） |
| `API_URL` | `http://localhost:8000` | 前端访问的后端地址 |

## 新增 API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册并返回访问令牌 |
| POST | `/api/auth/login` | 登录并返回访问令牌 |
| GET | `/api/users/me` | 获取当前用户 |
| PATCH | `/api/users/me` | 更新昵称与旅行偏好 |
| POST | `/api/trips` | 保存当前攻略 |
| GET | `/api/trips` | 获取攻略历史列表 |
| GET | `/api/trips/{id}` | 获取完整攻略 |
| DELETE | `/api/trips/{id}` | 删除攻略 |

除注册和登录外，所有账户接口都需要请求头：

```text
Authorization: Bearer <access_token>
```
