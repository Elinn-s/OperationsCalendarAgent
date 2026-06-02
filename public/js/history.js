(function () {
  function filteredNotices() {
    const q = $("searchInput").value.trim().toLowerCase();
    if (!q) return App.state.notices;
    return App.state.notices.filter((n) => [n.title, n.system_no, n.doc_ref, n.owner, n.issuer, n.department]
      .some((v) => String(v || "").toLowerCase().includes(q)));
  }

  async function loadHistory(id) {
    const root = $("history");
    root.innerHTML = `<div class="meta">加载中...</div>`;
    const rows = await request(`/notifications/${id}/history`);
    root.innerHTML = rows.length ? "" : `<div class="meta">暂无历史。</div>`;
    for (const row of rows) {
      const item = document.createElement("div");
      item.className = "timeline-item";
      item.innerHTML = `<b>${escapeHtml(row.type || "")} · ${escapeHtml(row.action || "")}</b><br>${escapeHtml(row.time || "")} · ${escapeHtml(row.actor || "系统")}<br>${escapeHtml(row.detail || "")}`;
      root.appendChild(item);
    }
  }

  async function loadNotifications() {
    const status = $("statusFilter").value;
    const params = new URLSearchParams({ limit: "300" });
    if (status) params.set("status", status);
    App.state.notices = await request(`/notifications?${params.toString()}`);
    Overview.render();
    renderList();
  }

  function renderList() {
    const root = $("noticeList");
    if (!App.state.historySearched) {
      root.innerHTML = `<div class="meta">请输入条件后点击“搜索”查看历史记录。</div>`;
      return;
    }
    const rows = filteredNotices();
    root.innerHTML = rows.length ? "" : `<div class="meta">暂无通告。</div>`;
    for (const n of rows) {
      const deadline = n.deadline || n.effective_end || "";
      const btn = document.createElement("button");
      btn.className = "notice-item" + (n.notification_id === App.state.selectedId ? " active" : "");
      btn.type = "button";
      btn.innerHTML = `
        <div class="row">
          <div class="title">${escapeHtml(n.title || "(无标题)")}</div>
          <span class="${statusBadgeClass(n.status, deadline)}">${escapeHtml(n.status || "未填")}</span>
        </div>
        <div class="meta">${escapeHtml(n.system_no || "未编号")} · 截止 ${escapeHtml(deadline || "未设置")}</div>
        <div class="meta">导入时间 ${escapeHtml(formatDateTime(n.created_at))}</div>
        <div class="meta">${escapeHtml(n.owner || n.issuer || n.department || "未设置负责人")}</div>
      `;
      btn.addEventListener("click", () => selectNotice(n.notification_id));
      root.appendChild(btn);
    }
  }

  async function selectNotice(id) {
    App.state.selectedId = id;
    const n = await request(`/notifications/${id}`);
    App.state.currentNotice = n;
    App.state.importDraft = null;
    fillNoticeForm("history", n);
    setNoticeEditMode(false);
    renderList();
    loadHistory(id);
  }

  async function saveNotice(event) {
    event.preventDefault();
    try {
      const payload = collectNoticePayload();
      const isImportDraft = Boolean(App.state.importDraft) && !App.state.selectedId;
      const shouldAskReminder = !isImportDraft
        && App.state.currentNotice
        && App.state.currentNotice.status !== "执行中"
        && payload.status === "执行中";
      const result = isImportDraft
        ? await request("/notifications", { method: "POST", body: JSON.stringify(payload) })
        : await request(`/notifications/${App.state.selectedId}`, { method: "PUT", body: JSON.stringify(payload) });
      App.state.selectedId = result.notification_id || App.state.selectedId;
      App.state.importDraft = null;
      let reminderText = "";
      if (shouldAskReminder && confirm("是否对 DDL 进行邮件提醒？")) {
        const stats = await request(`/notifications/${App.state.selectedId}/scan-reminders`, { method: "POST" });
        reminderText = ` 已扫描提醒：发送 ${stats.sent || 0}，失败 ${stats.failed || 0}，跳过 ${stats.skipped || 0}。`;
      }
      showToast((isImportDraft ? "识别通告已保存入库。" : "通告修改已保存。") + reminderText);
      await loadNotifications();
      if (App.state.selectedId) await selectNotice(App.state.selectedId);
    } catch (err) {
      showToast(`保存失败：${err.message}`);
    }
  }

  async function deleteNotice() {
    if (!App.state.selectedId || !confirm("确认删除当前通告？")) return;
    try {
      await request(`/notifications/${App.state.selectedId}?actor_email=${encodeURIComponent(App.state.email)}`, { method: "DELETE" });
      App.state.selectedId = null;
      App.state.currentNotice = null;
      showToast("已删除通告。");
      await loadNotifications();
      resetNoticeDetail("history");
    } catch (err) {
      showToast(`删除失败：${err.message}`);
    }
  }

  function cancelNoticeEdit() {
    if (App.state.currentNotice) {
      fillNoticeForm("history", App.state.currentNotice);
      setNoticeEditMode(false);
      showToast("已撤销未保存修改。");
      return;
    }
    if (App.state.importDraft) {
      fillNoticeForm("history", App.state.importDraft);
      setNoticeEditMode(true);
      showToast("已恢复识别结果。");
    }
  }

  window.History = {
    loadNotifications,
    renderList,
    selectNotice,
    saveNotice,
    deleteNotice,
    cancelNoticeEdit,
    enableEdit() {
      if (!App.state.selectedId && !App.state.importDraft) {
        showToast("请先选择一条通告。");
        return;
      }
      setNoticeEditMode(true);
      showToast("已进入编辑模式。");
    },
    search() {
      App.state.historySearched = true;
      renderList();
    },
    async refresh() {
      App.state.historySearched = true;
      await loadNotifications();
    },
  };
}());
