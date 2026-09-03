const state = {
  page: 'home',
  task: null,
  taskId: null,
  workspaceTab: 'overview',
  dashboardDimension: '',
  dashboardSearch: '',
  selectedEvidence: null,
  analysisHistory: [],
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));
const date = (value) => value ? String(value).slice(0, 10) : '—';
const money = (value) => value == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value));
const moneyPrecise = (value) => value == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value));
const number = (value) => value == null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(Number(value));
const pct = (value) => value == null ? '—' : `${Number(value).toFixed(1)}%`;
const stateClass = (value) => String(value || '').toLowerCase().replaceAll('_', '-');
const statusLabels = { READY: '数据就绪', COMPLETED: '已完成', PARTIAL: '部分完成', FAILED: '失败', CANCELLED: '已取消', ABSTAINED: '暂不支持', NOT_AVAILABLE: '暂不可用', PROPOSED: '待验证', TESTING: '验证中', SUPPORTED: '已支持', REJECTED: '已排除', INCONCLUSIVE: '尚无结论', VERIFIED: '已验证', QUALIFIED: '有条件支持', FACT: '事实', INFERENCE: '推断', RECOMMENDATION: '建议', SUPPORTS: '支持', MEASURED: '已测量', NOT_MEASURED: '未测量', CASES_LOADED_NOT_RUN: '未运行' };
const copyLabels = { 'State wholesale purchase/order amount; not consumer POS revenue.': '州级批发采购 / 订单金额，不是消费者 POS 收入。', 'Bottles on wholesale orders; not consumer units sold.': '批发订单中的瓶数，不是消费者实际购买量。', 'Volume represented by wholesale orders.': '批发订单所代表的容量。', 'Composite wholesale price per ordered bottle; mix-sensitive.': '每个订购瓶的综合批发价，受产品组合影响。', 'Transaction-level state acquisition cost estimate.': '交易级州采购成本估算。', 'Wholesale spread only; not store profit or net profit.': '仅代表批发价差，不是门店利润或净利润。', 'Wholesale spread divided by wholesale sales.': '批发价差除以批发销售额。' };
const uiLabel = (value) => statusLabels[value] || value || '—';
const uiText = (value) => copyLabels[value] || String(value ?? '—').replaceAll('onward', '起');
const unitLabel = (value) => ({ USD: '美元', bottles: '瓶', liters: '升', 'USD / bottle': '美元 / 瓶', '%': '%' }[value] || value || '—');

async function api(path, options) {
  const response = await fetch(`/api/v1${path}`, options);
  if (!response.ok) throw Error(await response.text() || `Request failed: ${response.status}`);
  return response.json();
}

function setTitle(title) {
  $('#page-title').textContent = title;
  $$('#nav button').forEach((button) => button.classList.toggle('active', button.dataset.page === state.page));
  const task = state.task;
  $('#mobile-task-context').textContent = task && state.page === 'workspace' ? `任务 ${task.task_id.slice(0, 8)} · ${task.resolved_context?.dataset_snapshot || '数据集待解析'}` : '';
}

function loading(label = '正在加载工作区…') {
  return `<div class="loading-shell"><div class="skeleton wide"></div><div class="skeleton medium"></div><div class="panel empty"><span class="spinner"></span>${esc(label)}</div><div class="skeleton large"></div></div>`;
}

function errorView(errorObject) {
  const message = errorObject?.message || String(errorObject || '未知错误');
  return `<div class="state-panel error-state"><div class="state-icon">!</div><h3>暂时无法加载</h3><p>${esc(message)}</p><button class="button secondary" onclick="navigate(state.page)">重试</button></div>`;
}

function emptyView(title, description, action = '') {
  return `<div class="empty"><strong>${esc(title)}</strong><p>${esc(description)}</p>${action}</div>`;
}

function badge(value, extra = '') {
  return `<span class="pill ${stateClass(value)} ${extra}">${esc(uiLabel(value || 'NOT_AVAILABLE'))}</span>`;
}

function metricKpi(label, data, formatter = money, unit = 'USD') {
  if (!data) return `<div class="panel kpi"><div class="label">${esc(label)}</div><div class="value">—</div><div class="change muted">后端未返回该指标</div></div>`;
  const delta = Number(data.delta || 0);
  const direction = delta >= 0 ? 'up' : 'down';
  return `<div class="panel kpi clickable" onclick="openMetricEvidence('${esc(label)}')"><div class="metric-card"><div><div class="label">${esc(label)}</div><div class="value">${formatter(data.current)}</div></div><div class="metric-icon">↗</div></div><div class="change ${direction}">${delta >= 0 ? '▲' : '▼'} ${formatter(Math.abs(delta))} · ${pct(Math.abs(data.change_pct))}</div><div class="period">当前周期 vs 对比周期 · ${esc(unitLabel(unit))}</div></div>`;
}

function trustStrip(dataset) {
  const status = dataset?.status || 'NOT_AVAILABLE';
  return `<div class="panel trust-strip"><div class="trust-item"><div class="trust-label">数据集状态</div><div class="trust-value ${status === 'READY' ? 'good' : 'warn'}">${esc(uiLabel(status))}</div><div class="trust-sub">${esc(dataset?.snapshot_id || '未连接快照')}</div></div><div class="trust-item"><div class="trust-label">业务日期覆盖</div><div class="trust-value">${date(dataset?.business_date_min)} — ${date(dataset?.business_date_max)}</div><div class="trust-sub">截至日来自快照</div></div><div class="trust-item"><div class="trust-label">已测行数</div><div class="trust-value">${number(dataset?.measured_row_count)}</div><div class="trust-sub">非估算值</div></div><div class="trust-item"><div class="trust-label">数据新鲜度</div><div class="trust-value">${date(dataset?.validated_at)}</div><div class="trust-sub">最近验证</div></div><div class="trust-item"><div class="trust-label">运行模式</div><div class="trust-value">确定性</div><div class="trust-sub">本地只读参考环境</div></div></div>`;
}

function recentRows(items, withActions = false) {
  if (!items?.length) return emptyView('还没有分析任务', '从一个业务问题开始，系统会先解析上下文，再执行受治理的分析。', '<button class="button" onclick="navigate(\'new\')">发起分析</button>');
  return items.map((task) => `<div class="analysis-row" onclick="openTask('${esc(task.task_id)}')"><div class="row-main"><div class="row-title">${esc(task.business_question)}</div><div class="row-meta">${date(task.updated_at || task.created_at)} · ${esc(task.resolved_context?.dataset_snapshot || '上下文待解析')} · ${esc(task.task_id.slice(0, 8))}</div></div><div class="row-end">${badge(task.state)}${withActions ? `<button class="icon-button row-action" onclick="event.stopPropagation();openTask('${esc(task.task_id)}')" aria-label="打开任务">→</button>` : ''}</div></div>`).join('');
}

async function home() {
  setTitle('首页');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/home');
    state.analysisHistory = data.recent_analyses || [];
    const dataset = data.dataset || {};
    $('#data-badge').textContent = dataset.available ? '数据就绪' : '数据不可用';
    $('#app').innerHTML = homeMarkup(data);
    const availability = (data.metrics || []).find((metric) => metric.label === 'Wholesale gross spread')?.availability;
    const availabilityNode = $('.window-grid div:nth-child(4) strong');
    if (availabilityNode) availabilityNode.textContent = availability || '后端未返回';
    return;
    $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">TODAY · IOWA LIQUOR WHOLESALE</span><h2>把业务问题变成可追溯的结论。</h2><p>从自然语言问题开始，沿着上下文、计划、证据和报告完成一次完整分析。</p></div><button class="button" onclick="navigate('new')">＋ 发起新分析</button></div>${trustStrip(dataset)}<div class="panel hero-question"><div class="question-box"><span class="eyebrow">START WITH A QUESTION</span><h2>你想理解什么？</h2><p>使用业务语言提问，系统会先展示解析后的指标、精确日期和维度。</p><div class="question-form"><textarea id="home-question" rows="2" placeholder="例如：比较 2026 年 7 月和 6 月的批发销售额，找出主要供应商贡献"></textarea><button class="button" onclick="submitHomeQuestion()">开始分析 →</button></div><div class="suggestion-chips">${(data.suggestions || []).slice(0, 4).map((item) => `<button class="chip" onclick="fillQuestion('${esc(item)}')">${esc(item)}</button>`).join('')}</div></div><div class="recommended"><div class="eyebrow">建议的探索</div><div class="suggestion-row" onclick="fillQuestion('比较 2026 年 7 月和 6 月的批发销售额')"><span class="suggestion-icon">↗</span><span class="suggestion-text">比较月度表现并定位变化</span><span>→</span></div><div class="suggestion-row" onclick="fillQuestion('哪些供应商对变化贡献最大？')"><span class="suggestion-icon">⌁</span><span class="suggestion-text">找出最大贡献者</span><span>→</span></div><div class="suggestion-row" onclick="fillQuestion('解释价格、数量和产品组合变化')"><span class="suggestion-icon">◌</span><span class="suggestion-text">拆解价格 / 数量 / 组合</span><span>→</span></div><div class="suggestion-row disabled-row"><span class="suggestion-icon">—</span><span class="suggestion-text">消费者利润分析</span><span class="unavailable">不支持</span></div></div></div><div class="section-head"><div><span class="eyebrow">MEASURED SNAPSHOT</span><h3>工作区脉搏</h3></div><span class="muted">${esc(dataset.snapshot_id || '快照不可用')}</span></div><div class="grid grid-4"><div class="panel kpi"><div class="label">数据截至</div><div class="value" style="font-size:20px">${date(dataset.business_date_max)}</div><div class="change muted">${esc(dataset.status || 'NOT AVAILABLE')}</div></div><div class="panel kpi"><div class="label">快照行数</div><div class="value">${number(dataset.measured_row_count)}</div><div class="change muted">已测量，不是估算</div></div><div class="panel kpi"><div class="label">已完成分析</div><div class="value">${number((data.recent_analyses || []).filter((item) => item.state === 'COMPLETED').length)}</div><div class="change muted">当前本地工作区</div></div><div class="panel kpi"><div class="label">成本 / spread 可用</div><div class="value" style="font-size:20px">2025-07 起</div><div class="change muted">之前周期显示不可用</div></div></div><div class="content-grid two-col"><div><div class="section-head"><div><span class="eyebrow">RECOMMENDED</span><h3>建议分析</h3></div></div><div class="suggestion-list">${(data.suggestions || []).map((item, index) => `<button class="suggestion-card" onclick="fillQuestion('${esc(item)}')"><span class="suggestion-number">0${index + 1}</span><span><strong>${esc(item)}</strong><small>结构化计划 · 证据链 · 报告</small></span><span class="arrow">→</span></button>`).join('')}</div></div><div><div class="section-head"><div><span class="eyebrow">RECENT</span><h3>最近分析</h3></div><button class="button ghost" onclick="navigate('history')">查看全部 →</button></div><div class="panel"><div class="analysis-list">${recentRows(data.recent_analyses, true)}</div></div></div></div><div class="section-head"><div><span class="eyebrow">LIMITATIONS</span><h3>数据质量与使用边界</h3></div><button class="button ghost" onclick="navigate('data')">查看数据状态 →</button></div><div class="panel limitation-grid"><div><span class="status-mark good">✓</span><strong>来源可追溯</strong><p>来源资产、快照、哈希和验证状态都来自数据清单。</p></div><div><span class="status-mark warn">!</span><strong>这是批发订单</strong><p>不代表消费者 POS 销售，也不等同于门店利润。</p></div><div><span class="status-mark info">i</span><strong>贡献不是因果</strong><p>贡献分析描述观测关联，不证明业务因果关系。</p></div></div>`;
  } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

