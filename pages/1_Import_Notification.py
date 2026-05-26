import json
import tempfile
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.db import generate_system_no, get_conn, init_db, log_action
from app.services.dify_client import extract_fields
from app.services.pdf_parser import extract_text
from app import storage
from app.ui import apply_backend_style, page_header, section_title, top_nav

init_db()
st.set_page_config(page_title="导入通告", page_icon="📋", layout="wide")
apply_backend_style()
top_nav()
page_header(
    "导入通告",
    "搜索历史记录，上传 PDF 自动识别，并在同一详情面板中完成核对、修改和删除。",
    "PDF OCR / 历史检索",
)

WARNING_WINDOW_DAYS = 5
STATUS_OPTIONS = ["执行中", "已截止"]
NOTICE_TYPE_OPTIONS = ["安全合规", "日常营运", "活动通知", "人事行政", "其他"]
HISTORY_PAGE_SIZE = 20


def _parse_date(raw: str | None, fallback: date) -> date:
    if not raw:
        return fallback
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y.%m.%d"):
        try:
            return datetime.strptime(str(raw)[:10], fmt).date()
        except ValueError:
            continue
    return fallback


def _delete_notifications(notification_ids: list[str], delete_files: bool, records: list) -> None:
    if delete_files:
        for record in records:
            if record["notification_id"] in notification_ids and record["file_path"]:
                try:
                    storage.delete_file(record["file_path"])
                except Exception:
                    pass

    placeholders = ",".join("?" for _ in notification_ids)
    with get_conn() as conn:
        conn.execute(
            f"DELETE FROM audit_log WHERE notification_id IN ({placeholders})",
            notification_ids,
        )
        conn.execute(
            f"DELETE FROM notifications WHERE notification_id IN ({placeholders})",
            notification_ids,
        )


def _status_index(status: str | None) -> int:
    return STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0


def _infer_notice_type(*values: str | None) -> str:
    text = " ".join(value or "" for value in values)
    rules = [
        ("安全合规", ["安全", "消防", "防火", "卫生", "检查", "合规", "演练", "风险"]),
        ("活动通知", ["活动", "促销", "节日", "会员", "营销", "陈列"]),
        ("人事行政", ["员工", "培训", "排班", "考勤", "人事", "行政", "入职"]),
        ("日常营运", ["盘点", "营运", "门店", "库存", "物料", "配送", "营业"]),
    ]
    for notice_type, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return notice_type
    return "其他"


def _select_history_record(record) -> None:
    title = record["title"] or record["doc_ref"] or "无标题"
    st.session_state["selected_history_id"] = record["notification_id"]
    st.session_state["history_detail_notice"] = f"已打开「{title}」的详情。"
    st.session_state.pop("import_candidate", None)
    st.rerun()


section_title("历史搜索")
with st.form("search"):
    s1, s2, s3, s4 = st.columns([2, 2, 1.4, 0.8])
    q_doc = s1.text_input("标题 / 档案编号", label_visibility="collapsed", placeholder="标题 / 档案编号")
    q_dept = s2.text_input("部门 / 负责人", label_visibility="collapsed", placeholder="部门 / 负责人")
    q_status = s3.selectbox("状态", ["全部", *STATUS_OPTIONS], label_visibility="collapsed")
    searched = s4.form_submit_button("🔍 搜索", type="primary", use_container_width=True)

    with st.expander("更多筛选"):
        s5, s6 = st.columns(2)
        date_from = s5.date_input("执行截止 从", value=None, min_value=date(2000, 1, 1))
        date_to = s6.date_input("执行截止 至", value=None, min_value=date(2000, 1, 1))

if searched:
    st.session_state["history_searched"] = True
    st.session_state["history_page"] = 1
    st.session_state.pop("selected_history_id", None)

