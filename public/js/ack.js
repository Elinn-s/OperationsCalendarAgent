(function () {
  async function loadAck(token) {
    if (!token) return;
    App.state.ackToken = token;
    switchView("ack");
    $("ackStatusBadge").textContent = t("待確認");
    $("ackStatusBadge").className = "badge amber";
    $("ackDetail").innerHTML = `<div class="meta">${t("正在載入回執資料...")}</div>`;
    $("confirmAckBtn").disabled = false;
    try {
      const row = await request(`/ack/${encodeURIComponent(token)}`);
      const deadline = row.deadline || row.effective_end || t("未設定");
      $("ackDetail").innerHTML = `
        <div class="metric-row"><strong>${t("通告標題")}</strong><span>${escapeHtml(row.title || `(${t("無標題")})`)}</span></div>
        <div class="metric-row"><strong>${t("通告編號")}</strong><span>${escapeHtml(row.system_no || t("未編號"))}</span></div>
        <div class="metric-row"><strong>${t("截止日期")}</strong><span>${escapeHtml(deadline)}</span></div>
        <div class="metric-row"><strong>${t("收件人")}</strong><span>${escapeHtml(row.recipient_name || row.email || t("未設定"))}</span></div>
        <div class="metric-row"><strong>${t("狀態")}</strong><span>${row.confirmed_at ? t("已回執") : t("待確認")}</span></div>
      `;
      if (row.confirmed_at) {
        $("ackStatusBadge").textContent = t("已回執");
        $("ackStatusBadge").className = "badge green";
        $("confirmAckBtn").disabled = true;
      }
    } catch (err) {
      $("ackStatusBadge").textContent = t("載入失敗");
      $("ackStatusBadge").className = "badge red";
      $("ackDetail").innerHTML = `<div class="meta">${t("回執資料載入失敗")}：${escapeHtml(err.message)}</div>`;
      $("confirmAckBtn").disabled = true;
    }
  }

  async function confirmAck() {
    const token = App.state.ackToken;
    if (!token) {
      showToast(t("缺少回執 token。"));
      return;
    }
    try {
      const result = await request(`/ack/${encodeURIComponent(token)}/confirm`, { method: "POST" });
      $("ackStatusBadge").textContent = result.status === "already_confirmed" ? t("已回執") : t("確認成功");
      $("ackStatusBadge").className = "badge green";
      $("confirmAckBtn").disabled = true;
      showToast(t("回執已確認。"));
      await loadAck(token);
    } catch (err) {
      showToast(`${t("回執確認失敗")}：${err.message}`);
    }
  }

  window.Ack = {
    loadAck,
    confirmAck,
  };
}());
