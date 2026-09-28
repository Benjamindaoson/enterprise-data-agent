// Enterprise Data Agent — Frontend SPA
// Modern, clean BI interface with clear visual hierarchy

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
const statusLabels = {
  READY: 'Ready', COMPLETED: 'Completed', PARTIAL: 'Partial', FAILED: 'Failed',
  CANCELLED: 'Cancelled', ABSTAINED: 'Not Supported', NOT_AVAILABLE: 'Not Available',
  PROPOSED: 'Proposed', TESTING: 'Testing', SUPPORTED: 'Supported', REJECTED: 'Rejected',
  INCONCLUSIVE: 'Inconclusive', VERIFIED: 'Verified', QUALIFIED: 'Qualified',
  FACT: 'Fact', INFERENCE: 'Inference', RECOMMENDATION: 'Recommendation',
  SUPPORTS: 'Supports', MEASURED: 'Measured', NOT_MEASURED: 'Not Measured',
  CASES_LOADED_NOT_RUN: 'Not Run',
};
const uiLabel = (value) => statusLabels[value] || value || '—';

async function api(path, options) {
  const response = await fetch(`/api/v1${path}`, options);
  if (!response.ok) throw Error(await response.text() || `Request failed: ${response.status}`);
  return response.json();
}

function setTitle(title) {
  $('#page-title').textContent = title;
  $$('#nav button').forEach((button) => {
    button.classList.toggle('active', button.dataset.page === state.page);
  });
}

function loading(label = 'Loading…') {
  return `<div class="loading-shell">
    <div class="skeleton wide"></div>
    <div class="skeleton medium"></div>
    <div class="panel empty"><span class="spinner"></span>${esc(label)}</div>
    <div class="skeleton large"></div>
  </div>`;
}

function errorView(errorObject) {
  const message = errorObject?.message || String(errorObject || 'Unknown error');
  return `<div class="state-panel error-state">
    <div class="state-icon">!</div>
    <h3>Unable to load</h3>
    <p>${esc(message)}</p>
    <button class="button secondary" onclick="navigate(state.page)">Retry</button>
  </div>`;
}

function emptyView(title, description, action = '') {
  return `<div class="empty"><strong>${esc(title)}</strong><p>${esc(description)}</p>${action}</div>`;
}

function badge(value, extra = '') {
  return `<span class="pill ${stateClass(value)} ${extra}">${esc(uiLabel(value || 'NOT_AVAILABLE'))}</span>`;
}

function metricKpi(label, data, formatter = money, unit = 'USD') {
  if (!data) return `<div class="panel kpi"><div class="label">${esc(label)}</div><div class="value">—</div><div class="change muted">No data returned</div></div>`;
  const delta = Number(data.delta || 0);
  const direction = delta >= 0 ? 'up' : 'down';
  return `<div class="panel kpi clickable" onclick="openMetricEvidence('${esc(label)}')">
    <div class="metric-card">
      <div>
        <div class="label">${esc(label)}</div>
        <div class="value">${formatter(data.current)}</div>
      </div>
      <div class="metric-icon">↗</div>
    </div>
    <div class="change ${direction}">${delta >= 0 ? '▲' : '▼'} ${formatter(Math.abs(delta))} · ${pct(Math.abs(data.change_pct))}</div>
    <div class="period">Current vs prior period · ${esc(unit)}</div>
  </div>`;
}

function trustStrip(dataset) {
  const status = dataset?.status || 'NOT_AVAILABLE';
  return `<div class="panel trust-strip">
    <div class="trust-item">
      <div class="trust-label">Dataset Status</div>
      <div class="trust-value ${status === 'READY' ? 'good' : 'warn'}">${esc(uiLabel(status))}</div>
      <div class="trust-sub">${esc(dataset?.snapshot_id || 'No snapshot')}</div>
    </div>
    <div class="trust-item">
      <div class="trust-label">Date Coverage</div>
      <div class="trust-value">${date(dataset?.business_date_min)} — ${date(dataset?.business_date_max)}</div>
      <div class="trust-sub">Snapshot end date</div>
    </div>
    <div class="trust-item">
      <div class="trust-label">Measured Rows</div>
      <div class="trust-value">${number(dataset?.measured_row_count)}</div>
      <div class="trust-sub">Not estimated</div>
    </div>
    <div class="trust-item">
      <div class="trust-label">Data Freshness</div>
      <div class="trust-value">${date(dataset?.validated_at)}</div>
      <div class="trust-sub">Last validated</div>
    </div>
    <div class="trust-item">
      <div class="trust-label">Run Mode</div>
      <div class="trust-value">Deterministic</div>
      <div class="trust-sub">Local read-only environment</div>
    </div>
  </div>`;
}

function recentRows(items, withActions = false) {
  if (!items?.length) return emptyView(
    'No analysis tasks yet',
    'Start with a business question. The system resolves context first, then executes governed analysis.',
    '<button class="button" onclick="navigate(\'new\')">Start Analysis</button>'
  );
  return items.map((task) => `
    <div class="analysis-row" onclick="openTask('${esc(task.task_id)}')">
      <div class="row-main">
        <div class="row-title">${esc(task.business_question)}</div>
        <div class="row-meta">${date(task.updated_at || task.created_at)} · ${esc(task.resolved_context?.dataset_snapshot || 'Context pending')} · ${esc(task.task_id.slice(0, 8))}</div>
      </div>
      <div class="row-end">${badge(task.state)}${withActions ? `<button class="icon-button row-action" onclick="event.stopPropagation();openTask('${esc(task.task_id)}')" aria-label="Open task">→</button>` : ''}</div>
    </div>
  `).join('');
}

// ─── Home ───────────────────────────────────────────────────────────────────

