"""
小红书热门帖子查询与仿写工具 - Flask 后端
"""

import os
import json
import re
import urllib.request
import ssl
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, static_folder="static", template_folder="templates")

# ============================================================
# 读取 .env 配置
# ============================================================
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key, value = key.strip(), value.strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                if key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass

load_env()

SOCIALDATAX_API_KEY = os.environ.get("SOCIALDATAX_API_KEY", "")
SOCIALDATAX_MCP_URL = os.environ.get("SOCIALDATAX_MCP_URL", "https://mcp.52choujiang.com/xhs/mcp")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_API_BASE = os.environ.get("AI_API_BASE", "")
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "true").lower() != "false"

# ============================================================
# 模拟数据
# ============================================================
MOCK_POSTS = [
    {
        "note_id": "64a1b2c3d4e5f6g7h8i9j0k1",
        "title": "打工人必看！5个让办公效率翻倍的隐藏技巧",
        "content": "用了3年才发现这些功能，之前都在浪费时间！\n\n1⃣ Windows虚拟桌面\n按Win+Tab可以创建多个桌面，工作一个、摸鱼一个，再也不怕老板突然出现 \U0001f440\n\n2⃣ 剪贴板历史\nWin+V 打开剪贴板历史，之前复制的内容都能找回来！\n\n3⃣ 分屏快捷键\nWin+方向键快速分屏，写文档查资料同时进行\n\n4⃣ 截图工具\nWin+Shift+S 任意区域截图，不需要登录微信\n\n5⃣ 搜索神器 Everything\n秒搜全盘文件，比Windows自带搜索快100倍\n\n收藏起来慢慢学，学会了记得回来感谢我～\n\n#办公技巧 #效率提升 #职场必备 #打工人",
        "likes": 23500, "collects": 18200, "comments": 3256, "shares": 8900,
        "images": ["https://picsum.photos/seed/xhs1/800/800", "https://picsum.photos/seed/xhs2/800/800", "https://picsum.photos/seed/xhs3/800/800"],
        "tags": ["办公技巧", "效率提升", "职场必备", "打工人"],
        "author": {"name": "效率控小陈", "avatar": "https://picsum.photos/seed/avatar1/100/100", "followers": 52000},
        "url": "https://www.xiaohongshu.com/explore/64a1b2c3d4e5f6g7",
        "created_at": "2025-06-15T10:30:00Z"
    },
    {
        "note_id": "64b2c3d4e5f6g7h8i9j0k1l2",
        "title": "自学Python三个月，我拿到了大厂offer❗学习路线分享",
        "content": "非科班转码成功！分享一下我的自学路线 \U0001f4da\n\n✅ 第一阶段（第1-2周）：Python基础\n- 变量、数据类型、条件判断、循环\n- 推荐：廖雪峰Python教程\n\n✅ 第二阶段（第3-4周）：进阶概念\n- 函数、类、模块、异常处理\n- 做个小项目：命令行待办清单\n\n✅ 第三阶段（第5-8周）：Web开发\n- Flask/Django框架\n- HTML/CSS基础\n- 数据库操作\n\n✅ 第四阶段（第9-12周）：项目实战\n- 搭建个人博客\n- 部署上线\n- 写进简历\n\n最重要的是坚持！每天至少写2小时代码，遇到问题先自己查再问人\n\n面试时面试官最看重的是你的学习能力和项目经验\n\n#编程入门 #Python学习 #转行IT #自学编程 #大厂上岸",
        "likes": 42100, "collects": 35600, "comments": 5843, "shares": 12300,
        "images": ["https://picsum.photos/seed/xhs4/800/800", "https://picsum.photos/seed/xhs5/800/800"],
        "tags": ["编程入门", "Python学习", "转行IT", "自学编程", "大厂上岸"],
        "author": {"name": "码农小鹿", "avatar": "https://picsum.photos/seed/avatar2/100/100", "followers": 89000},
        "url": "https://www.xiaohongshu.com/explore/64b2c3d4e5f6g7h8",
        "created_at": "2025-06-20T14:15:00Z"
    },
    {
        "note_id": "64c3d4e5f6g7h8i9j0k1l2m3",
        "title": "人均200吃到撑！上海这5家宝藏小店我藏不住了",
        "content": "在上海吃了3年，这5家店是我反复去的，今天含泪分享 \U0001f62d\n\n\U0001f35c 第一名：襄阳南路「老上海馄饨」\n人均35！鲜肉虾仁大馄饨，皮薄馅大，汤头是鸡骨熬的\n必点：虾仁鲜肉大馄饨 + 葱油拌面\n\n\U0001f356 第二名：定西路「阿姐烧烤」\n人均80吃到扶墙走！羊肉串2块钱一串你敢信？\n必点：烤羊肉串、烤茄子、烤馒头\n\n\U0001f35b 第三名：进贤路「海强面馆」\n人均50，红烧牛肉面绝了！牛肉炖得软烂入味\n必点：红烧牛肉面、炸猪排\n\n\U0001f95f 第四名：黄河路「佳家汤包」\n人均60，皮薄汤多，一咬爆汁\n必点：蟹粉鲜肉汤包\n\n\U0001f370 第五名：武康路「老麦咖啡馆」\n人均40，提拉米苏天花板！环境复古适合拍照\n\n建议收藏！周末可以一家一家打卡～\n\n#上海美食 #宝藏小店 #美食探店 #平价美食 #上海生活",
        "likes": 38900, "collects": 42100, "comments": 6721, "shares": 15600,
        "images": ["https://picsum.photos/seed/xhs6/800/800", "https://picsum.photos/seed/xhs7/800/800", "https://picsum.photos/seed/xhs8/800/800", "https://picsum.photos/seed/xhs9/800/800"],
        "tags": ["上海美食", "宝藏小店", "美食探店", "平价美食", "上海生活"],
        "author": {"name": "吃货小圆子", "avatar": "https://picsum.photos/seed/avatar3/100/100", "followers": 156000},
        "url": "https://www.xiaohongshu.com/explore/64c3d4e5f6g7h8i9",
        "created_at": "2025-06-25T09:00:00Z"
    },
    {
        "note_id": "64d4e5f6g7h8i9j0k1l2m3n4",
        "title": "iPhone隐藏功能大盘点！用了5年我才知道这些",
        "content": "苹果手机这些功能你不用就亏大了！\n\n\U0001f4f1 1. 背面敲击截图\n设置→辅助功能→触控→背面轻点\n敲两下截屏，敲三下打开相机\n\n\U0001f4f1 2. 扫描文档\n备忘录→相机→扫描文稿\n自动识别边缘，比扫描仪还清晰\n\n\U0001f4f1 3. 科学计算器\n把手机横过来，计算器秒变科学计算器\n\n\U0001f4f1 4. 隐藏照片\n选择照片→分享→隐藏\n在相册-已隐藏里查看（iOS16后支持FaceID锁定）\n\n\U0001f4f1 5. 自定义控制中心\n设置→控制中心→添加常用功能\n一键录屏、扫二维码超方便\n\n\U0001f4f1 6. 专注模式\n设置→专注模式→自定义场景\n工作模式自动屏蔽娱乐APP通知\n\n\U0001f4f1 7. Safari长截图\n截图→点击缩略图→选择「整页」\n\n你学废了吗？还有什么隐藏功能欢迎补充 \U0001f447\n\n#iPhone技巧 #苹果手机 #隐藏功能 #手机技巧",
        "likes": 56700, "collects": 48900, "comments": 8934, "shares": 21300,
        "images": ["https://picsum.photos/seed/xhs10/800/800", "https://picsum.photos/seed/xhs11/800/800", "https://picsum.photos/seed/xhs12/800/800"],
        "tags": ["iPhone技巧", "苹果手机", "隐藏功能", "手机技巧"],
        "author": {"name": "数码小达人", "avatar": "https://picsum.photos/seed/avatar4/100/100", "followers": 203000},
        "url": "https://www.xiaohongshu.com/explore/64d4e5f6g7h8i9j0",
        "created_at": "2025-06-28T16:45:00Z"
    },
    {
        "note_id": "64e5f6g7h8i9j0k1l2m3n4o5",
        "title": "跟着博主学穿搭❗基础款穿出高级感的5个秘诀",
        "content": "不买新衣服也能穿出高级感！学会这5招就够了 ✨\n\n\U0001f457 秘诀一：同色系搭配\n全身上下不超过3个颜色，同色系不同深浅最显高级\n推荐：米白+卡其+棕色系\n\n\U0001f457 秘诀二：注重面料质感\n宁愿买一件好的，不买十件差的\n棉麻、羊毛、真丝面料自带高级感\n\n\U0001f457 秘诀三：配饰是点睛之笔\n一条简约项链、一只质感手表\n细节决定品味\n\n\U0001f457 秘诀四：合身比品牌重要\n过大或过小都显廉价\n找对适合自己的版型是关键\n\n\U0001f457 秘诀五：保持衣物整洁\n熨烫平整的衣服看起来贵10倍\n常备粘毛器，出门前检查\n\n适合25-35岁职场女性的通勤穿搭\n\n#穿搭技巧 #高级感穿搭 #基础款搭配 #职场穿搭 #胶囊衣橱",
        "likes": 34500, "collects": 29800, "comments": 4521, "shares": 11200,
        "images": ["https://picsum.photos/seed/xhs13/800/800", "https://picsum.photos/seed/xhs14/800/800", "https://picsum.photos/seed/xhs15/800/800"],
        "tags": ["穿搭技巧", "高级感穿搭", "基础款搭配", "职场穿搭", "胶囊衣橱"],
        "author": {"name": "穿搭师Mia", "avatar": "https://picsum.photos/seed/avatar5/100/100", "followers": 278000},
        "url": "https://www.xiaohongshu.com/explore/64e5f6g7h8i9j0k1",
        "created_at": "2025-07-01T11:20:00Z"
    },
    {
        "note_id": "64f6g7h8i9j0k1l2m3n4o5p6",
        "title": "30天减脂餐食谱合集❗健康瘦了12斤的真实记录",
        "content": "不节食不吃药，靠吃瘦了12斤！把我的减脂餐分享给你们 \U0001f957\n\n\U0001f4cb 我的减脂原则：\n- 每天热量控制在1400-1600大卡\n- 碳水:蛋白质:脂肪 = 4:3:3\n- 16+8轻断食（只在8小时内进食）\n- 每周一天欺骗日\n\n\U0001f373 早餐（400卡）：\n周一三五：全麦面包+鸡蛋+牛奶+苹果\n周二四六：燕麦粥+坚果+蓝莓\n周日：想吃什么吃什么\n\n\U0001f969 午餐（500卡）：\n杂粮饭半碗 + 鸡胸肉/鱼肉/虾 + 蔬菜\n蔬菜不限量，吃到饱\n\n\U0001f9ec 晚餐（400卡）：\n蔬菜沙拉+豆腐/鸡蛋+少量紫薯/南瓜\n8点前吃完\n\n\U0001f34e 加餐（200卡）：\n下午3-4点：一根香蕉或一小把坚果\n\n⚠️ 重点：\n- 每天喝够2L水\n- 睡够7小时\n- 每周运动3-4次（30分钟有氧+20分钟力量）\n\n一个月下来不仅瘦了，皮肤也变好了！\n\n#减脂餐 #减肥食谱 #健康瘦身 #一个月瘦12斤 #自律生活",
        "likes": 78200, "collects": 67200, "comments": 12580, "shares": 28900,
        "images": ["https://picsum.photos/seed/xhs16/800/800", "https://picsum.photos/seed/xhs17/800/800", "https://picsum.photos/seed/xhs18/800/800", "https://picsum.photos/seed/xhs19/800/800"],
        "tags": ["减脂餐", "减肥食谱", "健康瘦身", "一个月瘦12斤", "自律生活"],
        "author": {"name": "健身女孩Lily", "avatar": "https://picsum.photos/seed/avatar6/100/100", "followers": 345000},
        "url": "https://www.xiaohongshu.com/explore/64f6g7h8i9j0k1l2",
        "created_at": "2025-07-02T07:30:00Z"
    },
]

