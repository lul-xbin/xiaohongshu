/**
 * 小红书热门帖子查询 & AI仿写工具 - 前端逻辑
 */

// ============================================================
// 全局状态
// ============================================================
const state = {
    currentTab: 'search',
    searchResults: [],
    hotPosts: [],
    config: { use_mock_data: true, has_api_key: false, has_ai_key: false }
};

// ============================================================
// DOM 引用
// ============================================================
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

// ============================================================
// 工具函数
// ============================================================
function formatNumber(n) {
    if (!n) return '0';
    if (n >= 10000) return (n / 10000).toFixed(1) + '万';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
}

function timeAgo(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days > 30) return Math.floor(days / 30) + '个月前';
    if (days > 0) return days + '天前';
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours > 0) return hours + '小时前';
    return '刚刚';
}

function truncate(str, len = 100) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '...' : str;
}

async function apiGet(url) {
    const resp = await fetch(url);
    return resp.json();
}

async function apiPost(url, data) {
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return resp.json();
}

function showToast(message, type = 'info') {
    const container = $('#toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ============================================================
// 标签页切换
// ============================================================
function switchTab(tab) {
    state.currentTab = tab;
    $$('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));

    $('#panel-search').style.display = tab === 'search' ? 'block' : 'none';
    $('#panel-hot').style.display = tab === 'hot' ? 'block' : 'none';

    if (tab === 'hot') loadHotPosts();
}

// ============================================================
// 搜索功能
// ============================================================
async function doSearch() {
    const keyword = $('#searchInput').value.trim();
    if (!keyword) { showToast('请输入搜索关键词', 'error'); return; }

    const sortBy = $('#sortBy').value;
    const btn = $('#searchBtn');
    const btnText = $('.btn-text', btn);
    const btnLoading = $('.btn-loading', btn);

    // 显示加载状态
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline-flex';
    $('#resultsArea').style.display = 'none';
    $('#loadingArea').style.display = 'block';

    try {
        const data = await apiGet(`/api/search?keyword=${encodeURIComponent(keyword)}&sort_by=${sortBy}&limit=30`);
        state.searchResults = data.posts || [];

        if (data.error) showToast(data.error, 'error');

        $('#resultsTitle').textContent = `「${data.keyword}」的搜索结果`;
        $('#resultsCount').textContent = `共 ${data.total} 条`;
        renderPosts(state.searchResults, $('#postsGrid'));

        $('#loadingArea').style.display = 'none';
        $('#resultsArea').style.display = 'block';
        $('#resultsEmpty').style.display = state.searchResults.length === 0 ? 'block' : 'none';

        if (data.data_source === 'mock_fallback') {
            showToast('⚠️ API积分不足，已自动切换到演示数据。充值后可恢复真实搜索：socialdatax.com', 'warning');
        } else if (data.data_source === 'mock') {
            showToast('当前使用模拟数据演示，配置API Key后可获取真实数据', 'info');
        }
    } catch (err) {
        console.error('Search failed:', err);
        showToast('搜索失败，请检查网络连接', 'error');
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
        $('#loadingArea').style.display = 'none';
    }
}

// ============================================================
// 渲染帖子卡片
// ============================================================
function renderPosts(posts, container) {
    if (!posts || posts.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = posts.map((post, idx) => {
        const firstImage = (post.images && post.images[0]) ? post.images[0] : 'https://picsum.photos/seed/default/400/400';
        const rank = idx < 3 ? ['🥇', '🥈', '🥉'][idx] : null;

        return `
        <article class="post-card" data-note-id="${post.note_id}" onclick="openPostDetail('${post.note_id}')">
            <div class="post-card-header">
                <img src="${firstImage}" alt="${post.title}" loading="lazy" onerror="this.src='https://picsum.photos/seed/fallback${idx}/400/400'">
                ${rank ? `<div class="post-card-badge">${rank} 热门</div>` : ''}
            </div>
            <div class="post-card-body">
                <h3 class="post-card-title">${post.title}</h3>
                <p class="post-card-excerpt">${truncate(post.content, 120)}</p>
                <div class="post-card-tags">
                    ${(post.tags || []).slice(0, 3).map(t => `<span class="post-card-tag">#${t}</span>`).join('')}
                </div>
            </div>
            <div class="post-card-footer">
                <div class="post-card-author">
                    ${post.author ? `
                        <img src="${post.author.avatar}" alt="" onerror="this.style.display='none'">
                        <span>${post.author.name}</span>
                    ` : ''}
                </div>
                <div class="post-card-stats">
                    <span class="post-card-stat">👍 ${formatNumber(post.likes)}</span>
                    <span class="post-card-stat">⭐ ${formatNumber(post.collects)}</span>
                    <span class="post-card-stat">💬 ${formatNumber(post.comments)}</span>
                </div>
            </div>
        </article>`;
    }).join('');
}

// ============================================================
// 帖子详情弹窗
// ============================================================
async function openPostDetail(noteId) {
    const overlay = $('#modalOverlay');
    const body = $('#modalBody');

    overlay.style.display = 'flex';
    body.innerHTML = '<div class="loading-area"><div class="loading-spinner"></div><p>加载中...</p></div>';

    try {
        const data = await apiGet(`/api/post/${noteId}`);
        const post = data.post;

        if (!post) {
            body.innerHTML = '<p style="text-align:center;padding:48px;">帖子不存在</p>';
            return;
        }

        body.innerHTML = `
            ${post.images ? `
            <div class="detail-images">
                ${post.images.map(img => `<img src="${img}" alt="" loading="lazy" onerror="this.style.display='none'">`).join('')}
            </div>` : ''}
            <h2 class="detail-title">${post.title}</h2>
            <div class="detail-author">
                ${post.author ? `
                    <img src="${post.author.avatar}" alt="">
                    <div class="detail-author-info">
                        <div class="name">${post.author.name}</div>
                        <div class="followers">${formatNumber(post.author.followers)} 粉丝</div>
                    </div>
                ` : ''}
            </div>
            <div class="detail-content">${post.content}</div>
            <div class="detail-tags">
                ${(post.tags || []).map(t => `<span class="detail-tag">#${t}</span>`).join('')}
            </div>
            <div class="detail-stats">
                <div class="detail-stat">👍 <span class="detail-stat-value">${formatNumber(post.likes)}</span> 点赞</div>
                <div class="detail-stat">⭐ <span class="detail-stat-value">${formatNumber(post.collects)}</span> 收藏</div>
                <div class="detail-stat">💬 <span class="detail-stat-value">${formatNumber(post.comments)}</span> 评论</div>
                <div class="detail-stat">🔄 <span class="detail-stat-value">${formatNumber(post.shares)}</span> 分享</div>
            </div>
            <div style="display:flex;gap:8px;">
                <button class="btn btn-outline" onclick="window.open('${post.url || '#'}', '_blank')">
                    🔗 查看原文
                </button>
            </div>
        `;
    } catch (err) {
        body.innerHTML = '<p style="text-align:center;padding:48px;">加载失败</p>';
    }
}

function closeModal() {
    $('#modalOverlay').style.display = 'none';
}

// ============================================================
// 热门榜单
// ============================================================
async function loadHotPosts() {
    $('#hotPostsGrid').innerHTML = '';
    $('#hotLoadingArea').style.display = 'block';

    const category = $('#hotCategory') ? $('#hotCategory').value : '';

    try {
        const data = await apiGet(`/api/hot-posts?category=${encodeURIComponent(category)}&limit=30`);
        state.hotPosts = data.posts || [];
        renderPosts(state.hotPosts, $('#hotPostsGrid'));
    } catch (err) {
        showToast('加载热门榜单失败', 'error');
    } finally {
        $('#hotLoadingArea').style.display = 'none';
    }
}

// ============================================================
// 加载配置
// ============================================================
async function loadConfig() {
    try {
        const data = await apiGet('/api/config');
        state.config = data;
        const statusDot = $('.status-dot', $('#headerStatus'));
        const statusText = $('.status-text', $('#headerStatus'));

        if (data.has_api_key) {
            statusDot.className = 'status-dot live';
            statusText.textContent = 'API已连接';
        } else {
            statusDot.className = 'status-dot mock';
            statusText.textContent = '演示模式';
        }
    } catch (err) {
        console.error('Failed to load config:', err);
    }
}

// ============================================================
// 事件绑定
// ============================================================
function init() {
    // 标签页切换
    $$('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // 搜索
    $('#searchInput').addEventListener('keydown', e => {
        if (e.key === 'Enter') doSearch();
        // 显示/隐藏清除按钮
        const clearBtn = $('#searchClear');
        if ($('#searchInput').value.trim()) {
            clearBtn.classList.add('visible');
        } else {
            clearBtn.classList.remove('visible');
        }
    });

    $('#searchInput').addEventListener('input', () => {
        const clearBtn = $('#searchClear');
        clearBtn.classList.toggle('visible', $('#searchInput').value.trim().length > 0);
    });

    $('#searchClear').addEventListener('click', () => {
        $('#searchInput').value = '';
        $('#searchClear').classList.remove('visible');
        $('#searchInput').focus();
    });

    $('#searchBtn').addEventListener('click', doSearch);

    // 快捷标签
    $$('.quick-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            $('#searchInput').value = tag.dataset.keyword;
            $('#searchClear').classList.add('visible');
            doSearch();
        });
    });

    // 排序切换自动搜索（如果已有结果）
    $('#sortBy').addEventListener('change', () => {
        if ($('#searchInput').value.trim()) doSearch();
    });

    // 热门榜单
    $('#hotRefreshBtn').addEventListener('click', loadHotPosts);
    if ($('#hotCategory')) {
        $('#hotCategory').addEventListener('change', loadHotPosts);
    }

    // 模态框
    $('#modalClose').addEventListener('click', closeModal);
    $('#modalOverlay').addEventListener('click', e => {
        if (e.target === $('#modalOverlay')) closeModal();
    });

    // 键盘关闭模态框
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeModal();
    });

    // 加载配置
    loadConfig();
}

// 启动
document.addEventListener('DOMContentLoaded', init);