async function home() {
  setTitle('Home');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/home');
    state.analysisHistory = data.recent_analyses || [];
    const dataset = data.dataset || {};
    $('#app').innerHTML = `<div class="page-intro">
        <div>
          <span class="eyebrow">ENTERPRISE DATA AGENT</span>
          <h2>Turn business questions into traceable conclusions.</h2>
          <p>Start with natural language. The system resolves metrics, periods, and constraints before executing governed analysis.</p>
        </div>
        <button class="button primary" onclick="navigate('new')">＋ New Analysis</button>
      </div>

      ${trustStrip(dataset)}

      <div class="hero-question">
        <div class="question-box">
          <span class="eyebrow">START WITH A QUESTION</span>
          <h2>What do you want to understand?</h2>
          <p>Ask in business language. The system shows resolved metrics, exact dates, and dimensions before executing.</p>
          <div class="question-form">
            <textarea id="home-question" rows="2" placeholder="e.g., Compare wholesale sales for July vs June 2026, broken down by vendor"></textarea>
            <button class="button" onclick="submitHomeQuestion()">Start Analysis →</button>
          </div>
          <div class="suggestion-chips">
            ${(data.suggestions || []).slice(0, 4).map((item) => `<button class="chip" onclick="fillQuestion('${esc(item)}')">${esc(item)}</button>`).join('')}
          </div>
        </div>
        <div class="recommended">
          <div class="eyebrow">SUGGESTED EXPLORATIONS</div>
          <div class="suggestion-row" onclick="fillQuestion('Compare July vs June 2026 wholesale sales')"><span class="suggestion-icon">↗</span><span class="suggestion-text">Compare monthly performance and identify changes</span><span>→</span></div>
          <div class="suggestion-row" onclick="fillQuestion('Which vendors contributed most to the change?')"><span class="suggestion-icon">⌁</span><span class="suggestion-text">Find the largest contributors</span><span>→</span></div>
          <div class="suggestion-row" onclick="fillQuestion('Explain price, volume, and mix changes')"><span class="suggestion-icon">◌</span><span class="suggestion-text">Break down price / volume / mix</span><span>→</span></div>
          <div class="suggestion-row disabled-row"><span class="suggestion-icon">—</span><span class="suggestion-text">Consumer profit analysis</span><span class="unavailable">Unsupported</span></div>
        </div>
      </div>

      <div class="section-head">
        <div><span class="eyebrow">WORKSPACE PULSE</span><h3>Data Snapshot</h3></div>
        <span class="muted">${esc(dataset.snapshot_id || 'Snapshot unavailable')}</span>
      </div>
      <div class="grid grid-4">
        <div class="panel kpi">
          <div class="label">Data Through</div>
          <div class="value" style="font-size:20px">${date(dataset.business_date_max)}</div>
          <div class="change muted">${esc(dataset.status || 'NOT AVAILABLE')}</div>
        </div>
        <div class="panel kpi">
          <div class="label">Snapshot Rows</div>
          <div class="value">${number(dataset.measured_row_count)}</div>
          <div class="change muted">Measured, not estimated</div>
        </div>
        <div class="panel kpi">
          <div class="label">Completed Analyses</div>
          <div class="value">${number((data.recent_analyses || []).filter((item) => item.state === 'COMPLETED').length)}</div>
          <div class="change muted">Current workspace</div>
        </div>
        <div class="panel kpi">
          <div class="label">Spread Available From</div>
          <div class="value" style="font-size:20px">2025-07</div>
          <div class="change muted">Earlier periods show unavailable</div>
        </div>
      </div>

      <div class="content-grid two-col">
        <div>
          <div class="section-head">
            <div><span class="eyebrow">RECOMMENDED</span><h3>Suggested Analyses</h3></div>
          </div>
          <div class="suggestion-list">
            ${(data.suggestions || []).map((item, index) => `
              <button class="suggestion-card" onclick="fillQuestion('${esc(item)}')">
                <span class="suggestion-number">0${index + 1}</span>
                <span><strong>${esc(item)}</strong><small>Structured plan · Evidence chain · Report</small></span>
                <span class="arrow">→</span>
              </button>
            `).join('')}
          </div>
        </div>
        <div>
          <div class="section-head">
            <div><span class="eyebrow">RECENT</span><h3>Recent Analyses</h3></div>
            <button class="button ghost" onclick="navigate('history')">View all →</button>
          </div>
          <div class="panel">
            <div class="analysis-list">${recentRows(data.recent_analyses, true)}</div>
          </div>
        </div>
      </div>

      <div class="section-head">
        <div><span class="eyebrow">LIMITATIONS</span><h3>Data Quality & Usage Boundaries</h3></div>
        <button class="button ghost" onclick="navigate('data')">View data status →</button>
      </div>
      <div class="panel limitation-grid">
        <div><span class="status-mark good">✓</span><strong>Source traceable</strong><p>Source assets, snapshots, hashes, and validation status come from the data manifest.</p></div>
        <div><span class="status-mark warn">!</span><strong>This is wholesale orders</strong><p>Not consumer POS sales, not equivalent to store profit.</p></div>
        <div><span class="status-mark info">i</span><strong>Contribution is not causation</strong><p>Contribution analysis describes observed correlations, not business causation.</p></div>
      </div>`;
  } catch (errorObject) {
    $('#app').innerHTML = errorView(errorObject);
  }
}

function fillQuestion(question) {
  if (state.page !== 'new') navigate('new');
  setTimeout(() => {
    const input = $('#question');
    if (input) { input.value = question; input.focus(); }
  }, 40);
}

function submitHomeQuestion() {
  const question = $('#home-question')?.value.trim();
  if (!question) return toast('Enter a business question first');
  navigate('new');
  setTimeout(() => {
    $('#question').value = question;
    submitQuestion();
  }, 40);
}

// ─── New Analysis ────────────────────────────────────────────────────────────

async function newPage() {
  setTitle('New Analysis');
  $('#app').innerHTML = `<div class="page-intro">
      <div>
        <span class="eyebrow">NEW ANALYSIS</span>
        <h2>Start with a business question</h2>
        <p>Before execution, metrics, periods, comparison dimensions, and data limits are resolved from the backend contract.</p>
      </div>
      <button class="button secondary" onclick="navigate('home')">Cancel</button>
    </div>

    <div class="new-analysis-grid">
      <div class="panel form-panel">
        <label class="field-label" for="question">Business Question</label>
        <textarea id="question" class="textarea" placeholder="e.g., Compare July vs June 2026 wholesale sales by vendor to find top contributors"></textarea>
        <div class="examples">
          <span class="muted">Example questions</span>
          <button class="chip" onclick="fillQuestion('Compare July vs June 2026 wholesale sales')">July vs June</button>
          <button class="chip" onclick="fillQuestion('Which vendors contributed most to July 2026 sales change?')">Vendor contribution</button>
          <button class="chip" onclick="fillQuestion('Explain price, volume, and mix changes for July 2026')">Price / Volume / Mix</button>
          <button class="chip" onclick="fillQuestion('Why did store profit decline in July 2026?')">Test support boundary</button>
        </div>
        <div class="action-row">
          <button class="button" onclick="submitQuestion()">Resolve and Create Analysis →</button>
          <span class="muted">Read-only queries · Budget limited · Results traceable</span>
        </div>
      </div>

      <div class="panel resolved-preview">
        <span class="eyebrow">RESOLVED REQUEST</span>
        <h3>Pre-execution resolution</h3>
        <div class="pending-resolution">
          <span class="status-mark info">i</span>
          <div>
            <strong>Awaiting business question</strong>
            <p>After submission, this shows the backend-resolved metrics, exact dates, dimensions, filters, and limits.</p>
          </div>
        </div>
        <div class="resolution-principles">
          <div><strong>Semantics</strong><span>Versioned metrics and dimensions</span></div>
          <div><strong>Governance</strong><span>Read-only objects and query budget</span></div>
          <div><strong>Evidence</strong><span>Observations, calculations, snapshot references</span></div>
        </div>
      </div>
    </div>

    <div class="section-head">
      <div><span class="eyebrow">WHAT HAPPENS NEXT</span><h3>Path of one analysis</h3></div>
    </div>
    <div class="path-strip">
      <div><b>01</b><strong>Resolve context</strong><span>Metrics · Periods · Scope</span></div>
      <div><b>02</b><strong>Generate plan</strong><span>Baseline · Drivers · Validation</span></div>
      <div><b>03</b><strong>Execute investigation</strong><span>Query · Observe · Hypothesize</span></div>
      <div><b>04</b><strong>Deliver evidence</strong><span>Conclusion · Report · Next steps</span></div>
    </div>`;
}

