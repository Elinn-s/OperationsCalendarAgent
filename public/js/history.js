(function () {
  function filteredNotices() {
    const q = $("searchInput").value.trim().toLowerCase();
    if (!q) return App.state.notices;
    return App.state.notices.filter((n) => [n.title, n.system_no, n.doc_ref, n.owner, n.issuer, n.department]
      .some((v) => String(v || "").toLowerCase().includes(q)));
  }

  async function loadHistory(id) {
    const root = $("history");
    root.innerHTML = `<div class="meta">載入中...</div>`;
    const rows = await request(`/notifications/${id}/history`);
    root.innerHTML = rows.length ? "" : `<div class="meta">暫無歷史。</div>`;
    for (const row of rows) {
      const item = document.createElement("div");
      item.className = "timeline-item";
      item.innerHTML = `<b>${escapeHtml(row.type || "")} · ${escapeHtml(row.action || "")}</b><br>${escapeHtml(row.time || "")} · ${escapeHtml(row.actor || "系統")}<br>${escapeHtml(row.detail || "")}`;
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
    const rows = filteredNotices().slice(0, 300);
    root.innerHTML = rows.length ? "" : `<div class="meta">暫無通告。</div>`;
    for (const n of rows) {
      const deadline = n.deadline || n.effective_end || "";
      const btn = document.createElement("button");
      btn.className = "notice-item" + (n.notification_id === App.state.selectedId ? " active" : "");
      btn.type = "button";
      btn.innerHTML = `
        <div class="row">
          <div class="title">${escapeHtml(n.title || "(無標題)")}</div>
          <span class="${statusBadgeClass(n.status, deadline)}">${escapeHtml(statusLabel(n.status, deadline))}</span>
        </div>
        <div class="meta">${escapeHtml(n.system_no || "未編號")} · 截止 ${escapeHtml(deadline || "未設定")}</div>
        <div class="meta">匯入時間 ${escapeHtml(formatDateTime(n.created_at))}</div>
        <div class="meta">${escapeHtml(n.owner || n.issuer || n.department || "未設定負責人")}</div>
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
      if (shouldAskReminder && confirm("是否對 DDL 進行郵件提醒？")) {
        const stats = await request(`/notifications/${App.state.selectedId}/scan-reminders`, { method: "POST" });
        reminderText = ` 已掃描提醒：發送 ${stats.sent || 0}，失敗 ${stats.failed || 0}，跳過 ${stats.skipped || 0}。`;
      }
      showToast((isImportDraft ? "識別通告已保存入庫。" : "通告修改已保存。") + reminderText);
      await loadNotifications();
      if (App.state.selectedId) await selectNotice(App.state.selectedId);
    } catch (err) {
      showToast(`保存失敗：${err.message}`);
    }
  }

  async function deleteNotice() {
    if (!App.state.selectedId || !confirm("確認刪除當前通告？")) return;
    try {
      await request(`/notifications/${App.state.selectedId}?actor_email=${encodeURIComponent(App.state.email)}`, { method: "DELETE" });
      App.state.selectedId = null;
      App.state.currentNotice = null;
      showToast("已刪除通告。");
      await loadNotifications();
      resetNoticeDetail("history");
    } catch (err) {
      showToast(`刪除失敗：${err.message}`);
    }
  }

  async function sendAckEmails() {
    if (!App.state.selectedId) {
      showToast("請先選擇一條通告。");
      return;
    }
    if (!confirm("確認向未回執收件人發送回執郵件？")) return;
    try {
      const stats = await request(`/ack/notifications/${App.state.selectedId}/send`, { method: "POST" });
      showToast(`回執郵件已處理：檢查 ${stats.checked || 0}，發送 ${stats.sent || 0}，失敗 ${stats.failed || 0}，跳過 ${stats.skipped || 0}。`);
      await loadHistory(App.state.selectedId);
    } catch (err) {
      showToast(`發送回執郵件失敗：${err.message}`);
    }
  }

  function cancelNoticeEdit() {
    if (App.state.currentNotice) {
      fillNoticeForm("history", App.state.currentNotice);
      setNoticeEditMode(false);
      showToast("已撤銷未保存修改。");
      return;
    }
    if (App.state.importDraft) {
      fillNoticeForm("history", App.state.importDraft);
      setNoticeEditMode(true);
      showToast("已恢復識別結果。");
    }
  }

  window.History = {
    loadNotifications,
    renderList,
    selectNotice,
    saveNotice,
    deleteNotice,
    sendAckEmails,
    cancelNoticeEdit,
    enableEdit() {
      if (!App.state.selectedId && !App.state.importDraft) {
        showToast("請先選擇一條通告。");
        return;
      }
      setNoticeEditMode(true);
      showToast("已進入編輯模式。");
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
