# 🔥 小红书爆款笔记查询 & AI仿写工具

一个完整的网页应用，用于搜索小红书热门帖子、查看详情，并基于爆款笔记自动生成仿写内容。

## 功能

1. **🔍 搜索发现** - 输入关键词，查询点赞数最高的热门帖子
2. **📈 热门榜单** - 查看当前最热门的帖子排行
3. **✍️ AI仿写** - 基于热门笔记的风格/结构自动生成原创内容
4. **📋 帖子详情** - 查看标题、正文、配图、互动数据、话题标签

## 快速开始

### Node.js 版本（推荐，无需安装依赖）

```bash
cd xhs-tool
node server.js
```

浏览器打开: `http://localhost:5000`

### Python 版本（需要安装依赖）

```bash
cd xhs-tool
pip install -r requirements.txt
python app.py
```

浏览器打开: `http://localhost:5000`

## API配置（可选）

### 获取真实小红书数据

复制 `.env.example` 为 `.env`，配置以下服务之一：

| 数据来源 | 说明 |
|---------|------|
| **第三方API** | 如 SocialDataX、飞瓜数据等，设置 `XHS_API_KEY` |
| **小红书开放平台** | 企业级API，需申请权限 |
| **MCP工具** | 基于MCP协议的小红书爬取工具 |

### AI仿写增强

设置 `ANTHROPIC_API_KEY` 环境变量以使用 Claude API 进行智能仿写（否则使用模板引擎）。

## 项目结构

```
xhs-tool/
├── server.js          # Node.js 后端（推荐）
├── app.py             # Python Flask 后端
├── requirements.txt   # Python 依赖
├── .env.example       # 环境变量模板
├── templates/
│   └── index.html     # 前端页面
└── static/
    ├── style.css      # 样式表
    └── app.js         # 前端逻辑
```

## 技术栈

- **后端**: Node.js (原生 http 模块) / Python Flask
- **前端**: 原生 HTML/CSS/JS（无框架依赖）
- **AI**: Claude API (Anthropic) / 模板引擎回退

## 替代方案

如果真实API权限受限，可考虑的路径：

1. **模拟数据演示**（默认）: 内置6条不同领域的热门帖子数据
2. **浏览器插件**: 开发Chrome插件从网页端提取数据
3. **RSS订阅**: 部分第三方服务提供小红书RSS订阅
4. **手动导入**: 支持CSV/JSON格式导入帖子数据