# ============================================================
# SocialDataX MCP 客户端
# ============================================================

class SocialDataXClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url

    def _mcp_request(self, method, params=None):
        body = {"jsonrpc": "2.0", "method": method, "id": 1}
        if params:
            body["params"] = params

        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.api_key}"
        }

        ctx = ssl.create_default_context()
        req = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                raw = resp.read().decode("utf-8")
                # 解析 SSE 格式: "event: message\ndata: {...}"
                json_str = raw
                if raw.startswith("event:"):
                    m = re.search(r'data:\s*(\{[\s\S]*\})', raw)
                    if m:
                        json_str = m.group(1)
                return json.loads(json_str)
        except Exception as e:
            print(f"  MCP请求失败: {e}")
            return None

    def initialize(self):
        print(f"  \U0001f50c 连接 SocialDataX MCP ({self.base_url})...")
        result = self._mcp_request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "xhs-tool", "version": "2.0.0"}
        })
        if result and result.get("result"):
            info = result["result"].get("serverInfo", {})
            print(f"  ✅ 已连接: {info.get('name', 'SocialDataX')} v{info.get('version', '?')}")
            return True
        print(f"  ❌ MCP 初始化失败")
        return False

    def call_tool(self, tool_name, args=None):
        if args is None:
            args = {}
        result = self._mcp_request("tools/call", {"name": tool_name, "arguments": args})
        if result and result.get("result"):
            r = result["result"]
            if r.get("isError"):
                msg = r.get("structuredContent", {}).get("message", "Unknown error")
                raise Exception(msg)
            for item in r.get("content", []):
                if item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except (json.JSONDecodeError, TypeError):
                        return item["text"]
            return r.get("content", [])
        return None

    def close(self):
        pass

