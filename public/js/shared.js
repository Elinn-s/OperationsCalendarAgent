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
    },
    fields: [
      "system_no", "doc_ref", "title", "status", "notice_type", "issuer", "owner",
      "owner_role", "department", "effective_start", "deadline", "target_scope",
      "impact_store", "impact_region", "impact_role", "reminder_email", "description"
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
    if (!raw) return "未记录";
    return String(raw).replace("T", " ").slice(0, 19);
  };

  window.statusBadgeClass = function statusBadgeClass(status, deadline) {
    const days = daysLeft(deadline);
    if (status === "已逾期" || days < 0) return "badge red";
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
      ...options,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    return res.json();
  };
}());
