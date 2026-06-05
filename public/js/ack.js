(function () {
  async function loadAck(token) {
    if (!token) return;
    App.state.ackToken = token;
    switchView("ack");
    $("ackStatusBadge").textContent = "待確認";
    $("ackStatusBadge").className = "badge amber";
    $("ackDetail").innerHTML = `<div class="meta">正在載入回執資料...</div>`;
    $("confirmAckBtn").disabled = false;
    try {
      const row = await request(`/ack/${encodeURIComponent(token)}`);
      const deadline = row.deadline || row.effective_end || "未設定";
      $("ackDetail").innerHTML = `
        <div class="metric-row"><strong>通告標題</strong><span>${escapeHtml(row.title || "(無標題)")}</span></div>
        <div class="metric-row"><strong>通告編號</strong><span>${escapeHtml(row.system_no || "未編號")}</span></div>
        <div class="metric-row"><strong>截止日期</strong><span>${escapeHtml(deadline)}</span></div>
        <div class="metric-row"><strong>收件人</strong><span>${escapeHtml(row.recipient_name || row.email || "未設定")}</span></div>
        <div class="metric-row"><strong>狀態</strong><span>${row.confirmed_at ? "已回執" : "待確認"}</span></div>
      `;
      if (row.confirmed_at) {
        $("ackStatusBadge").textContent = "已回執";
        $("ackStatusBadge").className = "badge green";
        $("confirmAckBtn").disabled = true;
      }
    } catch (err) {
      $("ackStatusBadge").textContent = "載入失敗";
      $("ackStatusBadge").className = "badge red";
      $("ackDetail").innerHTML = `<div class="meta">回執資料載入失敗：${escapeHtml(err.message)}</div>`;
      $("confirmAckBtn").disabled = true;
    }
  }

  async function confirmAck() {
    const token = App.state.ackToken;
    if (!token) {
      showToast("缺少回執 token。");
      return;
    }
    try {
      const result = await request(`/ack/${encodeURIComponent(token)}/confirm`, { method: "POST" });
      $("ackStatusBadge").textContent = result.status === "already_confirmed" ? "已回執" : "確認成功";
      $("ackStatusBadge").className = "badge green";
      $("confirmAckBtn").disabled = true;
      showToast("回執已確認。");
      await loadAck(token);
    } catch (err) {
      showToast(`回執確認失敗：${err.message}`);
    }
  }

  window.Ack = {
    loadAck,
    confirmAck,
  };
}());
