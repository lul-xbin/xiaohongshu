/**
 * 小红书热门帖子查询与仿写工具 - Node.js 后端
 * 运行: node server.js
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 5000;

// ============================================================
// 读取 .env 文件
// ============================================================
function loadEnv() {
    const envPath = path.join(__dirname, '.env');
    try {
        const content = fs.readFileSync(envPath, 'utf-8');
        content.split('\n').forEach(line => {
            line = line.trim();
            if (!line || line.startsWith('#')) return;
            const eqIdx = line.indexOf('=');
            if (eqIdx === -1) return;
            const key = line.slice(0, eqIdx).trim();
            let value = line.slice(eqIdx + 1).trim();
            if ((value.startsWith('"') && value.endsWith('"')) ||
                (value.startsWith("'") && value.endsWith("'"))) {
                value = value.slice(1, -1);
            }
            if (!process.env[key]) process.env[key] = value;
        });
        console.log('  📄 已加载 .env 配置');
    } catch (e) { /* .env 不存在，使用环境变量 */ }
}
loadEnv();

// ============================================================
// 配置
// ============================================================
const SOCIALDATAX_API_KEY = process.env.SOCIALDATAX_API_KEY || '';
const SOCIALDATAX_MCP_URL = process.env.SOCIALDATAX_MCP_URL || 'https://mcp.52choujiang.com/xhs/mcp';
const USE_MOCK_DATA = process.env.USE_MOCK_DATA === 'false' ? false : true;

// ============================================================
// SocialDataX MCP 客户端
// ============================================================
class SocialDataXClient {
    constructor(apiKey, baseUrl) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }

    async _mcpRequest(method, params = null) {
        const url = new URL(this.baseUrl);
        const body = { jsonrpc: '2.0', method, id: Date.now() };
        if (params) body.params = params;

        return new Promise((resolve, reject) => {
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'Authorization': `Bearer ${this.apiKey}`
            };
            if (this.sessionId) headers['Mcp-Session-Id'] = this.sessionId;

            const req = https.request({
                hostname: url.hostname,
                port: url.port || 443,
                path: url.pathname,
                method: 'POST',
                headers,
                timeout: 30000
            }, (res) => {
                const sid = res.headers['mcp-session-id'];
                if (sid) this.sessionId = sid;

                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        // 解析 SSE 格式: "event: message\ndata: {...}\n\n"
                        let jsonStr = data;
                        if (data.startsWith('event:')) {
                            const dataMatch = data.match(/data:\s*(\{[\s\S]*\})/);
                            if (dataMatch) jsonStr = dataMatch[1];
                        }
                        const parsed = JSON.parse(jsonStr);
                        resolve({ status: res.statusCode, headers: res.headers, body: parsed });
                    } catch {
                        resolve({ status: res.statusCode, headers: res.headers, body: data });
                    }
                });
            });
            req.on('timeout', () => { req.destroy(); reject(new Error('MCP timeout')); });
            req.on('error', reject);
            req.write(JSON.stringify(body));
            req.end();
        });
    }

    async initialize() {
        console.log('  🔌 连接 SocialDataX MCP (' + this.baseUrl + ')...');
        const result = await this._mcpRequest('initialize', {
            protocolVersion: '2025-06-18',
            capabilities: {},
            clientInfo: { name: 'xhs-tool', version: '1.0.0' }
        });
        if (result.status === 200 && result.body.result) {
            const serverInfo = result.body.result.serverInfo || {};
            console.log('  ✅ 已连接: ' + (serverInfo.name || 'SocialDataX') + ' v' + (serverInfo.version || '?'));
            // 该 MCP 服务是无状态的，不需要 session ID
            if (this.sessionId) {
                await this._mcpRequest('notifications/initialized');
            }
            return true;
        }
        console.log('  ❌ MCP 初始化失败: HTTP ' + result.status + ' - ' + JSON.stringify(result.body).slice(0, 150));
        return false;
    }

    async callTool(toolName, args = {}) {
        const result = await this._mcpRequest('tools/call', { name: toolName, arguments: args });
        if (result.status === 200 && result.body.result) {
            // 检查是否有错误
            if (result.body.result.isError) {
                const errMsg = (result.body.result.structuredContent || {}).message ||
                               'Unknown MCP error';
                console.log(`  ⚠️ ${toolName} 错误: ${errMsg}`);
                throw new Error(errMsg);
            }
            const content = result.body.result.content || [];
            for (const item of content) {
                if (item.type === 'text') {
                    try { return JSON.parse(item.text); }
                    catch { return item.text; }
                }
            }
            return content;
        }
        console.log(`  ⚠️ ${toolName}: HTTP ${result.status}`);
        throw new Error(`MCP request failed: HTTP ${result.status}`);
    }

    async close() {
        if (this.sessionId) {
            await this._mcpRequest('close');
            this.sessionId = null;
        }
    }
}

