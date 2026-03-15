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

// ============ APP GRAPH — Interactive Canvas ============

const graphState = {
    scan: null, graph: null,
    nodes: {},          // { stateName: { x, y, el } }
    pan: { x: 60, y: 60 },
    zoom: 1,
    dragging: null,     // node being dragged
    panning: false,
    lastMouse: null,
    selectedNode: null,
};

function initGraph() {
    const vp = document.getElementById('graph-viewport');
    if (!vp) return;

    // Pan
    vp.addEventListener('pointerdown', (e) => {
        if (e.target === vp || e.target.id === 'graph-world' || e.target.tagName === 'svg') {
            graphState.panning = true;
            graphState.lastMouse = { x: e.clientX, y: e.clientY };
            vp.setPointerCapture(e.pointerId);
        }
    });
    vp.addEventListener('pointermove', (e) => {
        if (graphState.panning && graphState.lastMouse) {
            const dx = e.clientX - graphState.lastMouse.x;
            const dy = e.clientY - graphState.lastMouse.y;
            graphState.pan.x += dx;
            graphState.pan.y += dy;
            graphState.lastMouse = { x: e.clientX, y: e.clientY };
            applyGraphTransform();
        }
    });
    vp.addEventListener('pointerup', () => { graphState.panning = false; graphState.lastMouse = null; });

    // Zoom
    vp.addEventListener('wheel', (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.08 : 0.92;
        const rect = vp.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        // Zoom toward cursor
        graphState.pan.x = mx - (mx - graphState.pan.x) * factor;
        graphState.pan.y = my - (my - graphState.pan.y) * factor;
        graphState.zoom = Math.max(0.15, Math.min(3, graphState.zoom * factor));
        applyGraphTransform();
    }, { passive: false });

    // Toolbar buttons
    document.getElementById('graph-fit-btn')?.addEventListener('click', graphFitToView);
    document.getElementById('graph-zoom-in')?.addEventListener('click', () => {
        graphState.zoom = Math.min(3, graphState.zoom * 1.25);
        applyGraphTransform();
    });
    document.getElementById('graph-zoom-out')?.addEventListener('click', () => {
        graphState.zoom = Math.max(0.15, graphState.zoom * 0.8);
        applyGraphTransform();
    });
}

function applyGraphTransform() {
    const world = document.getElementById('graph-world');
    if (world) world.style.transform = `translate(${graphState.pan.x}px, ${graphState.pan.y}px) scale(${graphState.zoom})`;
}

async function loadGraphScanList() {
    try {
        const resp = await fetch('/api/scans');
        const data = await resp.json();
        const select = document.getElementById('graph-scan-select');
        const current = select.value;
        select.innerHTML = '<option value="">Select a scan...</option>';
        data.scans.filter(s => s.has_app_graph).forEach(scan => {
            const opt = document.createElement('option');
            opt.value = scan.name;
            opt.textContent = `${scan.app_name || scan.name} (${scan.total_states} states)`;
            select.appendChild(opt);
        });
        if (current) select.value = current;
        select.onchange = () => { if (select.value) loadAppGraph(select.value); };
    } catch (e) {}
}

async function loadAppGraph(scanName) {
    try {
        const resp = await fetch(`/api/scans/${scanName}/graph`);
        if (!resp.ok) return;
        const graph = await resp.json();
        graphState.graph = graph;
        graphState.scan = scanName;
        renderGraph(graph, scanName);
    } catch (e) { console.error('Failed to load app graph:', e); }
}

function renderGraph(graph, scanName) {
    const nodesContainer = document.getElementById('graph-nodes');
    const edgesSvg = document.getElementById('graph-edges');
    nodesContainer.innerHTML = '';
    edgesSvg.innerHTML = '<defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" class="graph-edge-arrow"/></marker></defs>';
    graphState.nodes = {};

    const stateNames = Object.keys(graph.states);
    if (stateNames.length === 0) {
        nodesContainer.innerHTML = '<div style="color:var(--text-muted);padding:60px;position:absolute;">No states found.</div>';
        return;
    }

    // Layout: arrange in a force-like grid
    const cols = Math.ceil(Math.sqrt(stateNames.length));
    const nodeW = 240, nodeH = 220, gapX = 100, gapY = 80;

    stateNames.forEach((name, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const x = col * (nodeW + gapX);
        const y = row * (nodeH + gapY);

        const stateData = graph.states[name];
        const el = createGraphNode(name, stateData, scanName, x, y);
        nodesContainer.appendChild(el);
        graphState.nodes[name] = { x, y, w: nodeW, h: nodeH, el, data: stateData };
    });

    drawEdges(graph);
    initGraph();
    setTimeout(graphFitToView, 100);
}

