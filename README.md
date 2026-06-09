## 内网部署

1. 在服务器或长期在线的 Windows 电脑上安装项目依赖。
2. 配置 `.env` 或系统环境变量。
   默认使用本地 SQLite：`data/app.db`。
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

### FastAPI 后端

项目已引入 `src/` 包结构和 FastAPI 后端。当前默认入口就是 FastAPI 前端；API 健康检查：

```text
http://localhost:8000/health
```

### 当前目录结构

- `public/`：当前 HTML/CSS/JavaScript 前端主线。
- `src/storenotificationcircula/`：当前 FastAPI 后端、数据库和服务逻辑。
- `local_ocr_plan_b/`：本地 OCR Plan B 启动方式。
- `docs/`：产品和项目说明文档，例如 `docs/PRD.md`。
- `archive/`：旧模板接口和旧 OCR 备份，不参与当前主线运行。

### 本地试用配置

- `APP_DATABASE_MODE = "sqlite"`：数据写入 `data/app.db`
- `AUTH_ENABLED`：是否启用登录保护，默认 `false`；需要登录时设为 `true`
- `APP_ADMIN_EMAIL` / `APP_ADMIN_PASSWORD`：启用登录时，首次初始化数据库创建登录账号
- `AUTH_SESSION_SECONDS`：登录会话有效期，默认 `86400`
- `DIFY_API_KEY` / `DIFY_BASE_URL`：PDF 字段识别
- `APP_BASE_URL`：邮件回执确认链接使用的访问地址

### 切换正式数据库

后续如需切到 PostgreSQL：

- 设置 `APP_DATABASE_MODE = "postgres"`，并配置 `DATABASE_URL`

### 邮件配置

- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`：默认 SMTP 发件账号；也可在「郵箱設定」中维护发件账号。
- `REMINDER_DAYS`：正式通告 Deadline 前提醒窗口，默认 `"7"` 表示进入截止前一周提醒一次。
- `PLAN_REMINDER_DAYS`：预录备忘发布日期前提醒窗口，默认 `"7"`。
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

保存/修改正式通告后，系统会自动扫描一次 Deadline；预录备忘可在页面中单条扫描，也可由统一提醒扫描覆盖。当前默认进入截止前一周提醒一次、截止当天提醒、逾期升级，并写入 `reminder_log` 避免重复发送。

也可以在「郵箱設定」中点击「手動掃描提醒」，调用 `/reminders/run` 立即扫描正式通告与预录备忘。

如需无人值守，可用 Windows 任务计划每天运行：

```bat
.venv\Scripts\python.exe run_reminders.py
```

建议任务计划配置：

- 触发器：每天固定时间，例如 09:00。
- 操作：启动程序，选择项目内 `.venv\Scripts\python.exe`。
- 添加参数：`run_reminders.py`。
- 起始于：项目根目录，例如 `D:\ICDanymore\StoreNotificationCircula`。

预录备忘的「標記已發布」只表示备忘录进度已完成，不会生成正式通告。正式通告仍由 PDF 导入生成。

### Windows 防火墙

如其他电脑无法访问，请在服务器上开放 TCP 端口 `8000`。
