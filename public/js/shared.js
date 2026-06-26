(function () {
  const queryEmail = new URLSearchParams(window.location.search).get("email") || "";
  if (queryEmail && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(queryEmail)) {
    localStorage.setItem("opsAgentEmail", queryEmail.trim().toLowerCase());
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  window.App = {
    state: {
      language: localStorage.getItem("opsAgentLanguage") || "zh-Hant",
      email: localStorage.getItem("opsAgentEmail") || "",
      notices: [],
      plans: [],
      selectedId: null,
      currentNotice: null,
      selectedPlanId: null,
      importDraft: null,
      historySearched: false,
      emailSettings: null,
      calendarDate: new Date(),
      ackToken: null,
      currentUser: null,
      initialParams: Object.fromEntries(new URLSearchParams(window.location.search).entries()),
    },
    fields: [
      "system_no", "doc_ref", "title", "status", "notice_type", "issuer", "owner",
      "owner_role", "department", "effective_start", "deadline", "target_scope",
      "impact_store", "impact_region", "impact_role", "reminder_email", "reminder_days", "description"
    ],
  };

  window.$ = (id) => document.getElementById(id);

  const en = {
    "營運通告 Agent": "Operations Notice Agent",
    "營運通告管理": "Operations Notice Management",
    "通告歸檔、歷史查詢、預錄提醒與月度發佈觀察。": "Notice archiving, history search, pre-registration reminders, and monthly visibility.",
    "語言": "Language",
    "繁體中文": "Traditional Chinese",
    "English": "English",
    "登出": "Log out",
    "Overview": "Overview",
    "通告匯入": "Notice Import",
    "歷史查詢": "History",
    "通告預錄": "Notice Pre-registration",
    "郵箱設定": "Email Settings",
    "回執確認": "Acknowledgement",
    "登入驗證": "Login",
    "受保護": "Protected",
    "郵箱": "Email",
    "密碼": "Password",
    "登入": "Log in",
    "請使用系統管理員提供的賬號密碼。登入後才可查看通告、預錄、郵箱設定與提醒資料。": "Use the account provided by the administrator. After login, you can view notices, pre-registrations, email settings, and reminder data.",
    "本月通告總數": "Notices This Month",
    "正在執行中": "In Progress",
    "一週內截止": "Due Within 7 Days",
    "一週內即將到期": "Due Within 7 Days",
    "逾期風險": "Overdue Risk",
    "AI 總結": "AI Summary",
    "預留": "Reserved",
    "未來會在這裡接入 AI 摘要，快速總結本月通告重點、即將到期事項與需要跟進的風險。": "AI summaries will appear here in the future, covering monthly notice highlights, upcoming deadlines, and follow-up risks.",
    "通告類型分佈": "Notice Type Distribution",
    "本月集中時間": "Monthly Concentration",
    "需要關注": "Needs Attention",
    "進度日曆": "Progress Calendar",
    "本月": "This Month",
    "今天": "Today",
    "通告上傳識別": "Notice Upload & Extraction",
    "識別後進入詳情表單，核對後保存入庫。": "After extraction, review the detail form and save it to the database.",
    "識別通告並填表": "Extract Notice and Fill Form",
    "這裡是正式通告入口，不提供手工新增；識別結果可編輯，用於兜底修正 OCR/AI 提取偏差。": "This is the formal notice entry point. Manual creation is not provided; extracted results are editable for OCR/AI correction.",
    "識別結果去向": "Extraction Result Destination",
    "詳情表單": "Detail Form",
    "識別完成後會自動跳轉到「歷史查詢」的通告詳情表單。你可以先核對、修改，再保存入庫。": "After extraction, the app will open the notice detail form in History. Review, edit, then save it.",
    "歷史記錄查詢": "History Search",
    "刷新": "Refresh",
    "搜尋：標題 / 編號 / 負責人": "Search: title / number / owner",
    "全部狀態": "All Statuses",
    "草稿": "Draft",
    "執行中": "Running",
    "已回執": "Acknowledged",
    "已完成": "Completed",
    "回執：待確認": "Ack: Pending",
    "回執：部分確認": "Ack: Partially Confirmed",
    "回執：已確認": "Ack: Confirmed",
    "搜尋": "Search",
    "通告詳情": "Notice Details",
    "未選擇": "Not Selected",
    "請先搜尋並點擊一條歷史記錄。": "Search and select a history record first.",
    "編輯": "Edit",
    "刪除": "Delete",
    "發送回執郵件": "Send Acknowledgement Email",
    "取消編輯": "Cancel Edit",
    "保存修改": "Save Changes",
    "完整歷史": "Full History",
    "刷新預錄": "Refresh Pre-registrations",
    "貼上活動/通告內容": "Paste Event / Notice Content",
    "智能識別文案": "Extract Text",
    "活動名稱 *": "Activity Name *",
    "負責人": "Owner",
    "計劃發佈日期": "Planned Publish Date",
    "狀態": "Status",
    "已預錄": "Pre-registered",
    "已編寫": "Written",
    "已發佈": "Published",
    "郵件提醒": "Email Reminder",
    "開啟": "On",
    "關閉": "Off",
    "郵件提醒日": "Reminder Date",
    "自定義提前天數": "Custom Lead Days",
    "通告內容 / 備忘": "Notice Content / Memo",
    "新建預錄": "New Pre-registration",
    "編輯預錄": "Edit Pre-registration",
    "刪除預錄": "Delete Pre-registration",
    "保存預錄": "Save Pre-registration",
    "標記已編寫": "Mark Written",
    "標記已發佈": "Mark Published",
    "取消標記": "Clear Mark",
    "開啟郵件提醒後，系統會依照「郵箱設定」中的全局天數，或本條預錄的自定義天數提醒：記得編寫通告/發佈通告。": "When email reminders are enabled, the system will use global days from Email Settings or the custom days on this item to remind you to write/publish the notice.",
    "通告預錄清單": "Notice Pre-registration List",
    "郵箱對接": "Email Integration",
    "刷新設定": "Refresh Settings",
    "發件配置名稱": "SMTP Profile Name",
    "SMTP Host": "SMTP Host",
    "SMTP Port": "SMTP Port",
    "帳號": "Account",
    "密碼 / 授權碼": "Password / App Password",
    "發件人": "Sender",
    "發件郵箱": "Sender Email",
    "高級 SMTP 配置": "Advanced SMTP Settings",
    "綁定郵箱": "Bind Email",
    "輸入發件郵箱後會自動識別常見 SMTP 配置；授權碼仍需手動填寫。": "Enter the sender email to auto-detect common SMTP settings. The app password still needs to be entered manually.",
    "只需填入發件郵箱和授權碼，系統會自動識別常見 SMTP 配置。": "Enter only the sender email and app password. Common SMTP settings will be detected automatically.",
    "SSL": "SSL",
    "STARTTLS": "STARTTLS",
    "新建發件配置": "New SMTP Profile",
    "測試發送": "Send Test",
    "保存發件配置": "Save SMTP Profile",
    "提醒規則": "Reminder Rules",
    "正式通告提前天數": "Formal Notice Lead Days",
    "預錄 DDL 提前天數": "Pre-registration DDL Lead Days",
    "手動掃描提醒": "Run Reminder Scan",
    "保存提醒規則": "Save Reminder Rules",
    "常用郵箱與提醒記錄": "Common Emails and Reminder Logs",
    "當前提醒郵箱：未設定": "Current reminder email: Not set",
    "名稱 / 角色": "Name / Role",
    "收件人備註（可選）": "Recipient Note (Optional)",
    "收件人備註僅用於標識聯絡人，與發件郵箱綁定無關。": "Recipient notes are only for identifying contacts and are unrelated to sender email binding.",
    "普通收件人": "Regular Recipient",
    "默認收件人": "Default Recipient",
    "保存收件郵箱": "Save Recipient Email",
    "新建收件郵箱": "New Recipient Email",
    "清除當前郵箱": "Clear Current Email",
    "發件配置": "SMTP Profiles",
    "常用收件郵箱": "Common Recipient Emails",
    "最近提醒記錄": "Recent Reminder Logs",
    "清空記錄": "Clear Logs",
    "待確認": "Pending",
    "正在載入回執資料...": "Loading acknowledgement data...",
    "確認已收到並知悉": "Confirm Receipt and Acknowledgement",
    "返回 Overview": "Back to Overview",
    "系統編號": "System No.",
    "檔案編號": "Document Ref.",
    "標題 *": "Title *",
    "通告類型": "Notice Type",
    "發佈人 / Issuer": "Issuer",
    "負責人 / Owner": "Owner",
    "負責人角色": "Owner Role",
    "部門": "Department",
    "執行開始": "Effective Start",
    "截止日期": "Deadline",
    "影響對象 / 範圍": "Target Scope",
    "影響門店": "Impacted Stores",
    "影響區域": "Impacted Regions",
    "影響角色": "Impacted Roles",
    "默認提醒郵箱": "Default Reminder Email",
    "通告描述": "Notice Description",
    "安全合規": "Safety & Compliance",
    "日常營運": "Daily Operations",
    "活動通知": "Campaign Notice",
    "人事行政": "HR / Administration",
    "其他": "Other",
    "未記錄": "Not recorded",
    "未填": "Not set",
    "已逾期": "Overdue",
    "即將截止": "Due Soon",
    "未設定": "Not set",
    "未編號": "No number",
    "無標題": "Untitled",
    "待保存": "Pending Save",
    "留空使用全局，例如 7,3,1": "Leave blank to use global value, e.g. 7,3,1",
    "例：活動名稱：春節物料配貨\n負責人：張三\n計劃發佈日期：2026-01-20": "Example: Activity name: Spring Festival materials allocation\nOwner: Alex\nPlanned publish date: 2026-01-20",
    "例如 公司郵箱": "e.g. Company email",
    "留空則保留原密碼": "Leave blank to keep current password",
    "首次綁定請填郵箱授權碼；編輯時留空保留原密碼": "Enter the email app password for first-time binding; leave blank when editing to keep the current password",
    "例如 7,3,1": "e.g. 7,3,1",
    "例如 7": "e.g. 7",
    "載入中...": "Loading...",
    "暫無歷史。": "No history yet.",
    "暫無通告。": "No notices yet.",
    "系統": "System",
    "截止": "Deadline",
    "匯入時間": "Import time",
    "未設定負責人": "Owner not set",
    "是否對 DDL 進行郵件提醒？": "Send email reminders for the DDL?",
    "已掃描提醒": "Reminder scan complete",
    "發送": "sent",
    "失敗": "failed",
    "跳過": "skipped",
    "檢查": "checked",
    "識別通告已保存入庫。": "Extracted notice saved.",
    "通告修改已保存。": "Notice changes saved.",
    "保存失敗": "Save failed",
    "確認刪除當前通告？": "Delete the current notice?",
    "已刪除通告。": "Notice deleted.",
    "刪除失敗": "Delete failed",
    "請先選擇一條通告。": "Select a notice first.",
    "確認向未回執收件人發送回執郵件？": "Send acknowledgement emails to pending recipients?",
    "回執郵件已處理": "Acknowledgement emails processed",
    "發送回執郵件失敗": "Failed to send acknowledgement emails",
    "已撤銷未保存修改。": "Unsaved changes reverted.",
    "已恢復識別結果。": "Extraction result restored.",
    "已進入編輯模式。": "Edit mode enabled.",
    "識別結果詳情": "Extraction Result Details",
    "待保存，保存入庫後生成": "Pending save; generated after saving",
    "標題不能為空": "Title cannot be empty",
    "截止日期不能早於執行開始": "Deadline cannot be earlier than effective start",
    "暫無類型分佈。": "No type distribution yet.",
    "條": "items",
    "暫無需要關注的通告。": "No notices need attention.",
    "預錄 DDL": "Pre-registration DDL",
    "未命名": "Untitled",
    "暫無事項。": "No items.",
    "已選擇事項": "Selected item",
    "共": "Total",
    "項": "items",
    "查看詳情": "View Details",
    "星期一": "Mon",
    "星期二": "Tue",
    "星期三": "Wed",
    "星期四": "Thu",
    "星期五": "Fri",
    "星期六": "Sat",
    "星期日": "Sun",
    "另有": "plus",
    "暫無通告類型數據。": "No notice type data yet.",
    "本月暫無通告發佈記錄。": "No notice records this month.",
    "計劃發佈": "Planned publish",
    "預錄時間": "Pre-registration time",
    "提醒日": "Reminder date",
    "提前": "Lead",
    "天": "days",
    "暫無預錄。": "No pre-registrations yet.",
    "修改預錄狀態": "Change pre-registration status",
    "請先選擇要刪除的預錄。": "Select a pre-registration to delete.",
    "確認刪除當前預錄？": "Delete the current pre-registration?",
    "預錄已刪除。": "Pre-registration deleted.",
    "刪除預錄失敗": "Failed to delete pre-registration",
    "請先貼上預錄文案。": "Paste pre-registration text first.",
    "預錄文案已識別，請核對後保存。": "Pre-registration text extracted. Review and save.",
    "預錄識別失敗": "Pre-registration extraction failed",
    "活動名稱不能為空": "Activity name cannot be empty",
    "郵件提醒日已到，是否現在發送這條預錄提醒？": "The reminder date is due. Send this pre-registration reminder now?",
    "預錄已保存。": "Pre-registration saved.",
    "保存預錄失敗": "Failed to save pre-registration",
    "請先選擇一個預錄。": "Select a pre-registration first.",
    "預錄已標記為": "Pre-registration marked as",
    "標記失敗": "Mark failed",
    "已撤銷未保存的預錄修改。": "Unsaved pre-registration changes reverted.",
    "已清空新建預錄表單。": "New pre-registration form cleared.",
    "預錄已更新為": "Pre-registration updated to",
    "修改預錄狀態失敗": "Failed to update pre-registration status",
    "已進入預錄編輯模式。": "Pre-registration edit mode enabled.",
    "發件配置名稱和 SMTP Host 不能為空": "SMTP profile name and host cannot be empty",
    "發件郵箱不能為空": "Sender email cannot be empty",
    "未能自動識別此郵箱，請展開高級 SMTP 配置手動填寫。": "This email could not be detected automatically. Open Advanced SMTP Settings and fill it manually.",
    "自動識別郵箱": "Auto-detected Email",
    "已識別為": "Detected",
    "，SMTP 配置已自動填充；授權碼仍需手動填寫。": ". SMTP settings have been filled automatically. The app password still needs to be entered manually.",
    "暫未識別此郵箱服務商，請手動填寫 SMTP Host、端口和加密方式。": "This email provider is not recognized yet. Please fill SMTP host, port, and encryption manually.",
    "郵箱服務商識別失敗": "Email provider detection failed",
    "暫無發件配置，未配置時會嘗試使用 .env 中的 SMTP。": "No SMTP profiles. If none are configured, SMTP from .env will be used.",
    "默認": "Default",
    "備選": "Backup",
    "未設定發件人": "Sender not set",
    "確認刪除這個發件配置？": "Delete this SMTP profile?",
    "發件配置已刪除。": "SMTP profile deleted.",
    "當前提醒郵箱": "Current reminder email",
    "暫無常用收件郵箱。": "No common recipient emails yet.",
    "收件人": "Recipient",
    "設為當前郵箱": "Set as current email",
    "已設為當前提醒郵箱。": "Current reminder email set.",
    "確認刪除這個收件郵箱？": "Delete this recipient email?",
    "收件郵箱已刪除。": "Recipient email deleted.",
    "暫無提醒記錄。": "No reminder logs yet.",
    "確認清空最近提醒記錄？": "Clear recent reminder logs?",
    "提醒記錄已清空": "Reminder logs cleared",
    "清空提醒記錄失敗": "Failed to clear reminder logs",
    "跳過": "Skipped",
    "成功": "Success",
    "無收件人": "No recipient",
    "發件配置已保存。": "SMTP profile saved.",
    "郵箱已綁定。": "Email bound.",
    "保存發件配置失敗": "Failed to save SMTP profile",
    "綁定郵箱失敗": "Failed to bind email",
    "提醒規則已保存。": "Reminder rules saved.",
    "保存提醒規則失敗": "Failed to save reminder rules",
    "收件郵箱已保存。": "Recipient email saved.",
    "保存收件郵箱失敗": "Failed to save recipient email",
    "請先在常用郵箱中設定當前郵箱，或在收件郵箱輸入框填入測試收件人。": "Set a current email in common emails, or enter a test recipient in the recipient email field.",
    "測試郵件已發送。": "Test email sent.",
    "測試發送失敗": "Test send failed",
    "確認現在掃描正式通告與預錄提醒？": "Scan formal notice and pre-registration reminders now?",
    "提醒掃描完成": "Reminder scan complete",
    "提醒掃描失敗": "Reminder scan failed",
    "已清除當前提醒郵箱。": "Current reminder email cleared.",
    "通告標題": "Notice Title",
    "通告編號": "Notice No.",
    "載入失敗": "Load Failed",
    "回執資料載入失敗": "Failed to load acknowledgement data",
    "缺少回執 token。": "Missing acknowledgement token.",
    "確認成功": "Confirmed",
    "回執已確認。": "Acknowledgement confirmed.",
    "回執確認失敗": "Acknowledgement confirmation failed",
    "通告識別完成，已填入通告詳情。請核對後保存入庫。": "Notice extraction complete. Review details and save.",
    "請先選擇通告 PDF 文件。": "Select a notice PDF first.",
    "識別中...": "Extracting...",
    "正在識別通告，請稍候。首次 OCR 可能較慢。": "Extracting notice. Please wait. First OCR run may be slower.",
    "通告識別失敗": "Notice extraction failed",
    "如果是掃描版 PDF，請使用本地 OCR Plan B 啟動後再導入。": "If this is a scanned PDF, start with local OCR Plan B and import again.",
    "登入中...": "Logging in...",
    "登入成功。": "Logged in.",
    "登入失敗": "Login failed",
    "已登出。": "Logged out.",
    "郵箱設定載入失敗": "Failed to load email settings",
    "初始化失敗": "Initialization failed"
  };

  const zh = Object.fromEntries(Object.entries(en).map(([key, value]) => [value, key]));

  window.t = function t(text) {
    if (App.state.language === "en") return en[text] || text;
    return zh[text] || text;
  };

  window.setLanguage = function setLanguage(language) {
    App.state.language = language === "en" ? "en" : "zh-Hant";
    localStorage.setItem("opsAgentLanguage", App.state.language);
    document.documentElement.lang = App.state.language;
    document.title = t("營運通告 Agent");
    applyI18n();
  };

  window.applyI18n = function applyI18n(root = document.body) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const raw = node.nodeValue;
      const trimmed = raw.trim();
      if (!trimmed) return;
      const translated = t(trimmed);
      if (translated !== trimmed) node.nodeValue = raw.replace(trimmed, translated);
    });
    root.querySelectorAll("[placeholder]").forEach((el) => {
      const translated = t(el.getAttribute("placeholder"));
      if (translated) el.setAttribute("placeholder", translated);
    });
    root.querySelectorAll("option").forEach((el) => {
      const translated = t(el.textContent.trim());
      if (translated !== el.textContent.trim()) el.textContent = translated;
    });
    const select = $("languageSelect");
    if (select) select.value = App.state.language;
  };

  window.showToast = function showToast(message) {
    const el = $("toast");
    el.textContent = message;
    el.style.display = "block";
  };

  window.escapeHtml = function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[c]));
  };

  window.daysLeft = function daysLeft(raw) {
    if (!raw) return 99999;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const d = new Date(String(raw).slice(0, 10) + "T00:00:00");
    return Math.round((d - today) / 86400000);
  };

  window.formatDateTime = function formatDateTime(raw) {
    if (!raw) return t("未記錄");
    return String(raw).replace("T", " ").slice(0, 19);
  };

  window.statusLabel = function statusLabel(status, deadline) {
    const labels = {
      "草稿": t("草稿"),
      "执行中": t("執行中"),
      "已逾期": t("已逾期"),
      "已预录": t("已預錄"),
      "已编写": t("已編寫"),
      "已发布": t("已發佈"),
    };
    const base = labels[status] || status || t("未填");
    const days = daysLeft(deadline);
    if (status === "执行中" && days >= 0 && days <= 7) return `${base} · ${t("即將截止")}`;
    return base;
  };

  window.noticeAckLabel = function noticeAckLabel(notice = {}) {
    const total = Number(notice.ack_total_count || 0);
    const confirmed = Number(notice.ack_confirmed_count || 0);
    if (!total) return "";
    if (confirmed >= total) return t("回執：已確認");
    if (confirmed > 0) return t("回執：部分確認");
    return t("回執：待確認");
  };

  window.noticeTypeLabel = function noticeTypeLabel(type) {
    return ({
      "安全合规": t("安全合規"),
      "日常营运": t("日常營運"),
      "活动通知": t("活動通知"),
      "人事行政": t("人事行政"),
      "其他": t("其他"),
    }[type]) || type || t("其他");
  };

  window.statusBadgeClass = function statusBadgeClass(status, deadline) {
    const days = daysLeft(deadline);
    if (status === "已逾期") return "badge red";
    if (days >= 0 && days <= 7) return "badge amber";
    if (status === "执行中") return "badge green";
    return "badge";
  };

  window.switchView = function switchView(viewName) {
    document.querySelectorAll(".view").forEach((section) => {
      section.hidden = section.id !== `view-${viewName}`;
    });
    document.querySelectorAll(".nav-tabs button").forEach((button) => {
      button.classList.toggle("active", button.dataset.view === viewName);
    });
  };

  window.request = async function request(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      credentials: "same-origin",
      ...options,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      if (res.status === 401 && window.Auth) {
        Auth.showLogin();
      }
      throw new Error(detail);
    }
    return res.json();
  };
}());