function createGraphNode(name, stateData, scanName, x, y) {
    const el = document.createElement('div');
    el.className = 'graph-node';
    el.style.left = x + 'px';
    el.style.top = y + 'px';
    el.dataset.state = name;

    const elems = stateData.elements || [];
    const transitions = Object.keys(stateData.transitions || {}).length;
    const ssFile = (stateData.screenshot || '').replace('screenshots/', '');
    const imgSrc = ssFile ? `/api/scans/${scanName}/screenshots/${ssFile}` : '';

    el.innerHTML = `
        <div class="graph-node-header">
            <span class="graph-node-title" title="${escapeHtml(name)}">${escapeHtml(name.replace(/^state_\d+_/, '').replace(/_/g, ' '))}</span>
            <span class="graph-node-badge">${elems.length} el</span>
        </div>
        ${imgSrc ? `<img class="graph-node-screenshot" src="${imgSrc}" alt="" draggable="false" onerror="this.style.display='none'">` : '<div class="graph-node-screenshot" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:11px;">No screenshot</div>'}
        <div class="graph-node-footer">
            <span>${transitions} transition${transitions !== 1 ? 's' : ''}</span>
            <span style="color:var(--accent-cyan)">${stateData.description ? truncate(stateData.description, 25) : ''}</span>
        </div>
    `;

    // Node dragging
    el.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        graphState.dragging = { name, offsetX: e.clientX / graphState.zoom - x, offsetY: e.clientY / graphState.zoom - y };
        el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', (e) => {
        if (!graphState.dragging || graphState.dragging.name !== name) return;
        const nx = e.clientX / graphState.zoom - graphState.dragging.offsetX;
        const ny = e.clientY / graphState.zoom - graphState.dragging.offsetY;
        el.style.left = nx + 'px';
        el.style.top = ny + 'px';
        graphState.nodes[name].x = nx;
        graphState.nodes[name].y = ny;
        drawEdges(graphState.graph);
    });
    el.addEventListener('pointerup', (e) => {
        if (graphState.dragging && graphState.dragging.name === name) {
            // If barely moved, treat as click
            graphState.dragging = null;
        }
    });
    el.addEventListener('click', (e) => {
        e.stopPropagation();
        selectGraphNode(name, stateData, scanName);
    });

    return el;
}

function drawEdges(graph) {
    const svg = document.getElementById('graph-edges');
    // Clear old paths (keep defs)
    svg.querySelectorAll('path, text.edge-label').forEach(el => el.remove());

    for (const [srcName, stateData] of Object.entries(graph.states)) {
        const srcNode = graphState.nodes[srcName];
        if (!srcNode) continue;

        for (const [action, tgtName] of Object.entries(stateData.transitions || {})) {
            const tgtNode = graphState.nodes[tgtName];
            if (!tgtNode) continue;

            const sx = srcNode.x + srcNode.w / 2;
            const sy = srcNode.y + srcNode.h;
            const tx = tgtNode.x + tgtNode.w / 2;
            const ty = tgtNode.y;

            // Curved path
            const midY = (sy + ty) / 2;
            const dx = (tx - sx) * 0.3;
            const d = `M ${sx} ${sy} C ${sx + dx} ${midY}, ${tx - dx} ${midY}, ${tx} ${ty}`;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            path.setAttribute('class', 'graph-edge-line');
            path.setAttribute('marker-end', 'url(#arrowhead)');
            svg.appendChild(path);

            // Edge labels removed for cleaner look
        }
    }
}