_sdx_client = None

def get_sdx_client():
    global _sdx_client
    if not SOCIALDATAX_API_KEY:
        return None
    if _sdx_client:
        return _sdx_client
    _sdx_client = SocialDataXClient(SOCIALDATAX_API_KEY, SOCIALDATAX_MCP_URL)
    if _sdx_client.initialize():
        return _sdx_client
    _sdx_client = None
    return None

# ============================================================
# 数据获取
# ============================================================

def normalize_sdx_note(raw):
    author = raw.get("author", {})
    images = []
    if raw.get("cover_image_url"):
        images.append(raw["cover_image_url"])
    for img in raw.get("image_items", []):
        if img.get("image_url"):
            images.append(img["image_url"])
    if not images:
        images.append(f"https://picsum.photos/seed/{raw.get('note_id', 'xhs')}/400/400")

    tags = []
    for t in raw.get("topic_tags", []):
        if isinstance(t, str):
            tags.append(t)
        elif isinstance(t, dict):
            tags.append(t.get("name", ""))

    return {
        "note_id": raw.get("note_id", ""),
        "title": raw.get("title", ""),
        "content": raw.get("content") or raw.get("summary", ""),
        "likes": int(raw.get("like_count", 0)),
        "collects": int(raw.get("collect_count", 0)),
        "comments": int(raw.get("comment_count", 0)),
        "shares": int(raw.get("share_count", 0)),
        "images": images,
        "tags": tags,
        "author": {
            "name": author.get("name", ""),
            "avatar": author.get("avatar_url", ""),
            "followers": 0
        },
        "url": raw.get("note_url", f"https://www.xiaohongshu.com/explore/{raw.get('note_id', '')}"),
        "created_at": __import__('datetime').datetime.fromtimestamp(raw.get("publish_time", 0)).isoformat() if raw.get("publish_time") else ""
    }