async function submitQuestion() {
  const question = $('#question')?.value.trim();
  if (!question || question.length < 3) return toast('Enter at least 3 characters');
  $('#app').innerHTML = loading('Resolving question and creating analysis task…');
  try {
    const task = await api('/analysis-tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    await openTask(task.task_id);
  } catch (errorObject) {
    $('#app').innerHTML = errorView(errorObject);
  }
}

// ─── Task / Workspace ────────────────────────────────────────────────────────

async function openTask(taskId, tab = 'overview') {
  try {
    state.taskId = taskId;
    state.page = 'workspace';
    state.workspaceTab = tab;
    state.task = await api(`/analysis-tasks/${encodeURIComponent(taskId)}`);
    renderWorkspace();
  } catch (errorObject) {
    $('#app').innerHTML = errorView(errorObject);
  }
}

function taskContext(task) {
  const context = task.resolved_context || {};
  return `<div class="task-context">
    <span>${badge(task.state)}</span>
    <span class="context-chip">Dataset · ${esc(context.dataset_snapshot || 'Pending')}</span>
    <span class="context-chip">Period · ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}</span>
    <span class="context-chip">Task · ${esc(task.task_id.slice(0, 12))}</span>
  </div>`;
}

function renderWorkspace() {
  const task = state.task;
  document.body.classList.add('session-mode');
  setTitle('Analysis Workspace');
  const active = state.workspaceTab || 'overview';
  $('#app').innerHTML = workspaceMarkup(task, active);
}

function workspaceMarkup(task, active) {
  const context = task.resolved_context || {};
  const tabs = [
    ['overview', 'Overview'], ['context', 'Context'], ['plan', 'Plan'],
    ['investigation', 'Investigation'], ['dashboard', 'Dashboard'],
    ['findings', 'Findings'], ['evidence', 'Evidence'], ['report', 'Report'],
  ];
  const body = active === 'overview' ? overviewView(task) : workspaceBody(task, active);
  return `<div class="analysis-head">
    <div class="analysis-breadcrumb">
      <button class="back-link" onclick="navigate('history')">Analysis History</button>
      <span>/</span><span>${esc(task.task_id.slice(0, 12))}</span>
    </div>
    <div class="analysis-head-row">
      <div>
        <h2>${esc(task.business_question)}</h2>
        ${taskContext(task)}
      </div>
      <div class="action-row">
        <button class="button secondary" onclick="followUp('${esc(task.task_id)}')">＋ Follow-up</button>
        <button class="button" onclick="workspaceTab('report')">Export Report →</button>
      </div>
    </div>
  </div>

  ${task.clarification ? clarificationPanel(task) : ''}
  ${task.coverage_warning ? `<div class="notice warning"><strong>Data coverage note</strong><p>${esc(task.coverage_warning)}</p></div>` : ''}

  <nav class="workspace-tabs" aria-label="Analysis views">
    ${tabs.map(([key, label]) => `
      <button class="${active === key ? 'active' : ''}" onclick="workspaceTab('${key}')">${label}</button>
    `).join('')}
  </nav>

  <div class="workspace-content ${active === 'overview' ? 'overview-layout' : ''}">
    <main>${body}</main>
    ${active === 'overview' ? `<aside class="source-rail panel">
      ${inspectorContent(task, state.selectedEvidence)}
      <div class="rail-divider"></div>
      <div class="rail-meta">
        <span class="eyebrow">SOURCE CONTEXT</span>
        <strong>${esc(context.metrics?.[0]?.label || 'Metric not returned')}</strong>
        <small>${esc(context.semantic_version || 'Semantic version not returned')} · ${esc(context.context_version || 'Context version not returned')}</small>
        <button class="text-link" onclick="workspaceTab('context')">View full context →</button>
      </div>
    </aside>` : ''}
  </div>`;
}

function clarificationPanel(task) {
  return `<div class="notice clarification">
    <strong>Clarification required to continue</strong>
    <p>${esc(task.clarification.question)}</p>
    <div class="inline-form">
      <input id="clarification-response" class="filter" placeholder="Enter your selection or additional context" />
      <button class="button" onclick="submitClarification('${esc(task.task_id)}')">Submit Clarification</button>
    </div>
  </div>`;
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
  return `<div class="trust-strip compact-strip">
    <div class="trust-item"><div class="trust-label">Task Status</div><div class="trust-value">${esc(task.state)}</div></div>
    <div class="trust-item"><div class="trust-label">Primary Metric</div><div class="trust-value">${esc(task.resolved_context?.metrics?.[0]?.label || '—')}</div></div>
    <div class="trust-item"><div class="trust-label">Validations</div><div class="trust-value ${task.validations?.length || task.state === 'COMPLETED' ? 'good' : 'warn'}">${task.validations?.length || task.state === 'COMPLETED' ? 'Returned' : 'Pending'}</div></div>
    <div class="trust-item"><div class="trust-label">Evidence</div><div class="trust-value">${number(task.evidence?.length || 0)} items</div></div>
  </div>

  <div class="grid grid-4">
    ${metricKpi('Wholesale Sales Amount', summary.wholesale_sales_amount)}
    ${metricKpi('Bottles Ordered', summary.bottles_ordered, number, 'bottles')}
    ${metricKpi('Avg Wholesale Price/Bottle', summary.average_wholesale_price_per_bottle, moneyPrecise, 'USD / bottle')}
    ${metricKpi('Wholesale Gross Spread', summary.wholesale_gross_spread)}
  </div>

  <div class="content-grid two-col section-gap">
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">TREND</span><h3>Monthly Performance</h3></div>
        <span class="source-label">${esc(task.resolved_context?.dataset_snapshot || 'Source pending')}</span>
      </div>
      <p class="muted">Wholesale order amount · USD · click metric to open evidence</p>
      ${trend.length ? `<div class="bar-chart" role="img" aria-label="Monthly wholesale sales trend">
        ${trend.slice(-12).map((item) => `<div class="bar-column">
          <span class="bar-value">${money(item.wholesale_sales_amount)}</span>
          <div class="bar-track"><div class="bar" style="height:${Math.max(5, Math.abs(item.wholesale_sales_amount || 0) / max * 160)}px"></div></div>
          <span class="bar-label">${esc(item.dimension_value)}</span>
        </div>`).join('')}
      </div>` : emptyView('No trend results', 'No trend observations returned for this task.')}
    </div>
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">CLAIMS</span><h3>Key Findings</h3></div>
        <button class="button ghost" onclick="workspaceTab('evidence')">Evidence →</button>
      </div>
      ${claimsList(task)}
    </div>
  </div>

  <div class="section-head">
    <div><span class="eyebrow">DECOMPOSITION</span><h3>Sales Change Breakdown</h3></div>
    <button class="button ghost" onclick="workspaceTab('dashboard')">Go to Dashboard →</button>
  </div>
  <div class="panel pvm-grid">
    ${Object.entries(task.pvm || {}).map(([key, value]) => `<div>
      <div class="label">${esc(key.replaceAll('_', ' '))}</div>
      <div class="value">${money(value)}</div>
      <div class="muted">Backend computed</div>
    </div>`).join('') || emptyView('No decomposition available', 'Requires wholesale sales, bottles, and average price to all be available.')}
  </div>`;
}

function claimsList(task) {
  return task.claims?.length ? task.claims.map((claim, index) => `
    <button class="finding claim-button" onclick="openEvidence(${index})">
      <div class="finding-head"><span>${badge(claim.type)}</span>${badge(claim.status)}</div>
      <strong>${esc(claim.statement)}</strong>
      <small>Evidence ${claim.evidence_ids?.length || 0} items · Click for sources</small>
    </button>
  `).join('') : emptyView('No conclusions generated', 'This task did not return any claimable findings.');
}

// ─── Context ─────────────────────────────────────────────────────────────────

function contextView(task) {
  const context = task.resolved_context || {};
  const rows = [
    ['Context Version', context.context_version],
    ['Dataset Snapshot', context.dataset_snapshot],
    ['Dataset Status', context.dataset_status],
    ['Semantic Version', context.semantic_version],
    ['Dimension / Granularity', context.dimension || 'Overall'],
    ['Allowed Objects', context.allowed_objects?.join(', ')],
    ['Filters', Object.entries(context.filters || {}).map(([k, v]) => `${k}: ${v}`).join(' · ')],
    ['Primary Period', `${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}`],
    ['Comparison Period', `${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}`],
  ];
  return `<div class="panel">
    <div class="panel-heading">
      <div><span class="eyebrow">RESOLVED CONTEXT</span><h3>Backend resolution result</h3></div>
      ${badge(context.dataset_status || 'NOT AVAILABLE')}
    </div>
    <p class="muted">The fields below come from the task context contract. The frontend does not recompute or rewrite metric definitions locally.</p>
    <dl>
      ${rows.map(([key, value]) => `<div class="definition"><dt>${esc(key)}</dt><dd>${esc(value || '—')}</dd></div>`).join('')}
    </dl>
    ${context.metrics?.length ? `<div class="subsection"><h4>Resolved Metrics</h4>
      ${context.metrics.map((metric) => `<div class="metric-definition">
        <strong>${esc(metric.label)}</strong>
        <span class="code">${esc(metric.id)}</span>
        <p>${esc(metric.description || '')}</p>
        <small>${esc(metric.expression || '')} · ${esc(metric.unit || '')} · ${esc(metric.availability || '')}</small>
      </div>`).join('')}
    </div>` : ''}
    ${context.quality_warnings?.length ? `<div class="notice warning"><strong>Quality warnings</strong>
      <ul>${context.quality_warnings.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>
    </div>` : ''}
  </div>`;
}

// ─── Plan ─────────────────────────────────────────────────────────────────────

function planView(task) {
  const plan = task.plan || {};
  const steps = plan.steps || [];
  return `<div class="panel">
    <div class="panel-heading">
      <div><span class="eyebrow">GOVERNED PLAN</span><h3>Analysis Plan</h3></div>
      <span class="source-label">${steps.length} steps</span>
    </div>
    <p class="muted">Plan is generated by the backend. Click a step to see the corresponding event and observation.</p>
    ${steps.length ? `<div class="plan-list">
      ${steps.map((step, index) => `<button class="plan-step" onclick="focusPlanStep(${index})">
        <span class="plan-index">${index + 1}</span>
        <span><strong>${esc(step.title || step.name || `Step ${index + 1}`)}</strong>
        <small>${esc(step.description || step.objective || step.status || 'In task plan')}</small></span>
        <span>→</span>
      </button>`).join('')}
    </div>` : emptyView('Plan not yet returned', 'The plan may be generated after clarification is complete or data becomes available.')}
  </div>
  <div class="content-grid two-col section-gap">
    <div class="panel">
      <h3>Plan Constraints</h3>
      <div class="definition"><dt>Max queries</dt><dd>Returned by backend budget contract</dd></div>
      <div class="definition"><dt>Allowed objects</dt><dd>${esc(task.resolved_context?.allowed_objects?.join(', ') || '—')}</dd></div>
    </div>
    <div class="panel">
      <h3>Task Events</h3>
      ${timeline(task.events || [])}
    </div>
  </div>`;
}

// ─── Investigation ───────────────────────────────────────────────────────────

function investigationView(task) {
  const hypotheses = task.hypotheses || [];
  return `<div class="content-grid three-col">
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">HYPOTHESES</span><h3>Hypotheses</h3></div>
        <button class="button ghost" onclick="followUp('${esc(task.task_id)}')">Follow-up →</button>
      </div>
      ${hypotheses.length ? hypotheses.map((hypothesis, index) => `<button class="hypothesis ${index === 0 ? 'selected' : ''}" onclick="selectHypothesis(this)">
        <span class="hypothesis-mark">${hypothesis.state === 'SUPPORTED' ? '✓' : '?'}</span>
        <span><strong>${esc(hypothesis.topic || hypothesis.statement)}</strong>
        <small>${esc(hypothesis.statement || '')}</small></span>
        ${badge(hypothesis.state)}
      </button>`).join('') : emptyView('No backend hypotheses', 'No investigation hypotheses were returned for this task.')}
    </div>
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">TIMELINE</span><h3>Investigation Timeline</h3></div>
        <span class="source-label">Event log</span>
      </div>
      ${timeline(task.events || [])}
    </div>
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">SELECTED EVIDENCE</span><h3>Evidence Inspector</h3></div>
      </div>
      ${inspectorContent(task, state.selectedEvidence)}
    </div>
  </div>
  ${contributionTable(task, true)}`;
}

function timeline(events) {
  if (!events.length) return emptyView('No events yet', 'Task events are written during backend execution.');
  return `<div class="timeline">
    ${events.map((event) => `<div class="timeline-item">
      <span class="timeline-mark"></span>
      <div><strong>${esc(event.message || event.event_type)}</strong>
      <small>${date(event.occurred_at)} · ${esc(event.event_type)}</small></div>
    </div>`).join('')}
  </div>`;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function dashboardView(task, embedded = false) {
  const rows = (task.contributions || []).filter((row) =>
    !state.dashboardSearch || String(row.dimension_value).toLowerCase().includes(state.dashboardSearch.toLowerCase())
  );
  const trend = task.trend || [];
  const summary = task.summary || {};
  const maxVal = Math.max(...trend.map((x) => Math.abs(x.wholesale_sales_amount || 0)), 1);
  return `<div class="dashboard-toolbar">
    <div>
      <span class="eyebrow">DYNAMIC BI</span>
      <h3>${embedded ? 'Task Dashboard' : 'Dashboard'}</h3>
      <small>${esc(task.resolved_context?.metrics?.[0]?.label || 'Metric pending')} · ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)} vs ${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}</small>
    </div>
    <div class="filter-bar">
      <span class="filter-static">Snapshot · ${esc(task.resolved_context?.dataset_snapshot || '—')}</span>
      <select class="filter" onchange="requestBreakdown(this.value)">
        <option value="">Dimension · ${esc(task.resolved_context?.dimension || 'Overall')}</option>
        <option value="vendor">Break down by vendor</option>
        <option value="category">Break down by category</option>
        <option value="store">Break down by store</option>
        <option value="county">Break down by county</option>
      </select>
      <input class="filter search" value="${esc(state.dashboardSearch)}" oninput="setDashboardSearch(this.value)" placeholder="Filter table…" />
      <button class="button ghost" onclick="resetDashboard()">Reset</button>
    </div>
  </div>

  <div class="grid grid-4">
    ${metricKpi('Wholesale Sales Amount', summary.wholesale_sales_amount)}
    ${metricKpi('Bottles Ordered', summary.bottles_ordered, number, 'bottles')}
    ${metricKpi('Avg Wholesale Price/Bottle', summary.average_wholesale_price_per_bottle, moneyPrecise, 'USD / bottle')}
    ${metricKpi('Wholesale Gross Spread', summary.wholesale_gross_spread)}
  </div>

  <div class="content-grid two-col section-gap">
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">TREND</span><h3>Period Trend</h3></div>
        <span class="source-label">Data source · ${esc(task.resolved_context?.dataset_snapshot || '—')}</span>
      </div>
      ${trend.length ? `<div class="bar-chart dashboard-chart">
        ${trend.slice(-12).map((item) => `<div class="bar-column">
          <span class="bar-value">${money(item.wholesale_sales_amount)}</span>
          <div class="bar-track"><div class="bar" style="height:${Math.max(5, (Math.abs(item.wholesale_sales_amount || 0) / maxVal) * 160)}px"></div></div>
          <span class="bar-label">${esc(item.dimension_value)}</span>
        </div>`).join('')}
      </div>` : emptyView('No trend', 'No trend observations returned by backend.')}
    </div>
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">ACTIONS</span><h3>Chart Actions</h3></div>
      </div>
      <div class="action-menu-grid">
        <button onclick="toast('Record drill-through not available in this backend')">View records (unavailable)</button>
        <button onclick="followUp('${esc(task.task_id)}')">Investigate with AI</button>
        <button onclick="workspaceTab('evidence')">View supporting evidence</button>
      </div>
      <div class="notice info"><strong>Interaction boundary</strong>
        <p>Dimension switching creates a real follow-up task with the new dimension. Filtering only applies to contributions already returned by the backend.</p>
      </div>
    </div>
  </div>
  ${contributionTable({ ...task, contributions: rows }, true)}`;
}

function contributionTable(task, actions = false) {
  const rows = task.contributions || [];
  return `<div class="section-head">
    <div><span class="eyebrow">CONTRIBUTION</span><h3>Contribution Ranking</h3></div>
    <span class="muted">${rows.length} backend-returned results</span>
  </div>
  <div class="panel table-wrap">
    <table class="data-table">
      <thead><tr>
        <th>Dimension Value</th><th>Current Period</th><th>Comparison Period</th><th>Change</th>
        ${actions ? '<th>Actions</th>' : ''}
      </tr></thead>
      <tbody>
        ${rows.length ? rows.map((row, index) => `<tr>
          <td><strong>${esc(row.dimension_value)}</strong></td>
          <td>${money(row.current)}</td>
          <td>${money(row.comparison)}</td>
          <td class="${Number(row.delta || 0) >= 0 ? 'up' : 'down'}">${money(row.delta)}</td>
          ${actions ? `<td><button class="table-link" onclick="openContributionEvidence(${index})">Evidence / Action →</button></td>` : ''}
        </tr>`).join('') : `<tr><td colspan="${actions ? 5 : 4}">${emptyView('No contribution results', 'This task did not return a contribution ranking.')}</td></tr>`}
      </tbody>
    </table>
  </div>`;
}

// ─── Findings ─────────────────────────────────────────────────────────────────

function findingsView(task) {
  return `<div class="panel">
    <div class="panel-heading">
      <div><span class="eyebrow">FINDINGS</span><h3>Evidence-Supported Findings</h3></div>
      <span class="source-label">${task.claims?.length || 0} claims</span>
    </div>
    <p class="muted">Type, status, and limits all come from backend claims. Contribution results are not interpreted as causal.</p>
    ${claimsList(task)}
  </div>
  <div class="panel section-gap">
    <h3>Limitations & Boundaries</h3>
    ${task.limitations?.length ? `<ul class="limitations">${task.limitations.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>` : '<p class="muted">No additional limitations returned for this task.</p>'}
  </div>`;
}

// ─── Evidence ─────────────────────────────────────────────────────────────────

function evidenceView(task) {
  return `<div class="evidence-layout">
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">EVIDENCE LIBRARY</span><h3>Evidence Chain</h3></div>
        <input class="filter search" placeholder="Search claim / hash" oninput="filterEvidence(this.value)" />
      </div>
      <div id="evidence-list">${evidenceItems(task)}</div>
    </div>
    <div class="panel evidence-detail">${inspectorContent(task, state.selectedEvidence)}</div>
  </div>`;
}

function evidenceItems(task) {
  const items = task.evidence || [];
  return items.length ? items.map((evidence, index) => {
    const claim = task.claims?.find((item) => item.claim_id === evidence.claim_id) || task.claims?.[index];
    return `<button class="evidence-item" data-search="${esc(`${claim?.statement || ''} ${evidence.result_hash || ''}`)}" onclick="openEvidence(${index})">
      <span class="evidence-type">${esc(claim?.type || 'EVIDENCE')}</span>
      <span class="evidence-content"><strong>${esc(claim?.statement || 'Verified result')}</strong>
      <small>${esc(evidence.relation)} · ${esc(evidence.observation_ids?.join(', ') || 'observation unavailable')}</small></span>
      <span class="evidence-arrow">→</span>
    </button>`;
  }).join('') : emptyView('No evidence yet', 'Backend has not returned any provenance references yet.');
}

function inspectorContent(task, selectedIndex = null) {
  const index = selectedIndex == null ? 0 : selectedIndex;
  const evidence = task.evidence?.[index];
  const claim = task.claims?.find((item) => item.claim_id === evidence?.claim_id) || task.claims?.[index];
  if (!evidence && !claim) return `<div class="inspector-title"><h3>Evidence Inspector</h3></div>
    ${emptyView('Select a finding', 'Click a KPI, finding, or contribution result to view its evidence source.')}`;
  const checks = evidence?.validation || [];
  return `<div class="inspector-title">
    <div><span class="eyebrow">EVIDENCE INSPECTOR</span><h3>Evidence Inspector</h3></div>
    <button class="icon-button" onclick="closeInspector()" aria-label="Close">×</button>
  </div>
  <div class="claim-box">
    <div class="finding-head">${badge(claim?.type || 'CLAIM')}${badge(claim?.status || 'NOT AVAILABLE')}</div>
    <strong>${esc(claim?.statement || 'Verified result')}</strong>
  </div>
  <div class="inspector-section">
    <h4>Relation</h4><p>${esc(evidence?.relation || '—')}</p>
    <h4>Impact</h4><p>${claim?.impact ? esc(claim.impact) : 'Impact not returned by backend'}</p>
  </div>
  <div class="inspector-section">
    <h4>EVIDENCE</h4>
    <p><strong>Observation</strong> · ${esc(evidence?.observation_ids?.join(', ') || '—')}</p>
    <p><strong>Metric</strong> · ${esc(evidence?.metric_version || '—')}</p>
    <p><strong>Dataset</strong> · ${esc(evidence?.dataset_snapshot || '—')}</p>
    <p><strong>Context</strong> · ${esc(evidence?.context_version || '—')}</p>
    <p class="code hash">${esc(evidence?.result_hash || 'hash unavailable')}</p>
  </div>
  <div class="inspector-section">
    <h4>VALIDATION</h4>
    ${checks.length ? `<div class="validation-list">
      ${checks.map((check) => `<div class="validation-item ok"><span>✓</span>${esc(check)}</div>`).join('')}
    </div>` : '<p class="muted">Backend did not return validation checks. Not shown as validated.</p>'}
  </div>
  <div class="inspector-actions">
    <button class="button" onclick="followUp('${esc(task.task_id)}')">Investigate Further →</button>
    <button class="button secondary" onclick="copyReference('${esc(evidence?.evidence_id || '')}')">Copy Reference</button>
  </div>`;
}

// ─── Report ───────────────────────────────────────────────────────────────────

function reportView(task) {
  const claims = task.claims || [];
  const limitations = task.limitations || claims.flatMap((claim) => claim.limitations || []);
  return `<div class="report-toolbar">
    <div>
      <span class="eyebrow">SAVED ARTIFACT</span>
      <h3>Analysis Report</h3>
      <p class="muted">Content is composed from claims and evidence saved by the current task.</p>
    </div>
    <div class="report-actions">
      <a class="button secondary" href="/api/v1/analysis-tasks/${esc(task.task_id)}/artifacts/report.md" target="_blank">Markdown</a>
      <a class="button" href="/api/v1/analysis-tasks/${esc(task.task_id)}/artifacts/report.html" target="_blank">Open HTML →</a>
    </div>
  </div>
  <div class="report-body panel">
    <div class="report-section">
      <span class="eyebrow">EXECUTIVE SUMMARY</span>
      <h2>${esc(task.business_question)}</h2>
      <p>Task status: ${esc(task.state)}. Period: ${date(task.periods?.primary?.start)} — ${date(task.periods?.primary?.end)}, compared to ${date(task.periods?.comparison?.start)} — ${date(task.periods?.comparison?.end)}.</p>
    </div>
    <div class="report-section">
      <h3>Business Performance</h3>
      <div class="grid grid-3">
        ${metricKpi('Wholesale Sales Amount', task.summary?.wholesale_sales_amount)}
        ${metricKpi('Bottles Ordered', task.summary?.bottles_ordered, number, 'bottles')}
        ${metricKpi('Wholesale Gross Spread', task.summary?.wholesale_gross_spread)}
      </div>
    </div>
    <div class="report-section">
      <h3>Key Findings</h3>
      ${claims.length ? claims.map((claim, index) => `<div class="report-finding">
        <div>${badge(claim.type)} ${badge(claim.status)}</div>
        <strong>${esc(claim.statement)}</strong>
        <small>Evidence ${claim.evidence_ids?.length || 0} items · <button class="table-link" onclick="openEvidence(${index})">View source</button></small>
      </div>`).join('') : '<p class="muted">No saved findings.</p>'}
    </div>
    <div class="report-section">
      <h3>Supporting Evidence</h3>
      <p>This task saved ${number(task.evidence?.length || 0)} evidence references. Dataset: <span class="code">${esc(task.resolved_context?.dataset_snapshot || '—')}</span>.</p>
    </div>
    <div class="report-section">
      <h3>Limitations</h3>
      ${limitations.length ? `<ul class="limitations">${limitations.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>` : '<p class="muted">No additional limitations returned by backend.</p>'}
    </div>
  </div>`;
}

// ─── History ──────────────────────────────────────────────────────────────────

async function history() {
  setTitle('History');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/analysis-tasks');
    state.analysisHistory = data.tasks || [];
    const tasks = data.tasks || [];
    const completed = tasks.filter((t) => t.state === 'COMPLETED');
    const inProgress = tasks.filter((t) => t.state !== 'COMPLETED');
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">ANALYSIS HISTORY</span><h2>${tasks.length} Analysis${tasks.length !== 1 ? 's' : ''}</h2>
      <p>${completed.length} completed, ${inProgress.length} in progress.</p></div>
      <button class="button primary" onclick="navigate('new')">＋ New Analysis</button>
    </div>
    ${inProgress.length ? `<div class="section-head"><div><span class="eyebrow">IN PROGRESS</span><h3>${inProgress.length} active</h3></div></div>
      <div class="panel"><div class="analysis-list">${recentRows(inProgress, true)}</div></div>` : ''}
    ${completed.length ? `<div class="section-head"><div><span class="eyebrow">COMPLETED</span><h3>${completed.length} finished</h3></div></div>
      <div class="panel"><div class="analysis-list">${recentRows(completed, true)}</div></div>` : ''}
    ${!tasks.length ? emptyView('No analyses yet', 'Create your first analysis from the Home page.', '<button class="button" onclick="navigate(\'new\')">Start Analysis</button>') : ''}`;
  } catch (errorObject) {
    $('#app').innerHTML = errorView(errorObject);
  }
}

// ─── Data Sources ─────────────────────────────────────────────────────────────

async function data() {
  setTitle('Data Sources');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/home');
    const dataset = data.dataset || {};
    const metrics = data.metrics || [];
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">DATA GOVERNANCE</span><h2>Data Sources</h2>
      <p>Semantic definitions, dataset snapshots, and availability status.</p></div>
    </div>
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">SNAPSHOT</span><h3>Current Dataset</h3></div>
        ${badge(dataset.status || 'NOT AVAILABLE')}
      </div>
      <div class="grid grid-4">
        <div><div class="label">Snapshot ID</div><div class="value" style="font-size:16px">${esc(dataset.snapshot_id || '—')}</div></div>
        <div><div class="label">Date Range</div><div class="value" style="font-size:16px">${date(dataset.business_date_min)} — ${date(dataset.business_date_max)}</div></div>
        <div><div class="label">Measured Rows</div><div class="value" style="font-size:16px">${number(dataset.measured_row_count)}</div></div>
        <div><div class="label">Last Validated</div><div class="value" style="font-size:16px">${date(dataset.validated_at)}</div></div>
      </div>
    </div>
    <div class="section-head"><div><span class="eyebrow">SEMANTIC LAYER</span><h3>Metrics</h3></div></div>
    <div class="panel table-wrap">
      <table class="data-table">
        <thead><tr><th>Label</th><th>Unit</th><th>Availability</th><th>Description</th></tr></thead>
        <tbody>
          ${metrics.map((m) => `<tr>
            <td><strong>${esc(m.label)}</strong><small>${esc(m.id)}</small></td>
            <td>${esc(m.unit || '—')}</td>
            <td>${esc(m.availability || '—')}</td>
            <td>${esc(m.description || '—')}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  } catch (errorObject) {
    $('#app').innerHTML = errorView(errorObject);
  }
}

// ─── Semantic Layer ───────────────────────────────────────────────────────────

async function semantic() {
  setTitle('Semantic Layer');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/semantic');
    const definitions = data.definitions || [];
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">SEMANTIC LAYER</span><h2>Metric Definitions</h2>
      <p>Business metric definitions, computation logic, and data lineage.</p></div>
    </div>
    ${definitions.length ? definitions.map((def) => `<div class="panel">
      <div class="panel-heading"><h3>${esc(def.label)}</h3><span class="code">${esc(def.id)}</span></div>
      <p>${esc(def.description || 'No description')}</p>
      <div class="definition"><dt>Expression</dt><dd><span class="code">${esc(def.expression || '—')}</span></dd></div>
      <div class="definition"><dt>Unit</dt><dd>${esc(def.unit || '—')}</dd></div>
      <div class="definition"><dt>Data Source</dt><dd>${esc(def.source || '—')}</dd></div>
    </div>`).join('') : emptyView('No definitions', 'Semantic layer definitions are not available from the backend.')}`;
  } catch (errorObject) {
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">SEMANTIC LAYER</span><h2>Metric Definitions</h2>
      <p>Business metric definitions managed by the governance layer.</p></div>
    </div>
    <div class="panel">
      <p class="muted">Semantic layer definitions are maintained in the governance configuration. Connect to the backend API to view current definitions.</p>
    </div>`;
  }
}

// ─── Evaluation ───────────────────────────────────────────────────────────────

async function evaluation() {
  setTitle('Evaluation');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/evaluation');
    const suites = (data.metrics || []).filter((m) => m.status === 'MEASURED').map((m) => ({ name: m.name, score: m.value }));
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">QUALITY ASSURANCE</span><h2>Evaluation Center</h2>
      <p>Regression testing, quality metrics, and prompt versioning.</p></div>
      <button class="button secondary" onclick="runEvaluation()">Run Full Suite</button>
    </div>
    <div class="panel">
      <div class="panel-heading">
        <div><span class="eyebrow">STATUS</span><h3>${esc(data.status || 'NOT RUN')}</h3></div>
        <span class="source-label">${data.case_count || 0} test cases · Suite ${esc(data.suite_version || 'unknown')}</span>
      </div>
      <p class="muted">${esc(data.note || '')}</p>
    </div>
    ${suites.length ? `<div class="panel section-gap">
      <div class="panel-heading"><h3>Measured Metrics</h3></div>
      <div class="run-summary">
        ${suites.map((suite) => `<div>
          <strong>${number(suite.score)}%</strong>
          <span>${esc(suite.name)}</span>
        </div>`).join('')}
      </div>
    </div>` : ''}`;
  } catch (errorObject) {
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">QUALITY ASSURANCE</span><h2>Evaluation Center</h2>
      <p>Regression testing, quality metrics, and prompt versioning.</p></div>
    </div>
    <div class="panel">
      <p class="muted">Evaluation endpoint not available. Run the evaluation suite from the CLI:</p>
      <pre style="font-size:12px;background:#f1f4f5;padding:14px;border-radius:6px;overflow:auto">python -m evaluation.run --suite=all</pre>
    </div>`;
  }
}

async function runEvaluation() {
  toast('Running evaluation suite…');
  try {
    const result = await api('/evaluation/run', { method: 'POST' });
    toast(`Done: ${result.passed}/${result.results?.length || 0} passed`);
    await evaluation();
  } catch (e) {
    toast('Evaluation run failed');
  }
}

// ─── Settings ─────────────────────────────────────────────────────────────────

async function settings() {
  setTitle('Settings');
  $('#app').innerHTML = loading();
  try {
    const data = await api('/settings');
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">SYSTEM</span><h2>Settings</h2>
      <p>Application configuration and preferences.</p></div>
    </div>
    <div class="panel">
      <div class="panel-heading"><h3>Application Info</h3></div>
      <div class="definition"><dt>Version</dt><dd>${esc(data.analysis_budget ? '2.0.0' : '2.0.0')}</dd></div>
      <div class="definition"><dt>Provider</dt><dd>${esc(data.provider || 'deterministic')}</dd></div>
      <div class="definition"><dt>Dataset Version</dt><dd>${esc(data.dataset_version || '—')}</dd></div>
      <div class="definition"><dt>Semantic Version</dt><dd>${esc(data.semantic_version || 'unavailable')}</dd></div>
    </div>
    <div class="panel section-gap">
      <div class="panel-heading"><h3>Budget</h3></div>
      <div class="definition"><dt>Max Queries</dt><dd>${esc(String(data.analysis_budget?.max_queries || '—'))}</dd></div>
      <div class="definition"><dt>Max Tool Calls</dt><dd>${esc(String(data.analysis_budget?.max_tool_calls || '—'))}</dd></div>
      <div class="definition"><dt>Max Result Rows</dt><dd>${esc(String(data.analysis_budget?.max_result_rows || '—'))}</dd></div>
    </div>`;
  } catch (errorObject) {
    $('#app').innerHTML = `<div class="page-intro">
      <div><span class="eyebrow">SYSTEM</span><h2>Settings</h2>
      <p>Application configuration and preferences.</p></div>
    </div>
    <div class="panel">
      <div class="panel-heading"><h3>Application Info</h3></div>
      <div class="definition"><dt>Version</dt><dd>2.0.0</dd></div>
      <div class="definition"><dt>Backend</dt><dd>Enterprise Data Agent</dd></div>
      <div class="definition"><dt>Data Mode</dt><dd>Deterministic · Read-only · Local reference environment</dd></div>
    </div>`;
  }
}

// ─── Navigation ───────────────────────────────────────────────────────────────

function navigate(page) {
  document.body.classList.remove('session-mode');
  state.page = page;
  state.task = null;
  state.taskId = null;
  state.workspaceTab = 'overview';
  $$('#nav button').forEach((button) => button.classList.toggle('active', button.dataset.page === page));
  const routes = { home, new: newPage, dashboard: home, evidence: history, history, data, semantic, evaluation, settings };
  const fn = routes[page];
  if (fn) fn();
}

async function followUp(taskId) {
  if (!taskId) return;
  const question = prompt('Follow-up question:');
  if (!question?.trim()) return;
  try {
    const task = await api('/analysis-tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, referenced_task_id: taskId }),
    });
    await openTask(task.task_id);
  } catch (e) {
    toast('Failed to create follow-up task');
  }
}

async function submitClarification(taskId) {
  const response = $('#clarification-response')?.value.trim();
  if (!response) return toast('Enter your clarification response');
  try {
    await api(`/analysis-tasks/${encodeURIComponent(taskId)}/clarification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ response }),
    });
    await openTask(taskId, state.workspaceTab);
    toast('Clarification submitted');
  } catch (e) {
    toast('Failed to submit clarification');
  }
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function workspaceTab(tab) {
  state.workspaceTab = tab;
  state.selectedEvidence = null;
  renderWorkspace();
}

