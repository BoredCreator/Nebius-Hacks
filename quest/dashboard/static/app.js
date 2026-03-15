/*
 * Quest Dashboard - Frontend Logic
 * Handles WebSocket connection, log rendering, tab switching,
 * and all dashboard views.
 */

// ============ STATE ============
const state = {
    logs: [],
    autoScroll: true,
    ws: null,
    filters: { source: '', level: '', search: '' },
    currentTab: 'live-logs',
    stats: {},
    pollInterval: null,
};

// ============ HELPERS ============
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function truncate(str, max) {
    return str.length > max ? str.substring(0, max) + '...' : str;
}

function timeSince(isoStr) {
    const ms = Date.now() - new Date(isoStr).getTime();
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ${s % 60}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
}

function timeDiff(startIso, endIso) {
    const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    return `${m}m ${s % 60}s`;
}

// ============ INIT ============
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initFilters();
    initWebSocket();
    startPolling();
    loadInitialLogs();
});

// ============ TABS ============
function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            tab.classList.add('active');
            const tabId = tab.dataset.tab;
            document.getElementById(`tab-${tabId}`).classList.add('active');
            state.currentTab = tabId;

            if (tabId === 'scans') loadScans();
            if (tabId === 'bugs') loadBugs();
            if (tabId === 'llm-calls') loadLLMCalls();
            if (tabId === 'pipeline') loadPipelineStatus();
            if (tabId === 'app-graph') loadGraphScanList();
            if (tabId === 'test-cases') loadTCScanList();
        });
    });
}

// ============ FILTERS ============
function initFilters() {
    document.getElementById('filter-source').addEventListener('change', (e) => {
        state.filters.source = e.target.value;
        rerenderLogs();
    });
    document.getElementById('filter-level').addEventListener('change', (e) => {
        state.filters.level = e.target.value;
        rerenderLogs();
    });
    document.getElementById('filter-search').addEventListener('input', (e) => {
        state.filters.search = e.target.value.toLowerCase();
        rerenderLogs();
    });
    document.getElementById('btn-autoscroll').addEventListener('click', (e) => {
        state.autoScroll = !state.autoScroll;
        e.target.classList.toggle('active', state.autoScroll);
    });
    document.getElementById('btn-clear-logs').addEventListener('click', () => {
        state.logs = [];
        document.getElementById('log-entries').innerHTML = '';
    });
}