// SocialDataX 客户端实例（延迟初始化）
let sdxClient = null;
async function getSdxClient() {
    if (!SOCIALDATAX_API_KEY) return null;
    if (sdxClient && sdxClient.sessionId) return sdxClient;

    sdxClient = new SocialDataXClient(SOCIALDATAX_API_KEY, SOCIALDATAX_MCP_URL);
    const ok = await sdxClient.initialize();
    return ok ? sdxClient : null;
}

// 将 SocialDataX 返回数据转为统一格式
function normalizeSdxNote(raw) {
    // SocialDataX 返回字段: note_id, note_url, title, summary/content, cover_image_url,
    // image_items, like_count, collect_count, comment_count, share_count, publish_time, author, topic_tags
    const author = raw.author || {};
    const images = [];
    if (raw.cover_image_url) images.push(raw.cover_image_url);
    if (raw.image_items) {
        raw.image_items.forEach(img => {
            if (img.image_url) images.push(img.image_url);
        });
    }

    // topic_tags 可能是 [{name: "标签名", id: "..."}] 或字符串数组
    const tags = (raw.topic_tags || []).map(t => typeof t === 'string' ? t : (t.name || ''));

    return {
        note_id: raw.note_id || '',
        title: raw.title || '',
        content: raw.content || raw.summary || '',
        likes: parseInt(raw.like_count || 0),
        collects: parseInt(raw.collect_count || 0),
        comments: parseInt(raw.comment_count || 0),
        shares: parseInt(raw.share_count || 0),
        images: images.length > 0 ? images : ['https://picsum.photos/seed/' + (raw.note_id || 'xhs') + '/400/400'],
        tags: tags,
        author: {
            name: author.name || '',
            avatar: author.avatar_url || '',
            followers: 0  // SocialDataX 搜索接口不返回粉丝数
        },
        url: raw.note_url || `https://www.xiaohongshu.com/explore/${raw.note_id}`,
        created_at: raw.publish_time ? new Date(raw.publish_time * 1000).toISOString() : new Date().toISOString()
    };
}