def search_mock(keyword, sort_by="likes", limit=20):
    kw = keyword.lower()
    results = []
    for post in MOCK_POSTS:
        score = 0
        if kw in post["title"].lower():
            score += 10
        if kw in post["content"].lower():
            score += 5
        for tag in post["tags"]:
            if kw in tag.lower():
                score += 8
        if score > 0:
            p = post.copy()
            p["relevance_score"] = score
            results.append(p)

    if sort_by == "likes":
        results.sort(key=lambda x: x["likes"], reverse=True)
    elif sort_by == "collects":
        results.sort(key=lambda x: x["collects"], reverse=True)
    elif sort_by == "comments":
        results.sort(key=lambda x: x["comments"], reverse=True)
    elif sort_by == "relevance":
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return results[:limit]

def search_real(keyword, sort_by="likes", limit=20):
    client = get_sdx_client()
    if not client:
        raise Exception("SocialDataX MCP 连接失败")

    sort_map = {
        "likes": "like_count_descending",
        "collects": "collect_count_descending",
        "comments": "comment_count_descending",
        "relevance": "general"
    }

    raw = client.call_tool("xhs_search_notes", {
        "keyword": keyword,
        "sort_type": sort_map.get(sort_by, "general"),
        "note_type": "all"
    })

    if not raw:
        return []
    notes = raw if isinstance(raw, list) else raw.get("items", raw.get("notes", raw.get("data", [])))
    return [normalize_sdx_note(n) for n in notes]

