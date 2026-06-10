(function () {
  async function loadPlans() {
    App.state.plans = await request("/plans");
    renderPlans();
    if (!App.state.selectedPlanId && App.state.plans[0]) selectPlan(App.state.plans[0].id);
  }

  function planCardClass(status) {
    if (status === "已发布") return " plan-published";
    if (status === "已编写") return " plan-written";
    return "";
  }

  function defaultPlanReminderDays() {
    return (App.state.emailSettings && App.state.emailSettings.settings && App.state.emailSettings.settings.plan_reminder_days) || "7";
  }

  function maxReminderDays(raw) {
    const values = String(raw || "7").replace("，", ",").split(",")
      .map((part) => Number(part.trim()))
      .filter((value) => Number.isFinite(value) && value >= 0);
    return values.length ? Math.max(...values) : 7;
  }

  function planStatusSelectClass(status) {
    if (status === "已发布") return "inline-status status-published";
    if (status === "已编写") return "inline-status status-written";
    return "inline-status";
  }

  function defaultReminderDate(plannedDate) {
    if (!plannedDate) return "";
    const d = new Date(plannedDate + "T00:00:00");
    d.setDate(d.getDate() - maxReminderDays($("plan_reminder_days").value || defaultPlanReminderDays()));
    return d.toISOString().slice(0, 10);
  }

  function syncReminderDateFromDdl() {
    if ($("plan_publish_reminder_date").value) return;
    $("plan_publish_reminder_date").value = defaultReminderDate($("plan_planned_publish_date").value);
  }

  function isReminderDue(payload) {
    if (!Number(payload.reminder_enabled) || !payload.publish_reminder_date) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const reminderDate = new Date(payload.publish_reminder_date + "T00:00:00");
    return reminderDate <= today && ["已预录", "已编写"].includes(payload.status);
  }

  function setPlanEditMode(canEdit) {
    $("planForm").classList.toggle("readonly", !canEdit);
    [
      "plan_activity_name",
      "plan_owner",
      "plan_planned_publish_date",
      "plan_status",
      "plan_reminder_enabled",
      "plan_publish_reminder_date",
      "plan_reminder_days",
      "plan_notification_content",
    ].forEach((id) => {
      $(id).disabled = !canEdit;
    });
    $("editPlanBtn").hidden = canEdit || !App.state.selectedPlanId;
    $("deletePlanBtn").hidden = !canEdit;
    $("cancelPlanEditBtn").hidden = !canEdit;
    $("planForm").querySelector("button[type='submit']").hidden = !canEdit;
    $("markWrittenBtn").hidden = !canEdit;
    $("markPublishedBtn").hidden = !canEdit;
    $("clearPlanMarkBtn").hidden = !canEdit;
  }

  function renderPlans() {
    $("planCount").textContent = App.state.plans.length;
    const root = $("planList");
    root.innerHTML = App.state.plans.length ? "" : `<div class="meta">${t("暫無預錄。")}</div>`;
    for (const plan of App.state.plans) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "notice-item" + planCardClass(plan.status) + (plan.id === App.state.selectedPlanId ? " active" : "");
      btn.innerHTML = `
        <div class="row">
          <div class="title">${escapeHtml(plan.activity_name || `(${t("未命名")})`)}</div>
          <select class="${planStatusSelectClass(plan.status)}" data-plan-status-id="${plan.id}" aria-label="${t("修改預錄狀態")}">
            ${["已预录", "已编写", "已发布"].map((status) => `<option value="${status}"${status === (plan.status || "已预录") ? " selected" : ""}>${statusLabel(status)}</option>`).join("")}
          </select>
        </div>
        <div class="meta">${t("計劃發佈")} ${escapeHtml(plan.planned_publish_date || t("未設定"))} · ${escapeHtml(plan.owner || t("未設定負責人"))}</div>
        <div class="meta">${t("預錄時間")} ${escapeHtml(formatDateTime(plan.created_at))}</div>
        <div class="meta">${t("郵件提醒")} ${Number(plan.reminder_enabled == null ? 1 : plan.reminder_enabled) ? t("開啟") : t("關閉")} · ${t("提醒日")} ${escapeHtml(plan.publish_reminder_date || t("未設定"))} · ${t("提前")} ${escapeHtml(plan.reminder_days || defaultPlanReminderDays())} ${t("天")}</div>
      `;
      btn.addEventListener("click", () => selectPlan(plan.id));
      root.appendChild(btn);
    }
    root.querySelectorAll("[data-plan-status-id]").forEach((select) => {
      select.addEventListener("click", (event) => event.stopPropagation());
      select.addEventListener("change", (event) => updatePlanStatusFromList(Number(event.target.dataset.planStatusId), event.target.value));
    });
  }

  function selectPlan(id) {
    const plan = App.state.plans.find((item) => item.id === id);
    if (!plan) return;
    App.state.selectedPlanId = id;
    $("plan_activity_name").value = plan.activity_name || "";
    $("plan_owner").value = plan.owner || "";
    $("plan_planned_publish_date").value = (plan.planned_publish_date || "").slice(0, 10);
    $("plan_publish_reminder_date").value = (plan.publish_reminder_date || "").slice(0, 10);
    $("plan_reminder_days").value = plan.reminder_days || "";
    $("plan_reminder_enabled").value = String(Number(plan.reminder_enabled == null ? 1 : plan.reminder_enabled));
    $("plan_status").value = plan.status || "已预录";
    $("plan_notification_content").value = plan.notification_content || "";
    setPlanEditMode(false);
    renderPlans();
  }

  function clearPlanForm() {
    App.state.selectedPlanId = null;
    $("plan_activity_name").value = "";
    $("plan_owner").value = App.state.email;
    $("plan_planned_publish_date").value = "";
    $("plan_publish_reminder_date").value = "";
    $("plan_reminder_days").value = "";
    $("plan_reminder_enabled").value = "1";
    $("plan_status").value = "已预录";
    $("plan_notification_content").value = "";
    setPlanEditMode(true);
    renderPlans();
  }

  async function deletePlan() {
    if (!App.state.selectedPlanId) {
      showToast(t("請先選擇要刪除的預錄。"));
      return;
    }
    if (!confirm(t("確認刪除當前預錄？"))) return;
    try {
      await request(`/plans/${App.state.selectedPlanId}`, { method: "DELETE" });
      showToast(t("預錄已刪除。"));
      App.state.selectedPlanId = null;
      clearPlanForm();
      await loadPlans();
    } catch (err) {
      showToast(`${t("刪除預錄失敗")}：${err.message}`);
    }
  }

  async function extractPlanText() {
    const text = $("planRawText").value.trim();
    if (!text) {
      showToast(t("請先貼上預錄文案。"));
      return;
    }
    try {
      const fields = await request("/plans/extract", { method: "POST", body: JSON.stringify({ text }) });
      App.state.selectedPlanId = null;
      $("plan_activity_name").value = fields.activity_name || "";
      $("plan_owner").value = fields.owner || App.state.email;
      $("plan_planned_publish_date").value = fields.planned_publish_date || "";
      $("plan_reminder_days").value = "";
      $("plan_publish_reminder_date").value = fields.publish_reminder_date || defaultReminderDate(fields.planned_publish_date);
      $("plan_reminder_enabled").value = "1";
      $("plan_status").value = fields.status || "已预录";
      $("plan_notification_content").value = fields.notification_content || text;
      setPlanEditMode(true);
      showToast(t("預錄文案已識別，請核對後保存。"));
    } catch (err) {
      showToast(`${t("預錄識別失敗")}：${err.message}`);
    }
  }

  function collectPlanPayload() {
    const name = $("plan_activity_name").value.trim();
    if (!name) throw new Error(t("活動名稱不能為空"));
    return {
      activity_name: name,
      owner: $("plan_owner").value.trim(),
      planned_publish_date: $("plan_planned_publish_date").value || null,
      make_reminder_date: null,
      publish_reminder_date: $("plan_publish_reminder_date").value || defaultReminderDate($("plan_planned_publish_date").value) || null,
      notification_content: $("plan_notification_content").value.trim(),
      status: $("plan_status").value,
      reminder_enabled: Number($("plan_reminder_enabled").value),
      reminder_days: $("plan_reminder_days").value.trim(),
      actor_email: App.state.email,
      reminder_email: App.state.email,
    };
  }

  async function savePlan(event) {
    event.preventDefault();
    try {
      const payload = collectPlanPayload();
      let savedPlanId = App.state.selectedPlanId;
      if (App.state.selectedPlanId) {
        await request(`/plans/${App.state.selectedPlanId}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        const result = await request("/plans", { method: "POST", body: JSON.stringify(payload) });
        savedPlanId = result.id;
        App.state.selectedPlanId = result.id;
      }
      let reminderText = "";
      if (isReminderDue(payload) && confirm(t("郵件提醒日已到，是否現在發送這條預錄提醒？"))) {
        const stats = await request(`/plans/${savedPlanId}/scan-reminders`, { method: "POST" });
        reminderText = ` ${t("已掃描提醒")}：${t("發送")} ${stats.sent || 0}，${t("失敗")} ${stats.failed || 0}，${t("跳過")} ${stats.skipped || 0}。`;
      }
      showToast(t("預錄已保存。") + reminderText);
      await loadPlans();
      setPlanEditMode(false);
    } catch (err) {
      showToast(`${t("保存預錄失敗")}：${err.message}`);
    }
  }

  async function markPlanStatus(status) {
    if (!App.state.selectedPlanId) {
      showToast(t("請先選擇一個預錄。"));
      return;
    }
    try {
      $("plan_status").value = status;
      const payload = collectPlanPayload();
      await request(`/plans/${App.state.selectedPlanId}`, { method: "PUT", body: JSON.stringify(payload) });
      showToast(`${t("預錄已標記為")}：${statusLabel(status)}。`);
      await loadPlans();
    } catch (err) {
      showToast(`${t("標記失敗")}：${err.message}`);
    }
  }

  function cancelPlanEdit() {
    if (App.state.selectedPlanId) {
      selectPlan(App.state.selectedPlanId);
      showToast(t("已撤銷未保存的預錄修改。"));
      return;
    }
    clearPlanForm();
    showToast(t("已清空新建預錄表單。"));
  }

  async function updatePlanStatusFromList(planId, status) {
    const plan = App.state.plans.find((item) => item.id === planId);
    if (!plan) return;
    try {
      const payload = {
        activity_name: plan.activity_name || "",
        owner: plan.owner || "",
        planned_publish_date: plan.planned_publish_date || null,
        make_reminder_date: null,
        publish_reminder_date: plan.publish_reminder_date || defaultReminderDate(plan.planned_publish_date) || null,
        notification_content: plan.notification_content || "",
        status,
        reminder_enabled: Number(plan.reminder_enabled == null ? 1 : plan.reminder_enabled),
        reminder_days: plan.reminder_days || "",
        actor_email: App.state.email,
        reminder_email: App.state.email || plan.reminder_email || "",
      };
      await request(`/plans/${planId}`, { method: "PUT", body: JSON.stringify(payload) });
      showToast(`${t("預錄已更新為")}：${statusLabel(status)}。`);
      await loadPlans();
    } catch (err) {
      showToast(`${t("修改預錄狀態失敗")}：${err.message}`);
      await loadPlans();
    }
  }

  window.Plans = {
    loadPlans,
    renderPlans,
    selectPlan,
    clearPlanForm,
    deletePlan,
    extractPlanText,
    savePlan,
    cancelPlanEdit,
    markWritten() {
      markPlanStatus("已编写");
    },
    markPublished() {
      markPlanStatus("已发布");
    },
    clearMark() {
      markPlanStatus("已预录");
    },
    syncReminderDateFromDdl,
    enableEdit() {
      if (!App.state.selectedPlanId) {
        showToast(t("請先選擇一個預錄。"));
        return;
      }
      setPlanEditMode(true);
      showToast(t("已進入預錄編輯模式。"));
    },
  };
}());
