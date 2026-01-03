# 技术方案（Python MCP 图片压缩）

## 架构与流程

- 组件：MCP Server（Python） + 压缩处理器（Pillow）。
- 流程：请求 -> 参数校验（路径 allowlist、格式、目标大小） -> 单/批处理 -> 质量递减与按比例缩放 -> 写出 JPEG（去 EXIF） -> 汇总结果返回。
- 并发：单进程串行即可；预留异步接口方便后续扩展。

## 技术栈与依赖

- Python ≥ 3.11
- Pillow：图像读写/压缩/缩放
- （可选）pydantic：参数校验，或使用 dataclasses + 手动校验
- 日志：标准库 logging

## 参数与约束

- 目标大小：默认 10_000 字节，可自定义。
- 支持格式：输入 JPEG/PNG；拒绝 webp/gif 及其他未知格式。
- 输出：JPEG（默认），可选 PNG（但仍不生成 webp）。统一去除 EXIF/元数据。
- 路径：输入/输出需在 allowlist（默认建议 `~/Pictures/in`, `~/Pictures/out`），拒绝目录穿越。

## 压缩算法策略（最佳努力）

1) 读取图片，标准化为 RGB。  
2) 质量递减：从 85 递减到 30（步长 5），每次尝试保存到内存检查大小。  
3) 若仍超标：按比例缩放（保持宽高比），每次将长边乘以 0.9，最低不低于 min_edge=64，期间继续质量递减组合尝试。  
4) 若达不到目标：返回 status=partial，附实际大小与原因。

## 接口设计（示例）

- Tool: `compress_image`  
  - 输入：`path`（str），`target_bytes`（int=10000，可选），`format`（"jpeg"|"png"，默认 jpeg）  
  - 输出：`status` ("ok"|"partial"|"error"), `output_path`, `input_size`, `output_size`, `ratio`, `message`
- Tool: `compress_batch`  
  - 输入：`paths`（list[str]，同目录）、其他参数同上  
  - 输出：列表结果；单个失败不影响其他。
- Resource：可选 `list_images` 列出 allowlist 内符合格式的文件。

## 安全与健壮性

- 路径校验：规范化后必须位于 allowlist；拒绝绝对/相对越权。
- 格式校验：仅 JPEG/PNG；不处理 webp/gif。
- 失败处理：不可写、格式不支持、尺寸达不到目标 -> 返回错误或 partial。
- 超时：单次压缩可设置超时（后续扩展）；当前同步短任务无需特殊处理。

## 测试策略

- 单测：质量递减达标；超小 target 导致 partial；不支持格式报错；路径越权报错；批量部分失败不中断。
- 集成：启动 MCP server，使用示例 client 调用 compress_image/ compress_batch，全链路验证返回字段与文件大小。

## 目录约定

- 源码：`src/`（如 `src/server.py`, `src/compress.py`）
- 允许目录：`~/Pictures/in`, `~/Pictures/out`（可在配置中覆盖）
- Specs：`specs/mcp-img-compress/`