function selectGraphNode(name, stateData, scanName) {
    // Highlight
    document.querySelectorAll('.graph-node.selected').forEach(n => n.classList.remove('selected'));
    const nodeEl = graphState.nodes[name]?.el;
    if (nodeEl) nodeEl.classList.add('selected');

    const panel = document.getElementById('graph-detail');
    panel.classList.remove('hidden');
    const elems = stateData.elements || [];
    const transitions = stateData.transitions || {};
    const ssFile = (stateData.screenshot || '').replace('screenshots/', '');
    const imgSrc = ssFile ? `/api/scans/${scanName}/screenshots/${ssFile}` : '';

    panel.innerHTML = `
        <div style="display:flex;gap:16px;align-items:flex-start;">
            ${imgSrc ? `<img src="${imgSrc}" style="width:200px;border-radius:6px;flex-shrink:0;cursor:pointer;" onclick="window.open(this.src,'_blank')">` : ''}
            <div style="flex:1;min-width:0;">
                <h3>${escapeHtml(name)}</h3>
                <div class="detail-desc">${escapeHtml(stateData.description || '')}</div>
                <div style="display:flex;gap:16px;margin-bottom:8px;">
                    <span style="font-size:12px;color:var(--accent-cyan);">${elems.length} elements</span>
                    <span style="font-size:12px;color:var(--accent-blue);">${Object.keys(transitions).length} transitions</span>
                </div>
                ${Object.keys(transitions).length > 0 ? `
                    <div style="margin-bottom:8px;">
                        ${Object.entries(transitions).map(([k,v]) =>
                            `<span style="display:inline-block;background:var(--bg-tertiary);padding:2px 8px;border-radius:6px;font-size:11px;margin:2px 4px 2px 0;font-family:var(--font-mono);">
                                <span style="color:var(--accent-magenta);">${escapeHtml(k)}</span>
                                <span style="color:var(--text-muted);"> → </span>
                                <span style="color:var(--accent-cyan);">${escapeHtml(v)}</span>
                            </span>`
                        ).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
        <table class="graph-detail-table">
            <tr><th>ID</th><th>Role</th><th>Title</th><th>Position</th><th>Actions</th><th>Source</th></tr>
            ${elems.slice(0, 50).map(el => `
                <tr>
                    <td style="color:var(--text-muted);">${escapeHtml(el.id || '')}</td>
                    <td style="color:var(--accent-magenta);">${escapeHtml(el.role || '')}</td>
                    <td>${escapeHtml(el.title || el.description || '')}</td>
                    <td style="color:var(--text-muted);">${(el.position||[]).join(',')}</td>
                    <td style="color:var(--accent-blue);">${escapeHtml((el.actions||[]).join(', '))}</td>
                    <td style="color:${el.source === 'vision' ? 'var(--accent-orange)' : 'var(--text-muted)'};">${el.source || 'ax'}</td>
                </tr>
            `).join('')}
            ${elems.length > 50 ? `<tr><td colspan="6" style="color:var(--text-muted);">...and ${elems.length - 50} more</td></tr>` : ''}
        </table>
    `;
}

function graphFitToView() {
    const vp = document.getElementById('graph-viewport');
    if (!vp) return;
    const nodes = Object.values(graphState.nodes);
    if (nodes.length === 0) return;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    nodes.forEach(n => {
        minX = Math.min(minX, n.x);
        minY = Math.min(minY, n.y);
        maxX = Math.max(maxX, n.x + n.w);
        maxY = Math.max(maxY, n.y + n.h);
    });

    const pad = 40;
    const gw = maxX - minX + pad * 2;
    const gh = maxY - minY + pad * 2;
    const vpRect = vp.getBoundingClientRect();
    const scaleX = vpRect.width / gw;
    const scaleY = vpRect.height / gh;
    graphState.zoom = Math.min(scaleX, scaleY, 1.2);
    graphState.pan.x = (vpRect.width - gw * graphState.zoom) / 2 - minX * graphState.zoom + pad * graphState.zoom;
    graphState.pan.y = (vpRect.height - gh * graphState.zoom) / 2 - minY * graphState.zoom + pad * graphState.zoom;
    applyGraphTransform();
}

async function loadScanDetail(scanName) {
    document.querySelector('[data-tab="app-graph"]').click();
    document.getElementById('graph-scan-select').value = scanName;
    await loadAppGraph(scanName);
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