// ============================================================
// 模拟数据
// ============================================================
const MOCK_POSTS = [
    {
        note_id: "64a1b2c3d4e5f6g7h8i9j0k1",
        title: "打工人必看！5个让办公效率翻倍的隐藏技巧",
        content: "用了3年才发现这些功能，之前都在浪费时间！\n\n1️⃣ Windows虚拟桌面\n按Win+Tab可以创建多个桌面，工作一个、摸鱼一个，再也不怕老板突然出现 👀\n\n2️⃣ 剪贴板历史\nWin+V 打开剪贴板历史，之前复制的内容都能找回来！\n\n3️⃣ 分屏快捷键\nWin+方向键快速分屏，写文档查资料同时进行\n\n4️⃣ 截图工具\nWin+Shift+S 任意区域截图，不需要登录微信\n\n5️⃣ 搜索神器 Everything\n秒搜全盘文件，比Windows自带搜索快100倍\n\n收藏起来慢慢学，学会了记得回来感谢我～\n\n#办公技巧 #效率提升 #职场必备 #打工人",
        likes: 23500,
        collects: 18200,
        comments: 3256,
        shares: 8900,
        images: [
            "https://picsum.photos/seed/xhs1/800/800",
            "https://picsum.photos/seed/xhs2/800/800",
            "https://picsum.photos/seed/xhs3/800/800"
        ],
        tags: ["办公技巧", "效率提升", "职场必备", "打工人"],
        author: { name: "效率控小陈", avatar: "https://picsum.photos/seed/avatar1/100/100", followers: 52000 },
        url: "https://www.xiaohongshu.com/explore/64a1b2c3d4e5f6g7",
        created_at: "2025-06-15T10:30:00Z"
    },
    {
        note_id: "64b2c3d4e5f6g7h8i9j0k1l2",
        title: "自学Python三个月，我拿到了大厂offer｜学习路线分享",
        content: "非科班转码成功！分享一下我的自学路线 📚\n\n✅ 第一阶段（第1-2周）：Python基础\n- 变量、数据类型、条件判断、循环\n- 推荐：廖雪峰Python教程\n\n✅ 第二阶段（第3-4周）：进阶概念\n- 函数、类、模块、异常处理\n- 做个小项目：命令行待办清单\n\n✅ 第三阶段（第5-8周）：Web开发\n- Flask/Django框架\n- HTML/CSS基础\n- 数据库操作\n\n✅ 第四阶段（第9-12周）：项目实战\n- 搭建个人博客\n- 部署上线\n- 写进简历\n\n最重要的是坚持！每天至少写2小时代码，遇到问题先自己查再问人\n\n面试时面试官最看重的是你的学习能力和项目经验\n\n#编程入门 #Python学习 #转行IT #自学编程 #大厂上岸",
        likes: 42100,
        collects: 35600,
        comments: 5843,
        shares: 12300,
        images: [
            "https://picsum.photos/seed/xhs4/800/800",
            "https://picsum.photos/seed/xhs5/800/800"
        ],
        tags: ["编程入门", "Python学习", "转行IT", "自学编程", "大厂上岸"],
        author: { name: "码农小鹿", avatar: "https://picsum.photos/seed/avatar2/100/100", followers: 89000 },
        url: "https://www.xiaohongshu.com/explore/64b2c3d4e5f6g7h8",
        created_at: "2025-06-20T14:15:00Z"
    },
    {
        note_id: "64c3d4e5f6g7h8i9j0k1l2m3",
        title: "人均200吃到撑！上海这5家宝藏小店我藏不住了",
        content: "在上海吃了3年，这5家店是我反复去的，今天含泪分享 😭\n\n🍜 第一名：襄阳南路「老上海馄饨」\n人均35！鲜肉虾仁大馄饨，皮薄馅大，汤头是鸡骨熬的\n必点：虾仁鲜肉大馄饨 + 葱油拌面\n\n🍖 第二名：定西路「阿姐烧烤」\n人均80吃到扶墙走！羊肉串2块钱一串你敢信？\n必点：烤羊肉串、烤茄子、烤馒头\n\n🍛 第三名：进贤路「海强面馆」\n人均50，红烧牛肉面绝了！牛肉炖得软烂入味\n必点：红烧牛肉面、炸猪排\n\n🥟 第四名：黄河路「佳家汤包」\n人均60，皮薄汤多，一咬爆汁\n必点：蟹粉鲜肉汤包\n\n🍰 第五名：武康路「老麦咖啡馆」\n人均40，提拉米苏天花板！环境复古适合拍照\n\n建议收藏！周末可以一家一家打卡～\n\n#上海美食 #宝藏小店 #美食探店 #平价美食 #上海生活",
        likes: 38900,
        collects: 42100,
        comments: 6721,
        shares: 15600,
        images: [
            "https://picsum.photos/seed/xhs6/800/800",
            "https://picsum.photos/seed/xhs7/800/800",
            "https://picsum.photos/seed/xhs8/800/800",
            "https://picsum.photos/seed/xhs9/800/800"
        ],
        tags: ["上海美食", "宝藏小店", "美食探店", "平价美食", "上海生活"],
        author: { name: "吃货小圆子", avatar: "https://picsum.photos/seed/avatar3/100/100", followers: 156000 },
        url: "https://www.xiaohongshu.com/explore/64c3d4e5f6g7h8i9",
        created_at: "2025-06-25T09:00:00Z"
    },
    {
        note_id: "64d4e5f6g7h8i9j0k1l2m3n4",
        title: "iPhone隐藏功能大盘点！用了5年我才知道这些",
        content: "苹果手机这些功能你不用就亏大了！\n\n📱 1. 背面敲击截图\n设置→辅助功能→触控→背面轻点\n敲两下截屏，敲三下打开相机\n\n📱 2. 扫描文档\n备忘录→相机→扫描文稿\n自动识别边缘，比扫描仪还清晰\n\n📱 3. 科学计算器\n把手机横过来，计算器秒变科学计算器\n\n📱 4. 隐藏照片\n选择照片→分享→隐藏\n在相册-已隐藏里查看（iOS16后支持FaceID锁定）\n\n📱 5. 自定义控制中心\n设置→控制中心→添加常用功能\n一键录屏、扫二维码超方便\n\n📱 6. 专注模式\n设置→专注模式→自定义场景\n工作模式自动屏蔽娱乐APP通知\n\n📱 7. Safari长截图\n截图→点击缩略图→选择「整页」\n\n你学废了吗？还有什么隐藏功能欢迎补充 👇\n\n#iPhone技巧 #苹果手机 #隐藏功能 #手机技巧",
        likes: 56700,
        collects: 48900,
        comments: 8934,
        shares: 21300,
        images: [
            "https://picsum.photos/seed/xhs10/800/800",
            "https://picsum.photos/seed/xhs11/800/800",
            "https://picsum.photos/seed/xhs12/800/800"
        ],
        tags: ["iPhone技巧", "苹果手机", "隐藏功能", "手机技巧"],
        author: { name: "数码小达人", avatar: "https://picsum.photos/seed/avatar4/100/100", followers: 203000 },
        url: "https://www.xiaohongshu.com/explore/64d4e5f6g7h8i9j0",
        created_at: "2025-06-28T16:45:00Z"
    },
    {
        note_id: "64e5f6g7h8i9j0k1l2m3n4o5",
        title: "跟着博主学穿搭｜基础款穿出高级感的5个秘诀",
        content: "不买新衣服也能穿出高级感！学会这5招就够了 ✨\n\n👗 秘诀一：同色系搭配\n全身上下不超过3个颜色，同色系不同深浅最显高级\n推荐：米白+卡其+棕色系\n\n👗 秘诀二：注重面料质感\n宁愿买一件好的，不买十件差的\n棉麻、羊毛、真丝面料自带高级感\n\n👗 秘诀三：配饰是点睛之笔\n一条简约项链、一只质感手表\n细节决定品味\n\n👗 秘诀四：合身比品牌重要\n过大或过小都显廉价\n找对适合自己的版型是关键\n\n👗 秘诀五：保持衣物整洁\n熨烫平整的衣服看起来贵10倍\n常备粘毛器，出门前检查\n\n适合25-35岁职场女性的通勤穿搭\n\n#穿搭技巧 #高级感穿搭 #基础款搭配 #职场穿搭 #胶囊衣橱",
        likes: 34500,
        collects: 29800,
        comments: 4521,
        shares: 11200,
        images: [
            "https://picsum.photos/seed/xhs13/800/800",
            "https://picsum.photos/seed/xhs14/800/800",
            "https://picsum.photos/seed/xhs15/800/800"
        ],
        tags: ["穿搭技巧", "高级感穿搭", "基础款搭配", "职场穿搭", "胶囊衣橱"],
        author: { name: "穿搭师Mia", avatar: "https://picsum.photos/seed/avatar5/100/100", followers: 278000 },
        url: "https://www.xiaohongshu.com/explore/64e5f6g7h8i9j0k1",
        created_at: "2025-07-01T11:20:00Z"
    },
    {
        note_id: "64f6g7h8i9j0k1l2m3n4o5p6",
        title: "30天减脂餐食谱合集｜健康瘦了12斤的真实记录",
        content: "不节食不吃药，靠吃瘦了12斤！把我的减脂餐分享给你们 🥗\n\n📋 我的减脂原则：\n- 每天热量控制在1400-1600大卡\n- 碳水:蛋白质:脂肪 = 4:3:3\n- 16+8轻断食（只在8小时内进食）\n- 每周一天欺骗日\n\n🍳 早餐（400卡）：\n周一三五：全麦面包+鸡蛋+牛奶+苹果\n周二四六：燕麦粥+坚果+蓝莓\n周日：想吃什么吃什么\n\n🥩 午餐（500卡）：\n杂粮饭半碗 + 鸡胸肉/鱼肉/虾 + 蔬菜\n蔬菜不限量，吃到饱\n\n🥬 晚餐（400卡）：\n蔬菜沙拉+豆腐/鸡蛋+少量紫薯/南瓜\n8点前吃完\n\n🍎 加餐（200卡）：\n下午3-4点：一根香蕉或一小把坚果\n\n⚠️ 重点：\n- 每天喝够2L水\n- 睡够7小时\n- 每周运动3-4次（30分钟有氧+20分钟力量）\n\n一个月下来不仅瘦了，皮肤也变好了！\n\n#减脂餐 #减肥食谱 #健康瘦身 #一个月瘦12斤 #自律生活",
        likes: 78200,
        collects: 67200,
        comments: 12580,
        shares: 28900,
        images: [
            "https://picsum.photos/seed/xhs16/800/800",
            "https://picsum.photos/seed/xhs17/800/800",
            "https://picsum.photos/seed/xhs18/800/800",
            "https://picsum.photos/seed/xhs19/800/800"
        ],
        tags: ["减脂餐", "减肥食谱", "健康瘦身", "一个月瘦12斤", "自律生活"],
        author: { name: "健身女孩Lily", avatar: "https://picsum.photos/seed/avatar6/100/100", followers: 345000 },
        url: "https://www.xiaohongshu.com/explore/64f6g7h8i9j0k1l2",
        created_at: "2025-07-02T07:30:00Z"
    }
];