// ============ WEBSOCKET ============
function initWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws/logs`;
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        document.getElementById('connection-status').className = 'status-dot connected';
    };

    state.ws.onclose = () => {
        document.getElementById('connection-status').className = 'status-dot disconnected';
        setTimeout(initWebSocket, 2000);
    };

    state.ws.onmessage = (event) => {
        const log = JSON.parse(event.data);
        state.logs.push(log);

        if (state.logs.length > 5000) {
            state.logs = state.logs.slice(-3000);
        }

        appendLogEntry(log);
        updateHeaderStats(log);
    };
}

// ============ LOAD INITIAL LOGS ============
async function loadInitialLogs() {
    try {
        const resp = await fetch('/api/logs?n=500');
        const data = await resp.json();
        state.logs = data.logs;
        rerenderLogs();
    } catch (e) {
        console.error('Failed to load initial logs:', e);
    }
}

// ============ LOG RENDERING ============
function appendLogEntry(log) {
    if (!matchesFilters(log)) return;

    const container = document.getElementById('log-entries');
    const el = createLogElement(log);
    container.appendChild(el);

    if (state.autoScroll) {
        const logContainer = document.getElementById('log-container');
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

function rerenderLogs() {
    const container = document.getElementById('log-entries');
    container.innerHTML = '';

    const filtered = state.logs.filter(matchesFilters);
    const fragment = document.createDocumentFragment();

    filtered.forEach(log => {
        fragment.appendChild(createLogElement(log));
    });

    container.appendChild(fragment);

    if (state.autoScroll) {
        const logContainer = document.getElementById('log-container');
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

function createLogElement(log) {
    const div = document.createElement('div');
    div.className = 'log-entry';

    const ts = log.timestamp.split('T')[1]?.substring(0, 12) || '';
    const srcClass = `src-${log.source}`;
    const lvlClass = `lvl-${log.level}`;

    let html = `
        <span class="log-ts">${ts}</span>
        <span class="log-src ${srcClass}">${escapeHtml(log.source)}</span>
        <span class="log-lvl ${lvlClass}">${escapeHtml(log.level)}</span>
        <span class="log-msg">${escapeHtml(log.message)}</span>
    `;

    div.innerHTML = html;

    if (log.data && Object.keys(log.data).length > 0) {
        const dataDiv = document.createElement('div');
        dataDiv.className = 'log-data';
        const dataLines = Object.entries(log.data)
            .map(([k, v]) => `  \u2514\u2500 ${k}: ${truncate(JSON.stringify(v), 120)}`)
            .join('\n');
        dataDiv.textContent = dataLines;
        div.appendChild(dataDiv);
    }

    if (log.screenshot) {
        const imgLink = document.createElement('span');
        imgLink.textContent = ' [img]';
        imgLink.style.cursor = 'pointer';
        imgLink.style.color = 'var(--accent-cyan)';
        imgLink.title = log.screenshot;
        imgLink.onclick = () => {
            window.open(`/api/scans/${log.screenshot}`, '_blank');
        };
        div.querySelector('.log-msg').appendChild(imgLink);
    }

    return div;
}

function matchesFilters(log) {
    if (state.filters.source && log.source !== state.filters.source) return false;
    if (state.filters.level && log.level !== state.filters.level) return false;
    if (state.filters.search && !log.message.toLowerCase().includes(state.filters.search)
        && !JSON.stringify(log.data).toLowerCase().includes(state.filters.search)) return false;
    return true;
}

// ============ HEADER STATS ============
function updateHeaderStats(log) {
    document.getElementById('total-events').textContent = state.logs.length;

    if (log.level === 'bug') {
        const bugCount = state.logs.filter(l => l.level === 'bug').length;
        document.getElementById('total-bugs').textContent = bugCount;
    }
    if (log.level === 'llm_call') {
        const llmCount = state.logs.filter(l => l.level === 'llm_call').length;
        document.getElementById('total-llm').textContent = llmCount;
    }
    if (log.level === 'error' || log.level === 'critical') {
        const errCount = state.logs.filter(l => l.level === 'error' || l.level === 'critical').length;
        document.getElementById('total-errors').textContent = errCount;
    }
}

// ============ POLLING ============
function startPolling() {
    state.pollInterval = setInterval(async () => {
        if (state.currentTab === 'pipeline') await loadPipelineStatus();
        if (state.currentTab === 'execution') await loadExecutionStatus();

        try {
            const resp = await fetch('/api/stats');
            state.stats = await resp.json();
            document.getElementById('total-events').textContent = state.stats.total_events || 0;
            document.getElementById('total-bugs').textContent = state.stats.bugs_found || 0;
            document.getElementById('total-llm').textContent = state.stats.llm_calls || 0;
            document.getElementById('total-errors').textContent = state.stats.errors || 0;
        } catch (e) {}
    }, 2000);
}

// ============ PIPELINE STATUS ============
async function loadPipelineStatus() {
    try {
        const resp = await fetch('/api/pipeline_status');
        const data = await resp.json();

        const phases = ['discovery', 'generation', 'execution', 'reporting'];
        phases.forEach(phase => {
            const el = document.getElementById(`stage-${phase}`);
            const info = data.phases[phase];

            el.className = `pipeline-stage ${info.status}`;
            el.querySelector('.stage-status').textContent =
                info.status.charAt(0).toUpperCase() + info.status.slice(1);

            let details = '';
            if (info.details) {
                details = Object.entries(info.details)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' | ');
            }
            if (info.started) {
                const elapsed = info.ended
                    ? `Done in ${timeDiff(info.started, info.ended)}`
                    : `Running ${timeSince(info.started)}`;
                details = details ? `${elapsed} | ${details}` : elapsed;
            }
            el.querySelector('.stage-details').textContent = details;
        });
    } catch (e) {
        console.error('Failed to load pipeline status:', e);
    }
}

// ============ SCANS ============
async function loadScans() {
    try {
        const resp = await fetch('/api/scans');
        const data = await resp.json();

        const container = document.getElementById('scans-list');
        if (data.scans.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); padding: 32px; text-align: center;">No scans yet. Start a scan from the CLI.</div>';
            return;
        }

        container.innerHTML = data.scans.map(scan => `
            <div class="state-card" onclick="loadScanDetail('${escapeHtml(scan.name)}')">
                <div class="state-name">${escapeHtml(scan.app_name || scan.name)}</div>
                <div class="state-elem-count">
                    ${scan.has_app_graph ? `Graph (${scan.total_states} states, ${scan.total_elements} elements)` : 'No graph yet'}
                    <br>
                    ${scan.test_case_files.length} persona test files
                    <br>
                    ${scan.has_report ? 'Report generated' : 'No report yet'}
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load scans:', e);
    }
}

async function loadScanDetail(scanName) {
    document.querySelector('[data-tab="app-graph"]').click();
    document.getElementById('graph-scan-select').value = scanName;
    await loadAppGraph(scanName);
}

