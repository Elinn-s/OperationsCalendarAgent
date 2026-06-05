(function () {
  function applyExtractedFields(fields) {
    const draft = {
      status: "草稿",
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
    showToast("PDF 識別完成，已填入通告詳情。請核對後保存入庫。");
  }

  async function uploadPdfForExtract() {
    const file = $("pdfFile").files[0];
    if (!file) {
      showToast("請先選擇 PDF 文件。");
      return;
    }
    $("extractPdfBtn").disabled = true;
    $("extractPdfBtn").textContent = "識別中...";
    showToast("正在識別 PDF，請稍候。首次 OCR 可能較慢。");
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
      showToast(`PDF 識別失敗：${err.message}。如果是掃描版 PDF，請使用本地 OCR Plan B 啟動後再導入。`);
    } finally {
      $("extractPdfBtn").disabled = false;
      $("extractPdfBtn").textContent = "識別 PDF 並填表";
    }
  }

  window.ImportNotice = { uploadPdfForExtract };
}());
