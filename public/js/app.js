(function () {
  function saveTopEmail() {
    const email = $("topEmail").value.trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      alert("请输入有效邮箱。");
      return;
    }
    App.state.email = email;
    localStorage.setItem("opsAgentEmail", email);
    if ($("reminder_email")) $("reminder_email").value = email;
    showToast("邮箱已保存，将作为默认操作人和预录提醒收件人。");
  }

  function bindEvents() {
    $("logoutBtn").addEventListener("click", () => {
      localStorage.removeItem("opsAgentEmail");
      App.state.email = "";
      $("topEmail").value = "";
      if ($("reminder_email")) $("reminder_email").value = "";
      showToast("已清空邮箱，可在顶部重新输入。");
    });
    $("saveEmailBtn").addEventListener("click", saveTopEmail);

    $("searchBtn").addEventListener("click", History.search);
    $("refreshBtn").addEventListener("click", History.refresh);
    $("statusFilter").addEventListener("change", () => {
      if (App.state.historySearched) History.loadNotifications();
    });
    $("searchInput").addEventListener("keydown", (event) => {
      if (event.key === "Enter") History.search();
    });

    $("extractPdfBtn").addEventListener("click", ImportNotice.uploadPdfForExtract);
    $("reloadPlansBtn").addEventListener("click", Plans.loadPlans);
    $("extractPlanBtn").addEventListener("click", Plans.extractPlanText);
    $("plan_planned_publish_date").addEventListener("change", Plans.syncReminderDateFromDdl);
    $("newPlanBtn").addEventListener("click", Plans.clearPlanForm);
    $("editPlanBtn").addEventListener("click", Plans.enableEdit);
    $("deletePlanBtn").addEventListener("click", Plans.deletePlan);
    $("cancelPlanEditBtn").addEventListener("click", Plans.cancelPlanEdit);
    $("markWrittenBtn").addEventListener("click", Plans.markWritten);
    $("markPublishedBtn").addEventListener("click", Plans.markPublished);
    $("clearPlanMarkBtn").addEventListener("click", Plans.clearMark);
    $("editNoticeBtn").addEventListener("click", History.enableEdit);
    $("cancelBtn").addEventListener("click", History.cancelNoticeEdit);
    $("deleteBtn").addEventListener("click", History.deleteNotice);
    $("noticeForm").addEventListener("submit", History.saveNotice);
    $("planForm").addEventListener("submit", Plans.savePlan);

    document.querySelectorAll(".nav-tabs button").forEach((button) => {
      button.addEventListener("click", () => switchView(button.dataset.view));
    });
  }

  async function init() {
    renderNoticeFields("#noticeForm .notice-fields");
    $("topEmail").value = App.state.email;
    switchView("overview");
    bindEvents();
    resetNoticeDetail("history");
    await History.loadNotifications();
    await Plans.loadPlans();
  }

  window.addEventListener("DOMContentLoaded", () => {
    init().catch((err) => showToast(`初始化失败：${err.message}`));
  });
}());
