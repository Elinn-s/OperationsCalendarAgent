(function () {
  function on(id, eventName, handler) {
    const el = $(id);
    if (!el) {
      console.warn(`Missing element #${id}`);
      return;
    }
    el.addEventListener(eventName, handler);
  }

  function bindEvents() {
    on("searchBtn", "click", History.search);
    on("refreshBtn", "click", History.refresh);
    on("statusFilter", "change", () => {
      if (App.state.historySearched) History.loadNotifications();
    });
    on("searchInput", "keydown", (event) => {
      if (event.key === "Enter") History.search();
    });

    on("extractPdfBtn", "click", ImportNotice.uploadPdfForExtract);
    on("reloadPlansBtn", "click", Plans.loadPlans);
    on("extractPlanBtn", "click", Plans.extractPlanText);
    on("plan_planned_publish_date", "change", Plans.syncReminderDateFromDdl);
    on("plan_reminder_days", "change", Plans.syncReminderDateFromDdl);
    on("newPlanBtn", "click", Plans.clearPlanForm);
    on("editPlanBtn", "click", Plans.enableEdit);
    on("deletePlanBtn", "click", Plans.deletePlan);
    on("cancelPlanEditBtn", "click", Plans.cancelPlanEdit);
    on("markWrittenBtn", "click", Plans.markWritten);
    on("markPublishedBtn", "click", Plans.markPublished);
    on("clearPlanMarkBtn", "click", Plans.clearMark);
    on("editNoticeBtn", "click", History.enableEdit);
    on("cancelBtn", "click", History.cancelNoticeEdit);
    on("deleteBtn", "click", History.deleteNotice);
    on("sendAckBtn", "click", History.sendAckEmails);
    on("noticeForm", "submit", History.saveNotice);
    on("planForm", "submit", Plans.savePlan);
    on("reloadEmailSettingsBtn", "click", EmailSettings.loadSettings);
    on("smtpForm", "submit", EmailSettings.saveSmtp);
    on("reminderSettingsForm", "submit", EmailSettings.saveReminderSettings);
    on("contactForm", "submit", EmailSettings.saveContact);
    on("newContactBtn", "click", () => EmailSettings.fillContactForm({}));
    on("clearCurrentEmailBtn", "click", EmailSettings.clearCurrentEmail);
    on("newSmtpBtn", "click", () => EmailSettings.fillSmtpForm({}));
    on("testSmtpBtn", "click", EmailSettings.testSmtp);
    on("runRemindersBtn", "click", EmailSettings.runReminders);
    on("calendarTodayBtn", "click", Overview.goToday);
    on("calendarPrevBtn", "click", Overview.prevMonth);
    on("calendarNextBtn", "click", Overview.nextMonth);
    on("calendarMonthBtn", "click", Overview.openMonthPicker);
    on("calendarMonthPicker", "change", (event) => Overview.selectMonth(event.target.value));
    on("confirmAckBtn", "click", Ack.confirmAck);
    on("backToAppBtn", "click", () => switchView("overview"));

    document.querySelectorAll(".nav-tabs button").forEach((button) => {
      button.addEventListener("click", async () => {
        switchView(button.dataset.view);
        if (button.dataset.view === "email-settings") await EmailSettings.loadSettings();
      });
    });
  }

  async function init() {
    renderNoticeFields("#noticeForm .notice-fields");
    switchView("overview");
    bindEvents();
    resetNoticeDetail("history");
    Overview.render();
    try {
      await EmailSettings.loadSettings();
    } catch (err) {
      showToast(`郵箱設定載入失敗：${err.message}`);
    }
    await History.loadNotifications();
    await Plans.loadPlans();
    Overview.render();
    await applyInitialRoute();
  }

  async function applyInitialRoute() {
    const params = App.state.initialParams || {};
    if (params.ack_token) {
      await Ack.loadAck(params.ack_token);
      return;
    }
    if (params.notification_id || params.history_id) {
      const id = params.notification_id || params.history_id;
      switchView("history");
      App.state.historySearched = true;
      await History.selectNotice(id);
      return;
    }
    if (params.plan_id) {
      const planId = Number(params.plan_id);
      switchView("plans");
      if (Number.isFinite(planId)) Plans.selectPlan(planId);
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    init().catch((err) => showToast(`初始化失敗：${err.message}`));
  });
}());