function homeMarkup(data) {
  return homeReferenceMarkup(data);
  const dataset = data.dataset || {};
  const analyses = data.recent_analyses || [];
  const spreadMetric = (data.metrics || []).find((metric) => metric.label === 'Wholesale gross spread');
  const spreadAvailability = spreadMetric?.availability || '后端未返回';
  return `<div class="page-intro overview-intro"><div><span class="eyebrow">BUSINESS OVERVIEW</span><h2>Today</h2><p>从最近的分析和数据状态开始，快速找到需要跟进的业务变化。</p></div><div class="header-context"><span class="status-mark good">✓</span><span><strong>数据可用</strong><small>截至 ${date(dataset.business_date_max)}</small></span></div></div>
    <div class="overview-grid"><section class="primary-column"><div class="section-head compact-head"><div><span class="eyebrow">RECENT ANALYSES</span><h3>最近分析</h3></div><button class="button ghost" onclick="navigate('history')">查看全部 →</button></div><div class="panel recent-panel"><div class="analysis-list">${recentRows(analyses, true)}</div></div><div class="section-head compact-head"><div><span class="eyebrow">START HERE</span><h3>常用问题</h3></div></div><div class="quick-question-list">${(data.suggestions || []).slice(0, 4).map((question, index) => `<button class="quick-question" onclick="fillQuestion('${esc(question)}')"><span>${String(index + 1).padStart(2, '0')}</span><strong>${esc(question)}</strong><em>→</em></button>`).join('')}</div></section><aside class="secondary-column"><div class="panel data-window"><div class="panel-heading"><div><span class="eyebrow">DATA WINDOW</span><h3>数据窗口</h3></div><button class="button ghost" onclick="navigate('data')">详情 →</button></div><div class="window-date">${date(dataset.business_date_max)}</div><div class="muted">最新业务日期</div><div class="window-grid"><div><strong>${number(dataset.measured_row_count)}</strong><small>快照行数</small></div><div><strong>${number(dataset.exact_duplicate_raw_rows)}</strong><small>原始重复行</small></div><div><strong>${esc(dataset.status || '—')}</strong><small>快照状态</small></div><div><strong>2025-07</strong><small>价差起始日</small></div></div><div class="window-note"><span class="status-mark warn">!</span><span>这是 Iowa 批发订单数据，不代表消费者 POS 或门店利润。</span></div></div><div class="panel question-entry"><span class="eyebrow">NEW ANALYSIS</span><h3>查一个问题</h3><p>先写问题，执行前再确认指标和周期。</p><div class="mini-question"><input id="home-question" placeholder="例如：7 月销售额为何变化？" onkeydown="if(event.key==='Enter')submitHomeQuestion()" /><button onclick="submitHomeQuestion()" aria-label="提交问题">→</button></div><button class="text-link" onclick="navigate('new')">打开完整分析入口 →</button></div><div class="panel nav-shortcuts"><span class="eyebrow">GOVERNANCE</span><button onclick="navigate('evidence')"><span>证据库</span><small>已保存的 provenance</small><em>→</em></button><button onclick="navigate('semantic')"><span>语义配置</span><small>指标和业务规则</small><em>→</em></button><button onclick="navigate('evaluation')"><span>评测中心</span><small>运行质量与回归</small><em>→</em></button></div></aside></div>`;
}

function recentTaskTable(items) {
  if (!items?.length) return emptyView('还没有分析任务', '从一个业务问题开始创建第一条分析。', '<button class="button" onclick="navigate(\'new\')">发起分析</button>');
  return `<div class="table-wrap"><table class="data-table reference-table"><thead><tr><th>任务名称</th><th>状态</th><th>期间</th><th>关键结论</th><th>更新时间</th></tr></thead><tbody>${items.slice(0, 5).map((task) => `<tr onclick="openTask('${esc(task.task_id)}')"><td><strong>${esc(task.business_question)}</strong><small>${esc(task.task_id.slice(0, 10))}</small></td><td>${badge(task.state)}</td><td>${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}</td><td>${esc(task.claims?.[0]?.statement || '后端尚未返回结论')}</td><td>${date(task.updated_at || task.created_at)}</td></tr>`).join('')}</tbody></table></div>`;
}

function homeReferenceMarkup(data) {
  const dataset = data.dataset || {};
  const analyses = data.recent_analyses || [];
  const current = analyses[0];
  const previewClaim = current?.claims?.[0];
  const previewEvidence = current?.evidence?.length || 0;
  const suggestions = (data.suggestions || []).slice(0, 5);
  return `<div class="reference-home"><section class="reference-hero"><div class="hero-kicker">企业数据分析工作台</div><h2>把业务问题，直接变成<span>可执行的分析结论</span></h2><p>你提问题，系统理解问题、分析数据、提炼发现，并给出可复核的建议。</p><div class="reference-query"><input id="home-question" placeholder="请输入你想分析的经营问题，例如：7 月批发销售额为什么下降？" onkeydown="if(event.key==='Enter')submitHomeQuestion()" /><button class="example-button" onclick="fillQuestion('比较 2026 年 7 月和 6 月的批发销售额')">✦ 智能示例</button><button class="button" onclick="submitHomeQuestion()">开始分析 <span>➤</span></button></div></section><section class="reference-stats"><div><span class="stat-icon">▣</span><div><small>数据范围</small><strong>${date(dataset.business_date_min)} 至 ${date(dataset.business_date_max)}</strong></div></div><div><span class="stat-icon">◷</span><div><small>最新数据</small><strong>截至 ${date(dataset.business_date_max)}</strong></div></div><div><span class="stat-icon filled">✓</span><div><small>数据状态</small><strong class="good">${esc(uiLabel(dataset.status || 'NOT_AVAILABLE'))}</strong></div></div><div><span class="stat-icon">≡</span><div><small>数据类型</small><strong>批发订单分析</strong></div></div></section><section class="reference-layout"><div class="reference-main"><div class="reference-section-title"><h3>最近分析任务</h3><button class="text-link" onclick="navigate('history')">查看全部　→</button></div><div class="panel reference-table-panel">${recentTaskTable(analyses)}</div><div class="reference-section-title process-title"><h3>分析流程</h3><span>从问题到可复核结论</span></div><div class="process-strip"><div><span>01</span><i>⌕</i><strong>理解问题</strong><small>识别指标和分析范围</small></div><b>→</b><div><span>02</span><i>◔</i><strong>自动分析</strong><small>执行受治理的数据查询</small></div><b>→</b><div><span>03</span><i>▤</i><strong>形成发现</strong><small>提炼变化和主要来源</small></div><b>→</b><div><span>04</span><i>✦</i><strong>给出建议</strong><small>提供有证据的下一步</small></div></div></div><aside class="reference-side"><div class="panel reference-card"><div class="reference-section-title"><h3>推荐问题</h3><button class="refresh-button" onclick="toast('推荐问题已刷新')">换一换　↻</button></div><div class="recommended-list">${suggestions.map((question, index) => `<button onclick="fillQuestion('${esc(question)}')"><span class="recommend-icon">${['▥', '♧', '⌁', '▦', '♢'][index]}</span><strong>${esc(question)}</strong><em>›</em></button>`).join('')}</div></div><div class="panel reference-card preview-card"><div class="reference-section-title"><h3>当前分析预览</h3><span class="preview-badge">基于最新数据</span></div>${current ? `<div class="preview-item"><span class="preview-icon">◎</span><div><small>关键发现</small><strong>${esc(previewClaim?.statement || '任务已完成，暂无关键结论')}</strong></div></div><div class="preview-item"><span class="preview-icon">✓</span><div><small>证据状态</small><strong>${previewEvidence ? `已关联 ${previewEvidence} 条证据` : '后端尚未返回证据'}</strong></div></div><div class="preview-item"><span class="preview-icon">↗</span><div><small>下一步</small><strong>打开任务查看完整分析链路</strong></div></div><button class="button preview-button" onclick="openTask('${esc(current.task_id)}')">查看当前分析　→</button>` : emptyView('暂无当前分析', '创建分析后，这里会显示最新结果。', '<button class="button" onclick="navigate(\'new\')">创建分析</button>')}</div></aside></section></div>`;
}

function fillQuestion(question) {
  if (state.page !== 'new') navigate('new');
  setTimeout(() => { const input = $('#question'); if (input) { input.value = question; input.focus(); } }, 40);
}

function submitHomeQuestion() {
  const question = $('#home-question')?.value.trim();
  if (!question) return toast('先输入一个业务问题');
  navigate('new');
  setTimeout(() => { $('#question').value = question; submitQuestion(); }, 40);
}

async function newPage() {
  setTitle('发起分析');
  $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">NEW ANALYSIS</span><h2>从一个业务问题开始</h2><p>执行前会先解析指标、周期、对比、维度和数据限制。解析结果来自后端契约。</p></div><button class="button secondary" onclick="navigate('home')">取消</button></div><div class="new-analysis-grid"><div class="panel form-panel"><label class="field-label" for="question">业务问题</label><textarea id="question" class="textarea" placeholder="例如：比较 2026 年 7 月和 6 月的批发销售额，按供应商找出主要贡献者"></textarea><div class="examples"><span class="muted">示例问题</span><button class="chip" onclick="fillQuestion('比较 2026 年 7 月和 6 月的批发销售额')">7 月 vs 6 月</button><button class="chip" onclick="fillQuestion('哪些供应商对 2026 年 7 月的销售变化贡献最大？')">供应商贡献</button><button class="chip" onclick="fillQuestion('解释 2026 年 7 月价格、数量和产品组合变化')">价格 / 数量 / 组合</button><button class="chip" onclick="fillQuestion('为什么门店利润在 2026 年 7 月下降？')">测试支持边界</button></div><div class="action-row"><button class="button" onclick="submitQuestion()">解析并创建分析 →</button><span class="muted">只读查询 · 有预算限制 · 结果可追溯</span></div></div><div class="panel resolved-preview"><span class="eyebrow">RESOLVED REQUEST</span><h3>执行前解析</h3><div class="pending-resolution"><span class="status-mark info">i</span><div><strong>等待业务问题</strong><p>提交后这里会显示后端解析的指标、精确日期、维度、筛选条件和限制。</p></div></div><div class="resolution-principles"><div><strong>语义</strong><span>版本化指标和维度</span></div><div><strong>治理</strong><span>只读对象和查询预算</span></div><div><strong>证据</strong><span>观察、计算、快照引用</span></div></div></div></div><div class="section-head"><div><span class="eyebrow">WHAT HAPPENS NEXT</span><h3>一次分析的路径</h3></div></div><div class="path-strip"><div><b>01</b><strong>解析上下文</strong><span>指标 · 周期 · 范围</span></div><div><b>02</b><strong>生成计划</strong><span>基线 · 驱动 · 验证</span></div><div><b>03</b><strong>执行调查</strong><span>查询 · 观察 · 假设</span></div><div><b>04</b><strong>交付证据</strong><span>结论 · 报告 · 后续</span></div></div>`;
}