function focusPlanStep(index) {
  toast(`Focused on plan step ${index + 1}. Full events are in the task log.`);
  workspaceTab('investigation');
}

function selectHypothesis(button) {
  $$('.hypothesis').forEach((item) => item.classList.remove('selected'));
  button.classList.add('selected');
}

function requestBreakdown(dimension) {
  if (!dimension || !state.task) return;
  const labels = { vendor: 'vendor', category: 'category', store: 'store', county: 'county' };
  const current = state.task.resolved_context?.dimension;
  if (dimension === current) return toast('Current task already has this dimension');
  followUpWithQuestion(state.task.task_id, `Please break down the same analysis by ${labels[dimension] || dimension}, keeping the original period and metric.`);
}

function followUpWithQuestion(taskId, question) {
  followUp(taskId);
}

function setDashboardSearch(value) {
  state.dashboardSearch = value;
  if (state.page === 'workspace' && state.workspaceTab === 'dashboard') {
    renderWorkspace();
  }
}

function resetDashboard() {
  state.dashboardDimension = '';
  state.dashboardSearch = '';
  renderWorkspace();
}

function openMetricEvidence(label) {
  if (!state.task) return;
  state.selectedEvidence = 0;
  if (state.page === 'workspace') renderWorkspace();
  else openInspector(state.task, 0);
  toast(`${label}: Evidence inspector opened`);
}