// ============================================================
// MIME类型
// ============================================================
const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

// ============================================================
// 服务静态文件
// ============================================================
function serveStatic(filePath, res) {
    const fullPath = path.join(__dirname, filePath);
    try {
        const data = fs.readFileSync(fullPath);
        const ext = path.extname(fullPath).toLowerCase();
        res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
        res.end(data);
    } catch (err) {
        res.writeHead(404);
        res.end('Not Found');
    }
}

// ============================================================
// JSON 响应
// ============================================================
function jsonResponse(res, data, status = 200) {
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(data, null, 2));
}

// ============================================================
// 解析请求体
// ============================================================
function parseBody(req) {
    return new Promise((resolve) => {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try { resolve(JSON.parse(body)); }
            catch { resolve({}); }
        });
    });
}

// ============================================================
// 解析查询参数
// ============================================================
function parseQuery(url) {
    const q = {};
    const queryStr = url.split('?')[1];
    if (!queryStr) return q;
    queryStr.split('&').forEach(pair => {
        const [k, v] = pair.split('=');
        q[decodeURIComponent(k)] = decodeURIComponent(v || '');
    });
    return q;
}

// ============================================================
// 搜索逻辑
// ============================================================
function searchMockPosts(keyword, sortBy = 'likes', limit = 20) {
    const kw = keyword.toLowerCase();
    const results = [];

    for (const post of MOCK_POSTS) {
        let score = 0;
        if (post.title.toLowerCase().includes(kw)) score += 10;
        if (post.content.toLowerCase().includes(kw)) score += 5;
        for (const tag of post.tags) {
            if (tag.toLowerCase().includes(kw)) score += 8;
        }
        if (score > 0) {
            results.push({ ...post, relevance_score: score });
        }
    }

    // 排序
    if (sortBy === 'likes') results.sort((a, b) => b.likes - a.likes);
    else if (sortBy === 'collects') results.sort((a, b) => b.collects - a.collects);
    else if (sortBy === 'comments') results.sort((a, b) => b.comments - a.comments);
    else if (sortBy === 'relevance') results.sort((a, b) => b.relevance_score - a.relevance_score);

    return results.slice(0, Math.min(limit, 50));
}

