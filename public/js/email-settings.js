(function () {
  let providerDetectTimer = null;
  let lastProviderEmail = "";

  async function loadSettings() {
    App.state.emailSettings = await request("/email-settings");
    renderSettings();
  }

  function selectedSmtpId() {
    const value = $("smtp_id").value;
    return value ? Number(value) : null;
  }

  function fillSmtpForm(account = {}) {
    lastProviderEmail = (account.sender || account.username || "").trim().toLowerCase();
    $("smtp_id").value = account.id || "";
    $("smtp_name").value = account.name || "";
    $("smtp_host").value = account.host || "";
    $("smtp_port").value = account.port || 587;
    $("smtp_username").value = account.username || account.sender || "";
    $("smtp_password").value = "";
    $("smtp_sender").value = account.sender || account.username || "";
    $("smtp_use_ssl").value = String(Number(account.use_ssl || 0));
    $("smtp_use_tls").value = String(Number(account.use_tls == null ? 1 : account.use_tls));
    setProviderHint(t("只需填入發件郵箱和授權碼，系統會自動識別常見 SMTP 配置。"));
  }

  function collectSmtpPayload() {
    const email = $("smtp_sender").value.trim().toLowerCase();
    const name = $("smtp_name").value.trim() || email || t("自動識別郵箱");
    const host = $("smtp_host").value.trim();
    if (!email) throw new Error(t("發件郵箱不能為空"));
    if (!host) throw new Error(t("未能自動識別此郵箱，請展開高級 SMTP 配置手動填寫。"));
    return {
      name,
      host,
      port: Number($("smtp_port").value || 587),
      username: $("smtp_username").value.trim() || email,
      password: $("smtp_password").value,
      sender: email,
      use_ssl: Number($("smtp_use_ssl").value),
      use_tls: Number($("smtp_use_tls").value),
      is_default: 1,
    };
  }

  function smtpEmailCandidate() {
    return ($("smtp_sender").value || "").trim().toLowerCase();
  }

  function setProviderHint(message) {
    const hint = $("smtpProviderHint");
    if (hint) hint.textContent = message || "";
  }

  function applyProviderPreset(result) {
    $("smtp_host").value = result.host || "";
    $("smtp_port").value = result.port || 587;
    $("smtp_use_ssl").value = String(Number(result.use_ssl || 0));
    $("smtp_use_tls").value = String(Number(result.use_tls || 0));
    $("smtp_sender").value = result.email || $("smtp_sender").value;
    $("smtp_username").value = result.email || $("smtp_sender").value;
    if (!$("smtp_name").value) $("smtp_name").value = result.provider || t("自動識別郵箱");
  }

  async function detectSmtpProviderNow() {
    const email = smtpEmailCandidate();
    if (!email || !email.includes("@")) {
      setProviderHint(t("只需填入發件郵箱和授權碼，系統會自動識別常見 SMTP 配置。"));
      return;
    }
    if (email === lastProviderEmail && $("smtp_host").value.trim()) return;
    lastProviderEmail = email;
    try {
      const result = await request(`/email-settings/provider?email=${encodeURIComponent(email)}`);
      if (result.matched) {
        applyProviderPreset(result);
        setProviderHint(`${t("已識別為")} ${result.provider}${t("，SMTP 配置已自動填充；授權碼仍需手動填寫。")}`);
      } else {
        setProviderHint(t("暫未識別此郵箱服務商，請手動填寫 SMTP Host、端口和加密方式。"));
      }
    } catch (err) {
      setProviderHint(`${t("郵箱服務商識別失敗")}：${err.message}`);
    }
  }

  function detectSmtpProvider() {
    window.clearTimeout(providerDetectTimer);
    providerDetectTimer = window.setTimeout(detectSmtpProviderNow, 350);
  }

  function renderSmtpList(accounts) {
    const root = $("smtpList");
    root.innerHTML = accounts.length ? "" : `<div class="meta">${t("暫無發件配置，未配置時會嘗試使用 .env 中的 SMTP。")}</div>`;
    for (const account of accounts) {
      const item = document.createElement("div");
      item.className = "settings-list-item";
      item.innerHTML = `
        <div class="row">
          <strong>${escapeHtml(account.name)}</strong>
          <span class="badge small">${account.is_default ? t("默認") : t("備選")}</span>
        </div>
        <div class="meta">${escapeHtml(account.host)}:${escapeHtml(account.port)} · ${escapeHtml(account.sender || account.username || t("未設定發件人"))}</div>
        <div class="actions">
          <button type="button" data-edit-smtp="${account.id}">${t("編輯")}</button>
          <button type="button" class="danger" data-delete-smtp="${account.id}">${t("刪除")}</button>
        </div>
      `;
      root.appendChild(item);
    }
    root.querySelectorAll("[data-edit-smtp]").forEach((button) => {
      button.addEventListener("click", () => {
        const account = accounts.find((item) => item.id === Number(button.dataset.editSmtp));
        fillSmtpForm(account);
      });
    });
    root.querySelectorAll("[data-delete-smtp]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!confirm(t("確認刪除這個發件配置？"))) return;
        await request(`/email-settings/smtp/${button.dataset.deleteSmtp}`, { method: "DELETE" });
        showToast(t("發件配置已刪除。"));
        await loadSettings();
      });
    });
  }

  function renderContactList(contacts) {
    $("emailContactCount").textContent = contacts.length;
    $("currentEmailMeta").textContent = `${t("當前提醒郵箱")}：${App.state.email || t("未設定")}`;
    const root = $("contactList");
    root.innerHTML = contacts.length ? "" : `<div class="meta">${t("暫無常用收件郵箱。")}</div>`;
    for (const contact of contacts) {
      const item = document.createElement("div");
      item.className = "settings-list-item";
      item.innerHTML = `
        <div class="row">
          <strong>${escapeHtml(contact.label || contact.email)}</strong>
          <span class="badge small">${contact.is_default ? t("默認") : escapeHtml(t(contact.kind || "收件人"))}</span>
        </div>
        <div class="meta">${escapeHtml(contact.email)}</div>
        <div class="actions">
          <button type="button" data-use-contact="${escapeHtml(contact.email)}">${t("設為當前郵箱")}</button>
          <button type="button" data-edit-contact="${contact.id}">${t("編輯")}</button>
          <button type="button" class="danger" data-delete-contact="${contact.id}">${t("刪除")}</button>
        </div>
      `;
      root.appendChild(item);
    }
    root.querySelectorAll("[data-edit-contact]").forEach((button) => {
      button.addEventListener("click", () => {
        const contact = contacts.find((item) => item.id === Number(button.dataset.editContact));
        fillContactForm(contact);
      });
    });
    root.querySelectorAll("[data-use-contact]").forEach((button) => {
      button.addEventListener("click", () => {
        App.state.email = button.dataset.useContact;
        localStorage.setItem("opsAgentEmail", App.state.email);
        if ($("reminder_email")) $("reminder_email").value = App.state.email;
        $("currentEmailMeta").textContent = `${t("當前提醒郵箱")}：${App.state.email}`;
        showToast(t("已設為當前提醒郵箱。"));
      });
    });
    root.querySelectorAll("[data-delete-contact]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!confirm(t("確認刪除這個收件郵箱？"))) return;
        await request(`/email-settings/contacts/${button.dataset.deleteContact}`, { method: "DELETE" });
        showToast(t("收件郵箱已刪除。"));
        await loadSettings();
      });
    });
  }

  function fillContactForm(contact = {}) {
    $("contact_id").value = contact.id || "";
    $("contact_label").value = contact.label || "";
    $("contact_email").value = contact.email || "";
    $("contact_is_default").value = String(Number(contact.is_default || 0));
  }

  function renderReminderLogs(logs) {
    const root = $("reminderLogList");
    root.innerHTML = logs.length ? "" : `<div class="meta">${t("暫無提醒記錄。")}</div>`;
    for (const log of logs) {
      const statusText = log.status === "失败" ? t("失敗") : log.status === "跳过" ? t("跳過") : t(log.status || "");
      const statusClass = log.status === "成功" ? "badge green small" : log.status === "失败" ? "badge red small" : "badge small";
      const reminderType = String(log.reminder_type || "提醒")
        .replace("预录", "預錄")
        .replace("提前一周", "提前一週")
        .replace("截止当日", "截止當日")
        .replace("逾期升级", "逾期升級");
      const item = document.createElement("div");
      item.className = "settings-list-item";
      item.innerHTML = `
        <div class="row">
          <strong>${escapeHtml(reminderType)}</strong>
          <span class="${statusClass}">${escapeHtml(statusText)}</span>
        </div>
        <div class="meta">${escapeHtml(formatDateTime(log.created_at))} · ${escapeHtml(log.recipient_email || t("無收件人"))}</div>
        <div class="meta">${escapeHtml(log.error || "")}</div>
      `;
      root.appendChild(item);
    }
  }

  function renderSettings() {
    const data = App.state.emailSettings || {};
    const settings = data.settings || {};
    $("notification_reminder_days").value = settings.notification_reminder_days || "7";
    $("global_plan_reminder_days").value = settings.plan_reminder_days || "7";
    renderSmtpList(data.smtp_accounts || []);
    renderContactList(data.contacts || []);
    renderReminderLogs(data.reminder_logs || []);
  }

  async function saveSmtp(event) {
    event.preventDefault();
    try {
      await detectSmtpProviderNow();
      const id = selectedSmtpId();
      const payload = collectSmtpPayload();
      await request(id ? `/email-settings/smtp/${id}` : "/email-settings/smtp", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      showToast(t("郵箱已綁定。"));
      await loadSettings();
    } catch (err) {
      showToast(`${t("綁定郵箱失敗")}：${err.message}`);
    }
  }

  async function saveReminderSettings(event) {
    event.preventDefault();
    try {
      await request("/email-settings/settings", {
        method: "PUT",
        body: JSON.stringify({
          notification_reminder_days: $("notification_reminder_days").value.trim() || "7",
          plan_reminder_days: $("global_plan_reminder_days").value.trim() || "7",
        }),
      });
      showToast(t("提醒規則已保存。"));
      await loadSettings();
    } catch (err) {
      showToast(`${t("保存提醒規則失敗")}：${err.message}`);
    }
  }

  async function saveContact(event) {
    event.preventDefault();
    try {
      const id = $("contact_id").value;
      await request(id ? `/email-settings/contacts/${id}` : "/email-settings/contacts", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify({
          label: $("contact_label").value.trim(),
          email: $("contact_email").value.trim(),
          kind: "收件人",
          is_default: Number($("contact_is_default").value),
        }),
      });
      fillContactForm({});
      showToast(t("收件郵箱已保存。"));
      await loadSettings();
    } catch (err) {
      showToast(`${t("保存收件郵箱失敗")}：${err.message}`);
    }
  }

  async function testSmtp() {
    const to = App.state.email || $("contact_email").value.trim();
    if (!to) {
      showToast(t("請先在常用郵箱中設定當前郵箱，或在收件郵箱輸入框填入測試收件人。"));
      return;
    }
    try {
      await request("/email-settings/test", {
        method: "POST",
        body: JSON.stringify({ to_email: to, smtp_id: selectedSmtpId() }),
      });
      showToast(t("測試郵件已發送。"));
    } catch (err) {
      showToast(`${t("測試發送失敗")}：${err.message}`);
    }
  }

  async function runReminders() {
    if (!confirm(t("確認現在掃描正式通告與預錄提醒？"))) return;
    try {
      const stats = await request("/reminders/run", { method: "POST" });
      showToast(`${t("提醒掃描完成")}：${t("檢查")} ${stats.checked || 0}，${t("發送")} ${stats.sent || 0}，${t("失敗")} ${stats.failed || 0}，${t("跳過")} ${stats.skipped || 0}。`);
      await loadSettings();
    } catch (err) {
      showToast(`${t("提醒掃描失敗")}：${err.message}`);
    }
  }

  async function clearReminderLogs() {
    if (!confirm(t("確認清空最近提醒記錄？"))) return;
    try {
      const result = await request("/email-settings/reminder-logs", { method: "DELETE" });
      showToast(`${t("提醒記錄已清空")}（${t("共")} ${result.deleted || 0} ${t("項")}）`);
      await loadSettings();
    } catch (err) {
      showToast(`${t("清空提醒記錄失敗")}：${err.message}`);
    }
  }

  function clearCurrentEmail() {
    App.state.email = "";
    localStorage.removeItem("opsAgentEmail");
    if ($("reminder_email")) $("reminder_email").value = "";
    $("currentEmailMeta").textContent = `${t("當前提醒郵箱")}：${t("未設定")}`;
    showToast(t("已清除當前提醒郵箱。"));
  }

  window.EmailSettings = {
    loadSettings,
    renderSettings,
    fillSmtpForm,
    detectSmtpProvider,
    saveSmtp,
    saveReminderSettings,
    saveContact,
    testSmtp,
    runReminders,
    clearReminderLogs,
    clearCurrentEmail,
    fillContactForm,
  };
}());
