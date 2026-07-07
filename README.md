# 📔 心语日记 — 多智能体 AI 日记助手

> 基于多智能体协作的个性化 AI 日记应用，能够感知情绪、记忆重要瞬间、生成温暖日记。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![LLM](https://img.shields.io/badge/LLM-Agnes%20AI-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 项目亮点

- **4 个智能体协作**：情绪感知器、记忆管家、日记生成器、对话精灵
- **4 个工具函数**：情绪分析、记忆保存/检索/遗忘、日记生成
- **长期记忆**：ChromaDB 向量数据库 + BGE 中文嵌入模型（`BAAI/bge-small-zh-v1.5`）
- **短期记忆**：上下文窗口，保留最近 10 轮对话
- **SSE 流式响应**：实时显示每个智能体的处理进度
- **日记管理**：自动保存、历史浏览、关键词搜索、Markdown 导出
- **统计看板**：日记总数、记忆总数、情绪分布、平均强度
- **文学期刊美学 UI**：纸质信笺风格，朱砂印章 + 墨色排版，支持移动端

## 🏗️ 架构设计

![架构图](docs/architecture.svg)

```
用户输入 → 情绪感知器(分析情绪) → 记忆管家(检索+保存) → 日记生成器(写日记) → 对话精灵(整合回复) → 用户
                ↓                       ↓                       ↓
          情绪标签+强度         ChromaDB向量检索          融合情绪+记忆
```

### 智能体角色

| 智能体 | 职责 | 工具 | 记忆权限 |
|--------|------|------|----------|
| 🎭 情绪感知器 | 识别用户情绪状态 | `analyze_emotion` | 仅当前输入 |
| 🧠 记忆管家 | 管理长期记忆 | `save_memory` / `search_memory` / `forget_memory` | 读写向量库 |
| 📝 日记生成器 | 生成个性化日记 | `generate_diary` | 读短期+长期记忆 |
| ✨ 对话精灵 | 整合温暖回复 | — | 读短期记忆 |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- [Agnes AI API Key](https://agnes-ai.com/)（OpenAI 兼容协议）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/w020316/geren-riji.git
cd geren-riji

# 2. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 Agnes AI API Key
#   LLM_API_KEY=sk-xxxxxxxx
#   LLM_BASE_URL=https://apihub.agnes-ai.com/v1
#   LLM_MODEL=agnes-2.0-flash

# 4. 启动服务
python main.py
```

打开浏览器访问 **http://localhost:8000**

> 首次启动会自动下载 BGE 中文嵌入模型（约 100MB）到项目 `models/` 目录。

### Windows 一键启动

双击 `start.bat` 即可自动安装依赖并启动服务。

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 或手动构建
docker build -t xinyu-diary .
docker run -p 8000:8000 -e LLM_API_KEY=your_key xinyu-diary
```

## 📁 项目结构

```
geren-riji/
├── main.py              # FastAPI 后端服务入口
├── agents.py            # 4 个智能体 + 编排器
├── tools.py             # 工具函数（情绪分析、日记生成）
├── memory.py            # 长期记忆(ChromaDB) + 短期记忆
├── diary_store.py       # 日记持久化存储与导出（线程安全）
├── llm_client.py        # LLM 调用封装（@lru_cache 复用客户端）
├── config.py            # 配置管理（Agnes AI / OpenAI 兼容）
├── static/
│   └── index.html       # 前端界面（文学期刊美学）
├── index.html           # 项目落地页（GitHub Pages 部署用）
├── docs/
│   ├── architecture.svg # 架构图
│   └── 项目说明文档.html # 详细说明文档
├── tests/               # 单元测试 + 集成测试
│   ├── conftest.py
│   ├── test_diary_store.py
│   ├── test_memory.py
│   ├── test_agents.py
│   └── test_api.py
├── requirements.txt     # Python 依赖
├── requirements-dev.txt # 开发与测试依赖
├── pytest.ini           # pytest 配置
├── Dockerfile           # Docker 部署文件
├── docker-compose.yml   # Docker Compose 配置
├── .env.example         # 环境变量模板
└── .gitignore
```

## 🔧 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat/stream` | SSE 流式对话（推荐） |
| `POST` | `/api/chat` | 普通对话 |
| `GET` | `/api/diaries` | 获取日记列表 |
| `GET` | `/api/diaries/search?keyword=` | 按关键词搜索日记 |
| `GET` | `/api/diaries/{id}` | 获取日记详情 |
| `DELETE` | `/api/diaries/{id}` | 删除日记 |
| `GET` | `/api/diaries/{id}/export` | 导出单篇日记(Markdown) |
| `GET` | `/api/diaries/export/all` | 导出全部日记 |
| `GET` | `/api/memories` | 获取长期记忆列表 |
| `DELETE` | `/api/memories/{id}` | 删除记忆 |
| `POST` | `/api/clear_context` | 清空短期记忆 |
| `GET` | `/api/stats` | 统计看板（日记数/记忆数/情绪分布） |
| `GET` | `/api/health` | 健康检查 |

### SSE 事件协议

`/api/chat/stream` 返回 `text/event-stream`，事件类型：

| type | 说明 |
|------|------|
| `progress` | 智能体处理进度（`agent` + `status: working/done`） |
| `emotion` | 情绪分析结果 |
| `diary` | 生成的日记 |
| `complete` | 完整响应（含 `response`/`emotion`/`diary`/`diary_id`） |
| `error` | 错误信息 |

## ⚙️ 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_API_KEY` | — | Agnes AI API 密钥（必填） |
| `LLM_BASE_URL` | `https://apihub.agnes-ai.com/v1` | LLM API 地址（OpenAI 兼容） |
| `LLM_MODEL` | `agnes-2.0-flash` | 模型名称（可选 `agnes-1.5-flash`） |
| `LLM_TIMEOUT` | `60` | 请求超时（秒） |
| `LLM_MAX_TOKENS` | `2000` | 单次最大生成 token |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 嵌入模型 |
| `SHORT_MEMORY_MAX_TURNS` | `10` | 短期记忆轮数 |

> 向后兼容：仍支持旧变量 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`，但建议迁移至 `LLM_*`。

## 🧪 测试

### 运行测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行全部测试
pytest

# 带覆盖率
pytest --cov=. --cov-report=term-missing
```

### 测试结构

| 文件 | 覆盖范围 |
|------|---------|
| `tests/test_diary_store.py` | 日记存储 CRUD、搜索、导出、并发安全 |
| `tests/test_memory.py` | 短期记忆写入、截断、清空、时间戳 |
| `tests/test_agents.py` | 4 个智能体的编排逻辑（mock LLM） |
| `tests/test_api.py` | 全部 REST 端点的成功与错误分支（TestClient） |

测试通过 `conftest.py` 注入 ChromaDB / SentenceTransformer 轻量替身，**无需下载真实模型**即可运行。

## 🛡️ 安全与健壮性

- **CORS**：`allow_origins=["*"]` + `allow_credentials=False`，避免通配符与凭证并用的安全隐患
- **输入校验**：Pydantic Field 限制消息长度 1–2000 字符
- **线程安全**：`DiaryStore` 索引读写加 `threading.Lock`
- **错误处理**：SSE 流包裹 try/except，失败时 yield `error` 事件；404 使用 `HTTPException`
- **客户端复用**：`@lru_cache` 复用 OpenAI 客户端，避免重复建连
- **密钥隔离**：`.env` 通过 `.gitignore` 排除，不提交到仓库

## 📄 License

MIT License
