(function () {
  function applyExtractedFields(fields) {
    const draft = {
      status: "执行中",
      notice_type: fields.notice_type || "其他",
      owner: fields.owner || App.state.email,
      reminder_email: App.state.email,
    };
    const mapping = {
      doc_ref: "doc_ref",
      system_no: "system_no",
      title: "title",
      issuer: "issuer",
      owner: "owner",
      owner_role: "owner_role",
      department: "department",
      description: "description",
      purpose: "description",
      target_scope: "target_scope",
      impact_store: "impact_store",
      impact_region: "impact_region",
      impact_role: "impact_role",
      deadline: "deadline",
      effective_start: "effective_start",
      effective_end: "deadline",
    };
    for (const [source, target] of Object.entries(mapping)) {
      if (fields[source]) {
        draft[target] = String(fields[source]).slice(0, target === "deadline" || target === "effective_start" ? 10 : 9999);
      }
    }
    App.state.selectedId = null;
    App.state.currentNotice = null;
    App.state.importDraft = draft;
    App.state.historySearched = true;
    switchView("history");
    fillNoticeForm("history", draft);
    setNoticeEditMode(true);
    History.renderList();
    showToast("PDF 识别完成，已填入通告详情。请核对后保存入库。");
  }

  async function uploadPdfForExtract() {
    const file = $("pdfFile").files[0];
    if (!file) {
      showToast("请先选择 PDF 文件。");
      return;
    }
    $("extractPdfBtn").disabled = true;
    $("extractPdfBtn").textContent = "识别中...";
    showToast("正在识别 PDF，请稍候。首次 OCR 可能较慢。");
    try {
      const res = await fetch(`/notifications/extract-pdf?filename=${encodeURIComponent(file.name)}`, {
        method: "POST",
        headers: { "Content-Type": "application/pdf" },
        body: await file.arrayBuffer(),
      });
      if (!res.ok) {
        let detail = res.statusText;
        try { detail = (await res.json()).detail || detail; } catch (_) {}
        throw new Error(detail);
      }
      const data = await res.json();
      applyExtractedFields(data.fields || {});
    } catch (err) {
      showToast(`PDF 识别失败：${err.message}`);
    } finally {
      $("extractPdfBtn").disabled = false;
      $("extractPdfBtn").textContent = "识别 PDF 并填表";
    }
  }

  window.ImportNotice = { uploadPdfForExtract };
}());