query_history_id = None if searched else st.query_params.get("history_id")
if query_history_id and query_history_id != st.session_state.get("selected_history_id"):
    st.session_state["selected_history_id"] = query_history_id
    st.session_state["history_detail_notice"] = "已打开历史通告详情。"
    st.session_state.pop("import_candidate", None)

left_col, right_col = st.columns(2)

with right_col:
    title_col, batch_col = st.columns([3, 1])
    with title_col:
        section_title("历史记录")
    rows = []
    if st.session_state.get("history_searched"):
        sql = "SELECT * FROM notifications WHERE 1=1"
        params: list = []

        if q_doc:
            sql += " AND (doc_ref LIKE ? OR title LIKE ?)"
            params += [f"%{q_doc}%", f"%{q_doc}%"]
        if q_dept:
            sql += " AND (department LIKE ? OR drafter LIKE ?)"
            params += [f"%{q_dept}%", f"%{q_dept}%"]
        if q_status != "全部":
            sql += " AND status = ?"
            params.append(q_status)
        if isinstance(date_from, date):
            sql += " AND effective_end >= ?"
            params.append(date_from.isoformat())
        if isinstance(date_to, date):
            sql += " AND effective_end <= ?"
            params.append(date_to.isoformat())

        sql += " ORDER BY created_at DESC"
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        if not rows:
            st.info("没有找到符合条件的通告。")
        else:
            total_rows = len(rows)
            total_pages = max(1, (total_rows + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
            current_page = min(max(1, st.session_state.get("history_page", 1)), total_pages)
            st.session_state["history_page"] = current_page
            start = (current_page - 1) * HISTORY_PAGE_SIZE
            end = start + HISTORY_PAGE_SIZE
            paged_rows = rows[start:end]

            if total_rows > HISTORY_PAGE_SIZE:
                page_info, prev_col, next_col = st.columns([3, 1, 1])
                page_info.caption(f"共 {total_rows} 条，当前第 {current_page} / {total_pages} 页")
                if prev_col.button("上一页", disabled=current_page <= 1, use_container_width=True):
                    st.session_state["history_page"] = current_page - 1
                    st.rerun()
                if next_col.button("下一页", disabled=current_page >= total_pages, use_container_width=True):
                    st.session_state["history_page"] = current_page + 1
                    st.rerun()
            else:
                st.caption(f"共 {total_rows} 条，点击表格行查看详情。")

            df = pd.DataFrame([dict(r) for r in paged_rows])
            display_cols = ["system_no", "doc_ref", "title", "notice_type", "department", "status", "effective_end", "created_at"]
            for col in display_cols:
                if col not in df.columns:
                    df[col] = ""

            table_df = df[display_cols].rename(
                columns={
                    "system_no": "系统编号",
                    "doc_ref": "档案编号",
                    "title": "标题",
                    "notice_type": "类型",
                    "department": "部门",
                    "status": "状态",
                    "effective_end": "执行截止",
                    "created_at": "录入时间",
                }
            )

            batch_mode = st.session_state.get("history_batch_mode", False)
            if batch_mode:
                table_df.insert(0, "选择", st.session_state.get("history_select_all", False))
                edited_table = st.data_editor(
                    table_df,
                    column_config={"选择": st.column_config.CheckboxColumn("选择")},
                    disabled=[col for col in table_df.columns if col != "选择"],
                    use_container_width=True,
                    hide_index=True,
                    key=f"history_results_table_{st.session_state.get('history_table_version', 0)}",
                )
                selected_ids = [
                    paged_rows[i]["notification_id"]
                    for i, selected in enumerate(edited_table["选择"].tolist())
                    if selected
                ]
            else:
                st.caption("点击任意一行可在下方查看详情。")
                header_cols = st.columns([1.2, 1, 2.0, 0.9, 0.9, 0.9])
                for col, label in zip(header_cols, ["系统编号", "档案编号", "标题", "类型", "状态", "执行截止"]):
                    col.markdown(f"**{label}**")
                st.divider()

                selected_history_id = st.session_state.get("selected_history_id")
                for index, record in enumerate(paged_rows):
                    selected_prefix = "● " if record["notification_id"] == selected_history_id else ""
                    row_label = (
                        f"{record['system_no'] or '未编号'}    "
                        f"{record['doc_ref'] or '无档案编号'}    "
                        f"{selected_prefix}{record['title'] or '(无标题)'}    "
                        f"{record['notice_type'] or '其他'}    "
                        f"{record['status'] or '未填'}    "
                        f"{record['effective_end'] or '无截止'}"
                    )
                    if st.button(
                        row_label,
                        key=f"history_row_{record['notification_id']}_{current_page}_{index}",
                        use_container_width=True,
                    ):
                        _select_history_record(record)
                selected_ids = []

            with batch_col.popover("批量处理"):
                if not batch_mode:
                    if st.button("进入批量处理"):
                        st.session_state["history_batch_mode"] = True
                        st.rerun()
                    st.caption("进入后可勾选记录、全选和删除。")
                else:
                    st.caption(f"已选择 {len(selected_ids)} 条记录")
                    select_col, clear_col = st.columns(2)
                    if select_col.button("一键全选"):
                        st.session_state["history_select_all"] = True
                        st.session_state["history_table_version"] = st.session_state.get("history_table_version", 0) + 1
                        st.rerun()
                    if clear_col.button("取消全选"):
                        st.session_state["history_select_all"] = False
                        st.session_state["history_table_version"] = st.session_state.get("history_table_version", 0) + 1
                        st.rerun()
                    if st.button("退出批量处理"):
                        st.session_state["history_batch_mode"] = False
                        st.session_state["history_select_all"] = False
                        st.session_state.pop("pending_delete_history_ids", None)
                        st.session_state.pop("pending_delete_history_files", None)
                        st.session_state["history_table_version"] = st.session_state.get("history_table_version", 0) + 1
                        st.rerun()

                    delete_files_batch = st.checkbox("同时删除原始 PDF 文件")
                    if st.button("删除选中记录"):
                        if not selected_ids:
                            st.error("请先在表格勾选记录。")
                        else:
                            st.session_state["pending_delete_history_ids"] = selected_ids
                            st.session_state["pending_delete_history_files"] = delete_files_batch
                            st.rerun()

                    pending_delete_ids = st.session_state.get("pending_delete_history_ids", [])
                    if pending_delete_ids:
                        st.warning(f"确认删除选中的 {len(pending_delete_ids)} 条记录吗？")
                        confirm_col, cancel_col = st.columns(2)
                        if confirm_col.button("确认删除"):
                            delete_files = st.session_state.get("pending_delete_history_files", False)
                            _delete_notifications(pending_delete_ids, delete_files, rows)
                            st.session_state.pop("pending_delete_history_ids", None)
                            st.session_state.pop("pending_delete_history_files", None)
                            st.success(f"已删除 {len(pending_delete_ids)} 条通告")
                            st.rerun()
                        if cancel_col.button("取消"):
                            st.session_state.pop("pending_delete_history_ids", None)
                            st.session_state.pop("pending_delete_history_files", None)
                            st.rerun()

    else:
        st.info("请先在顶部搜索。")

with left_col:
    section_title("导入通告")
    uploaded = st.file_uploader("上传通告 PDF", type=["pdf"])

    if uploaded:
        file_signature = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("import_file_signature") != file_signature:
            raw_bytes = uploaded.getvalue()

            with st.status("正在解析 PDF…", expanded=True) as status:
                st.write("🔍 OCR 识别中（首次运行会下载模型，约 1 分钟）…")
                try:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(raw_bytes)
                        tmp_path = Path(tmp.name)
                    text = extract_text(tmp_path)
                except Exception as e:
                    st.error(f"OCR 失败：{e}")
                    st.stop()
                finally:
                    tmp_path.unlink(missing_ok=True)
                st.write(f"✅ OCR 完成，识别 {len(text):,} 字符")

                st.write("🤖 调用 AI 提取字段…")
                try:
                    fields = extract_fields(text)
                except Exception as e:
                    st.error(f"Dify API 调用失败：{e}")
                    st.stop()
                st.write("✅ AI 提取完成")
                status.update(label="解析完成", state="complete")
            st.session_state["import_file_signature"] = file_signature
            st.session_state["import_candidate"] = {
                "uploaded_name": uploaded.name,
                "raw_bytes": raw_bytes,
                "fields": fields,
            }
            st.session_state.pop("selected_history_id", None)
            st.rerun()

    if st.session_state.get("import_candidate"):
        st.success("已识别 PDF，请在下方详情区核对、保存或取消。")
    else:
        st.info("上传 PDF 后会自动识别关键字段，识别结果会在下方详情区显示。")

st.divider()
st.markdown('<div id="history-detail-anchor"></div>', unsafe_allow_html=True)
section_title("通告详情")
history_notice = st.session_state.pop("history_detail_notice", None)
if history_notice:
    st.success(history_notice)
    components.html(
        """
        <script>
        const anchor = window.parent.document.getElementById("history-detail-anchor");
        if (anchor) {
            anchor.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        </script>
        """,
        height=0,
    )
candidate = st.session_state.get("import_candidate")
selected_history_id = st.session_state.get("selected_history_id")

if candidate:
    fields = candidate["fields"]
    effective_start_default = _parse_date(fields["effective_start"], date.today())
    effective_end_default = _parse_date(fields["effective_end"], date.today() + timedelta(days=30))
    generated_system_no = st.session_state.setdefault("import_system_no", generate_system_no())
    inferred_notice_type = _infer_notice_type(fields.get("title"), fields.get("purpose"), fields.get("target_scope"))

    with st.expander("查看 AI 原始返回", expanded=False):
        st.json(fields.get("_raw", {}))

    with st.form("confirm_import"):
        col1, col2 = st.columns(2)
        with col1:
            system_no = st.text_input("系统编号", value=generated_system_no, disabled=True)
            doc_ref = st.text_input("档案编号（原始文件编号，可为空）", value=fields["doc_ref"])
            department = st.text_input("发文部门", value=fields["department"])
            title = st.text_input("通告标题", value=fields["title"])
        with col2:
            drafter = st.text_input("拟稿人", value=fields["drafter"])
            reviewer = st.text_input("复核人", value=fields["reviewer"])
            approver = st.text_input("审核人", value=fields["approver"])

        purpose = st.text_area("通告目的摘要", value=fields["purpose"], height=80)
        target_scope = st.text_input("适用范围", value=fields["target_scope"])

        col3, col4 = st.columns(2)
        effective_start = col3.date_input("执行开始时间", value=effective_start_default)
        no_effective_end = col4.checkbox("无执行截止日期")
        effective_end = None
        if not no_effective_end:
            effective_end = col4.date_input("执行截止时间", value=effective_end_default)

        type_col, status_col = st.columns(2)
        notice_type = type_col.selectbox(
            "通告类型",
            NOTICE_TYPE_OPTIONS,
            index=NOTICE_TYPE_OPTIONS.index(inferred_notice_type),
        )
        status_opt = status_col.selectbox("状态", STATUS_OPTIONS)
        tags_raw = st.text_input("标签（逗号分隔）", placeholder="春节, 物料, 包装")

        save_col, cancel_col = st.columns(2)
        submitted = save_col.form_submit_button("💾 保存通告", type="primary")
        cancelled = cancel_col.form_submit_button("取消本次识别")

    if cancelled:
        st.session_state.pop("import_candidate", None)
        st.session_state.pop("import_file_signature", None)
        st.session_state.pop("import_system_no", None)
        st.info("已取消本次识别，未保存通告。")
        st.rerun()

    if submitted:
        nid = str(uuid.uuid4())
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        now = datetime.now().isoformat()
        storage_key = f"{nid}_{candidate['uploaded_name']}"
        try:
            storage.upload_file(storage_key, candidate["raw_bytes"])
        except Exception as e:
            st.error(f"文件上传到云存储失败：{e}")
            st.stop()

        with get_conn() as conn:
            conn.execute(
                """INSERT INTO notifications
                   (notification_id, doc_ref, system_no, notice_type, department, drafter, reviewer, approver,
                    title, purpose, target_scope, effective_start, effective_end,
                    status, tags, file_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    nid, doc_ref, system_no, notice_type, department, drafter, reviewer, approver,
                    title, purpose, target_scope,
                    effective_start.isoformat(),
                    effective_end.isoformat() if effective_end else None,
                    status_opt, json.dumps(tags, ensure_ascii=False), storage_key,
                    now, now,
                ),
            )
        log_action(nid, "上传并确认", f"档案编号: {doc_ref}")
        st.session_state.pop("import_candidate", None)
        st.session_state.pop("import_file_signature", None)
        st.session_state.pop("import_system_no", None)

        warnings = []
        if effective_end:
            exec_left = (effective_end - date.today()).days
            if exec_left < 0:
                warnings.append(f"执行截止时间已过期 **{-exec_left}** 天")
            elif exec_left <= WARNING_WINDOW_DAYS:
                warnings.append(f"执行截止时间仅剩 **{exec_left}** 天")
        if warnings:
            st.error("⚠️ 警告：" + "；".join(warnings) + "，请尽快处理。")
        st.success(f"✅ 已保存，系统编号：`{system_no}`")
        st.rerun()

elif selected_history_id:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notifications WHERE notification_id = ?", (selected_history_id,)).fetchone()
    if not row:
        st.info("所选通告不存在，可能已被删除。")
        st.session_state.pop("selected_history_id", None)
        st.stop()

    r = row
    c1, c2 = st.columns(2)
    c1.markdown(f"**系统编号** {r['system_no'] or '—'}")
    c1.markdown(f"**档案编号** {r['doc_ref'] or '—'}")
    c1.markdown(f"**通告类型** {r['notice_type'] or '其他'}")
    c1.markdown(f"**发文部门** {r['department'] or '—'}")
    c1.markdown(f"**拟稿人** {r['drafter'] or '—'}")
    c1.markdown(f"**复核人** {r['reviewer'] or '—'}")
    c1.markdown(f"**审核人** {r['approver'] or '—'}")
    c2.markdown(f"**标题** {r['title'] or '—'}")
    c2.markdown(f"**状态** {r['status'] or '—'}")
    c2.markdown(f"**执行开始** {r['effective_start'] or '—'}")
    c2.markdown(f"**执行截止** {r['effective_end'] or '—'}")
    c2.markdown(f"**适用范围** {r['target_scope'] or '—'}")

    if r["purpose"]:
        st.markdown(f"**目的摘要** {r['purpose']}")

    tags = json.loads(r["tags"] or "[]")
    if tags:
        st.write("标签：" + "　".join(f"`{t}`" for t in tags))

    storage_key = r["file_path"] if r["file_path"] else None
    if storage_key:
        try:
            pdf_bytes = storage.download_file(storage_key)
            st.download_button(
                "⬇ 下载原始 PDF",
                data=pdf_bytes,
                file_name=storage.original_filename(storage_key),
                mime="application/pdf",
            )
        except Exception:
            st.caption("原始 PDF 文件不可用")

    with st.expander("修改并保存"):
        effective_start_default = _parse_date(r["effective_start"], date.today())
        effective_end_default = _parse_date(r["effective_end"], date.today() + timedelta(days=30))
        no_effective_end_default = not r["effective_end"]

        with st.form(f"edit_{r['notification_id']}"):
            e1, e2 = st.columns(2)
            new_system_no = e1.text_input("系统编号", value=r["system_no"] or "", disabled=True)
            new_doc_ref = e2.text_input("档案编号（原始文件编号，可为空）", value=r["doc_ref"] or "")
            new_department = e1.text_input("发文部门", value=r["department"] or "")
            new_title = e2.text_input("通告标题", value=r["title"] or "")
            new_drafter = e1.text_input("拟稿人", value=r["drafter"] or "")
            new_reviewer = e2.text_input("复核人", value=r["reviewer"] or "")
            new_approver = e1.text_input("审核人", value=r["approver"] or "")
            new_target_scope = e2.text_input("适用范围", value=r["target_scope"] or "")
            new_purpose = st.text_area("通告目的摘要", value=r["purpose"] or "", height=100)

            d1, d2 = st.columns(2)
            new_effective_start = d1.date_input("执行开始时间", value=effective_start_default)
            no_effective_end = d2.checkbox("无执行截止日期", value=no_effective_end_default)
            new_effective_end = None
            if not no_effective_end:
                new_effective_end = d2.date_input("执行截止时间", value=effective_end_default)

            s1, s2 = st.columns(2)
            new_status = s1.selectbox("状态", STATUS_OPTIONS, index=_status_index(r["status"]))
            current_notice_type = r["notice_type"] if r["notice_type"] in NOTICE_TYPE_OPTIONS else "其他"
            new_notice_type = s2.selectbox(
                "通告类型",
                NOTICE_TYPE_OPTIONS,
                index=NOTICE_TYPE_OPTIONS.index(current_notice_type),
            )
            new_tags_raw = st.text_input("标签（逗号分隔）", value=", ".join(tags))

            saved = st.form_submit_button("保存修改", type="primary")

        if saved:
            if new_status == "执行中" and new_effective_end and new_effective_end < date.today():
                st.error("执行截止时间已早于今天，不能保存为「执行中」。请把执行截止改到今天或以后，或勾选「无执行截止日期」。")
            else:
                now = datetime.now().isoformat()
                new_tags = [tag.strip() for tag in new_tags_raw.split(",") if tag.strip()]
                with get_conn() as conn:
                    conn.execute(
                        """UPDATE notifications
                           SET doc_ref = ?, system_no = ?, department = ?, notice_type = ?,
                               drafter = ?, reviewer = ?, approver = ?, title = ?, purpose = ?,
                               target_scope = ?, effective_start = ?, effective_end = ?,
                               status = ?, tags = ?, updated_at = ?
                           WHERE notification_id = ?""",
                        (
                            new_doc_ref.strip(), new_system_no.strip(), new_department.strip(), new_notice_type,
                            new_drafter.strip(), new_reviewer.strip(), new_approver.strip(),
                            new_title.strip(), new_purpose.strip(), new_target_scope.strip(),
                            new_effective_start.isoformat(),
                            new_effective_end.isoformat() if new_effective_end else None,
                            new_status, json.dumps(new_tags, ensure_ascii=False), now,
                            r["notification_id"],
                        ),
                    )
                log_action(r["notification_id"], "修改通告", "更新历史记录字段")
                st.success("已保存修改")
                st.rerun()

    with st.expander("删除通告"):
        st.warning("删除后会移除此通告记录和操作日志。原始 PDF 默认保留，可勾选一并删除。")
        with st.form(f"delete_{r['notification_id']}"):
            delete_file = st.checkbox("同时删除原始 PDF 文件")
            confirm_delete = st.checkbox("我确认要删除这条通告")
            deleted = st.form_submit_button("删除通告")

        if deleted:
            if not confirm_delete:
                st.error("请先勾选确认删除。")
            else:
                _delete_notifications([r["notification_id"]], delete_file, [dict(r)])
                st.session_state.pop("selected_history_id", None)
                st.success("通告已删除")
                st.rerun()
else:
    st.info("请选择一条历史记录，或上传 PDF 完成识别后查看详情。")