// ============ APP GRAPH ============
async function loadGraphScanList() {
    try {
        const resp = await fetch('/api/scans');
        const data = await resp.json();
        const select = document.getElementById('graph-scan-select');
        const current = select.value;
        select.innerHTML = '<option value="">Select a scan...</option>';
        data.scans.forEach(scan => {
            const opt = document.createElement('option');
            opt.value = scan.name;
            opt.textContent = scan.app_name || scan.name;
            select.appendChild(opt);
        });
        if (current) select.value = current;

        select.onchange = () => {
            if (select.value) loadAppGraph(select.value);
        };
    } catch (e) {}
}

async function loadAppGraph(scanName) {
    try {
        const resp = await fetch(`/api/scans/${scanName}/graph`);
        if (!resp.ok) {
            document.getElementById('graph-states').innerHTML =
                '<div style="color: var(--text-muted); padding: 32px;">No app graph found for this scan.</div>';
            return;
        }
        const graph = await resp.json();
        const container = document.getElementById('graph-states');

        const states = graph.states || [];
        if (states.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); padding: 32px;">No states in this graph.</div>';
            return;
        }

        container.innerHTML = states.map((s, i) => `
            <div class="state-card" onclick='showStateDetail(${JSON.stringify(s).replace(/'/g, "&#39;")})'>
                <div class="state-name">${escapeHtml(s.title || s.state_id || `State ${i}`)}</div>
                <div class="state-elem-count">${(s.elements || []).length} elements</div>
                ${s.screenshot ? `<img class="state-thumb" src="/api/scans/${scanName}/screenshots/${s.screenshot}" alt="screenshot">` : ''}
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load app graph:', e);
    }
}

function showStateDetail(stateData) {
    const panel = document.getElementById('graph-detail');
    const elements = stateData.elements || [];
    panel.innerHTML = `
        <h3>${escapeHtml(stateData.title || stateData.state_id || 'State')}</h3>
        <p style="color: var(--text-secondary); margin: 8px 0;">${elements.length} elements</p>
        <table style="width: 100%; font-size: 12px; font-family: var(--font-mono);">
            <tr style="color: var(--text-secondary);"><th>Role</th><th>Label</th><th>Actions</th></tr>
            ${elements.map(el => `
                <tr>
                    <td>${escapeHtml(el.role || '')}</td>
                    <td>${escapeHtml(el.label || el.title || '')}</td>
                    <td>${escapeHtml((el.actions || []).join(', '))}</td>
                </tr>
            `).join('')}
        </table>
    `;
}

// ============ TEST CASES ============
async function loadTCScanList() {
    try {
        const resp = await fetch('/api/scans');
        const data = await resp.json();
        const select = document.getElementById('tc-scan-select');
        select.innerHTML = '<option value="">Select a scan...</option>';
        data.scans.forEach(scan => {
            const opt = document.createElement('option');
            opt.value = scan.name;
            opt.textContent = scan.app_name || scan.name;
            select.appendChild(opt);
        });

        select.onchange = () => {
            if (select.value) loadTestCases(select.value);
        };
    } catch (e) {}
}

async function loadTestCases(scanName) {
    try {
        const resp = await fetch(`/api/scans/${scanName}/test_cases`);
        const data = await resp.json();
        const container = document.getElementById('test-cases-list');

        const allCases = [];
        for (const [persona, cases] of Object.entries(data.test_cases)) {
            const caseList = Array.isArray(cases) ? cases : [cases];
            caseList.forEach(tc => {
                allCases.push({ ...tc, _persona: persona });
            });
        }

        if (allCases.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); padding: 32px;">No test cases found.</div>';
            return;
        }

        container.innerHTML = allCases.map(tc => `
            <div class="test-case-card">
                <div class="tc-header">
                    <div>
                        <div class="tc-title">${escapeHtml(tc.title || tc.test_id || 'Test Case')}</div>
                        <div class="tc-persona">${escapeHtml(tc.persona || tc._persona)}</div>
                    </div>
                    <span class="tc-severity severity-${(tc.severity || 'medium').toLowerCase()}">${escapeHtml(tc.severity || 'medium')}</span>
                </div>
                ${tc.steps ? `
                    <div class="tc-steps">
                        ${tc.steps.map((step, i) => `
                            <div class="tc-step">${i + 1}. ${escapeHtml(typeof step === 'string' ? step : step.description || step.action || JSON.stringify(step))}</div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load test cases:', e);
    }
}

// ============ EXECUTION MONITOR ============
async function loadExecutionStatus() {
    try {
        const resp = await fetch('/api/pipeline_status');
        const data = await resp.json();
        const exec = data.phases.execution;

        const started = exec.details.tests_started || 0;
        const completed = exec.details.tests_completed || 0;
        const pct = started > 0 ? Math.round((completed / started) * 100) : 0;

        document.getElementById('exec-progress-fill').style.width = `${pct}%`;
        document.getElementById('exec-stats').textContent = `${completed} / ${started} tests (${pct}%)`;

        // Show latest execution logs
        const logsResp = await fetch('/api/logs?n=50&source=executor');
        const logsData = await logsResp.json();
        const resultsList = document.getElementById('exec-results-list');

        const testLogs = logsData.logs.filter(l => l.level === 'test_end');
        resultsList.innerHTML = testLogs.map(l => {
            const status = l.data.status || 'unknown';
            const cls = status === 'PASS' ? 'pass' : status === 'FAIL' ? 'fail' : 'error';
            return `<div class="exec-result-item ${cls}">
                <span class="result-icon"></span>
                <span>${escapeHtml(l.data.test_id || l.message)}</span>
            </div>`;
        }).join('');

        // Show latest screenshot
        const screenshotLogs = logsData.logs.filter(l => l.screenshot);
        if (screenshotLogs.length > 0) {
            const latest = screenshotLogs[screenshotLogs.length - 1];
            document.getElementById('exec-screenshot-img').src = `/api/scans/${latest.screenshot}`;
        }
    } catch (e) {}
}

// ============ BUGS ============
async function loadBugs() {
    try {
        const resp = await fetch('/api/bugs');
        const data = await resp.json();

        const bugs = data.bugs;
        let critical = 0, high = 0, medium = 0, low = 0;
        bugs.forEach(b => {
            const sev = (b.data.severity || 'medium').toLowerCase();
            if (sev === 'critical') critical++;
            else if (sev === 'high') high++;
            else if (sev === 'medium') medium++;
            else low++;
        });

        document.getElementById('bugs-critical').textContent = `${critical} Critical`;
        document.getElementById('bugs-high').textContent = `${high} High`;
        document.getElementById('bugs-medium').textContent = `${medium} Medium`;
        document.getElementById('bugs-low').textContent = `${low} Low`;

        const container = document.getElementById('bugs-list');
        if (bugs.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); padding: 32px; text-align: center;">No bugs detected yet.</div>';
            return;
        }

        container.innerHTML = bugs.map(b => {
            const sev = (b.data.severity || 'medium').toLowerCase();
            return `
                <div class="bug-card ${sev}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>${escapeHtml(b.data.title || b.message)}</strong>
                        <span class="tc-severity severity-${sev}">${sev}</span>
                    </div>
                    <div style="color: var(--text-secondary); font-size: 13px; margin-top: 8px;">
                        ${escapeHtml(b.message)}
                    </div>
                    ${b.data.bug_id ? `<div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-top: 4px;">ID: ${escapeHtml(b.data.bug_id)}</div>` : ''}
                    ${b.screenshot ? `<div style="margin-top: 8px;"><img src="/api/scans/${b.screenshot}" style="max-width: 300px; border-radius: 4px;" alt="evidence"></div>` : ''}
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load bugs:', e);
    }
}

// ============ LLM CALLS ============
async function loadLLMCalls() {
    try {
        const resp = await fetch('/api/llm_calls');
        const data = await resp.json();

        const calls = data.llm_calls.filter(l => l.level === 'llm_call');
        const responses = data.llm_calls.filter(l => l.level === 'llm_response');

        document.getElementById('llm-total-calls').textContent = calls.length;

        let totalTokens = 0;
        let totalLatency = 0;
        let latencyCount = 0;
        calls.forEach(c => {
            if (c.data.prompt_tokens) totalTokens += c.data.prompt_tokens;
            if (c.data.completion_tokens) totalTokens += c.data.completion_tokens;
        });
        responses.forEach(r => {
            if (r.data.latency_ms) {
                totalLatency += r.data.latency_ms;
                latencyCount++;
            }
            if (r.data.tokens) totalTokens += r.data.tokens;
        });

        document.getElementById('llm-total-tokens').textContent = totalTokens.toLocaleString();
        document.getElementById('llm-avg-latency').textContent =
            latencyCount > 0 ? `${Math.round(totalLatency / latencyCount)}ms` : 'N/A';

        const container = document.getElementById('llm-calls-list');
        container.innerHTML = calls.map((c, i) => `
            <div class="llm-call-card" onclick="this.classList.toggle('expanded')">
                <div class="llm-call-header">
                    <div>
                        <strong>${escapeHtml(c.data.model || 'Unknown model')}</strong>
                        <span style="color: var(--text-secondary); margin-left: 12px;">${escapeHtml(c.message)}</span>
                    </div>
                    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">
                        ${c.data.prompt_tokens || '?'} tokens
                    </div>
                </div>
                <div class="llm-call-body">${escapeHtml(c.data.prompt || JSON.stringify(c.data, null, 2))}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load LLM calls:', e);
    }
}
