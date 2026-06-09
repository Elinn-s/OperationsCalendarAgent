(function () {
  const queryEmail = new URLSearchParams(window.location.search).get("email") || "";
  if (queryEmail && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(queryEmail)) {
    localStorage.setItem("opsAgentEmail", queryEmail.trim().toLowerCase());
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  window.App = {
    state: {
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
    if (!raw) return "未記錄";
    return String(raw).replace("T", " ").slice(0, 19);
  };

  window.statusLabel = function statusLabel(status, deadline) {
    const labels = {
      "草稿": "草稿",
      "执行中": "執行中",
      "已回执": "已回執",
      "已完成": "已完成",
      "已逾期": "執行中 · 已逾期",
      "已预录": "已預錄",
      "已编写": "已編寫",
      "已发布": "已發佈",
    };
    const base = labels[status] || status || "未填";
    const days = daysLeft(deadline);
    if (["执行中", "已回执"].includes(status) && days < 0) return `${base} · 已逾期`;
    if (["执行中", "已回执"].includes(status) && days >= 0 && days <= 7) return `${base} · 即將截止`;
    return base;
  };

  window.noticeTypeLabel = function noticeTypeLabel(type) {
    return ({
      "安全合规": "安全合規",
      "日常营运": "日常營運",
      "活动通知": "活動通知",
      "人事行政": "人事行政",
      "其他": "其他",
    }[type]) || type || "其他";
  };

  window.statusBadgeClass = function statusBadgeClass(status, deadline) {
    const days = daysLeft(deadline);
    if (days < 0) return "badge red";
    if (days >= 0 && days <= 7) return "badge amber";
    if (status === "执行中" || status === "已回执" || status === "已完成") return "badge green";
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