def get_real_detail(note_id):
    client = get_sdx_client()
    if not client:
        raise Exception("SocialDataX MCP 连接失败")
    raw = client.call_tool("xhs_get_note_detail_by_note_id", {"note_id": note_id})
    if not raw:
        return None
    note = raw.get("note") or raw.get("data") or raw
    return normalize_sdx_note(note)

def get_mock_detail(note_id):
    for post in MOCK_POSTS:
        if post["note_id"] == note_id:
            return post
    return None

# ============================================================
# 模板仿写
# ============================================================

def ai_rewrite(source_post, custom_theme="", similarity=50):
    """使用 AI API 进行智能仿写"""
    if not AI_API_KEY:
        return None

    title = source_post.get("title", "")
    content = source_post.get("content", "")
    tags = source_post.get("tags", [])

    # 根据相似度构建改写强度指令
    if similarity <= 30:
        intensity_prompt = f"【改写强度：低相似度 {similarity}%】大幅改写，仅保留核心主题思想。使用完全不同的表达方式、例证、具体细节和个人经历。结构也可以适当调整。"
    elif similarity <= 60:
        intensity_prompt = f"【改写强度：中相似度 {similarity}%】保持原帖的风格和基本结构，但替换具体内容、例证和细节。使用不同的措辞和表达方式。"
    else:
        intensity_prompt = f"【改写强度：高相似度 {similarity}%】保持原帖框架和主要观点，微调措辞和表达方式。保留核心结构和关键信息，替换少量细节和例证。"

    theme_instruction = ""
    if custom_theme:
        theme_instruction = f"""
【重要】用户指定的仿写方向：{custom_theme}
请严格按照这个方向来改写内容，替换相关的主体、场景、关键词等。
"""

    prompt = f"""你是一个小红书爆款笔记仿写专家。请分析以下爆款笔记的风格特点，然后仿写一篇全新的原创笔记。

## 原帖信息
标题：{title}
标签：{', '.join(tags)}
内容：
{content}

{theme_instruction}
## 仿写要求
1. 保持原帖的结构、段落格式、emoji使用风格
2. 保持原帖的叙述口吻（第一人称/教程式/清单式等）
3. 将内容主题替换为全新的方向{('：' + custom_theme) if custom_theme else '（与原文保持同一领域但内容不同）'}
4. 生成新的相关标签（3-5个）
5. 标题也要重新创作，保持吸引眼球的风格
6. 内容必须原创，不能直接复制原帖
7. {intensity_prompt}

请以JSON格式返回：
{{
    "title": "新标题",
    "content": "新内容",
    "tags": ["标签1", "标签2", "标签3"],
    "style_analysis": "风格分析（一句话）"
}}"""

    try:
        import urllib.request
        api_base = AI_API_BASE.rstrip('/') if AI_API_BASE else "https://api.openai.com/v1"
        url = f"{api_base}/chat/completions"

        body = json.dumps({
            "model": os.environ.get("AI_MODEL", "gpt-3.5-turbo"),
            "messages": [
                {"role": "system", "content": "你是一个小红书爆款笔记仿写专家，擅长分析爆款内容风格并生成原创仿写。请只返回JSON格式的结果。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 1.0 if similarity <= 30 else (0.8 if similarity <= 60 else 0.6),
            "max_tokens": 2000
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}"
        }

        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw)

        ai_text = result["choices"][0]["message"]["content"].strip()

        # 尝试提取 JSON（处理 AI 可能包裹的 ```json ``` 标记）
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', ai_text)
        if json_match:
            ai_text = json_match.group(1).strip()

        ai_result = json.loads(ai_text)

        return {
            "title": ai_result.get("title", "【仿写】" + title),
            "content": ai_result.get("content", content),
            "tags": ai_result.get("tags", tags)[:5],
            "style_analysis": ai_result.get("style_analysis", ""),
            "method": "ai_powered",
            "similarity": similarity
        }

    except Exception as e:
        print(f"  AI仿写失败: {e}")
        return None


def template_rewrite(source_post, custom_theme="", similarity=50):
    """
    模板仿写（AI API 不可用时的回退方案）。
    当用户指定 custom_theme 时，解析其中的关键词对（如"上海→北京"、"美食→旅行"），
    并用这些映射替换原文中的关键词。
    根据 similarity 参数控制替换的力度。
    """
    title = source_post.get("title", "")
    content = source_post.get("content", "")
    tags = list(source_post.get("tags", []))

    # --- 构建替换映射 ---
    replace_map = {}

    # 1. 解析用户自定义主题方向
    if custom_theme:
        pairs = re.split(r'[,，、\s]+', custom_theme)
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            m = re.match(r'(.+?)\s*[→\->]\s*(.+)', pair)
            if m:
                replace_map[m.group(1).strip()] = m.group(2).strip()
            else:
                m = re.match(r'(.+?)[换改]\s*(?:成|为|到)\s*(.+)', pair)
                if m:
                    replace_map[m.group(1).strip()] = m.group(2).strip()

    # 2. 如果用户没给明确映射，尝试从 custom_theme 中提取有意义的词作为新主题
    if not replace_map and custom_theme:
        core_words = extract_core_keywords(title, content, tags)
        if core_words and custom_theme:
            new_theme_word = custom_theme.strip()
            new_theme_word = re.sub(r'^.*?[换改仿][成写到]?\s*', '', new_theme_word)
            if core_words[0] in replace_map:
                pass
            for cw in core_words[:2]:
                if cw not in replace_map and len(cw) >= 2:
                    replace_map[cw] = new_theme_word
                    break

    # 3. 根据相似度决定替换数量
    replace_items = list(replace_map.items())
    if similarity <= 30:
        effective_count = len(replace_items)  # 全部替换
    elif similarity <= 60:
        effective_count = max(1, int(len(replace_items) * 0.6))
    else:
        effective_count = max(0, int(len(replace_items) * 0.3))

    # 4. 应用替换
    for old, new in replace_items[:effective_count]:
        title = title.replace(old, new)
        content = content.replace(old, new)

    # 5. 更新标签
    new_tags = []
    for tag in tags:
        nt = tag
        for old, new in replace_items[:effective_count]:
            nt = nt.replace(old, new)
        if nt not in new_tags:
            new_tags.append(nt)

    if title == source_post.get("title", "") and not replace_map:
        title = "【仿写】" + title

    if custom_theme and replace_map:
        title = f"【{custom_theme}】" + title if not title.startswith("【") else title

    has_emoji = bool(re.search(r'[^\w\s一-鿿，。！？、；：「」（）\n]', content))
    sections = content.count('\n\n')
    theme_info = f"、方向: {custom_theme}" if custom_theme else ""
    style = f"风格特点：{'emoji丰富' if has_emoji else '文字为主'}、{'多段落' if sections >= 3 else '紧凑型'}、约{len(content)}字{theme_info}"

    return {
        "title": title,
        "content": content,
        "tags": new_tags[:5],
        "style_analysis": style,
        "method": "template_based",
        "similarity": similarity
    }


def extract_core_keywords(title, content, tags):
    """从帖子中提取核心关键词（用于主题替换）"""
    import collections
    # 常见的可替换主题词
    candidates = []
    # 从标题和标签中提取
    text = title + " " + " ".join(tags)
    # 简单的分词：按常见分隔符拆分
    words = re.findall(r'[一-鿿\w]+', text)
    # 过滤掉常见的无意义词
    stop_words = {'的', '了', '是', '我', '你', '他', '她', '它', '们', '在', '有', '和', '都',
                  '不', '就', '也', '还', '要', '会', '可', '到', '对', '去', '来', '能', '让',
                  '把', '被', '从', '最', '为', '及', '与', '或', '但', '而', '且', '所', '如',
                  '这', '那', '个', '中', '上', '下', '前', '后', '里', '外', '大', '小', '多',
                  '少', '很', '真', '太', '更', '非常', '比较', '一个', '什么', '怎么', '如何',
                  '为什么', '多少', '可以', '应该', '已经', '没有', '知道', '觉得', '一个', '一种',
                  '技巧', '方法', '秘诀', '分享', '推荐', '必备', '教程', '攻略', '合集', '盘点',
                  '隐藏', '学习', '提升', '入门', '必看', '效率', '好物', '神器', '宝藏', '笔记'}
    for w in words:
        if len(w) >= 2 and w not in stop_words:
            candidates.append(w)

    # 按频率排序
    counter = collections.Counter(candidates)
    return [w for w, _ in counter.most_common(10)]


# ============================================================
# 文本差异计算 (基于 LCS 算法)
# ============================================================

def compute_diff(source_text, rewritten_text):
    """计算原文和仿写文之间的差异"""
    def split_to_chars(text):
        segments = []
        current = ''
        for ch in text:
            current += ch
            if ch in ('\n', '。', '！', '？', '；'):
                if current.strip():
                    segments.append(current.strip())
                current = ''
        if current.strip():
            segments.append(current.strip())
        return segments if segments else [text]

    source_segs = split_to_chars(source_text)
    rewritten_segs = split_to_chars(rewritten_text)

    m, n = len(source_segs), len(rewritten_segs)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if source_segs[i - 1] == rewritten_segs[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # 回溯找出匹配
    lcs_matches = set()
    i, j = m, n
    while i > 0 and j > 0:
        if source_segs[i - 1] == rewritten_segs[j - 1]:
            lcs_matches.add((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    # 生成 diff blocks
    blocks = []
    si, ri = 0, 0
    while si < len(source_segs) or ri < len(rewritten_segs):
        if si < len(source_segs) and ri < len(rewritten_segs) and (si, ri) in lcs_matches:
            blocks.append({"type": "unchanged", "text": source_segs[si], "oldPosition": si, "newPosition": ri})
            si += 1
            ri += 1
        elif si < len(source_segs) and ri < len(rewritten_segs):
            blocks.append({"type": "modified", "oldText": source_segs[si], "newText": rewritten_segs[ri], "oldPosition": si, "newPosition": ri})
            si += 1
            ri += 1
        elif si < len(source_segs):
            blocks.append({"type": "deleted", "oldText": source_segs[si], "newText": None, "oldPosition": si, "newPosition": None})
            si += 1
        elif ri < len(rewritten_segs):
            blocks.append({"type": "added", "oldText": None, "newText": rewritten_segs[ri], "oldPosition": None, "newPosition": ri})
            ri += 1

    unchanged_count = sum(1 for b in blocks if b["type"] == "unchanged")
    total_blocks = len(blocks) or 1
    similarity_score = round((unchanged_count / total_blocks) * 100)

    return {
        "similarity_score": similarity_score,
        "total_blocks": len(blocks),
        "unchanged": unchanged_count,
        "added": sum(1 for b in blocks if b["type"] == "added"),
        "deleted": sum(1 for b in blocks if b["type"] == "deleted"),
        "modified": sum(1 for b in blocks if b["type"] == "modified"),
        "blocks": blocks
    }


def apply_diff_decisions(source_text, rewritten_text, decisions):
    """根据用户的差异决策拼接最终文本"""
    diff = compute_diff(source_text, rewritten_text)
    result_parts = []

    for i, block in enumerate(diff["blocks"]):
        decision = decisions.get(f"block_{i}", "accept")

        if block["type"] == "unchanged":
            result_parts.append(block["text"])
        elif block["type"] == "added":
            if decision == "accept":
                result_parts.append(block["newText"])
        elif block["type"] == "deleted":
            if decision != "accept":
                result_parts.append(block["oldText"])
        elif block["type"] == "modified":
            if decision == "accept":
                result_parts.append(block["newText"])
            else:
                result_parts.append(block["oldText"])

    return '\n'.join(result_parts)


# ============================================================
# Flask 路由
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config')
def get_config():
    return jsonify({
        "use_mock_data": USE_MOCK_DATA or not SOCIALDATAX_API_KEY,
        "has_api_key": bool(SOCIALDATAX_API_KEY),
        "has_ai_key": bool(AI_API_KEY),
        "api_base": SOCIALDATAX_MCP_URL if SOCIALDATAX_API_KEY else "(未配置)"
    })

@app.route('/health')
@app.route('/api/health')
def health():
    import time as _time
    return jsonify({"status": "ok", "timestamp": __import__('datetime').datetime.now().isoformat()})

@app.route('/api/search')
def search():
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify({"error": "请输入搜索关键词", "posts": []}), 400

    sort_by = request.args.get('sort_by', 'likes')
    limit = min(int(request.args.get('limit', 20)), 50)

    posts, data_source, api_error = [], "mock", None

    if not USE_MOCK_DATA and SOCIALDATAX_API_KEY:
        try:
            posts = search_real(keyword, sort_by, limit)
            data_source = "socialdatax"
        except Exception as e:
            print(f"  SocialDataX搜索失败: {e}")
            api_error = str(e)
            posts = search_mock(keyword, sort_by, limit)
            data_source = "mock_fallback"
    else:
        posts = search_mock(keyword, sort_by, limit)

    return jsonify({
        "keyword": keyword, "total": len(posts),
        "sort_by": sort_by, "posts": posts,
        "data_source": data_source, "api_error": api_error
    })

@app.route('/api/post/<note_id>')
def post_detail(note_id):
    post = None
    if not USE_MOCK_DATA and SOCIALDATAX_API_KEY:
        try:
            post = get_real_detail(note_id)
        except Exception as e:
            print(f"  详情获取失败: {e}")

    if not post:
        post = get_mock_detail(note_id)

    if not post:
        return jsonify({"error": "帖子不存在"}), 404
    return jsonify({"post": post})

@app.route('/api/rewrite', methods=['POST'])
def rewrite():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供请求数据"}), 400

    note_id = data.get('note_id', '')
    custom_theme = data.get('custom_theme', '')
    similarity = min(90, max(10, int(data.get('similarity', 50))))

    if not note_id:
        return jsonify({"error": "请提供帖子ID"}), 400

    source_post = None
    if not USE_MOCK_DATA and SOCIALDATAX_API_KEY:
        try:
            source_post = get_real_detail(note_id)
        except Exception:
            pass
    if not source_post:
        source_post = get_mock_detail(note_id)
    if not source_post:
        return jsonify({"error": "帖子不存在"}), 404

    # 优先使用 AI 仿写，失败时回退到模板仿写
    result = None
    if AI_API_KEY:
        result = ai_rewrite(source_post, custom_theme, similarity)

    if not result:
        result = template_rewrite(source_post, custom_theme, similarity)

    # 计算文本差异
    diff = compute_diff(source_post.get("content", ""), result.get("content", ""))

    return jsonify({
        "source_post": {
            "title": source_post.get("title"),
            "content": source_post.get("content"),
            "tags": source_post.get("tags"),
            "likes": source_post.get("likes"),
            "collects": source_post.get("collects"),
            "comments": source_post.get("comments"),
        },
        "rewritten": result,
        "diff": diff
    })


@app.route('/api/rewrite/adjust', methods=['POST'])
def rewrite_adjust():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供请求数据"}), 400

    source_content = data.get('source_content', '')
    rewritten_content = data.get('rewritten_content', '')
    decisions = data.get('decisions', {})

    if not source_content or not rewritten_content:
        return jsonify({"error": "请提供原帖内容和仿写内容"}), 400

    adjusted = apply_diff_decisions(source_content, rewritten_content, decisions)
    return jsonify({"content": adjusted})

@app.route('/api/hot-posts')
def hot_posts():
    category = request.args.get('category', '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)

    posts, data_source = [], "mock"

    if not USE_MOCK_DATA and SOCIALDATAX_API_KEY:
        try:
            client = get_sdx_client()
            if client:
                raw = client.call_tool("xhs_search_notes", {
                    "keyword": category or "热门",
                    "sort_type": "like_count_descending",
                    "note_type": "all"
                })
                if raw:
                    notes = raw if isinstance(raw, list) else raw.get("items", raw.get("notes", []))
                    posts = [normalize_sdx_note(n) for n in notes]
                    data_source = "socialdatax"
        except Exception as e:
            print(f"  热榜获取失败: {e}")

    if not posts:
        posts = list(MOCK_POSTS)
        if category:
            posts = [p for p in posts if category in p.get("title", "") or any(category in t for t in p.get("tags", []))]
        posts.sort(key=lambda x: x["likes"], reverse=True)
        posts = posts[:limit]

    return jsonify({"total": len(posts), "posts": posts, "data_source": data_source})

# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("  \U0001f525 小红书热门帖子查询 & AI仿写工具 (Flask)")
    print(f"  \U0001f4e1 数据源: {'Mock模拟数据' if USE_MOCK_DATA or not SOCIALDATAX_API_KEY else 'SocialDataX 真实API'}")
    print(f"  \U0001f310 访问: http://localhost:{port}")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=port)
