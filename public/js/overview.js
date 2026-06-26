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

  function dateKey(raw) {
    return raw ? String(raw).slice(0, 10) : "";
  }

  function localDateKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  function renderTypePie(entries) {
    const pie = $("typePie");
    const legend = $("typePieLegend");
    const colors = ["#5e6ad2", "#16a34a", "#b45309", "#dc2626", "#2563eb", "#7c3aed"];
    const total = entries.reduce((sum, [, value]) => sum + value, 0);
    if (!total) {
      pie.style.background = "#eef0fc";
      legend.innerHTML = `<div class="meta">${t("暫無類型分佈。")}</div>`;
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
      item.innerHTML = `<span class="pie-dot" style="background:${colors[index % colors.length]}"></span><span>${escapeHtml(noticeTypeLabel(label))} · ${value} ${t("條")} · ${percent}%</span>`;
      legend.appendChild(item);
    });
  }

  function renderAttention(rows) {
    const root = $("attentionList");
    root.innerHTML = rows.length ? "" : `<div class="meta">${t("暫無需要關注的通告。")}</div>`;
    for (const n of rows.slice(0, 6)) {
      const deadline = n.deadline || n.effective_end || "";
      const ack = noticeAckLabel(n);
      const statusText = statusLabel(n.status, deadline);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "notice-item";
      btn.innerHTML = `
        <div class="row">
          <div class="title">${escapeHtml(n.title || `(${t("無標題")})`)}</div>
          <span class="${statusBadgeClass(n.status, deadline)}">${escapeHtml(ack ? `${statusText} · ${ack}` : statusText)}</span>
        </div>
        <div class="meta">${escapeHtml(n.system_no || t("未編號"))} · ${t("截止")} ${escapeHtml(deadline || t("未設定"))}</div>
      `;
      btn.addEventListener("click", async () => {
        switchView("history");
        App.state.historySearched = true;
        await window.History.selectNotice(n.notification_id);
      });
      root.appendChild(btn);
    }
  }

  function calendarItems() {
    const items = [];
    for (const n of App.state.notices || []) {
      const deadline = dateKey(n.deadline || n.effective_end);
      if (!deadline) continue;
      const left = daysLeft(deadline);
      let kind = "running";
      let label = t("執行中");
      if (left < 0) {
        kind = "overdue";
        label = t("已逾期");
      } else if (left <= 7) {
        kind = "soon";
        label = t("即將截止");
      }
      const ack = noticeAckLabel(n);
      items.push({
        date: deadline,
        kind,
        label,
        title: n.title || `(${t("無標題")})`,
        meta: `${n.system_no || t("未編號")} · ${statusLabel(n.status, deadline)}${ack ? ` · ${ack}` : ""}`,
        open: () => {
          switchView("history");
          App.state.historySearched = true;
          window.History.selectNotice(n.notification_id);
        },
      });
    }
    for (const plan of App.state.plans || []) {
      const ddl = dateKey(plan.planned_publish_date);
      if (!ddl) continue;
      items.push({
        date: ddl,
        kind: "plan",
        label: statusLabel(plan.status),
        title: plan.activity_name || `(${t("未命名")})`,
        meta: `${t("預錄 DDL")} · ${plan.owner || t("未設定負責人")}`,
        open: () => {
          switchView("plans");
          window.Plans.selectPlan(plan.id);
        },
      });
    }
    return items;
  }

  function eventChip(item) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `calendar-event ${item.kind}`;
    chip.title = `${item.label} · ${item.title}`;
    chip.textContent = `${item.label} · ${item.title}`;
    chip.addEventListener("click", (event) => {
      event.stopPropagation();
      renderCalendarDetail(item.date, [item], true);
    });
    return chip;
  }

  function renderCalendarDetail(date, items, focused) {
    const root = $("calendarDayDetail");
    if (!items.length) {
      root.innerHTML = `<div class="meta">${escapeHtml(date)} ${t("暫無事項。")}</div>`;
      return;
    }
    root.innerHTML = "";
    const heading = document.createElement("div");
    heading.className = "calendar-detail-heading";
    heading.innerHTML = `<strong>${escapeHtml(date)}</strong><span class="meta">${focused ? t("已選擇事項") : `${t("共")} ${items.length} ${t("項")}`}</span>`;
    root.appendChild(heading);
    for (const item of items) {
      const card = document.createElement("div");
      card.className = "calendar-detail-card";
      card.innerHTML = `
        <div class="row">
          <div class="title">${escapeHtml(item.title)}</div>
          <span class="calendar-dot ${item.kind}">${escapeHtml(item.label)}</span>
        </div>
        <div class="meta">${escapeHtml(date)} · ${escapeHtml(item.meta)}</div>
        <div class="actions"><button type="button" class="primary">${t("查看詳情")}</button></div>
      `;
      card.querySelector("button").addEventListener("click", item.open);
      root.appendChild(card);
    }
  }

  function renderCalendar() {
    const root = $("overviewCalendar");
    const current = App.state.calendarDate || new Date();
    const now = new Date();
    const year = current.getFullYear();
    const month = current.getMonth();
    const todayKey = localDateKey(now);
    const monthText = App.state.language === "en" ? `${year}-${String(month + 1).padStart(2, "0")}` : `${year} 年 ${month + 1} 月`;
    $("calendarMonthBtn").textContent = monthText;
    $("calendarMonthPicker").value = `${year}-${String(month + 1).padStart(2, "0")}`;

    const grouped = new Map();
    for (const item of calendarItems()) {
      const key = item.date;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(item);
    }

    root.innerHTML = "";
    const table = document.createElement("table");
    table.className = "calendar-table";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    [t("星期一"), t("星期二"), t("星期三"), t("星期四"), t("星期五"), t("星期六"), t("星期日")].forEach((label) => {
      const th = document.createElement("th");
      th.textContent = label;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const first = new Date(year, month, 1);
    const startOffset = (first.getDay() + 6) % 7;
    const gridStart = new Date(year, month, 1 - startOffset);
    const tbody = document.createElement("tbody");
    for (let week = 0; week < 6; week += 1) {
      const row = document.createElement("tr");
      for (let weekday = 0; weekday < 7; weekday += 1) {
        const index = week * 7 + weekday;
        const cellDate = new Date(gridStart);
        cellDate.setDate(gridStart.getDate() + index);
        const key = localDateKey(cellDate);
        const items = grouped.get(key) || [];
        const cell = document.createElement("td");
        cell.className = "calendar-cell"
          + (key === todayKey ? " is-today" : "")
          + (cellDate.getMonth() !== month ? " is-outside-month" : "")
          + (items.length ? " has-events" : "");

        const cellInner = document.createElement("div");
        cellInner.className = "calendar-cell-inner";
        const dateEl = document.createElement("div");
        dateEl.className = "calendar-date";
        dateEl.textContent = String(cellDate.getDate());
        cellInner.appendChild(dateEl);
        for (const item of items.slice(0, 3)) {
          cellInner.appendChild(eventChip(item));
        }
        if (items.length > 3) {
          const more = document.createElement("span");
          more.className = "meta";
          more.textContent = `${t("另有")} ${items.length - 3} ${t("項")}`;
          cellInner.appendChild(more);
        }
        cellInner.addEventListener("click", () => renderCalendarDetail(key, items));
        cell.appendChild(cellInner);
        row.appendChild(cell);
      }
      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    root.appendChild(table);
    renderCalendarDetail(todayKey, grouped.get(todayKey) || []);
  }

  function changeMonth(offset) {
    const current = App.state.calendarDate || new Date();
    App.state.calendarDate = new Date(current.getFullYear(), current.getMonth() + offset, 1);
    renderCalendar();
  }

  function goToday() {
    App.state.calendarDate = new Date();
    renderCalendar();
  }

  function openMonthPicker() {
    const picker = $("calendarMonthPicker");
    if (picker.showPicker) {
      picker.showPicker();
      return;
    }
    picker.focus();
    picker.click();
  }

  function selectMonth(value) {
    if (!value) return;
    const [year, month] = value.split("-").map(Number);
    if (!year || !month) return;
    App.state.calendarDate = new Date(year, month - 1, 1);
    renderCalendar();
  }

  window.Overview = {
    render() {
      renderCalendar();

      const rows = App.state.notices || [];
      const monthRows = rows.filter((n) => isThisMonth(n.created_at || n.effective_start || n.deadline));
      const attention = rows.filter((n) => {
        const d = daysLeft(n.deadline || n.effective_end);
        return d < 0 || d <= 7;
      });

      $("kpiMonthTotal").textContent = monthRows.length;
      $("kpiRunning").textContent = rows.filter((n) => n.status === "执行中").length;
      $("kpiSoon").textContent = rows.filter((n) => {
        const d = daysLeft(n.deadline || n.effective_end);
        return d >= 0 && d <= 7;
      }).length;
      $("kpiCompleted").textContent = rows.filter((n) => n.status === "已逾期").length;

      const typeMap = new Map();
      for (const n of rows) {
        const type = n.notice_type || "其他";
        typeMap.set(type, (typeMap.get(type) || 0) + 1);
      }
      const typeRows = [...typeMap.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([label, value]) => ({ label: noticeTypeLabel(label), value: `${value} ${t("條")}` }));
      $("typeCount").textContent = typeRows.length;
      renderTypePie([...typeMap.entries()].sort((a, b) => b[1] - a[1]));
      renderMetricRows("typeSummary", typeRows, t("暫無通告類型數據。"));

      const dayMap = new Map();
      for (const n of monthRows) {
        const raw = n.created_at || n.effective_start || n.deadline || "";
        const day = String(raw).slice(0, 10) || t("未設定");
        dayMap.set(day, (dayMap.get(day) || 0) + 1);
      }
      const dayRows = [...dayMap.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([label, value]) => ({ label, value: `${value} ${t("條")}` }));
      $("monthNoticeCount").textContent = monthRows.length;
      renderMetricRows("monthTimeline", dayRows, t("本月暫無通告發佈記錄。"));

      $("attentionCount").textContent = attention.length;
      renderAttention(attention);
      applyI18n($("view-overview"));
    },
    prevMonth() {
      changeMonth(-1);
    },
    nextMonth() {
      changeMonth(1);
    },
    goToday,
    openMonthPicker,
    selectMonth,
  };
}());
