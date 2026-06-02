(function () {
  function isThisMonth(raw) {
    if (!raw) return false;
    const d = new Date(String(raw).slice(0, 10) + "T00:00:00");
    const now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
  }

  function renderMetricRows(rootId, rows, emptyText) {
    const root = $(rootId);
    root.innerHTML = rows.length ? "" : `<div class="meta">${emptyText}</div>`;
    for (const row of rows) {
      const item = document.createElement("div");
      item.className = "metric-row";
      item.innerHTML = `<strong>${escapeHtml(row.label)}</strong><span>${escapeHtml(row.value)}</span>`;
      root.appendChild(item);
    }
  }

  function renderTypePie(entries) {
    const pie = $("typePie");
    const legend = $("typePieLegend");
    const colors = ["#5e6ad2", "#16a34a", "#b45309", "#dc2626", "#2563eb", "#7c3aed"];
    const total = entries.reduce((sum, [, value]) => sum + value, 0);
    if (!total) {
      pie.style.background = "#eef0fc";
      legend.innerHTML = `<div class="meta">暂无类型分布。</div>`;
      return;
    }

    let cursor = 0;
    const slices = entries.map(([label, value], index) => {
      const start = cursor;
      const end = cursor + (value / total) * 100;
      cursor = end;
      return `${colors[index % colors.length]} ${start}% ${end}%`;
    });
    pie.style.background = `conic-gradient(${slices.join(", ")})`;
    legend.innerHTML = "";
    entries.forEach(([label, value], index) => {
      const item = document.createElement("div");
      item.className = "pie-legend-item";
      const percent = Math.round((value / total) * 100);
      item.innerHTML = `<span class="pie-dot" style="background:${colors[index % colors.length]}"></span><span>${escapeHtml(label)} · ${value} 条 · ${percent}%</span>`;
      legend.appendChild(item);
    });
  }

  function renderAttention(rows) {
    const root = $("attentionList");
    root.innerHTML = rows.length ? "" : `<div class="meta">暂无需要关注的通告。</div>`;
    for (const n of rows.slice(0, 6)) {
      const deadline = n.deadline || n.effective_end || "";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "notice-item";
      btn.innerHTML = `
        <div class="row">
          <div class="title">${escapeHtml(n.title || "(无标题)")}</div>
          <span class="${statusBadgeClass(n.status, deadline)}">${escapeHtml(n.status || "未填")}</span>
        </div>
        <div class="meta">${escapeHtml(n.system_no || "未编号")} · 截止 ${escapeHtml(deadline || "未设置")}</div>
      `;
      btn.addEventListener("click", async () => {
        switchView("history");
        App.state.historySearched = true;
        await window.History.selectNotice(n.notification_id);
      });
      root.appendChild(btn);
    }
  }

  window.Overview = {
    render() {
      const rows = App.state.notices || [];
      const monthRows = rows.filter((n) => isThisMonth(n.created_at || n.effective_start || n.deadline));
      const attention = rows.filter((n) => {
        const d = daysLeft(n.deadline || n.effective_end);
        return d < 0 || d <= 7 || n.status === "已逾期";
      });

      $("kpiMonthTotal").textContent = monthRows.length;
      $("kpiRunning").textContent = rows.filter((n) => ["执行中", "已回执"].includes(n.status)).length;
      $("kpiSoon").textContent = rows.filter((n) => {
        const d = daysLeft(n.deadline || n.effective_end);
        return d >= 0 && d <= 7;
      }).length;
      $("kpiOverdue").textContent = rows.filter((n) => n.status === "已逾期" || daysLeft(n.deadline || n.effective_end) < 0).length;

      const typeMap = new Map();
      for (const n of rows) {
        const type = n.notice_type || "其他";
        typeMap.set(type, (typeMap.get(type) || 0) + 1);
      }
      const typeRows = [...typeMap.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([label, value]) => ({ label, value: `${value} 条` }));
      $("typeCount").textContent = typeRows.length;
      renderTypePie([...typeMap.entries()].sort((a, b) => b[1] - a[1]));
      renderMetricRows("typeSummary", typeRows, "暂无通告类型数据。");

      const dayMap = new Map();
      for (const n of monthRows) {
        const raw = n.created_at || n.effective_start || n.deadline || "";
        const day = String(raw).slice(0, 10) || "未设置";
        dayMap.set(day, (dayMap.get(day) || 0) + 1);
      }
      const dayRows = [...dayMap.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([label, value]) => ({ label, value: `${value} 条` }));
      $("monthNoticeCount").textContent = monthRows.length;
      renderMetricRows("monthTimeline", dayRows, "本月暂无通告发布记录。");

      $("attentionCount").textContent = attention.length;
      renderAttention(attention);
    },
  };
}());
