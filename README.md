# MCP 图片压缩服务

一个基于 MCP（Model Context Protocol）的图片压缩工具，可在 Cursor/Claude Desktop 中直接调用。

## 功能

- **compress_image**：压缩单张图片到目标大小（默认 10KB），保持宽高比，输出 JPEG/PNG（非 webp），去除 EXIF。
- **compress_batch**：批量压缩多张图片，单个失败不影响其他。
- **images://list**：列出允许目录下的可压缩图片。

## 安装

```bash
cd /Volumes/boxs/学习区/mcp/mcp-demo
pip install -r requirements.txt
```

## 测试

```bash
PYTHONPATH=. python -m tests.smoke
```

## 在 Cursor 中使用

### 方式一：项目级配置

在项目根目录创建或编辑 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "img-compress": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/Volumes/boxs/学习区/mcp/mcp-demo"
    }
  }
}
```

### 方式二：全局配置

编辑 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "img-compress": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/Volumes/boxs/学习区/mcp/mcp-demo"
    }
  }
}
```

配置后重启 Cursor，即可在对话中调用 `compress_image` / `compress_batch` 工具。

## 工具参数

### compress_image

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | ✅ | 图片路径（必须在允许目录内） |
| target_bytes | integer | ❌ | 目标大小（字节），默认 10000 |
| output_format | string | ❌ | 输出格式：jpeg/png，默认 jpeg |
| input_dir | string | ❌ | 输入目录，默认 ~/Pictures/in |
| output_dir | string | ❌ | 输出目录，默认 ~/Pictures/out |

### compress_batch

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| paths | string[] | ✅ | 图片路径列表 |
| target_bytes | integer | ❌ | 目标大小（字节），默认 10000 |
| output_format | string | ❌ | 输出格式：jpeg/png，默认 jpeg |
| input_dir | string | ❌ | 输入目录，默认 ~/Pictures/in |
| output_dir | string | ❌ | 输出目录，默认 ~/Pictures/out |

## 使用示例

在 Cursor 对话中：

> 帮我把 ~/Pictures/in/photo.jpg 压缩到 10KB 以下

Cursor 会调用 `compress_image` 工具并返回压缩结果。

## 目录结构

```
mcp-demo/
├── src/
│   ├── __init__.py
│   ├── compress.py      # 核心压缩逻辑
│   ├── mcp_server.py    # MCP 协议服务器
│   └── server.py        # FastAPI HTTP 服务（可选）
├── tests/
│   └── smoke.py         # 烟雾测试
├── specs/               # 需求/设计/任务文档
├── requirements.txt
├── pyproject.toml
└── README.md
```

## HTTP API（可选）

如需 HTTP 方式调用：

```bash
uvicorn src.server:app --reload --port 8000
```

然后访问 `http://127.0.0.1:8000/docs` 查看 Swagger 文档。

## 许可

MIT

