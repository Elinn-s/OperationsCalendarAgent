(function () {
  function fieldDefinitions() {
    return [
    ["system_no", "系統編號", "input", { disabled: true }],
    ["doc_ref", "檔案編號", "input"],
    ["title", "標題 *", "input", { required: true, span: true }],
    ["status", "狀態", "select", { options: [["草稿", "草稿"], ["执行中", "執行中"], ["已回执", "已回執"], ["已完成", "已完成"]] }],
    ["notice_type", "通告類型", "select", { options: [["安全合规", "安全合規"], ["日常营运", "日常營運"], ["活动通知", "活動通知"], ["人事行政", "人事行政"], ["其他", "其他"]] }],
    ["issuer", "發佈人 / Issuer", "input"],
    ["owner", "負責人 / Owner", "input"],
    ["owner_role", "負責人角色", "input"],
    ["department", "部門", "input"],
    ["effective_start", "執行開始", "input", { type: "date" }],
    ["deadline", "截止日期", "input", { type: "date" }],
    ["target_scope", "影響對象 / 範圍", "input", { span: true }],
    ["impact_store", "影響門店", "input"],
    ["impact_region", "影響區域", "input"],
    ["impact_role", "影響角色", "input"],
    ["reminder_email", "默認提醒郵箱", "input", { type: "email" }],
    ["reminder_days", "自定義提前天數", "input", { placeholder: t("留空使用全局，例如 7,3,1") }],
    ["description", "通告描述", "textarea", { span: true }],
    ];
  }

  function controlHtml(id, type, config = {}) {
    if (type === "textarea") return `<textarea id="${id}"></textarea>`;
    if (type === "select") {
      return `<select id="${id}">${config.options.map((option) => {
        const value = Array.isArray(option) ? option[0] : option;
        const label = Array.isArray(option) ? option[1] : option;
        return `<option value="${escapeHtml(value)}">${escapeHtml(t(label))}</option>`;
      }).join("")}</select>`;
    }
    const inputType = config.type || "text";
    const disabled = config.disabled ? " disabled" : "";
    const required = config.required ? " required" : "";
    const placeholder = config.placeholder ? ` placeholder="${escapeHtml(config.placeholder)}"` : "";
    return `<input id="${id}" type="${inputType}"${disabled}${required}${placeholder} />`;
  }

  window.renderNoticeFields = function renderNoticeFields(rootSelector) {
    document.querySelectorAll(rootSelector).forEach((root) => {
      root.innerHTML = fieldDefinitions().map(([id, label, type, config = {}]) => {
        const span = config.span ? " class=\"span-2\"" : "";
        return `<label${span}>${t(label)}${controlHtml(id, type, config)}</label>`;
      }).join("");
    });
  };

  window.fillNoticeForm = function fillNoticeForm(prefix, notice = {}) {
    const detailCard = $("detailCard");
    const historyView = $("view-history");
    const form = $("noticeForm");
    const empty = $("historyEmpty");
    if (detailCard) detailCard.hidden = false;
    if (historyView) historyView.classList.add("detail-open");
    if (form) form.hidden = false;
    if (empty) empty.hidden = true;

    const titleEl = $("detailTitle");
    const badgeEl = $("detailBadge");
    const metaEl = $("detailMeta");
    titleEl.textContent = notice.notification_id ? t("通告詳情") : t("識別結果詳情");
    badgeEl.textContent = notice.notification_id ? statusLabel(notice.status, notice.deadline || notice.effective_end) : t("待保存");
    badgeEl.className = statusBadgeClass(notice.status, notice.deadline || notice.effective_end);
    if (metaEl) {
      metaEl.textContent = notice.notification_id
        ? `${t("匯入時間")}：${formatDateTime(notice.created_at)}`
        : `${t("匯入時間")}：${t("待保存，保存入庫後生成")}`;
    }

    for (const key of App.fields) {
      const el = $(key);
      if (!el) continue;
      el.value = notice[key] || "";
    }
    $("deadline").value = (notice.deadline || notice.effective_end || "").slice(0, 10);
    $("effective_start").value = (notice.effective_start || "").slice(0, 10);
    $("reminder_email").value = notice.reminder_email || App.state.email;
    if ($("deleteBtn")) $("deleteBtn").disabled = !notice.notification_id;
  };

  window.setNoticeEditMode = function setNoticeEditMode(canEdit) {
    $("noticeForm").classList.toggle("readonly", !canEdit);
    for (const key of App.fields) {
      const el = $(key);
      if (!el) continue;
      el.disabled = !canEdit || key === "system_no";
    }
    $("editNoticeBtn").hidden = canEdit;
    $("deleteBtn").hidden = !canEdit;
    $("sendAckBtn").hidden = canEdit || !App.state.selectedId;
    $("cancelBtn").hidden = !canEdit;
    $("noticeForm").querySelector("button[type='submit']").hidden = !canEdit;
  };

  window.collectNoticePayload = function collectNoticePayload() {
    const title = $("title").value.trim();
    const start = $("effective_start").value;
    const deadline = $("deadline").value;
    if (!title) throw new Error(t("標題不能為空"));
    if (start && deadline && deadline < start) throw new Error(t("截止日期不能早於執行開始"));

    const payload = {
      actor_email: App.state.email,
      reminder_email: $("reminder_email").value.trim() || App.state.email,
      effective_end: deadline || null,
      tags: [],
    };
    for (const key of App.fields) {
      if (key === "reminder_email") continue;
      payload[key] = $(key).value.trim();
    }
    payload.deadline = deadline || null;
    return payload;
  };

  window.resetNoticeDetail = function resetNoticeDetail(prefix) {
    const detailCard = $("detailCard");
    const historyView = $("view-history");
    const form = $("noticeForm");
    const empty = $("historyEmpty");
    if (detailCard) detailCard.hidden = true;
    if (historyView) historyView.classList.remove("detail-open");
    if (form) form.hidden = true;
    if (empty) empty.hidden = false;
    $("detailTitle").textContent = t("通告詳情");
    $("detailBadge").textContent = t("未選擇");
    $("detailBadge").className = "badge";
    $("detailMeta").textContent = "";
    $("history").innerHTML = "";
    setNoticeEditMode(false);
  };
}());
