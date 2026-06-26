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

## Render 部署（推荐）

项目已提供 `render.yaml`，可通过 Render Blueprint 一键创建 Web Service + PostgreSQL。

### 部署步骤

1. 在 Render 新建 Blueprint，连接本仓库。
2. Render 会读取 `render.yaml`，自动创建：
   - Web Service：`ops-calendar-agent`
   - PostgreSQL：`ops-calendar-db`
3. 在 Render 的环境变量中补齐 `sync: false` 的项目（至少）：
   - `APP_ADMIN_EMAIL`
   - `APP_ADMIN_PASSWORD`
   - `APP_BASE_URL`（填写你的 Render 公网域名）
   - `DIFY_API_KEY`、`DIFY_BASE_URL`（如使用 Dify）
   - SMTP 相关变量（如需默认发信账号）
4. 部署成功后访问：
   - `https://<你的Render域名>/app`
   - `https://<你的Render域名>/health`

### Render 注意事项

- 生产环境不要使用 SQLite（实例重启/重建会丢失本地文件）。
- `APP_DATABASE_MODE` 已在 `render.yaml` 固定为 `postgres`。
- 默认不安装本地 OCR 可选依赖，扫描版 PDF 建议走本地 Plan B。
- 如需无人值守提醒，可使用 Render Cron 任务调用 `POST /reminders/run`。

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

云端部署（如 Vercel）默认不安装本地 OCR 重依赖，以减少构建失败风险。若需在本地启用扫描版 PDF OCR，请执行：

```bash
uv sync --extra local-ocr
```

### 本地试用配置

- `APP_DATABASE_MODE = "sqlite"`：数据写入 `data/app.db`
- `AUTH_ENABLED`：是否启用登录保护，默认 `false`；需要登录时设为 `true`
- `APP_ADMIN_EMAIL` / `APP_ADMIN_PASSWORD`：启用登录时，首次初始化数据库创建登录账号
- `AUTH_SESSION_SECONDS`：登录会话有效期，默认 `86400`
- `LLM_PROVIDER`：PDF 字段识别模型来源，支持 `dify` / `claude`
- `DIFY_API_KEY` / `DIFY_BASE_URL`：`LLM_PROVIDER=dify` 时使用 Dify workflow 做字段识别
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`：`LLM_PROVIDER=claude` 时直连 Claude 做字段识别
- `APP_BASE_URL`：邮件回执确认链接使用的访问地址

### 切换正式数据库

后续如需切到 PostgreSQL：

- 设置 `APP_DATABASE_MODE = "postgres"`，并配置 `DATABASE_URL`

### 邮件配置

- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM`：默认 SMTP 发件账号；也可在「郵箱設定」中维护发件账号。
- `REMINDER_DAYS`：正式通告 Deadline 前提醒窗口，默认 `"7"` 表示进入截止前一周提醒一次。
- `PLAN_REMINDER_DAYS`：预录备忘发布日期前提醒窗口，默认 `"7"`。
- `ESCALATION_EMAILS`：逾期升级收件人，多个邮箱用逗号分隔

「郵箱設定」支持简化绑定：主界面只需要填写发件邮箱和邮箱授权码，系统会按发件邮箱自动识别常见 SMTP 配置，例如 163、126、QQ、Foxmail、腾讯企业邮、Outlook/Hotmail/Office 365、Gmail。自动识别只会填充 SMTP host、端口、SSL/STARTTLS，邮箱授权码仍需在对应邮箱后台开启 SMTP 服务后手动填写；未知邮箱可展开「高级 SMTP 配置」手动填写。

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