function openEvidence(index) {
  state.selectedEvidence = index;
  if (state.page === 'workspace') renderWorkspace();
  else openInspector(state.task, index);
}

function openContributionEvidence(index) {
  state.selectedEvidence = Math.min(index, Math.max(0, (state.task?.evidence?.length || 1) - 1));
  renderWorkspace();
  toast('Evidence for this contribution result opened');
}

function closeInspector() {
  state.selectedEvidence = null;
  if ($('#modal-root').innerHTML) closeDrawer();
  else renderWorkspace();
}

function openInspector(task, index) {
  state.selectedEvidence = index;
  $('#modal-root').innerHTML = `<div class="drawer-backdrop open" onclick="closeDrawer()"></div>
    <aside class="drawer open">${inspectorContent(task, index)}</aside>`;
}

function closeDrawer() {
  $('#modal-root').innerHTML = '';
}

function filterEvidence(value) {
  $$('.evidence-item').forEach((item) => {
    item.hidden = value && !item.dataset.search.toLowerCase().includes(value.toLowerCase());
  });
}

function copyReference(reference) {
  if (!reference) return toast('No evidence ID to copy');
  navigator.clipboard?.writeText(reference).then(() => toast('Evidence ID copied')).catch(() => toast(reference));
}

function toggleSidebar() {
  $('#sidebar').classList.toggle('open');
}