async function submitQuestion() {
  const question = $('#question')?.value.trim();
  if (!question || question.length < 3) return toast('请输入至少 3 个字符的问题');
  $('#app').innerHTML = loading('正在解析问题并创建分析任务…');
  try { const task = await api('/analysis-tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) }); await openTask(task.task_id); } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

async function openTask(taskId, tab = 'overview') {
  try { state.taskId = taskId; state.page = 'workspace'; state.workspaceTab = tab; state.task = await api(`/analysis-tasks/${encodeURIComponent(taskId)}`); renderWorkspace(); } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

function taskContext(task) {
  const context = task.resolved_context || {};
  return `<div class="task-context"><span>${badge(task.state)}</span><span class="context-chip">数据集 · ${esc(context.dataset_snapshot || '待解析')}</span><span class="context-chip">周期 · ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}</span><span class="context-chip">任务 · ${esc(task.task_id.slice(0, 12))}</span></div>`;
}

function workspaceNavigation(active) {
  const items = [['overview', '总览'], ['context', '上下文'], ['plan', '分析计划'], ['investigation', '调查'], ['dashboard', 'Dashboard'], ['findings', '发现'], ['evidence', '证据'], ['report', '报告']];
  return `<aside class="analysis-nav panel"><div class="side-title">ANALYSIS</div>${items.map(([key, label]) => `<button class="${active === key ? 'active' : ''}" onclick="workspaceTab('${key}')">${label}</button>`).join('')}</aside>`;
}

function renderWorkspace() {
  const task = state.task;
  document.body.classList.add('session-mode');
  setTitle('分析工作区');
  const active = state.workspaceTab || 'overview';
  $('#app').innerHTML = sessionMarkup(task, active);
  return;
  $('#app').innerHTML = `<div class="page-intro task-header"><div><span class="eyebrow">ANALYSIS WORKSPACE</span><h2>${esc(task.business_question)}</h2>${taskContext(task)}</div><div class="action-row"><button class="button secondary" onclick="followUp('${esc(task.task_id)}')">＋ 发起后续</button><button class="button" onclick="workspaceTab('report')">打开报告 →</button></div></div>${task.clarification ? clarificationPanel(task) : ''}${task.coverage_warning ? `<div class="notice warning"><strong>数据覆盖提示</strong><p>${esc(task.coverage_warning)}</p></div>` : ''}<div class="workspace-layout">${workspaceNavigation(active)}<main class="workspace-main">${workspaceBody(task, active)}</main><aside class="panel evidence-inspector">${inspectorContent(task, state.selectedEvidence)}</aside></div>`;
}

function eventMessage(event) {
  const messages = { 'Analysis task created.': '已创建分析任务。', 'Context compiled from the semantic package and immutable snapshot.': '已确认指标口径、分析范围和数据快照。', 'Structured analysis plan created.': '已生成分析计划。', 'Baseline metrics computed with governed DuckDB execution.': '已完成基准指标计算。', 'Contribution analysis completed by vendor.': '已完成主要供应商贡献分析。', 'Evidence captured during analysis.': '已保存分析依据。', 'Metric, period, evidence coverage, and result consistency checks passed.': '已核对指标、期间、依据覆盖和结果一致性。', 'Analysis completed.': '分析已完成。' };
  return messages[event.message] || uiText(event.message || event.event_type || '分析步骤已完成');
}

function sessionMarkup(task, active) {
  return sessionWorkbenchMarkup(task, active);
  const normalized = active === 'findings' ? 'overview' : active === 'context' || active === 'plan' ? 'investigation' : active;
  const body = normalized === 'overview' ? sessionOverview(task) : normalized === 'investigation' ? investigationView(task) : normalized === 'dashboard' ? dashboardView(task, true) : normalized === 'evidence' ? evidenceView(task) : reportView(task);
  const tabs = [['overview', '分析结果'], ['investigation', '分析过程'], ['dashboard', '数据看板'], ['evidence', '依据'], ['report', '成果']];
  const context = task.resolved_context || {};
  return `<div class="session-header"><div class="session-breadcrumb"><button class="back-link" onclick="navigate('history')">分析历史</button><span>/</span><span>分析会话 ${esc(task.task_id.slice(0, 10))}</span></div><div class="session-title-row"><div><h2>${esc(task.business_question)}</h2><div class="session-meta">${badge(task.state)}<span>${esc(context.dataset_snapshot || '数据快照待确认')}</span><span>${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}</span></div></div><div class="action-row"><button class="button secondary" onclick="followUp('${esc(task.task_id)}')">继续提问</button><button class="button" onclick="workspaceTab('report')">整理成果</button></div></div></div>${task.clarification ? clarificationPanel(task) : ''}${task.coverage_warning ? `<div class="notice warning"><strong>数据覆盖提示</strong><p>${esc(task.coverage_warning)}</p></div>` : ''}<nav class="session-tabs" aria-label="分析会话导航">${tabs.map(([key, label]) => `<button class="${normalized === key ? 'active' : ''}" onclick="workspaceTab('${key}')">${label}</button>`).join('')}</nav><div class="session-layout"><main class="session-main">${body}</main><aside class="session-rail">${sessionRail(task)}</aside></div>`;
}

function claimStatement(task, claim) {
  if (!claim) return '分析结果正在整理中。';
  const summary = task.summary?.wholesale_sales_amount;
  if (claim.type === 'FACT' && summary?.delta != null) {
    const direction = Number(summary.delta) >= 0 ? '增加' : '减少';
    return `所选期间批发销售额${direction} ${money(Math.abs(summary.delta))}，变化率 ${pct(Math.abs(summary.change_pct))}。`;
  }
  if (claim.type === 'INFERENCE' && task.contributions?.[0]) {
    return `${task.contributions[0].dimension_value} 是所选供应商变化中绝对贡献最大的供应商。`;
  }
  return uiText(claim.statement);
}

function questionText(question) {
  const translations = {
    'Compare July 2026 with June 2026 by vendor': '按供应商比较 2026 年 7 月与 6 月的批发销售额',
  };
  return translations[question] || question || '未命名分析';
}

function sessionHistoryRows(task, includeCurrent = true) {
  const items = [...(state.analysisHistory || [])];
  if (includeCurrent && !items.some((item) => item.task_id === task.task_id)) items.unshift(task);
  if (!includeCurrent) items.splice(0, items.length, ...items.filter((item) => item.task_id !== task.task_id));
  if (!items.length) return '<div class="session-history-empty">暂无历史分析</div>';
  return items.slice(0, 6).map((item, index) => `<button class="session-history-item ${item.task_id === task.task_id ? 'active' : ''}" onclick="openTask('${esc(item.task_id)}')"><span class="history-item-icon">${index === 0 ? '◈' : '▧'}</span><span><strong>${esc(questionText(item.business_question))}</strong><small>${index === 0 ? '当前分析' : date(item.updated_at || item.created_at)}</small></span><em>⋮</em></button>`).join('');
}

function sessionProcess(task) {
  const steps = [
    ['理解问题', `已识别为${task.resolved_context?.metrics?.[0]?.label || '业务指标'}分析`],
    ['确定分析范围', `${date(task.periods?.primary?.start)} 至 ${date(task.periods?.primary?.end)}`],
    ['获取相关数据', `已加载 ${task.evidence?.length ? task.evidence.length : '相关'} 个数据依据`],
    ['数据对齐与比较', '已对齐当前期间与对比期间'],
    ['发现关键驱动因素', task.contributions?.length ? `识别出 ${task.contributions.length} 个供应商变化来源` : '正在识别变化来源'],
    ['深入分析原因', '正在检查数量、价格和产品结构'],
    ['形成结论与建议', '生成可复核的结论和下一步'],
  ];
  const completed = task.state === 'COMPLETED';
  return steps.map(([title, detail], index) => {
    const done = completed && index < 5;
    const current = !done && ((completed && index === 5) || (!completed && index === Math.min(5, Math.max(0, (task.events?.length || 1) - 2))));
    return `<div class="session-process-step ${done ? 'done' : current ? 'current' : ''}"><span class="process-node">${done ? '✓' : index + 1}</span><div><strong>${title}</strong><small>${detail}</small>${current ? '<b>正在分析…</b>' : ''}</div></div>`;
  }).join('');
}

function sessionTrendSvg(task) {
  const values = [...(task.trend || [])].sort((a, b) => String(a.dimension_value).localeCompare(String(b.dimension_value))).slice(-12);
  if (!values.length) return emptyView('暂无趋势结果', '后端没有返回趋势观察。');
  const nums = values.map((item) => Number(item.wholesale_sales_amount || 0));
  const min = Math.min(...nums) * .96;
  const max = Math.max(...nums) * 1.02;
  const points = nums.map((value, index) => `${30 + index * (650 / Math.max(1, nums.length - 1))},${190 - ((value - min) / Math.max(1, max - min)) * 145}`).join(' ');
  const dots = nums.map((value, index) => { const x = 30 + index * (650 / Math.max(1, nums.length - 1)); const y = 190 - ((value - min) / Math.max(1, max - min)) * 145; return `<circle cx="${x}" cy="${y}" r="4"/><text x="${x}" y="216" text-anchor="middle">${esc(String(values[index].dimension_value).slice(5))}</text>`; }).join('');
  return `<svg class="session-trend-svg" viewBox="0 0 710 235" role="img" aria-label="销售额趋势"><path class="chart-gridline" d="M30 45H680M30 93H680M30 141H680M30 190H680"/><polyline points="${points}"/><g>${dots}</g></svg>`;
}

function sessionResultView(task) {
  const summary = task.summary || {};
  const sales = summary.wholesale_sales_amount || {};
  const top = task.contributions?.[0];
  const rows = (task.contributions || []).slice(0, 5);
  const maxDelta = Math.max(...rows.map((item) => Math.abs(Number(item.delta || 0))), 1);
  const positive = rows.filter((item) => Number(item.delta || 0) > 0).reduce((total, item) => total + Number(item.delta || 0), 0);
  const negative = rows.filter((item) => Number(item.delta || 0) < 0).reduce((total, item) => total + Math.abs(Number(item.delta || 0)), 0);
  const total = Math.max(1, positive + negative);
  const claim = task.claims?.[0];
  const kpis = [
    ['批发销售额（7月）', money(sales.current), `${Number(sales.change_pct || 0) >= 0 ? '▲' : '▼'} ${pct(Math.abs(sales.change_pct))} 对比上期`, Number(sales.change_pct || 0) >= 0 ? 'up' : 'down'],
    ['期间变化', money(sales.delta), `${pct(Math.abs(sales.change_pct))} 对比上期`, Number(sales.delta || 0) >= 0 ? 'up' : 'down'],
    ['最大变化来源', top?.dimension_value || '—', top ? money(top.delta) : '暂无', Number(top?.delta || 0) >= 0 ? 'up' : 'down'],
    ['依据覆盖', `${number(task.evidence?.length || 0)} 条`, task.evidence?.length ? '已验证，可复核' : '等待依据', 'neutral'],
  ];
  return `<section class="result-summary"><div class="result-summary-label"><span class="result-spark">✧</span><strong>初步结论</strong><span>${task.state === 'COMPLETED' ? '已完成' : '正在分析…'}</span></div><h1>${esc(claimStatement(task, claim))}</h1><p>相比上期，批发销售额从 ${money(sales.comparison)} 变为 ${money(sales.current)}，${Number(sales.delta || 0) >= 0 ? '增加' : '减少'} ${money(Math.abs(sales.delta || 0))}。</p><div class="result-summary-actions"><button onclick="openEvidence(0)">查看依据</button><button onclick="toast('已记录反馈')">赞</button><button onclick="toast('已记录反馈')">踩</button><button onclick="workspaceTab('report')">整理成果</button></div></section><div class="session-kpi-row">${kpis.map(([label, value, change, tone]) => `<div class="session-kpi"><small>${label}</small><strong>${esc(value)}</strong><span class="${tone}">${change}</span></div>`).join('')}</div><div class="session-viz-grid"><section class="viz-card trend-card"><div class="viz-heading"><div><h3>销售额趋势（近 12 个月）</h3><p>当前任务返回的月度批发销售额</p></div><span class="viz-legend"><i></i>销售额</span></div>${sessionTrendSvg(task)}</section><section class="viz-card driver-card"><div class="viz-heading"><div><h3>销售额变化原因分解</h3><p>按供应商观察贡献（单位：美元）</p></div><button onclick="workspaceTab('investigation')">更多</button></div><div class="driver-bars"><div class="driver-axis"><span>上期</span><span>本期</span></div>${rows.map((item) => `<div class="driver-bar-row"><span>${esc(item.dimension_value)}</span><div><i class="${Number(item.delta || 0) < 0 ? 'negative' : ''}" style="width:${Math.max(7, Math.abs(Number(item.delta || 0)) / maxDelta * 100)}%"></i></div><b class="${Number(item.delta || 0) < 0 ? 'down' : 'up'}">${money(item.delta)}</b></div>`).join('')}</div></section></div><div class="session-bottom-grid"><section class="viz-card ranking-card"><div class="viz-heading"><div><h3>前 5 个供应商销售额变化</h3><p>按绝对变化排序</p></div><button onclick="workspaceTab('dashboard')">查看全部 →</button></div><div class="session-ranking-table"><div class="ranking-head"><span>供应商</span><span>上期</span><span>本期</span><span>变化</span></div>${rows.map((item) => `<div class="ranking-row"><strong>${esc(item.dimension_value)}</strong><span>${money(item.comparison)}</span><span>${money(item.current)}</span><b class="${Number(item.delta || 0) < 0 ? 'down' : 'up'}">${money(item.delta)}</b></div>`).join('')}</div></section><section class="viz-card share-card"><div class="viz-heading"><div><h3>销售额变化贡献占比</h3><p>正负变化的相对占比</p></div></div><div class="share-body"><div class="share-donut" style="--positive:${positive / total * 100}%"><span>${money(sales.delta)}</span><small>总变化</small></div><div class="share-legend"><div><i class="purple"></i><span>增加</span><b>${pct(positive / total * 100)}</b></div><div><i class="blue"></i><span>减少</span><b>${pct(negative / total * 100)}</b></div><div><i class="gray"></i><span>其他来源</span><b>${pct(Math.max(0, 100 - positive / total * 100 - negative / total * 100))}</b></div></div></div></section></div><div class="follow-up-area"><h3>你可以继续问</h3><div class="follow-up-chips"><button onclick="followUpWithQuestion('${esc(task.task_id)}','深入分析主要供应商变化原因')">⌕ 深入分析主要供应商变化原因</button><button onclick="followUpWithQuestion('${esc(task.task_id)}','按产品类别判断下降原因')">⌕ 按产品类别判断下降原因</button><button onclick="followUpWithQuestion('${esc(task.task_id)}','价格变化的具体影响是什么？')">⌕ 价格变化的具体影响</button><button onclick="followUpWithQuestion('${esc(task.task_id)}','同比去年 7 月变化如何？')">⌕ 同比去年 7 月</button></div><div class="follow-up-input"><input placeholder="继续追问或调整分析方向…" onkeydown="if(event.key==='Enter' && this.value.trim()) followUpWithQuestion('${esc(task.task_id)}', this.value.trim())"/><button onclick="followUp('${esc(task.task_id)}')">➜</button></div></div>`;
}

function sessionWorkbenchMarkup(task, active) {
  const normalized = active === 'findings' ? 'overview' : active === 'context' || active === 'plan' ? 'investigation' : active;
  const body = normalized === 'overview' ? sessionResultView(task) : normalized === 'investigation' ? investigationView(task) : normalized === 'dashboard' ? dashboardView(task, true) : normalized === 'evidence' ? evidenceView(task) : reportView(task);
  return `<div class="session-workbench"><header class="session-workbench-topbar"><button class="session-brand" onclick="navigate('home')"><span class="session-brand-mark">✧</span><strong>企业智能分析工作区</strong><em>分析助手</em></button><div class="session-top-actions"><button onclick="toast('分享链接已复制')">⇧ 分享</button><button aria-label="收藏" onclick="toast('已加入收藏')">▢</button><button aria-label="历史" onclick="navigate('history')">◷</button><span class="session-avatar">张</span></div></header><div class="session-workbench-body"><aside class="session-history-pane"><button class="new-session-button" onclick="navigate('new')"><b>＋</b> 新建分析</button><div class="session-history-label">当前分析</div>${sessionHistoryRows(task)}<div class="session-history-label recent-label">最近的分析</div>${sessionHistoryRows(task, false)}<div class="session-help-card"><span>✧</span><strong>让分析帮助业务决策</strong><p>提出任何业务问题，系统会自动完成分析并提供可复核的依据。</p><button onclick="navigate('new')">查看示例问题 →</button></div></aside><aside class="session-process-pane"><div class="process-pane-heading"><strong>分析过程</strong><span>${task.state === 'COMPLETED' ? '已完成' : '正在分析…'}</span></div>${sessionProcess(task)}<button class="stop-analysis" onclick="toast('当前任务已完成，无需停止')">◉ 停止分析</button></aside><main class="session-result-pane"><div class="session-question-bar"><input value="${esc(questionText(task.business_question))}" aria-label="当前分析问题" onkeydown="if(event.key==='Enter')followUp('${esc(task.task_id)}')"/><button onclick="followUp('${esc(task.task_id)}')">➜</button></div><div class="session-mode-tabs"><button class="active">快速分析</button><button onclick="workspaceTab('investigation')">深度调查</button><button onclick="workspaceTab('evidence')">联网搜索</button></div><div class="session-result-content">${body}</div></main></div></div>`;
}

function sessionRail(task) {
  const context = task.resolved_context || {};
  return `<div class="panel rail-card"><div class="rail-heading"><span>当前范围</span><button class="text-link" onclick="workspaceTab('investigation')">查看过程</button></div><div class="rail-field"><small>指标</small><strong>${esc(context.metrics?.[0]?.label || '未返回')}</strong></div><div class="rail-field"><small>分析期间</small><strong>${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}</strong></div><div class="rail-field"><small>对比期间</small><strong>${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}</strong></div><div class="rail-field"><small>分析维度</small><strong>${esc(context.dimension || '整体')}</strong></div></div><div class="panel rail-card"><div class="rail-heading"><span>可信状态</span>${badge(task.state === 'COMPLETED' ? 'VERIFIED' : 'NOT_AVAILABLE')}</div><div class="rail-check"><span class="status-mark ${task.evidence?.length ? 'good' : 'warn'}">${task.evidence?.length ? '✓' : '!'}</span><span><strong>${task.evidence?.length ? `已关联 ${task.evidence.length} 条依据` : '依据尚未返回'}</strong><small>点击“依据”查看计算来源和限制</small></span></div><button class="button secondary rail-button" onclick="workspaceTab('evidence')">查看依据</button></div><div class="panel rail-card process-summary"><div class="rail-heading"><span>分析过程</span><span class="muted">${task.events?.length || 0} 个步骤</span></div>${(task.events || []).slice(-4).map((event) => `<div class="rail-event"><span class="timeline-mark"></span><span>${esc(eventMessage(event))}</span></div>`).join('') || '<p class="muted">等待分析过程返回。</p>'}<button class="text-link" onclick="workspaceTab('investigation')">查看完整过程 →</button></div>`;
}

function sessionOverview(task) {
  const summary = task.summary || {};
  const trend = task.trend || [];
  const top = task.contributions?.[0];
  const claim = task.claims?.[0];
  const delta = summary.wholesale_sales_amount?.delta;
  const max = Math.max(...trend.map((item) => Math.abs(item.wholesale_sales_amount || 0)), 1);
  return `<section class="session-answer panel"><div class="answer-topline"><span>分析结论</span><span>${claim ? `${uiLabel(claim.type)} · ${uiLabel(claim.status)}` : '等待后端结论'}</span></div>${claim ? `<h1>${esc(claim.statement)}</h1><button class="text-link" onclick="openEvidence(0)">为什么这么说？ 查看依据 →</button>` : emptyView('结论尚未返回', '先查看分析过程，确认任务是否仍在执行或需要澄清。')}<div class="answer-facts"><div><small>销售额变化</small><strong class="${delta == null ? '' : Number(delta) >= 0 ? 'up' : 'down'}">${delta == null ? '—' : money(delta)}</strong><span>当前期间对比上期</span></div><div><small>主要变化来源</small><strong>${esc(top?.dimension_value || '—')}</strong><span>${top ? money(top.delta) : '后端未返回贡献结果'}</span></div><div><small>依据</small><strong>${number(task.evidence?.length || 0)} 条</strong><span>${task.evidence?.length ? '已保存，可复核' : '尚未返回'}</span></div></div></section><div class="grid grid-4 session-kpis">${metricKpi('批发销售额', summary.wholesale_sales_amount)}${metricKpi('订购瓶数', summary.bottles_ordered, number, '瓶')}${metricKpi('综合瓶价', summary.average_wholesale_price_per_bottle, moneyPrecise, '美元 / 瓶')}${metricKpi('批发价差', summary.wholesale_gross_spread)}</div><div class="content-grid two-col session-visuals"><div class="panel"><div class="panel-heading"><div><span class="section-label">变化趋势</span><h3>期间表现</h3></div><button class="text-link" onclick="workspaceTab('dashboard')">查看完整看板 →</button></div><p class="muted">当前任务返回的月度批发销售额</p>${trend.length ? `<div class="bar-chart session-chart" role="img" aria-label="期间表现">${trend.slice(-12).map((item) => `<div class="bar-column"><span class="bar-value">${money(item.wholesale_sales_amount)}</span><div class="bar-track"><div class="bar" style="height:${Math.max(5, Math.abs(item.wholesale_sales_amount || 0) / max * 160)}px"></div></div><span class="bar-label">${esc(item.dimension_value)}</span></div>`).join('')}</div>` : emptyView('暂无趋势结果', '后端没有返回趋势观察。')}</div><div class="panel"><div class="panel-heading"><div><span class="section-label">变化来源</span><h3>主要贡献者</h3></div><button class="text-link" onclick="workspaceTab('investigation')">继续调查 →</button></div>${top ? `<div class="driver-summary"><small>最大观测贡献者</small><strong>${esc(top.dimension_value)}</strong><b class="${Number(top.delta || 0) >= 0 ? 'up' : 'down'}">${money(top.delta)}</b><p>这是观测关联，不代表因果。</p></div><div class="mini-ranking">${(task.contributions || []).slice(0, 4).map((row, index) => `<button onclick="openContributionEvidence(${index})"><span>${index + 1}</span><strong>${esc(row.dimension_value)}</strong><em class="${Number(row.delta || 0) >= 0 ? 'up' : 'down'}">${money(row.delta)}</em></button>`).join('')}</div>` : emptyView('暂无贡献排名', '后端没有返回可用的驱动拆解。')}</div></div><div class="session-next"><div><span>下一步</span><strong>继续推进这次分析</strong></div><button onclick="workspaceTab('investigation')">查看分析过程　→</button><button onclick="workspaceTab('evidence')">核对依据　→</button><button onclick="workspaceTab('report')">整理成果　→</button></div>`;
}

function workspaceMarkup(task, active) {
  const context = task.resolved_context || {};
  const tabs = [['overview', '概览'], ['context', '上下文'], ['plan', '分析计划'], ['investigation', '调查'], ['dashboard', 'Dashboard'], ['findings', '发现'], ['evidence', '证据'], ['report', '报告']];
  const body = active === 'overview' ? answerOverview(task) : workspaceBody(task, active);
  return `<div class="analysis-head"><div class="analysis-breadcrumb"><button class="back-link" onclick="navigate('history')">分析历史</button><span>/</span><span>${esc(task.task_id.slice(0, 12))}</span></div><div class="analysis-head-row"><div><h2>${esc(task.business_question)}</h2><div class="task-context"><span>${badge(task.state)}</span><span class="context-chip">${esc(context.dataset_snapshot || '数据集待解析')}</span><span class="context-chip">${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}</span></div></div><div class="action-row"><button class="button secondary" onclick="followUp('${esc(task.task_id)}')">＋ 后续分析</button><button class="button" onclick="workspaceTab('report')">导出报告 →</button></div></div></div>${task.clarification ? clarificationPanel(task) : ''}${task.coverage_warning ? `<div class="notice warning"><strong>数据覆盖提示</strong><p>${esc(task.coverage_warning)}</p></div>` : ''}<nav class="workspace-tabs" aria-label="分析视图">${tabs.map(([key, label]) => `<button class="${active === key ? 'active' : ''}" onclick="workspaceTab('${key}')">${label}</button>`).join('')}</nav><div class="workspace-content ${active === 'overview' ? 'overview-layout' : ''}"><main>${body}</main>${active === 'overview' ? `<aside class="source-rail panel">${inspectorContent(task, state.selectedEvidence)}<div class="rail-divider"></div><div class="rail-meta"><span class="eyebrow">SOURCE CONTEXT</span><strong>${esc(context.metrics?.[0]?.label || '指标未返回')}</strong><small>${esc(context.semantic_version || '语义版本未返回')} · ${esc(context.context_version || '上下文版本未返回')}</small><button class="text-link" onclick="workspaceTab('context')">查看完整上下文 →</button></div></aside>` : ''}</div>`;
}

function answerOverview(task) {
  const summary = task.summary || {};
  const trend = task.trend || [];
  const top = task.contributions?.[0];
  const primaryClaim = task.claims?.[0];
  const delta = summary.wholesale_sales_amount?.delta;
  const direction = delta == null ? '' : Number(delta) >= 0 ? 'up' : 'down';
  const max = Math.max(...trend.map((item) => Math.abs(item.wholesale_sales_amount || 0)), 1);
  return `<section class="answer-card panel"><div class="answer-heading"><div><span class="eyebrow">ANSWER</span><h3>这次分析回答了什么</h3></div><span class="source-label">${esc(contextLabel(task))}</span></div>${primaryClaim ? `<div class="answer-statement"><div class="finding-head">${badge(primaryClaim.type)}${badge(primaryClaim.status)}</div><h1>${esc(primaryClaim.statement)}</h1><button class="text-link" onclick="openEvidence(0)">查看支持证据 →</button></div>` : emptyView('还没有可展示的回答', '任务尚未返回 claim；请查看分析计划或任务状态。')}<div class="answer-signal"><div><span class="label">批发销售额变化</span><strong class="${direction}">${delta == null ? '—' : money(delta)}</strong><small>当前周期 vs 对比周期</small></div><div><span class="label">最大观测贡献者</span><strong>${esc(top?.dimension_value || '—')}</strong><small>${top ? money(top.delta) : '后端未返回贡献排名'}</small></div><div><span class="label">证据覆盖</span><strong>${number(task.evidence?.length || 0)} 条</strong><small>${task.evidence?.length ? '已保存 provenance' : '未返回 evidence'}</small></div></div></section><div class="grid grid-4 answer-kpis">${metricKpi('批发销售额', summary.wholesale_sales_amount)}${metricKpi('订购瓶数', summary.bottles_ordered, number, 'bottles')}${metricKpi('综合瓶价', summary.average_wholesale_price_per_bottle, moneyPrecise, 'USD / bottle')}${metricKpi('批发价差', summary.wholesale_gross_spread)}</div><div class="content-grid two-col section-gap"><div class="panel"><div class="panel-heading"><div><span class="eyebrow">WHAT CHANGED</span><h3>变化趋势</h3></div><button class="button ghost" onclick="workspaceTab('dashboard')">展开 Dashboard →</button></div><p class="muted">只展示当前任务已返回的时间序列结果。</p>${trend.length ? `<div class="bar-chart answer-chart" role="img" aria-label="月度批发销售额趋势">${trend.slice(-12).map((item) => `<div class="bar-column"><span class="bar-value">${money(item.wholesale_sales_amount)}</span><div class="bar-track"><div class="bar" style="height:${Math.max(5, Math.abs(item.wholesale_sales_amount || 0) / max * 160)}px"></div></div><span class="bar-label">${esc(item.dimension_value)}</span></div>`).join('')}</div>` : emptyView('没有趋势结果', '后端没有为此任务返回趋势观察。')}</div><div class="panel"><div class="panel-heading"><div><span class="eyebrow">WHY IT MOVED</span><h3>主要变化来源</h3></div><button class="button ghost" onclick="workspaceTab('investigation')">调查 →</button></div>${top ? `<div class="driver-lead"><span class="label">最大观测贡献者</span><strong>${esc(top.dimension_value)}</strong><span class="${Number(top.delta || 0) >= 0 ? 'up' : 'down'}">${money(top.delta)}</span><small>贡献是观测关联，不代表因果。</small></div>` : emptyView('没有贡献排名', '该任务没有返回可用的驱动拆解。')}${task.contributions?.length ? `<div class="mini-ranking">${task.contributions.slice(0, 4).map((row, index) => `<button onclick="openContributionEvidence(${index})"><span>${index + 1}</span><strong>${esc(row.dimension_value)}</strong><em class="${Number(row.delta || 0) >= 0 ? 'up' : 'down'}">${money(row.delta)}</em></button>`).join('')}</div>` : ''}</div></div><div class="section-head"><div><span class="eyebrow">NEXT</span><h3>下一步</h3></div></div><div class="next-step-row"><button onclick="workspaceTab('evidence')"><span class="next-icon">01</span><strong>核对证据</strong><small>查看 observation、版本和 validation</small><em>→</em></button><button onclick="workspaceTab('investigation')"><span class="next-icon">02</span><strong>继续调查</strong><small>验证数量、价格或组合假设</small><em>→</em></button><button onclick="workspaceTab('report')"><span class="next-icon">03</span><strong>生成报告</strong><small>使用当前保存的结论和证据</small><em>→</em></button></div>`;
}

function contextLabel(task) {
  const context = task.resolved_context || {};
  return `${context.dimension || 'Overall'} · ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}`;
}

function clarificationPanel(task) {
  return `<div class="notice clarification"><strong>需要澄清后才能继续</strong><p>${esc(task.clarification.question)}</p><div class="inline-form"><input id="clarification-response" class="filter" placeholder="输入你的选择或补充说明" /><button class="button" onclick="submitClarification('${esc(task.task_id)}')">提交澄清</button></div></div>`;
}

function workspaceBody(task, active) {
  if (active === 'context') return contextView(task);
  if (active === 'plan') return planView(task);
  if (active === 'investigation') return investigationView(task);
  if (active === 'dashboard') return dashboardView(task, true);
  if (active === 'findings') return findingsView(task);
  if (active === 'evidence') return evidenceView(task);
  if (active === 'report') return reportView(task);
  return overviewView(task);
}

function overviewView(task) {
  const summary = task.summary || {};
  const trend = task.trend || [];
  const max = Math.max(...trend.map((item) => Math.abs(item.wholesale_sales_amount || 0)), 1);
  return `<div class="trust-strip compact-strip"><div class="trust-item"><div class="trust-label">任务状态</div><div class="trust-value">${esc(task.state)}</div></div><div class="trust-item"><div class="trust-label">主指标</div><div class="trust-value">${esc(task.resolved_context?.metrics?.[0]?.label || '—')}</div></div><div class="trust-item"><div class="trust-label">验证</div><div class="trust-value ${task.validations?.length || task.state === 'COMPLETED' ? 'good' : 'warn'}">${task.validations?.length || task.state === 'COMPLETED' ? '已返回' : '未返回'}</div></div><div class="trust-item"><div class="trust-label">证据条数</div><div class="trust-value">${number(task.evidence?.length || 0)}</div></div></div><div class="grid grid-4">${metricKpi('批发销售额', summary.wholesale_sales_amount)}${metricKpi('订购瓶数', summary.bottles_ordered, number, 'bottles')}${metricKpi('综合瓶价', summary.average_wholesale_price_per_bottle, moneyPrecise, 'USD / bottle')}${metricKpi('批发价差', summary.wholesale_gross_spread)}</div><div class="content-grid two-col section-gap"><div class="panel"><div class="panel-heading"><div><span class="eyebrow">TREND</span><h3>月度表现趋势</h3></div><span class="source-label">${esc(task.resolved_context?.dataset_snapshot || '数据源待返回')}</span></div><p class="muted">批发订单金额 · 单位 USD · 点击指标可打开证据</p>${trend.length ? `<div class="bar-chart" role="img" aria-label="月度批发销售额趋势">${trend.slice(-12).map((item) => `<div class="bar-column"><span class="bar-value">${money(item.wholesale_sales_amount)}</span><div class="bar-track"><div class="bar" style="height:${Math.max(5, Math.abs(item.wholesale_sales_amount || 0) / max * 160)}px"></div></div><span class="bar-label">${esc(item.dimension_value)}</span></div>`).join('')}</div>` : emptyView('没有趋势结果', '后端没有为此任务返回趋势观察。')}</div><div class="panel"><div class="panel-heading"><div><span class="eyebrow">CLAIMS</span><h3>关键发现</h3></div><button class="button ghost" onclick="workspaceTab('evidence')">看证据 →</button></div>${claimsList(task)}</div></div><div class="section-head"><div><span class="eyebrow">DECOMPOSITION</span><h3>销售变化拆解</h3></div><button class="button ghost" onclick="workspaceTab('dashboard')">进入 Dashboard →</button></div><div class="panel pvm-grid">${Object.entries(task.pvm || {}).map(([key, value]) => `<div><div class="label">${esc(key.replaceAll('_', ' '))}</div><div class="value">${money(value)}</div><div class="muted">后端计算结果</div></div>`).join('') || emptyView('暂无拆解结果', '需要销售额、瓶数和综合瓶价都可用。')}</div>`;
}

function claimsList(task) {
  return task.claims?.length ? task.claims.map((claim, index) => `<button class="finding claim-button" onclick="openEvidence(${index})"><div class="finding-head"><span>${badge(claim.type)}</span>${badge(claim.status)}</div><strong>${esc(claim.statement)}</strong><small>证据 ${claim.evidence_ids?.length || 0} 条 · 点击查看来源</small></button>`).join('') : emptyView('没有产生结论', '该任务没有返回可展示的 claim。');
}

function contextView(task) {
  const context = task.resolved_context || {};
  const rows = [['上下文版本', context.context_version], ['数据集快照', context.dataset_snapshot], ['数据状态', context.dataset_status], ['语义版本', context.semantic_version], ['维度 / 粒度', context.dimension || 'Overall'], ['允许对象', context.allowed_objects?.join(', ')], ['筛选条件', Object.entries(context.filters || {}).map(([key, value]) => `${key}: ${value}`).join(' · ')], ['主周期', `${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}`], ['对比周期', `${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}`]];
  return `<div class="panel"><div class="panel-heading"><div><span class="eyebrow">RESOLVED CONTEXT</span><h3>后端解析结果</h3></div>${badge(context.dataset_status || 'NOT AVAILABLE')}</div><p class="muted">以下字段来自任务上下文契约。前端不在本地重新计算或改写指标定义。</p><dl>${rows.map(([key, value]) => `<div class="definition"><dt>${esc(key)}</dt><dd>${esc(value || '—')}</dd></div>`).join('')}</dl>${context.metrics?.length ? `<div class="subsection"><h4>已解析指标</h4>${context.metrics.map((metric) => `<div class="metric-definition"><strong>${esc(metric.label)}</strong><span class="code">${esc(metric.id)}</span><p>${esc(metric.description || '')}</p><small>${esc(metric.expression || '')} · ${esc(metric.unit || '')} · ${esc(metric.availability || '')}</small></div>`).join('')}</div>` : ''}${context.quality_warnings?.length ? `<div class="notice warning"><strong>质量警告</strong><ul>${context.quality_warnings.map((item) => `<li>${esc(item)}</li>`).join('')}</ul></div>` : ''}</div>`;
}

function planView(task) {
  const plan = task.plan || {};
  const steps = plan.steps || [];
  return `<div class="panel"><div class="panel-heading"><div><span class="eyebrow">GOVERNED PLAN</span><h3>分析计划</h3></div><span class="source-label">${steps.length} 个步骤</span></div><p class="muted">计划由后端生成；点击步骤可查看对应事件和观察结果。</p>${steps.length ? `<div class="plan-list">${steps.map((step, index) => `<button class="plan-step" onclick="focusPlanStep(${index})"><span class="plan-index">${index + 1}</span><span><strong>${esc(step.title || step.name || `步骤 ${index + 1}`)}</strong><small>${esc(step.description || step.objective || step.status || '已纳入任务计划')}</small></span><span>→</span></button>`).join('')}</div>` : emptyView('计划尚未返回', '计划可能会在澄清完成或数据可用后生成。')}</div><div class="content-grid two-col section-gap"><div class="panel"><h3>计划约束</h3><div class="definition"><dt>最大查询数</dt><dd>由后端 budget contract 返回</dd></div><div class="definition"><dt>允许对象</dt><dd>${esc(task.resolved_context?.allowed_objects?.join(', ') || '—')}</dd></div></div><div class="panel"><h3>任务事件</h3>${timeline(task.events || [])}</div></div>`;
}

function investigationView(task) {
  const hypotheses = task.hypotheses || [];
  return `<div class="content-grid three-col"><div class="panel"><div class="panel-heading"><div><span class="eyebrow">HYPOTHESES</span><h3>假设</h3></div><button class="button ghost" onclick="followUp('${esc(task.task_id)}')">后续 →</button></div>${hypotheses.length ? hypotheses.map((hypothesis, index) => `<button class="hypothesis ${index === 0 ? 'selected' : ''}" onclick="selectHypothesis(this)"><span class="hypothesis-mark">${hypothesis.state === 'SUPPORTED' ? '✓' : '?'}</span><span><strong>${esc(hypothesis.topic || hypothesis.statement)}</strong><small>${esc(hypothesis.statement || '')}</small></span>${badge(hypothesis.state)}</button>`).join('') : emptyView('没有后端假设', '当前任务没有返回调查假设。')}</div><div class="panel"><div class="panel-heading"><div><span class="eyebrow">TIMELINE</span><h3>调查时间线</h3></div><span class="source-label">事件日志</span></div>${timeline(task.events || [])}</div><div class="panel"><div class="panel-heading"><div><span class="eyebrow">SELECTED EVIDENCE</span><h3>选中证据</h3></div></div>${inspectorContent(task, state.selectedEvidence)}</div></div>${contributionTable(task, true)}`;
}

function timeline(events) {
  if (!events.length) return emptyView('还没有事件', '任务事件会在后端执行阶段写入。');
  return `<div class="timeline">${events.map((event) => `<div class="timeline-item"><span class="timeline-mark"></span><div><strong>${esc(event.message || event.event_type)}</strong><small>${date(event.occurred_at)} · ${esc(event.event_type)}</small></div></div>`).join('')}</div>`;
}

function dashboardView(task, embedded = false) {
  const rows = (task.contributions || []).filter((row) => !state.dashboardSearch || String(row.dimension_value).toLowerCase().includes(state.dashboardSearch.toLowerCase()));
  const trend = task.trend || [];
  const summary = task.summary || {};
  return `<div class="dashboard-toolbar"><div><span class="eyebrow">DYNAMIC BI</span><h3>${embedded ? '任务 Dashboard' : 'Dashboard'}</h3><small>${esc(task.resolved_context?.metrics?.[0]?.label || '指标待返回')} · ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)} vs ${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}</small></div><div class="filter-bar"><span class="filter-static">快照 · ${esc(task.resolved_context?.dataset_snapshot || '—')}</span><select class="filter" onchange="requestBreakdown(this.value)"><option value="">维度 · ${esc(task.resolved_context?.dimension || 'Overall')}</option><option value="vendor">按供应商发起后续</option><option value="category">按品类发起后续</option><option value="store">按门店发起后续</option><option value="county">按县发起后续</option></select><input class="filter search" value="${esc(state.dashboardSearch)}" oninput="setDashboardSearch(this.value)" placeholder="筛选表格…" /><button class="button ghost" onclick="resetDashboard()">重置</button></div></div><div class="grid grid-4">${metricKpi('批发销售额', summary.wholesale_sales_amount)}${metricKpi('订购瓶数', summary.bottles_ordered, number, 'bottles')}${metricKpi('综合瓶价', summary.average_wholesale_price_per_bottle, moneyPrecise, 'USD / bottle')}${metricKpi('批发价差', summary.wholesale_gross_spread)}</div><div class="content-grid two-col section-gap"><div class="panel"><div class="panel-heading"><div><span class="eyebrow">TREND</span><h3>期间趋势</h3></div><span class="source-label">数据来源 · ${esc(task.resolved_context?.dataset_snapshot || '—')}</span></div>${trend.length ? `<div class="bar-chart dashboard-chart">${trend.slice(-12).map((item) => `<div class="bar-column"><span class="bar-value">${money(item.wholesale_sales_amount)}</span><div class="bar-track"><div class="bar" style="height:${Math.max(5, (Math.abs(item.wholesale_sales_amount || 0) / Math.max(...trend.map((x) => Math.abs(x.wholesale_sales_amount || 0)), 1)) * 160)}px"></div></div><span class="bar-label">${esc(item.dimension_value)}</span></div>`).join('')}</div>` : emptyView('暂无趋势', '后端没有返回趋势观察。')}</div><div class="panel"><div class="panel-heading"><div><span class="eyebrow">ACTIONS</span><h3>图表操作</h3></div></div><div class="action-menu-grid"><button onclick="toast('当前后端没有返回 record drill-through，无法伪造记录结果')">查看记录（不可用）</button><button onclick="followUp('${esc(task.task_id)}')">用 AI 调查</button><button onclick="workspaceTab('evidence')">查看支持证据</button></div><div class="notice info"><strong>交互边界</strong><p>维度切换会创建带新维度的真实后续任务；当前结果的筛选仅作用于后端已返回的贡献表。</p></div></div></div>${contributionTable({ ...task, contributions: rows }, true)}`;
}

function contributionTable(task, actions = false) {
  const rows = task.contributions || [];
  return `<div class="section-head"><div><span class="eyebrow">CONTRIBUTION</span><h3>贡献排名</h3></div><span class="muted">${rows.length} 个后端返回的结果</span></div><div class="panel table-wrap"><table class="data-table"><thead><tr><th>维度值</th><th>当前周期</th><th>对比周期</th><th>变化</th>${actions ? '<th>操作</th>' : ''}</tr></thead><tbody>${rows.length ? rows.map((row, index) => `<tr><td><strong>${esc(row.dimension_value)}</strong></td><td>${money(row.current)}</td><td>${money(row.comparison)}</td><td class="${Number(row.delta || 0) >= 0 ? 'up' : 'down'}">${money(row.delta)}</td>${actions ? `<td><button class="table-link" onclick="openContributionEvidence(${index})">证据 / 操作 →</button></td>` : ''}</tr>`).join('') : `<tr><td colspan="${actions ? 5 : 4}">${emptyView('没有贡献结果', '该任务没有返回贡献排名。')}</td></tr>`}</tbody></table></div>`;
}

function findingsView(task) {
  return `<div class="panel"><div class="panel-heading"><div><span class="eyebrow">FINDINGS</span><h3>证据支持的发现</h3></div><span class="source-label">${task.claims?.length || 0} 条 claim</span></div><p class="muted">类型、状态和限制都来自后端 claims；贡献结果不被解释为因果关系。</p>${claimsList(task)}</div><div class="panel section-gap"><h3>限制与边界</h3>${task.limitations?.length ? `<ul class="limitations">${task.limitations.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>` : '<p class="muted">任务没有返回额外限制。</p>'}</div>`;
}

function evidenceView(task) {
  return `<div class="evidence-layout"><div class="panel"><div class="panel-heading"><div><span class="eyebrow">EVIDENCE LIBRARY</span><h3>证据链</h3></div><input class="filter search" placeholder="搜索 claim / hash" oninput="filterEvidence(this.value)" /></div><div id="evidence-list">${evidenceItems(task)}</div></div><div class="panel evidence-detail">${inspectorContent(task, state.selectedEvidence)}</div></div>`;
}

function evidenceItems(task) {
  const items = task.evidence || [];
  return items.length ? items.map((evidence, index) => { const claim = task.claims?.find((item) => item.claim_id === evidence.claim_id) || task.claims?.[index]; return `<button class="evidence-item" data-search="${esc(`${claim?.statement || ''} ${evidence.result_hash || ''}`)}" onclick="openEvidence(${index})"><span class="evidence-type">${esc(claim?.type || 'EVIDENCE')}</span><span class="evidence-content"><strong>${esc(claim?.statement || 'Verified result')}</strong><small>${esc(evidence.relation)} · ${esc(evidence.observation_ids?.join(', ') || 'observation unavailable')}</small></span><span class="evidence-arrow">→</span></button>`; }).join('') : emptyView('暂无证据', '后端尚未返回可展示的 provenance reference。');
}

function inspectorContent(task, selectedIndex = null) {
  const index = selectedIndex == null ? 0 : selectedIndex;
  const evidence = task.evidence?.[index];
  const claim = task.claims?.find((item) => item.claim_id === evidence?.claim_id) || task.claims?.[index];
  if (!evidence && !claim) return `<div class="inspector-title"><h3>证据检查器</h3></div>${emptyView('选择一条发现', '点击 KPI、发现或贡献结果查看它的证据来源。')}`;
  const checks = evidence?.validation || [];
  return `<div class="inspector-title"><div><span class="eyebrow">EVIDENCE INSPECTOR</span><h3>证据检查器</h3></div><button class="icon-button" onclick="closeInspector()" aria-label="关闭">×</button></div><div class="claim-box"><div class="finding-head">${badge(claim?.type || 'CLAIM')}${badge(claim?.status || 'NOT AVAILABLE')}</div><strong>${esc(claim?.statement || 'Verified result')}</strong></div><div class="inspector-section"><h4>关系</h4><p>${esc(evidence?.relation || '—')}</p><h4>影响</h4><p>${claim?.impact ? esc(claim.impact) : '后端未返回影响量'}</p></div><div class="inspector-section"><h4>EVIDENCE</h4><p><strong>Observation</strong> · ${esc(evidence?.observation_ids?.join(', ') || '—')}</p><p><strong>Metric</strong> · ${esc(evidence?.metric_version || '—')}</p><p><strong>Dataset</strong> · ${esc(evidence?.dataset_snapshot || '—')}</p><p><strong>Context</strong> · ${esc(evidence?.context_version || '—')}</p><p class="code hash">${esc(evidence?.result_hash || 'hash unavailable')}</p></div><div class="inspector-section"><h4>VALIDATION</h4>${checks.length ? `<div class="validation-list">${checks.map((check) => `<div class="validation-item ok"><span>✓</span>${esc(check)}</div>`).join('')}</div>` : '<p class="muted">后端未返回 validation checks，不显示为已验证。</p>'}</div><div class="inspector-actions"><button class="button" onclick="followUp('${esc(task.task_id)}')">调查进一步 →</button><button class="button secondary" onclick="copyReference('${esc(evidence?.evidence_id || '')}')">复制引用</button></div>`;
}

function reportView(task) {
  const claims = task.claims || [];
  const limitations = task.limitations || claims.flatMap((claim) => claim.limitations || []);
  return `<div class="report-toolbar"><div><span class="eyebrow">SAVED ARTIFACT</span><h3>分析报告</h3><p class="muted">内容由当前任务已保存的 claims 和 evidence 组成。</p></div><div class="report-actions"><a class="button secondary" href="/api/v1/analysis-tasks/${esc(task.task_id)}/artifacts/report.md" target="_blank">Markdown</a><a class="button" href="/api/v1/analysis-tasks/${esc(task.task_id)}/artifacts/report.html" target="_blank">打开 HTML →</a></div></div><div class="report-body panel"><div class="report-section"><span class="eyebrow">EXECUTIVE SUMMARY</span><h2>${esc(task.business_question)}</h2><p>任务状态：${esc(task.state)}。周期为 ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}，对比 ${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}。</p></div><div class="report-section"><h3>Business Performance</h3><div class="grid grid-3">${metricKpi('批发销售额', task.summary?.wholesale_sales_amount)}${metricKpi('订购瓶数', task.summary?.bottles_ordered, number, 'bottles')}${metricKpi('批发价差', task.summary?.wholesale_gross_spread)}</div></div><div class="report-section"><h3>Key Findings</h3>${claims.length ? claims.map((claim, index) => `<div class="report-finding"><div>${badge(claim.type)} ${badge(claim.status)}</div><strong>${esc(claim.statement)}</strong><small>证据 ${claim.evidence_ids?.length || 0} 条 · <button class="table-link" onclick="openEvidence(${index})">查看来源</button></small></div>`).join('') : '<p class="muted">没有已保存的 finding。</p>'}</div><div class="report-section"><h3>Supporting Evidence</h3><p>本任务保存了 ${number(task.evidence?.length || 0)} 条 evidence reference，数据集为 <span class="code">${esc(task.resolved_context?.dataset_snapshot || '—')}</span>。</p></div><div class="report-section"><h3>Limitations</h3>${limitations.length ? `<ul class="limitations">${limitations.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>` : '<p class="muted">后端没有返回额外限制。</p>'}</div></div>`;
}

function workspaceTab(tab) { state.workspaceTab = tab; state.selectedEvidence = null; renderWorkspace(); }
function focusPlanStep(index) { toast(`已聚焦计划步骤 ${index + 1}，对应事件仍以任务日志为准`); workspaceTab('investigation'); }
function selectHypothesis(button) { $$('.hypothesis').forEach((item) => item.classList.remove('selected')); button.classList.add('selected'); }
function requestBreakdown(dimension) {
  if (!dimension || !state.task) return;
  const labels = { vendor: '供应商', category: '品类', store: '门店', county: '县' };
  const current = state.task.resolved_context?.dimension;
  if (dimension === current) return toast('当前任务已经按此维度返回结果');
  followUpWithQuestion(state.task.task_id, `请将同一分析按${labels[dimension] || dimension}拆解，并保留原有期间和指标。`);
}
function setDashboardSearch(value) { state.dashboardSearch = value; if (state.page === 'workspace' && state.workspaceTab === 'dashboard') { const body = $('.workspace-main'); if (body) body.innerHTML = dashboardView(state.task, true); } }
function resetDashboard() { state.dashboardDimension = ''; state.dashboardSearch = ''; renderWorkspace(); }
function openMetricEvidence(label) { if (!state.task) return; state.selectedEvidence = 0; if (state.page === 'workspace') renderWorkspace(); else openInspector(state.task, 0); toast(`${label}：已打开证据检查器`); }
function openEvidence(index) { state.selectedEvidence = index; if (state.page === 'workspace') renderWorkspace(); else openInspector(state.task, index); }
function openContributionEvidence(index) { state.selectedEvidence = Math.min(index, Math.max(0, (state.task?.evidence?.length || 1) - 1)); renderWorkspace(); toast('已打开该贡献结果的支持证据'); }
function closeInspector() { state.selectedEvidence = null; if ($('#modal-root').innerHTML) closeDrawer(); else renderWorkspace(); }
function openInspector(task, index) { state.selectedEvidence = index; $('#modal-root').innerHTML = `<div class="drawer-backdrop open" onclick="closeDrawer()"></div><aside class="drawer open">${inspectorContent(task, index)}</aside>`; }
function closeDrawer() { $('#modal-root').innerHTML = ''; }
function filterEvidence(value) { $$('.evidence-item').forEach((item) => { item.hidden = value && !item.dataset.search.toLowerCase().includes(value.toLowerCase()); }); }
function copyReference(reference) { if (!reference) return toast('没有可复制的 evidence id'); navigator.clipboard?.writeText(reference).then(() => toast('Evidence ID 已复制')).catch(() => toast(reference)); }

async function history() {
  setTitle('分析历史'); $('#app').innerHTML = loading();
  try { const data = await api('/analysis-tasks'); $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">HISTORY</span><h2>分析历史</h2><p>重新打开任务、查看 lineage 或从已有证据创建后续分析。</p></div><button class="button" onclick="navigate('new')">＋ 新建分析</button></div><div class="filter-bar history-filters"><input class="filter search" id="history-search" placeholder="搜索业务问题…" oninput="filterHistory(this.value)" /><select class="filter" onchange="filterHistoryState(this.value)"><option value="">所有状态</option><option>COMPLETED</option><option>PARTIAL</option><option>FAILED</option><option>CANCELLED</option></select><span class="muted">${data.items?.length || 0} 个任务</span></div><div class="panel"><div id="history-list" class="analysis-list">${recentRows(data.items, true)}</div></div>`; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}
function filterHistory(value) { $$('#history-list .analysis-row').forEach((row) => { row.hidden = value && !row.innerText.toLowerCase().includes(value.toLowerCase()); }); }
function filterHistoryState(value) { $$('#history-list .analysis-row').forEach((row) => { row.hidden = value && !row.innerText.includes(value); }); }

async function dashboardPage() {
  setTitle('Dashboard'); $('#app').innerHTML = loading('正在载入可视化结果…');
  try { const data = await api('/analysis-tasks'); const task = data.items?.find((item) => item.state === 'COMPLETED') || data.items?.[0]; if (!task) { $('#app').innerHTML = emptyView('还没有可视化任务', '先发起一个分析，Dashboard 会使用该任务的后端结果。', '<button class="button" onclick="navigate(\'new\')">发起分析</button>'); return; } state.task = task; state.taskId = task.task_id; state.page = 'dashboard'; $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">DYNAMIC BI</span><h2>Dashboard</h2><p>选择一个已有任务查看它的指标、趋势、贡献和证据入口。</p></div><button class="button secondary" onclick="openTask('${esc(task.task_id)}', 'dashboard')">在分析工作区打开 →</button></div>${dashboardView(task)}`; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

async function evidenceLibrary() {
  setTitle('证据库'); $('#app').innerHTML = loading();
  try { const data = await api('/analysis-tasks'); const tasks = data.items || []; const evidence = tasks.flatMap((task) => (task.evidence || []).map((item, index) => ({ ...item, task, claim: task.claims?.find((claim) => claim.claim_id === item.claim_id) || task.claims?.[index] }))); state.page = 'evidence'; $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">EVIDENCE LIBRARY</span><h2>证据库</h2><p>只展示任务中由后端生成并带 provenance reference 的 evidence。</p></div><div class="filter-bar"><select class="filter"><option>所有 Claim 类型</option><option>FACT</option><option>INFERENCE</option><option>RECOMMENDATION</option></select><select class="filter"><option>所有状态</option><option>VERIFIED</option><option>QUALIFIED</option></select></div></div><div class="evidence-library-layout"><div class="panel"><div class="panel-heading"><h3>Claim list</h3><span class="muted">${evidence.length} 条 evidence</span></div><input class="filter search full" placeholder="搜索 claim、快照或 hash" oninput="filterEvidence(this.value)" /><div class="library-list">${evidence.length ? evidence.map((item, index) => `<button class="evidence-item library-evidence" data-search="${esc(`${item.claim?.statement || ''} ${item.dataset_snapshot || ''} ${item.result_hash || ''}`)}" onclick="selectLibraryEvidence(${index})"><span class="evidence-type">${esc(item.claim?.type || 'EVIDENCE')}</span><span class="evidence-content"><strong>${esc(item.claim?.statement || 'Verified result')}</strong><small>${esc(item.relation)} · ${esc(item.dataset_snapshot)} · 任务 ${esc(item.task.task_id.slice(0, 8))}</small></span><span>${badge(item.claim?.status || 'NOT AVAILABLE')}</span></button>`).join('') : emptyView('还没有证据', '完成一个分析后，后端 evidence 会出现在这里。')}</div></div><div id="library-detail" class="panel evidence-detail">${evidence.length ? inspectorContent(evidence[0].task, 0) : emptyView('选择证据', '证据详情会显示 observation、计算、版本和验证。')}</div></div>`; window.__evidenceLibrary = evidence; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}
function selectLibraryEvidence(index) { const item = window.__evidenceLibrary?.[index]; if (!item) return; const evidenceIndex = item.task.evidence.findIndex((entry) => entry.evidence_id === item.evidence_id); $('#library-detail').innerHTML = inspectorContent(item.task, evidenceIndex); }

async function dataPage() {
  setTitle('数据状态'); $('#app').innerHTML = loading();
  try { const data = await api('/data/status'); const dataset = data.dataset || {}; $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">DATA GOVERNANCE</span><h2>数据状态</h2><p>数据源、快照、质量检查和可用性窗口都来自后端 manifest。</p></div>${badge(dataset.status)}</div>${trustStrip(dataset)}<div class="content-grid two-col"><div class="panel"><div class="panel-heading"><h3>Snapshot manifest</h3><span class="source-label">不可变快照</span></div><dl>${[['Source publisher', 'Iowa Department of Revenue'], ['Source asset', dataset.source_assets?.join(', ')], ['Source catalog', dataset.source_catalog], ['Snapshot ID', dataset.snapshot_id], ['Business date range', `${date(dataset.business_date_min)} — ${date(dataset.business_date_max)}`], ['Extracted at', dataset.extracted_at], ['Validated at', dataset.validated_at], ['Measured rows', dataset.measured_row_count], ['Exact raw duplicates', dataset.exact_duplicate_raw_rows], ['Current dimension join rows', dataset.current_dimension_joined_rows], ['Joined sales', dataset.current_dimension_joined_sales], ['Raw SHA-256', dataset.raw_file_sha256], ['Curated SHA-256', dataset.curated_file_sha256], ['Schema fingerprint', dataset.schema_hash], ['License', dataset.license]].map(([key, value]) => `<div class="definition"><dt>${esc(key)}</dt><dd class="${String(key).includes('SHA') || String(key).includes('fingerprint') ? 'code' : ''}">${esc(value || '—')}</dd></div>`).join('')}</dl></div><div class="panel"><div class="panel-heading"><h3>Quality checks</h3><span class="source-label">${Object.values(dataset.validation || {}).filter((value) => value === 'PASSED').length} passed</span></div><div class="quality-list">${Object.entries(dataset.validation || {}).map(([key, value]) => `<div class="quality-row"><span class="status-mark ${value === 'PASSED' ? 'good' : 'warn'}">${value === 'PASSED' ? '✓' : '!'}</span><span><strong>${esc(key.replaceAll('_', ' '))}</strong><small>${esc(value)}</small></span></div>`).join('')}</div><div class="notice warning"><strong>已知限制</strong><ul>${(dataset.notes || []).map((note) => `<li>${esc(note)}</li>`).join('')}</ul></div></div></div><div class="section-head"><div><span class="eyebrow">AVAILABILITY</span><h3>指标与维度</h3></div></div><div class="content-grid two-col"><div class="panel"><h3>Metrics</h3>${(data.metrics || []).map((metric) => `<div class="metric-definition"><strong>${esc(metric.label || metric.id)}</strong><span class="code">${esc(metric.id)}</span><p>${esc(metric.description || '')}</p><small>${esc(metric.unit || '')} · ${esc(metric.availability?.from || metric.availability || '')} — ${esc(metric.availability?.to || '')}</small></div>`).join('')}</div><div class="panel"><h3>Dimensions</h3><div class="tag-cloud">${(data.dimensions || []).map((dimension) => `<span class="tag">${esc(dimension.label)} <small>${esc(dimension.id)}</small></span>`).join('')}</div></div></div>`; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

async function semantic() {
  setTitle('语义配置'); $('#app').innerHTML = loading();
  try { const data = await api('/semantic'); const pkg = data.package || {}; $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">VERSIONED SEMANTICS</span><h2>语义配置</h2><p>${esc(pkg.description || '只读浏览指标定义、公式、来源映射和业务规则。')}</p></div><span class="badge">v${esc(pkg.version || '—')}</span></div><div class="panel"><div class="panel-heading"><div><h3>${esc(pkg.title || 'Iowa Liquor Wholesale')}</h3><span class="muted">Semantic package · ${esc(pkg.package_id || 'iowa_liquor_wholesale')}</span></div><span class="source-label">只读 explorer</span></div><div class="section-head"><div><span class="eyebrow">METRICS</span><h3>指标定义</h3></div></div>${(data.metrics || []).map((metric) => `<div class="metric-definition rich"><div><strong>${esc(metric.label || metric.id)}</strong><span class="code">${esc(metric.id)}</span></div><p>${esc(metric.description || '')}</p><div class="metric-meta"><span>Formula · ${esc(metric.expression || '—')}</span><span>Unit · ${esc(metric.unit || '—')}</span><span>Availability · ${esc(metric.availability?.from || metric.availability || '—')} → ${esc(metric.availability?.to || '—')}</span></div></div>`).join('') || emptyView('没有指标定义', '语义包不可用。')}<div class="section-head"><div><span class="eyebrow">BUSINESS RULES</span><h3>业务规则</h3></div></div>${(data.business_rules || []).map((rule) => `<div class="definition"><dt>${esc(rule.id)}</dt><dd>${esc(rule.rule)}</dd></div>`).join('') || emptyView('没有业务规则', '语义包没有返回规则。')}</div>`; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

async function evaluation() {
  setTitle('评测中心'); $('#app').innerHTML = loading();
  try { const data = await api('/evaluation'); const run = data.latest_run; const results = run?.results || []; $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">EVALUATION</span><h2>质量与评测</h2><p>${esc(data.note)}</p></div><button class="button" onclick="runEvaluation(this)">运行回归套件</button></div><div class="grid grid-4"><div class="panel kpi"><div class="label">Suite version</div><div class="value" style="font-size:20px">${esc(data.suite_version)}</div><div class="change muted">${number(data.case_count)} cases</div></div><div class="panel kpi"><div class="label">最近运行</div><div class="value" style="font-size:20px">${run ? `${run.passed}/${data.case_count}` : 'NOT RUN'}</div><div class="change muted">${run ? date(run.completed_at) : '未测量不显示分数'}</div></div><div class="panel kpi"><div class="label">执行状态</div><div class="value" style="font-size:20px">${esc(data.status)}</div><div class="change muted">结果持久化在工作区</div></div><div class="panel kpi"><div class="label">Provider</div><div class="value" style="font-size:20px">Deterministic</div><div class="change muted">本地参考运行路径</div></div></div><div class="content-grid two-col section-gap"><div class="panel"><div class="panel-heading"><h3>Measured dimensions</h3><span class="source-label">未测量 = —</span></div><table class="data-table"><thead><tr><th>维度</th><th>状态</th><th>值</th></tr></thead><tbody>${(data.metrics || []).map((metric) => `<tr><td>${esc(metric.name)}</td><td>${badge(metric.status)}</td><td>${metric.value == null ? '—' : `${esc(metric.value)}%`}</td></tr>`).join('')}</tbody></table></div><div class="panel"><div class="panel-heading"><h3>最近运行摘要</h3></div>${run ? `<div class="run-summary"><div><strong>${number(run.passed)}</strong><span>passed</span></div><div><strong>${number(run.failed)}</strong><span>failed</span></div><div><strong>${esc(run.run_id.slice(0, 10))}</strong><span>run id</span></div></div>` : emptyView('尚未运行', 'Cases loaded 不代表已通过；点击运行后才会产生测量结果。')}</div></div>${results.length ? `<div class="panel section-gap"><div class="panel-heading"><h3>Case results</h3><span class="muted">失败用例应链接到任务轨迹</span></div><div class="case-list">${results.map((result) => `<div class="case-row"><span class="status-mark ${result.passed ? 'good' : 'bad'}">${result.passed ? '✓' : '×'}</span><strong>${esc(result.case_id)}</strong>${badge(result.state)}<span class="muted">${esc(result.details || '')}</span></div>`).join('')}</div></div>` : ''}`; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

async function runEvaluation(button) { if (button) button.disabled = true; try { await api('/evaluation/run', { method: 'POST' }); evaluation(); } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); } }

async function settings() {
  setTitle('系统设置'); $('#app').innerHTML = loading();
  try { const data = await api('/settings'); $('#app').innerHTML = `<div class="page-intro"><div><span class="eyebrow">WORKSPACE SETTINGS</span><h2>系统设置</h2><p>影响分析的配置由后端 configuration contract 提供，前端只读展示。</p></div><span class="badge">${esc(data.provider || '—')}</span></div><div class="content-grid two-col"><div class="panel"><div class="panel-heading"><h3>运行配置</h3><span class="source-label">backend contract</span></div><dl>${[['Model provider', data.provider], ['Credential status', data.credential_configured ? 'Configured' : 'Not configured · deterministic mode'], ['Dataset version', data.dataset_version], ['Semantic version', data.semantic_version]].map(([key, value]) => `<div class="definition"><dt>${esc(key)}</dt><dd>${esc(value || '—')}</dd></div>`).join('')}</dl></div><div class="panel"><div class="panel-heading"><h3>分析预算</h3><span class="source-label">enforced server-side</span></div><dl>${Object.entries(data.analysis_budget || {}).map(([key, value]) => `<div class="definition"><dt>${esc(key.replaceAll('_', ' '))}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl></div></div><div class="content-grid two-col section-gap"><div class="panel"><h3>环境与权限</h3><div class="quality-list"><div class="quality-row"><span class="status-mark info">i</span><span><strong>数据分类上限</strong><small>由当前用户策略决定，敏感凭据不会在 UI 暴露。</small></span></div><div class="quality-row"><span class="status-mark good">✓</span><span><strong>本地只读模式</strong><small>分析执行不会写入源数据。</small></span></div></div></div><div class="panel"><h3>治理链接</h3><button class="link-row" onclick="navigate('data')">数据限制与来源 <span>→</span></button><button class="link-row" onclick="navigate('semantic')">语义包与业务规则 <span>→</span></button><button class="link-row" onclick="navigate('evaluation')">评测与回归结果 <span>→</span></button></div></div>`; } catch (errorObject) { $('#app').innerHTML = errorView(errorObject); }
}

async function submitClarification(taskId) { const response = $('#clarification-response')?.value.trim(); if (!response) return toast('请先填写澄清内容'); try { state.task = await api(`/analysis-tasks/${taskId}/clarifications`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ response }) }); renderWorkspace(); } catch (errorObject) { toast(errorObject.message); } }
async function followUp(taskId) { const question = prompt('请输入后续问题：'); if (!question?.trim()) return; try { const task = await api(`/analysis-tasks/${taskId}/follow-ups`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: question.trim(), referenced_evidence_ids: state.task?.evidence?.map((item) => item.evidence_id) || [] }) }); await openTask(task.task_id); } catch (errorObject) { toast(errorObject.message); } }
async function followUpWithQuestion(taskId, question) { try { const task = await api(`/analysis-tasks/${taskId}/follow-ups`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, referenced_evidence_ids: state.task?.evidence?.map((item) => item.evidence_id) || [] }) }); await openTask(task.task_id); } catch (errorObject) { toast(errorObject.message); } }
function downloadReport(taskId, filename) { window.open(`/api/v1/analysis-tasks/${encodeURIComponent(taskId)}/artifacts/${filename}`, '_blank'); }
function toast(message) { const node = $('#toast'); node.textContent = message; node.classList.add('show'); clearTimeout(window.__toastTimer); window.__toastTimer = setTimeout(() => node.classList.remove('show'), 2600); }
function toggleSidebar() { $('#sidebar').classList.toggle('open'); }

const visibleTranslations = {
  'ENTERPRISE INTELLIGENCE WORKSPACE': '企业数据分析工作台', 'IOWA LIQUOR WHOLESALE': '爱荷华州酒类批发', 'BUSINESS OVERVIEW': '业务总览', 'RECENT ANALYSES': '最近分析', 'START HERE': '从这里开始', 'DATA WINDOW': '数据窗口', 'NEW ANALYSIS': '新建分析', 'GOVERNANCE': '数据治理', 'ANALYSIS WORKSPACE': '分析工作区', 'RESOLVED CONTEXT': '已解析上下文', 'GOVERNED PLAN': '受治理的分析计划', 'HYPOTHESES': '分析假设', 'TIMELINE': '调查时间线', 'SELECTED EVIDENCE': '选中证据', 'DYNAMIC BI': '数据看板', 'EVIDENCE LIBRARY': '证据库', 'EVIDENCE INSPECTOR': '证据检查器', 'SOURCE CONTEXT': '来源上下文', 'SAVED ARTIFACT': '已保存报告', 'EXECUTIVE SUMMARY': '执行摘要', 'BUSINESS PERFORMANCE': '业务表现', 'KEY FINDINGS': '关键发现', 'SUPPORTING EVIDENCE': '支持证据', 'LIMITATIONS': '限制条件', 'MEASURED SNAPSHOT': '已测数据快照', 'WHAT HAPPENS NEXT': '接下来', 'WHAT CHANGED': '发生了什么', 'WHY IT MOVED': '变化来源', 'ANSWER': '分析答案', 'NEXT': '下一步', 'METRICS': '指标', 'BUSINESS RULES': '业务规则', 'AVAILABILITY': '可用范围', 'DATA GOVERNANCE': '数据治理', 'SNAPSHOT MANIFEST': '快照清单', 'QUALITY CHECKS': '质量检查', 'VERSIONED SEMANTICS': '版本化语义', 'WORKSPACE SETTINGS': '工作区设置', 'EVALUATION': '评测中心', 'Measured dimensions': '已测指标', 'Case results': '用例结果', 'Claim list': '结论列表', 'Provider': '运行提供方', 'Deterministic': '确定性', 'passed': '通过', 'failed': '失败', 'run id': '运行编号', 'cases': '个用例', 'Metric': '指标', 'Metrics': '指标', 'Dimension': '维度', 'Dimensions': '维度', 'Source': '来源', 'Source publisher': '来源发布方', 'Source asset': '来源资产', 'Source catalog': '来源目录', 'Snapshot ID': '快照编号', 'Business date range': '业务日期范围', 'Extracted at': '提取时间', 'Validated at': '验证时间', 'Measured rows': '已测行数', 'Exact raw duplicates': '原始重复行', 'Current dimension join rows': '当前维度关联行数', 'Joined sales': '关联销售额', 'Schema fingerprint': '结构指纹', 'License': '授权许可', 'Formula': '计算公式', 'Unit': '单位', 'Availability': '可用范围', 'Current': '当前周期', 'Comparison': '对比周期', 'Change': '变化', 'Relation': '关系', 'Observation': '观测', 'Dataset': '数据集', 'Context': '上下文', 'VALIDATION': '验证', 'EVIDENCE': '证据', 'NOT AVAILABLE': '暂不可用', 'NOT RUN': '未运行', 'Iowa': '爱荷华州', 'provenance reference': '来源引用', 'provenance': '来源链', 'backend contract': '后端配置契约', 'enforced server-side': '由后端执行', 'read-only explorer': '只读浏览', 'Claim': '结论', 'claim': '结论', 'hash': '哈希', 'onward': '起', 'bottles': '瓶', 'USD / bottle': '美元 / 瓶', 'USD': '美元', 'Overall': '整体'
};

Object.assign(visibleTranslations, { 'Iowa Liquor Wholesale': '爱荷华州酒类批发', 'Iowa Department of Revenue': '爱荷华州税收部门', 'Semantic contract for Iowa Class E licensee liquor purchase orders. This is wholesale/order analysis, not consumer POS data and not store profit.': '爱荷华州 Class E 持证商酒类采购订单的语义契约。本系统分析批发 / 订单数据，不是消费者 POS 数据，也不是门店利润。', 'Amount invoiced by the Iowa state distributor to the licensed store.': '爱荷华州经销商向持证门店开具的订单金额。', 'Do not label wholesale_gross_spread as store profit, gross profit, or accounting profit.': '不得将 wholesale_gross_spread 标记为门店利润、毛利或会计利润。', 'Cost, spread, rate, and average state cost queries outside 2025-07-01 to 2026-07-31 must be partial or unavailable.': '2025-07-01 至 2026-07-31 之外的成本、价差、价差率和平均州采购成本查询，必须标记为部分可用或不可用。', 'Historical names and county/category/vendor/product descriptions are taken from fact event-time fields.': '历史名称以及县、品类、供应商、产品描述，取自事实表的事件时间字段。', 'iowa_liquor_rolling must resolve to an immutable snapshot before planning or execution.': 'iowa_liquor_rolling 必须在计划或执行前解析为不可变数据快照。', 'State wholesale purchase/order amount; not consumer POS revenue.': '州级批发采购 / 订单金额，不是消费者 POS 收入。', 'Bottles on wholesale orders; not consumer units sold.': '批发订单中的瓶数，不是消费者实际购买量。', 'Volume represented by wholesale orders.': '批发订单所代表的容量。', 'Composite wholesale price per ordered bottle; mix-sensitive.': '每个订购瓶的综合批发价，受产品组合影响。', 'Transaction-level state acquisition cost estimate.': '交易级州采购成本估算。', 'Wholesale spread only; not store profit or net profit.': '仅代表批发价差，不是门店利润或净利润。', 'Wholesale spread divided by wholesale sales.': '批发价差除以批发销售额。' });

function localizeVisibleDom(root = document) {
  const nodes = root.querySelectorAll ? root.querySelectorAll('*') : [];
  const replace = (value) => Object.entries(visibleTranslations).sort((a, b) => b[0].length - a[0].length).reduce((text, [from, to]) => text.replaceAll(from, to), value);
  nodes.forEach((element) => {
    if (element.matches('code,input,textarea,script,style,.code,.context-chip,.source-label')) return;
    [...element.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE).forEach((node) => { node.nodeValue = replace(node.nodeValue); });
    ['placeholder', 'aria-label', 'title'].forEach((attribute) => { if (element.hasAttribute(attribute)) element.setAttribute(attribute, replace(element.getAttribute(attribute))); });
  });
}

const localizationObserver = new MutationObserver(() => localizeVisibleDom(document));
localizationObserver.observe(document.body, { childList: true, subtree: true });
localizeVisibleDom(document);

async function navigate(page) {
  state.page = page;
  document.body.classList.toggle('session-mode', page === 'workspace');
  if (page === 'home') return home();
  if (page === 'new') return newPage();
  if (page === 'history') return history();
  if (page === 'dashboard') return dashboardPage();
  if (page === 'evidence') return evidenceLibrary();
  if (page === 'data') return dataPage();
  if (page === 'semantic') return semantic();
  if (page === 'evaluation') return evaluation();
  if (page === 'settings') return settings();
}

$$('#nav button').forEach((button) => button.addEventListener('click', () => { toggleSidebar(); navigate(button.dataset.page); }));
$('#global-search')?.addEventListener('keydown', (event) => { if (event.key === 'Enter') { const value = event.currentTarget.value.trim(); if (value) { fillQuestion(value); event.currentTarget.value = ''; } } });
document.addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); $('#global-search')?.focus(); } });
home();
