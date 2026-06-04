# Local OCR Plan B

这个文件夹用于本地 OCR 应急方案，和普通本地启动 `start.bat` 区分。

## 使用方式

双击：

```text
local_ocr_plan_b/start_local_ocr.bat
```

然后访问：

```text
http://localhost:8000/app
```

## 和普通模式的区别

- 普通模式：`src/storenotificationcircula/services/pdf_parser.py` 默认只读取 PDF 文本层，适合 Render 低内存环境。
- Plan B 本地 OCR：启动时设置 `ENABLE_LOCAL_OCR=true`，扫描版 PDF 会调用 `src/storenotificationcircula/services/local_ocr/pdf_parser.py` 进行逐页 OCR。

## 注意

本地 OCR 会加载 `rapidocr-onnxruntime`、`onnxruntime`、`opencv`，比线上模式更耗内存，但适合在本机演示扫描版 PDF。
