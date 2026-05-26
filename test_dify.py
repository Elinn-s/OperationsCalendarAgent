"""诊断：用小段 OCR 文字直接调 Dify，看能否提取字段"""
import json, requests, os
from dotenv import load_dotenv
load_dotenv()

API_KEY  = os.getenv("DIFY_API_KEY")
BASE_URL = os.getenv("DIFY_BASE_URL").rstrip("/")

SHORT_TEXT = """CHOWTAIFOOK
日常通告
总务部
有关：2026年春节期间物料配货安排的通告
档案编号
H_GO26_001
拟稿杨琪
复核卿吉祥、黄小英
审核袁捷
单号PB-
TGFB202601160005
三、执行时间：2026年1月1日至2026年2月28日
二、适用范围：各营运管理中心、办事处、办公室、全国周大福珠宝分店
"""

resp = requests.post(
    f"{BASE_URL}/workflows/run",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={"inputs": {"pdf_text": SHORT_TEXT}, "response_mode": "blocking", "user": "demo-user"},
    timeout=90,
)
print("HTTP:", resp.status_code)
try:
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
except Exception:
    print(resp.text)
