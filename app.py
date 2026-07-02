"""
小红书热门帖子查询与仿写工具 - 后端服务
Xiaohongshu Hot Post Search & Rewrite Tool
"""

import os
import json
import hashlib
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

# ============================================================
# 配置
# ============================================================
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# API 配置 - 从环境变量或 .env 文件读取
XHS_API_BASE = os.environ.get("XHS_API_BASE", "https://api.socialdatax.com/v1")  # 第三方API示例
XHS_API_KEY = os.environ.get("XHS_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "true").lower() == "true"

# ============================================================
# 模拟数据 - 当没有真实 API Key 时使用
# ============================================================
MOCK_POSTS = [
    {
        "note_id": "64a1b2c3d4e5f6g7h8i9j0k1",
        "title": "打工人必看！5个让办公效率翻倍的隐藏技巧",
        "content": "用了3年才发现这些功能，之前都在浪费时间！\n\n1️⃣ Windows虚拟桌面\n按Win+Tab可以创建多个桌面，工作一个、摸鱼一个，再也不怕老板突然出现 👀\n\n2️⃣ 剪贴板历史\nWin+V 打开剪贴板历史，之前复制的内容都能找回来！\n\n3️⃣ 分屏快捷键\nWin+方向键快速分屏，写文档查资料同时进行\n\n4️⃣ 截图工具\nWin+Shift+S 任意区域截图，不需要登录微信\n\n5️⃣ 搜索神器 Everything\n秒搜全盘文件，比Windows自带搜索快100倍\n\n收藏起来慢慢学，学会了记得回来感谢我～\n\n#办公技巧 #效率提升 #职场必备 #打工人",
        "likes": 23500,
        "collects": 18200,
        "comments": 3256,
        "shares": 8900,
        "images": [
            "https://picsum.photos/seed/xhs1/800/800",
            "https://picsum.photos/seed/xhs2/800/800",
            "https://picsum.photos/seed/xhs3/800/800"
        ],
        "tags": ["办公技巧", "效率提升", "职场必备", "打工人"],
        "author": {"name": "效率控小陈", "avatar": "https://picsum.photos/seed/avatar1/100/100", "followers": 52000},
        "url": "https://www.xiaohongshu.com/explore/64a1b2c3d4e5f6g7",
        "created_at": "2025-06-15T10:30:00Z",
        "platform": "xiaohongshu"
    },
    {
        "note_id": "64b2c3d4e5f6g7h8i9j0k1l2",
        "title": "自学Python三个月，我拿到了大厂offer｜学习路线分享",
        "content": "非科班转码成功！分享一下我的自学路线 📚\n\n✅ 第一阶段（第1-2周）：Python基础\n- 变量、数据类型、条件判断、循环\n- 推荐：廖雪峰Python教程\n\n✅ 第二阶段（第3-4周）：进阶概念\n- 函数、类、模块、异常处理\n- 做个小项目：命令行待办清单\n\n✅ 第三阶段（第5-8周）：Web开发\n- Flask/Django框架\n- HTML/CSS基础\n- 数据库操作\n\n✅ 第四阶段（第9-12周）：项目实战\n- 搭建个人博客\n- 部署上线\n- 写进简历\n\n最重要的是坚持！每天至少写2小时代码，遇到问题先自己查再问人\n\n面试时面试官最看重的是你的学习能力和项目经验\n\n#编程入门 #Python学习 #转行IT #自学编程 #大厂上岸",
        "likes": 42100,
        "collects": 35600,
        "comments": 5843,
        "shares": 12300,
        "images": [
            "https://picsum.photos/seed/xhs4/800/800",
            "https://picsum.photos/seed/xhs5/800/800"
        ],
        "tags": ["编程入门", "Python学习", "转行IT", "自学编程", "大厂上岸"],
        "author": {"name": "码农小鹿", "avatar": "https://picsum.photos/seed/avatar2/100/100", "followers": 89000},
        "url": "https://www.xiaohongshu.com/explore/64b2c3d4e5f6g7h8",
        "created_at": "2025-06-20T14:15:00Z",
        "platform": "xiaohongshu"
    },
    {
        "note_id": "64c3d4e5f6g7h8i9j0k1l2m3",
        "title": "人均200吃到撑！上海这5家宝藏小店我藏不住了",
        "content": "在上海吃了3年，这5家店是我反复去的，今天含泪分享 😭\n\n🍜 第一名：襄阳南路「老上海馄饨」\n人均35！鲜肉虾仁大馄饨，皮薄馅大，汤头是鸡骨熬的\n必点：虾仁鲜肉大馄饨 + 葱油拌面\n\n🍖 第二名：定西路「阿姐烧烤」\n人均80吃到扶墙走！羊肉串2块钱一串你敢信？\n必点：烤羊肉串、烤茄子、烤馒头\n\n🍛 第三名：进贤路「海强面馆」\n人均50，红烧牛肉面绝了！牛肉炖得软烂入味\n必点：红烧牛肉面、炸猪排\n\n🥟 第四名：黄河路「佳家汤包」\n人均60，皮薄汤多，一咬爆汁\n必点：蟹粉鲜肉汤包\n\n🍰 第五名：武康路「老麦咖啡馆」\n人均40，提拉米苏天花板！环境复古适合拍照\n\n建议收藏！周末可以一家一家打卡～\n\n#上海美食 #宝藏小店 #美食探店 #平价美食 #上海生活",
        "likes": 38900,
        "collects": 42100,
        "comments": 6721,
        "shares": 15600,
        "images": [
            "https://picsum.photos/seed/xhs6/800/800",
            "https://picsum.photos/seed/xhs7/800/800",
            "https://picsum.photos/seed/xhs8/800/800",
            "https://picsum.photos/seed/xhs9/800/800"
        ],
        "tags": ["上海美食", "宝藏小店", "美食探店", "平价美食", "上海生活"],
        "author": {"name": "吃货小圆子", "avatar": "https://picsum.photos/seed/avatar3/100/100", "followers": 156000},
        "url": "https://www.xiaohongshu.com/explore/64c3d4e5f6g7h8i9",
        "created_at": "2025-06-25T09:00:00Z",
        "platform": "xiaohongshu"
    },
    {
        "note_id": "64d4e5f6g7h8i9j0k1l2m3n4",
        "title": "iPhone隐藏功能大盘点！用了5年我才知道这些",
        "content": "苹果手机这些功能你不用就亏大了！\n\n📱 1. 背面敲击截图\n设置→辅助功能→触控→背面轻点\n敲两下截屏，敲三下打开相机\n\n📱 2. 扫描文档\n备忘录→相机→扫描文稿\n自动识别边缘，比扫描仪还清晰\n\n📱 3. 科学计算器\n把手机横过来，计算器秒变科学计算器\n\n📱 4. 隐藏照片\n选择照片→分享→隐藏\n在相册-已隐藏里查看（iOS16后支持FaceID锁定）\n\n📱 5. 自定义控制中心\n设置→控制中心→添加常用功能\n一键录屏、扫二维码超方便\n\n📱 6. 专注模式\n设置→专注模式→自定义场景\n工作模式自动屏蔽娱乐APP通知\n\n📱 7. Safari长截图\n截图→点击缩略图→选择"整页"\n\n你学废了吗？还有什么隐藏功能欢迎补充 👇\n\n#iPhone技巧 #苹果手机 #隐藏功能 #手机技巧",
        "likes": 56700,
        "collects": 48900,
        "comments": 8934,
        "shares": 21300,
        "images": [
            "https://picsum.photos/seed/xhs10/800/800",
            "https://picsum.photos/seed/xhs11/800/800",
            "https://picsum.photos/seed/xhs12/800/800"
        ],
        "tags": ["iPhone技巧", "苹果手机", "隐藏功能", "手机技巧"],
        "author": {"name": "数码小达人", "avatar": "https://picsum.photos/seed/avatar4/100/100", "followers": 203000},
        "url": "https://www.xiaohongshu.com/explore/64d4e5f6g7h8i9j0",
        "created_at": "2025-06-28T16:45:00Z",
        "platform": "xiaohongshu"
    },
    {
        "note_id": "64e5f6g7h8i9j0k1l2m3n4o5",
        "title": "跟着博主学穿搭｜基础款穿出高级感的5个秘诀",
        "content": "不买新衣服也能穿出高级感！学会这5招就够了 ✨\n\n👗 秘诀一：同色系搭配\n全身上下不超过3个颜色，同色系不同深浅最显高级\n推荐：米白+卡其+棕色系\n\n👗 秘诀二：注重面料质感\n宁愿买一件好的，不买十件差的\n棉麻、羊毛、真丝面料自带高级感\n\n👗 秘诀三：配饰是点睛之笔\n一条简约项链、一只质感手表\n细节决定品味\n\n👗 秘诀四：合身比品牌重要\n过大或过小都显廉价\n找对适合自己的版型是关键\n\n👗 秘诀五：保持衣物整洁\n熨烫平整的衣服看起来贵10倍\n常备粘毛器，出门前检查\n\n适合25-35岁职场女性的通勤穿搭\n\n#穿搭技巧 #高级感穿搭 #基础款搭配 #职场穿搭 #胶囊衣橱",
        "likes": 34500,
        "collects": 29800,
        "comments": 4521,
        "shares": 11200,
        "images": [
            "https://picsum.photos/seed/xhs13/800/800",
            "https://picsum.photos/seed/xhs14/800/800",
            "https://picsum.photos/seed/xhs15/800/800"
        ],
        "tags": ["穿搭技巧", "高级感穿搭", "基础款搭配", "职场穿搭", "胶囊衣橱"],
        "author": {"name": "穿搭师Mia", "avatar": "https://picsum.photos/seed/avatar5/100/100", "followers": 278000},
        "url": "https://www.xiaohongshu.com/explore/64e5f6g7h8i9j0k1",
        "created_at": "2025-07-01T11:20:00Z",
        "platform": "xiaohongshu"
    },
    {
        "note_id": "64f6g7h8i9j0k1l2m3n4o5p6",
        "title": "30天减脂餐食谱合集｜健康瘦了12斤的真实记录",
        "content": "不节食不吃药，靠吃瘦了12斤！把我的减脂餐分享给你们 🥗\n\n📋 我的减脂原则：\n- 每天热量控制在1400-1600大卡\n- 碳水:蛋白质:脂肪 = 4:3:3\n- 16+8轻断食（只在8小时内进食）\n- 每周一天欺骗日\n\n🍳 早餐（400卡）：\n周一三五：全麦面包+鸡蛋+牛奶+苹果\n周二四六：燕麦粥+坚果+蓝莓\n周日：想吃什么吃什么\n\n🥩 午餐（500卡）：\n杂粮饭半碗 + 鸡胸肉/鱼肉/虾 + 蔬菜\n蔬菜不限量，吃到饱\n\n🥬 晚餐（400卡）：\n蔬菜沙拉+豆腐/鸡蛋+少量紫薯/南瓜\n8点前吃完\n\n🍎 加餐（200卡）：\n下午3-4点：一根香蕉或一小把坚果\n\n⚠️ 重点：\n- 每天喝够2L水\n- 睡够7小时\n- 每周运动3-4次（30分钟有氧+20分钟力量）\n\n一个月下来不仅瘦了，皮肤也变好了！\n\n#减脂餐 #减肥食谱 #健康瘦身 #一个月瘦12斤 #自律生活",
        "likes": 78200,
        "collects": 67200,
        "comments": 12580,
        "shares": 28900,
        "images": [
            "https://picsum.photos/seed/xhs16/800/800",
            "https://picsum.photos/seed/xhs17/800/800",
            "https://picsum.photos/seed/xhs18/800/800",
            "https://picsum.photos/seed/xhs19/800/800"
        ],
        "tags": ["减脂餐", "减肥食谱", "健康瘦身", "一个月瘦12斤", "自律生活"],
        "author": {"name": "健身女孩Lily", "avatar": "https://picsum.photos/seed/avatar6/100/100", "followers": 345000},
        "url": "https://www.xiaohongshu.com/explore/64f6g7h8i9j0k1l2",
        "created_at": "2025-07-02T07:30:00Z",
        "platform": "xiaohongshu"
    },
]

# ============================================================
# 数据获取层 - 支持多种后端
# ============================================================

class XHSDataProvider:
    """小红书数据提供者 - 支持 Mock / 第三方API / MCP 多种模式"""

    @staticmethod
    def search_by_keyword(keyword, sort_by="likes", limit=20):
        """根据关键词搜索帖子"""
        if USE_MOCK_DATA or not XHS_API_KEY:
            return XHSDataProvider._mock_search(keyword, sort_by, limit)
        else:
            return XHSDataProvider._api_search(keyword, sort_by, limit)

    @staticmethod
    def get_post_detail(note_id):
        """获取帖子详情"""
        if USE_MOCK_DATA or not XHS_API_KEY:
            return XHSDataProvider._mock_detail(note_id)
        else:
            return XHSDataProvider._api_detail(note_id)

    @staticmethod
    def _mock_search(keyword, sort_by="likes", limit=20):
        """模拟搜索 - 根据关键词匹配本地数据"""
        keyword_lower = keyword.lower()
        results = []
        for post in MOCK_POSTS:
            score = 0
            if keyword_lower in post["title"].lower():
                score += 10
            if keyword_lower in post["content"].lower():
                score += 5
            for tag in post["tags"]:
                if keyword_lower in tag.lower():
                    score += 8
            if score > 0:
                post_copy = post.copy()
                post_copy["relevance_score"] = score
                results.append(post_copy)

        # 按指定方式排序
        if sort_by == "likes":
            results.sort(key=lambda x: x["likes"], reverse=True)
        elif sort_by == "collects":
            results.sort(key=lambda x: x["collects"], reverse=True)
        elif sort_by == "comments":
            results.sort(key=lambda x: x["comments"], reverse=True)
        elif sort_by == "relevance":
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return results[:limit]

    @staticmethod
    def _mock_detail(note_id):
        """模拟获取帖子详情"""
        for post in MOCK_POSTS:
            if post["note_id"] == note_id:
                return post
        return None

    @staticmethod
    def _api_search(keyword, sort_by="likes", limit=20):
        """
        通过第三方API搜索帖子
        示例使用 SocialDataX API 格式
        实际使用时请根据具体API文档调整
        """
        try:
            headers = {
                "Authorization": f"Bearer {XHS_API_KEY}",
                "Content-Type": "application/json"
            }
            params = {
                "keyword": keyword,
                "sort_by": sort_by,
                "limit": limit,
                "platform": "xiaohongshu"
            }
            resp = requests.get(
                f"{XHS_API_BASE}/search/notes",
                headers=headers,
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("notes", [])
            else:
                print(f"API Error: {resp.status_code} - {resp.text}")
                return []
        except Exception as e:
            print(f"API Request Failed: {e}")
            return []

    @staticmethod
    def _api_detail(note_id):
        """通过第三方API获取帖子详情"""
        try:
            headers = {
                "Authorization": f"Bearer {XHS_API_KEY}",
                "Content-Type": "application/json"
            }
            resp = requests.get(
                f"{XHS_API_BASE}/note/{note_id}",
                headers=headers,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {})
            else:
                print(f"API Error: {resp.status_code}")
                return None
        except Exception as e:
            print(f"API Request Failed: {e}")
            return None


# ============================================================
# AI 仿写服务 - 使用 Claude API
# ============================================================

class AIRewriteService:
    """AI仿写服务 - 基于原帖风格生成新内容"""

    REWRITE_SYSTEM_PROMPT = """你是一个专业的小红书内容创作助手。你的任务是分析一篇热门小红书笔记的写作风格、结构和表达逻辑，然后创作一篇主题相似但内容完全不同的全新笔记。

请严格遵循以下要求：
1. **保持风格一致**：模仿原帖的语气（口语化/专业化/亲切感等）、emoji使用习惯、排版方式
2. **保持结构一致**：保留原帖的段落组织方式（如分点列举、故事叙述、教程步骤等）
3. **保持互动模式**：模仿原帖与读者互动的方式（提问、号召收藏/点赞等）
4. **话题标签仿写**：生成与原帖相关但不同的3-5个话题标签
5. **内容完全原创**：主题可以相近但具体内容必须是新的，不能直接复制原文

输出格式为JSON，包含以下字段：
- title: 仿写后的标题（15-30字）
- content: 仿写后的正文内容（保持原帖长度和结构）
- tags: 新的话题标签列表
- style_analysis: 对原帖风格特点的简短总结（50字以内）"""

    @staticmethod
    def rewrite(source_post, custom_theme=None):
        """
        基于原帖进行仿写
        source_post: 原始帖子数据
        custom_theme: 可选的自定义主题方向
        """
        if not ANTHROPIC_API_KEY:
            # 无API Key时，使用模板化的仿写
            return AIRewriteService._template_rewrite(source_post, custom_theme)

        return AIRewriteService._ai_rewrite(source_post, custom_theme)

    @staticmethod
    def _template_rewrite(source_post, custom_theme=None):
        """模板化仿写 - 基于规则的替换方案，无需API"""
        import re

        title = source_post.get("title", "")
        content = source_post.get("content", "")
        tags = source_post.get("tags", [])

        # 分析原帖结构
        has_emoji = bool(re.search(r'[^\w\s一-鿿，。！？、；：""''（）]', content))
        has_numbers = bool(re.search(r'[①②③④⑤1-9️⃣🍜📱👗🥗]', content))
        has_sections = content.count('\n\n') >= 3
        content_length = len(content)

        # 生成主题变体
        theme_map = {
            "办公": "学习", "效率": "效率", "Python": "JavaScript",
            "编程": "写作", "美食": "旅行", "上海": "北京",
            "iPhone": "安卓", "穿搭": "护肤", "减脂": "增肌",
            "手机": "平板", "吃": "玩"
        }

        # 生成仿写标题
        new_title = title
        for old, new in theme_map.items():
            if old in new_title:
                new_title = new_title.replace(old, new)
                break
        if new_title == title:
            new_title = "【仿写】" + title

        # 生成仿写内容
        new_content = content
        for old, new in theme_map.items():
            new_content = new_content.replace(old, new)

        # 替换数字和部分内容以体现差异化
        replacements = {
            "5个": "6个", "5家": "6家", "30天": "21天",
            "12斤": "8斤", "3年": "2年", "三个月": "两个月",
            "200": "150", "35": "30", "80": "70", "50": "45", "60": "55", "40": "35"
        }
        for old, new in replacements.items():
            new_content = new_content.replace(old, new)

        # 生成新标签
        new_tags = []
        for tag in tags:
            new_tag = tag
            for old, new in theme_map.items():
                new_tag = new_tag.replace(old, new)
            if new_tag not in new_tags:
                new_tags.append(new_tag)

        style_analysis = f"风格特点：{'emoji丰富' if has_emoji else '文字为主'}、{'分点列举' if has_numbers else '段落叙述'}、{'多段落结构' if has_sections else '紧凑型'}、约{content_length}字"

        return {
            "title": new_title,
            "content": new_content,
            "tags": new_tags[:5],
            "style_analysis": style_analysis,
            "method": "template_based"
        }

    @staticmethod
    def _ai_rewrite(source_post, custom_theme=None):
        """使用 Claude API 进行AI仿写"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

            user_message = f"""请分析以下小红书热门笔记，然后进行仿写创作：

【原帖标题】
{source_post.get('title', '')}

【原帖正文】
{source_post.get('content', '')}

【原帖标签】
{', '.join(source_post.get('tags', []))}

【互动数据】
点赞:{source_post.get('likes', 0)} | 收藏:{source_post.get('collects', 0)} | 评论:{source_post.get('comments', 0)}

{"【自定义主题方向】" + custom_theme if custom_theme else ""}

请以JSON格式返回仿写结果。"""

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=AIRewriteService.REWRITE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.8,
            )

            # 解析返回的JSON
            response_text = response.content[0].text
            # 提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                result["method"] = "ai_powered"
                return result
            else:
                # JSON解析失败，回退到模板模式
                return AIRewriteService._template_rewrite(source_post, custom_theme)

        except ImportError:
            print("Anthropic SDK not installed, falling back to template mode")
            return AIRewriteService._template_rewrite(source_post, custom_theme)
        except Exception as e:
            print(f"AI Rewrite Failed: {e}")
            return AIRewriteService._template_rewrite(source_post, custom_theme)


# ============================================================
# Flask 路由
# ============================================================

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/search')
def search():
    """
    搜索帖子
    GET /api/search?keyword=xxx&sort_by=likes&limit=20
    """
    keyword = request.args.get('keyword', '').strip()
    sort_by = request.args.get('sort_by', 'likes')
    limit = min(int(request.args.get('limit', 20)), 50)

    if not keyword:
        return jsonify({"error": "请输入搜索关键词", "posts": []}), 400

    posts = XHSDataProvider.search_by_keyword(keyword, sort_by, limit)

    return jsonify({
        "keyword": keyword,
        "total": len(posts),
        "sort_by": sort_by,
        "posts": posts,
        "data_source": "mock" if (USE_MOCK_DATA or not XHS_API_KEY) else "api"
    })


@app.route('/api/post/<note_id>')
def post_detail(note_id):
    """
    获取帖子详情
    GET /api/post/<note_id>
    """
    post = XHSDataProvider.get_post_detail(note_id)
    if not post:
        return jsonify({"error": "帖子不存在"}), 404
    return jsonify({"post": post})


@app.route('/api/rewrite', methods=['POST'])
def rewrite():
    """
    仿写帖子
    POST /api/rewrite
    Body: {"note_id": "xxx", "custom_theme": "可选的自定义主题"}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供请求数据"}), 400

    note_id = data.get('note_id', '')
    custom_theme = data.get('custom_theme', '')

    if not note_id:
        return jsonify({"error": "请提供帖子ID"}), 400

    # 获取原帖
    source_post = XHSDataProvider.get_post_detail(note_id)
    if not source_post:
        return jsonify({"error": "帖子不存在"}), 404

    # 执行仿写
    result = AIRewriteService.rewrite(source_post, custom_theme)

    return jsonify({
        "source_post": {
            "title": source_post.get("title"),
            "content": source_post.get("content"),
            "tags": source_post.get("tags"),
            "likes": source_post.get("likes"),
            "collects": source_post.get("collects"),
            "comments": source_post.get("comments"),
        },
        "rewritten": result
    })


@app.route('/api/hot-posts')
def hot_posts():
    """
    获取热门帖子（按点赞排序）
    GET /api/hot-posts?category=xxx&limit=20
    """
    category = request.args.get('category', '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)

    if USE_MOCK_DATA or not XHS_API_KEY:
        posts = MOCK_POSTS.copy()
        if category:
            posts = [p for p in posts if category in p.get("tags", []) or category in p.get("title", "")]
        posts.sort(key=lambda x: x["likes"], reverse=True)
        return jsonify({
            "total": len(posts[:limit]),
            "posts": posts[:limit],
            "data_source": "mock"
        })

    # 真实API调用
    try:
        headers = {"Authorization": f"Bearer {XHS_API_KEY}"}
        params = {"sort_by": "likes", "limit": limit}
        if category:
            params["category"] = category
        resp = requests.get(f"{XHS_API_BASE}/hot-notes", headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return jsonify({
                "total": data.get("total", 0),
                "posts": data.get("data", {}).get("notes", []),
                "data_source": "api"
            })
    except Exception as e:
        print(f"Hot Posts API Failed: {e}")

    return jsonify({"error": "获取热门帖子失败", "posts": []}), 500


@app.route('/api/config')
def get_config():
    """返回当前配置状态"""
    return jsonify({
        "use_mock_data": USE_MOCK_DATA or not XHS_API_KEY,
        "has_api_key": bool(XHS_API_KEY),
        "has_ai_key": bool(ANTHROPIC_API_KEY),
        "api_base": XHS_API_BASE if XHS_API_KEY else "(未配置)",
    })


# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("小红书热门帖子查询与仿写工具")
    print("XHS Hot Post Search & Rewrite Tool")
    print("=" * 60)
    print(f"数据源: {'Mock模拟数据' if USE_MOCK_DATA or not XHS_API_KEY else '真实API'}")
    print(f"AI仿写: {'Claude API' if ANTHROPIC_API_KEY else '模板引擎'}")
    print(f"访问地址: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
