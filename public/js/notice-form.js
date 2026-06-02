(function () {
  const fieldDefinitions = [
    ["system_no", "系统编号", "input", { disabled: true }],
    ["doc_ref", "档案编号", "input"],
    ["title", "标题 *", "input", { required: true, span: true }],
    ["status", "状态", "select", { options: ["草稿", "执行中", "已回执", "已完成", "已逾期"] }],
    ["notice_type", "通告类型", "select", { options: ["安全合规", "日常营运", "活动通知", "人事行政", "其他"] }],
    ["issuer", "发布人 / Issuer", "input"],
    ["owner", "负责人 / Owner", "input"],
    ["owner_role", "负责人角色", "input"],
    ["department", "部门", "input"],
    ["effective_start", "执行开始", "input", { type: "date" }],
    ["deadline", "截止日期", "input", { type: "date" }],
    ["target_scope", "影响对象 / 范围", "input", { span: true }],
    ["impact_store", "影响门店", "input"],
    ["impact_region", "影响区域", "input"],
    ["impact_role", "影响角色", "input"],
    ["reminder_email", "默认提醒邮箱", "input", { type: "email" }],
    ["description", "通告描述", "textarea", { span: true }],
  ];

  function controlHtml(id, type, config = {}) {
    if (type === "textarea") return `<textarea id="${id}"></textarea>`;
    if (type === "select") {
      return `<select id="${id}">${config.options.map((option) => `<option>${escapeHtml(option)}</option>`).join("")}</select>`;
    }
    const inputType = config.type || "text";
    const disabled = config.disabled ? " disabled" : "";
    const required = config.required ? " required" : "";
    return `<input id="${id}" type="${inputType}"${disabled}${required} />`;
  }

  window.renderNoticeFields = function renderNoticeFields(rootSelector) {
    document.querySelectorAll(rootSelector).forEach((root) => {
      root.innerHTML = fieldDefinitions.map(([id, label, type, config = {}]) => {
        const span = config.span ? " class=\"span-2\"" : "";
        return `<label${span}>${label}${controlHtml(id, type, config)}</label>`;
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
    titleEl.textContent = notice.notification_id ? "通告详情" : "识别结果详情";
    badgeEl.textContent = notice.status || (notice.notification_id ? "未填" : "待保存");
    badgeEl.className = statusBadgeClass(notice.status, notice.deadline || notice.effective_end);
    if (metaEl) {
      metaEl.textContent = notice.notification_id
        ? `导入时间：${formatDateTime(notice.created_at)}`
        : "导入时间：待保存，保存入库后生成";
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
    $("cancelBtn").hidden = !canEdit;
    $("noticeForm").querySelector("button[type='submit']").hidden = !canEdit;
  };

  window.collectNoticePayload = function collectNoticePayload() {
    const title = $("title").value.trim();
    const start = $("effective_start").value;
    const deadline = $("deadline").value;
    if (!title) throw new Error("标题不能为空");
    if (start && deadline && deadline < start) throw new Error("截止日期不能早于执行开始");

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
    $("detailTitle").textContent = "通告详情";
    $("detailBadge").textContent = "未选择";
    $("detailBadge").className = "badge";
    $("detailMeta").textContent = "";
    $("history").innerHTML = "";
    setNoticeEditMode(false);
  };
}());