// ─── Toast ────────────────────────────────────────────────────────────────────

let toastTimer;
function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

// ─── Init ─────────────────────────────────────────────────────────────────────

$$('#nav button[data-page]').forEach((button) => {
  button.addEventListener('click', () => navigate(button.dataset.page));
});

window.navigate = navigate;
window.submitHomeQuestion = submitHomeQuestion;
window.fillQuestion = fillQuestion;
window.submitQuestion = submitQuestion;
window.openTask = openTask;
window.workspaceTab = workspaceTab;
window.focusPlanStep = focusPlanStep;
window.selectHypothesis = selectHypothesis;
window.requestBreakdown = requestBreakdown;
window.setDashboardSearch = setDashboardSearch;
window.resetDashboard = resetDashboard;
window.openMetricEvidence = openMetricEvidence;
window.openEvidence = openEvidence;
window.openContributionEvidence = openContributionEvidence;
window.closeInspector = closeInspector;
window.openInspector = openInspector;
window.closeDrawer = closeDrawer;
window.filterEvidence = filterEvidence;
window.copyReference = copyReference;
window.toggleSidebar = toggleSidebar;
window.toast = toast;
window.followUp = followUp;
window.followUpWithQuestion = followUpWithQuestion;
window.submitClarification = submitClarification;
window.runEvaluation = runEvaluation;

// Load home on startup
home();