async function searchRealPosts(keyword, sortBy = 'likes', limit = 20) {
    const client = await getSdxClient();
    if (!client) throw new Error('SocialDataX MCP 连接失败');

    const sortMap = {
        'likes': 'like_count_descending',
        'collects': 'collect_count_descending',
        'comments': 'comment_count_descending',
        'relevance': 'general'
    };

    const raw = await client.callTool('xhs_search_notes', {
        keyword: keyword,
        sort_type: sortMap[sortBy] || 'general',
        note_type: 'all'
    });

    if (!raw) return [];
    const notes = Array.isArray(raw) ? raw : (raw.notes || raw.data || raw.items || []);
    return notes.map(normalizeSdxNote);
}

async function getRealPostDetail(noteId) {
    const client = await getSdxClient();
    if (!client) throw new Error('SocialDataX MCP 连接失败');

    const raw = await client.callTool('xhs_get_note_detail_by_note_id', { note_id: noteId });
    if (!raw) return null;

    // 可能返回单个对象或包装在 data/note 字段中
    const note = raw.note || raw.data || raw;
    return normalizeSdxNote(note);
}

// ============================================================
// 路由处理
// ============================================================
async function handleRequest(req, res) {
    const url = req.url;
    const method = req.method;
    const parsedUrl = url.split('?')[0];

    // 主页
    if (method === 'GET' && (parsedUrl === '/' || parsedUrl === '/index.html')) {
        const html = fs.readFileSync(path.join(__dirname, 'templates', 'index.html'), 'utf-8');
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(html);
        return;
    }

    // 静态资源
    if (method === 'GET' && (parsedUrl.startsWith('/static/'))) {
        serveStatic(parsedUrl, res);
        return;
    }

    // 健康检查（部署平台需要）
    if (method === 'GET' && (parsedUrl === '/health' || parsedUrl === '/api/health')) {
        jsonResponse(res, { status: 'ok', uptime: process.uptime(), timestamp: new Date().toISOString() });
        return;
    }

    // API: 获取配置
    if (method === 'GET' && parsedUrl === '/api/config') {
        jsonResponse(res, {
            use_mock_data: USE_MOCK_DATA || !SOCIALDATAX_API_KEY,
            has_api_key: !!SOCIALDATAX_API_KEY,
            api_base: SOCIALDATAX_API_KEY ? SOCIALDATAX_MCP_URL : '(未配置)'
        });
        return;
    }

    // API: 搜索
    if (method === 'GET' && parsedUrl === '/api/search') {
        const q = parseQuery(url);
        const keyword = (q.keyword || '').trim();
        if (!keyword) { jsonResponse(res, { error: '请输入搜索关键词', posts: [] }, 400); return; }
        const sortBy = q.sort_by || 'likes';
        const limit = Math.min(parseInt(q.limit) || 20, 50);

        let posts, dataSource, apiError = null;
        if (!USE_MOCK_DATA && SOCIALDATAX_API_KEY) {
            try {
                posts = await searchRealPosts(keyword, sortBy, limit);
                dataSource = 'socialdatax';
            } catch (err) {
                console.log('  ⚠️ SocialDataX 搜索失败，回退到 Mock:', err.message);
                apiError = err.message;
                posts = searchMockPosts(keyword, sortBy, limit);
                dataSource = 'mock_fallback';
            }
        } else {
            posts = searchMockPosts(keyword, sortBy, limit);
            dataSource = 'mock';
        }

        jsonResponse(res, { keyword, total: posts.length, sort_by: sortBy, posts, data_source: dataSource, api_error: apiError });
        return;
    }

    // API: 帖子详情
    if (method === 'GET' && parsedUrl.startsWith('/api/post/')) {
        const noteId = parsedUrl.replace('/api/post/', '');
        let post;

        if (!USE_MOCK_DATA && SOCIALDATAX_API_KEY) {
            try {
                post = await getRealPostDetail(noteId);
            } catch (err) {
                console.log('  ⚠️ SocialDataX 详情获取失败，回退到 Mock:', err.message);
            }
        }
        if (!post) {
            post = MOCK_POSTS.find(p => p.note_id === noteId);
        }
        if (!post) { jsonResponse(res, { error: '帖子不存在' }, 404); return; }
        jsonResponse(res, { post });
        return;
    }

    // API: 热门帖子
    if (method === 'GET' && parsedUrl === '/api/hot-posts') {
        const q = parseQuery(url);
        const category = (q.category || '').trim();
        const limit = Math.min(parseInt(q.limit) || 20, 50);

        let posts, dataSource;
        if (!USE_MOCK_DATA && SOCIALDATAX_API_KEY) {
            try {
                // xhs_get_search_hot_list 返回热搜关键词，不是帖子
                // 用热门关键词搜索来获取热门帖子
                const client = await getSdxClient();
                if (client) {
                    const hotList = await client.callTool('xhs_get_search_hot_list', {});
                    if (hotList && hotList.items && hotList.items.length > 0) {
                        // 用前3个热搜词搜索帖子
                        const topKeyword = hotList.items[0].title;
                        const raw = await client.callTool('xhs_search_notes', {
                            keyword: category || topKeyword,
                            sort_type: 'like_count_descending',
                            note_type: 'all'
                        });
                        if (raw) {
                            const notes = Array.isArray(raw) ? raw : (raw.items || raw.notes || []);
                            posts = notes.map(normalizeSdxNote);
                            dataSource = 'socialdatax';
                        }
                    }
                }
            } catch (err) {
                console.log('  ⚠️ SocialDataX 热榜获取失败:', err.message);
            }
        }

        if (!posts) {
            posts = [...MOCK_POSTS];
            if (category) {
                posts = posts.filter(p =>
                    p.tags.some(t => t.includes(category)) ||
                    p.title.includes(category)
                );
            }
            posts.sort((a, b) => b.likes - a.likes);
            posts = posts.slice(0, limit);
            dataSource = 'mock';
        }

        jsonResponse(res, { total: posts.length, posts, data_source: dataSource });
        return;
    }

    // 404
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not Found');
}

// ============================================================
// 启动服务器
// ============================================================
const server = http.createServer(handleRequest);
server.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log('  🔥 小红书热门帖子查询工具');
    console.log('  📡 数据源: ' + ((SOCIALDATAX_API_KEY && !USE_MOCK_DATA) ? 'SocialDataX 真实API' : 'Mock模拟数据'));
    console.log(`  🌐 访问: http://localhost:${PORT}`);
    console.log('='.repeat(60));
    console.log('  按 Ctrl+C 停止服务器');
});
