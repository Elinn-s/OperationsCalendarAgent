## 内网部署

1. 在服务器或长期在线的 Windows 电脑上安装项目依赖。
2. 配置环境变量，或复制 `.streamlit/secrets.example.toml` 为 `.streamlit/secrets.toml` 后填入真实值。
   默认使用本地 SQLite 和本地 PDF 存储，可先不配置 Supabase 数据库。
3. 本机试用或部署启动可双击：

```bat
start.bat
```

默认启动新版 Fetch + FastAPI 前端：

```text
http://localhost:8000/app
```

部署完成后，给同事发送服务器地址即可：

```text
http://服务器IP:8000/app
```

备用 Streamlit demo 启动：

```bat
start_streamlit.bat
```

### FastAPI 后端

项目已引入 `src/` 包结构和 FastAPI 后端。当前默认入口就是 FastAPI 前端；API 健康检查：

```text
http://localhost:8000/health
```

Streamlit 仅作为备用 demo 保留在 `streamlit_demo/`。

### 本地试用配置

- `APP_DATABASE_MODE = "sqlite"`：数据写入 `data/app.db`
- `APP_STORAGE_MODE = "local"`：PDF 写入 `data/uploads`
- `DIFY_API_KEY` / `DIFY_BASE_URL`：PDF 字段识别
- `APP_BASE_URL`：邮件回执确认链接使用的访问地址

### 切换正式数据库 / 云存储

后续如需切回 Supabase/PostgreSQL：

- 设置 `APP_DATABASE_MODE = "postgres"`，并配置 `DATABASE_URL`
- 设置 `APP_STORAGE_MODE = "supabase"`，并配置 `SUPABASE_URL` / `SUPABASE_KEY`

### 邮件配置

- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`：回执邮件发送
- `REMINDER_DAYS`：Deadline 前提醒窗口，默认 `"7"` 表示进入截止前一周提醒一次
- `ESCALATION_EMAILS`：逾期升级收件人，多个邮箱用逗号分隔

当前试用默认按 163 网易邮箱配置：

```toml
SMTP_HOST = "smtp.163.com"
SMTP_PORT = "25"
SMTP_STARTTLS = "true"
SMTP_SSL = "false"
```

`SMTP_PASSWORD` 需填写 163 邮箱的客户端授权码，不是网页登录密码。

### 自动提醒

保存/修改正式通告或从预录发布正式通告后，系统会自动扫描一次 Deadline；也可以用计划任务定时扫描。当前默认进入截止前一周提醒一次、截止当天提醒、逾期升级，并写入 `reminder_log` 避免重复发送。

如需无人值守，可用 Windows 任务计划每天运行：

```bat
.venv\Scripts\python.exe run_reminders.py
```

### Windows 防火墙

如其他电脑无法访问，请在服务器上开放 TCP 端口 `8501`。
