let sentimentChart;
let performanceChart;
let lastFullData = [];
let exchangeBalances = {};

// State tracking to prevent redundant DOM updates
let dashboardState = {
    balance: null,
    posCount: null,
    sentimentScore: null,
    historyHash: "",
    symbolsHash: "",
    hotSymbolsHash: "",
    positionsHash: "",
    logsHash: "",
    botActive: null,
    currentExchange: null,
    isDemo: null,
    isTradingDay: null,
    tradingDays: [],
    lastServerStartHour: null,
    lastServerEndHour: null
};

async function updateDashboard() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        
        if (data.status === "loading") return;

        lastFullData = data.entries;
        exchangeBalances = data.exchange_balances || {};

        // Concurrent UI tasks
        await Promise.all([
            updateCoreMetrics(data),
            updateExchangeContext(data),
            renderHistoryTask(data.history),
            renderSymbolsTask(data.symbols, data.hot_symbols),
            renderPositionsTask(data.positions),
            renderLogsTask(data.entries, data.bot_active),
            renderAnalyticsTask(data.analytics),
            updateChartsTask(data.entries),
            updateScheduleUI(data.trading_days, data.is_trading_day, data.trading_start_hour || 0, data.trading_end_hour || 24)
        ].map(t => t.catch(e => console.warn("Task error:", e))));

    } catch (err) {
        console.warn("Dashboard sync deferred...");
    }
}

async function updateCoreMetrics(data) {
    if (data.balance !== undefined) {
        const balanceEl = document.getElementById('total-balance');
        const formatted = `${Number(data.balance).toFixed(2)} USDT`;
        if (balanceEl && balanceEl.innerText !== formatted) {
            balanceEl.innerText = formatted;
            balanceEl.classList.add('animate-pulse');
            setTimeout(() => balanceEl.classList.remove('animate-pulse'), 1000);
        }
        dashboardState.balance = data.balance;
    }
    if (data.positions) {
        safeSetText('pos-count', data.positions.length);
        dashboardState.posCount = data.positions.length;
    }

    if (data.entries && data.entries.length > 0) {
        const score = data.entries[0].score || 0;
        safeSetText('market-sentiment', score);
        const label = score >= 7 ? "Bullish Edge" : score <= 3 ? "Bearish Pressure" : "Neutral Range";
        safeSetText('sentiment-label', label);
    }
}

async function updateExchangeContext(data) {
    const currentExchange = data.active_exchanges && data.active_exchanges.length > 0 ? data.active_exchanges[0] : 'okx';
    const isDemo = data.sandbox_modes[currentExchange];
    
    if (dashboardState.currentExchange !== currentExchange || dashboardState.isDemo !== isDemo) {
        const exSelect = document.getElementById('exchange-select');
        if (exSelect) exSelect.value = currentExchange;
        
        const modeStatus = document.getElementById('mode-status');
        if (modeStatus) {
            modeStatus.innerText = isDemo ? "DEMO MODE (SANDBOX)" : "REAL TRADING (LIVE)";
            modeStatus.className = isDemo ? "text-[11px] font-bold text-blue-400" : "text-[11px] font-bold text-red-500";
        }
        dashboardState.currentExchange = currentExchange;
        dashboardState.isDemo = isDemo;
    }
    
    if (dashboardState.botActive !== data.bot_active || dashboardState.isTradingDay !== data.is_trading_day) {
        updatePowerUI(data.bot_active, data.is_trading_day);
        dashboardState.botActive = data.bot_active;
        dashboardState.isTradingDay = data.is_trading_day;
    }
}

async function renderHistoryTask(history) {
    const currentHash = JSON.stringify(history);
    if (dashboardState.historyHash === currentHash) return;
    
    const container = document.getElementById('history-container');
    if (!container) return;

    if (history && history.length > 0) {
        container.innerHTML = history.map(t => `
            <tr>
                <td class="p-3 font-bold text-gray-400">${t.exchange || 'OKX'}</td>
                <td class="p-3 font-bold">${t.symbol}</td>
                <td class="p-3"><span class="${t.side === 'buy' ? 'text-green-400' : 'text-red-400'} font-bold uppercase">${t.side}</span></td>
                <td class="p-3 text-white">${t.price.toFixed(2)}</td>
                <td class="p-3 text-gray-400">${t.amount.toFixed(4)}</td>
                <td class="p-3 font-bold text-blue-400">${t.cost.toFixed(2)} USDT</td>
                <td class="p-3 text-gray-500">${new Date(t.timestamp).toLocaleTimeString()}</td>
            </tr>`).join('');
    } else {
        container.innerHTML = '<tr><td colspan="7" class="p-10 text-center text-gray-600 font-bold uppercase tracking-widest italic">No trades recorded yet</td></tr>';
    }
    dashboardState.historyHash = currentHash;
}

async function renderSymbolsTask(symbols, hotSymbols = []) {
    const currentHash = JSON.stringify(symbols) + JSON.stringify(hotSymbols);
    if (dashboardState.symbolsHash === currentHash) return;
    
    const list = document.getElementById('symbols-list');
    if (!list) return;

    list.innerHTML = symbols.map(s => {
        const isHot = hotSymbols.includes(s);
        return `
        <div class="flex justify-between items-center ${isHot ? 'bg-orange-500/10 border-orange-500/30' : 'bg-white/5 border-white/0'} p-2 rounded group border hover:border-blue-500/20 transition-all mb-1">
            <div class="flex items-center gap-2">
                ${isHot ? `<span class="text-[10px] animate-pulse">🔥</span>` : ''}
                <span class="text-[10px] font-mono ${isHot ? 'text-orange-300 font-bold' : 'text-blue-300'}">${s}</span>
            </div>
            <button onclick="deleteSymbol('${s}')" class="text-red-500/50 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all p-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3"><path d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        </div>`
    }).join('');
    dashboardState.symbolsHash = currentHash;
}

async function renderPositionsTask(positions) {
    const currentHash = JSON.stringify(positions);
    if (dashboardState.positionsHash === currentHash) return;
    
    const container = document.getElementById('positions-container');
    if (!container) return;

    container.innerHTML = positions.map(p => `
        <div class="flex justify-between items-center text-sm bg-white/5 p-3 rounded border border-white/5">
            <div class="flex flex-col">
                <span class="text-xs font-bold text-gray-400 uppercase tracking-tight">${p.symbol.split('/')[0]}</span>
                <span class="${p.side === 'long' ? 'text-green-400' : 'text-red-400'} text-[10px] font-bold uppercase">${p.side} ${p.leverage}x</span>
            </div>
            <span class="${p.percentage >= 0 ? 'text-green-500' : 'text-red-500'} font-orbitron font-bold">${p.percentage.toFixed(2)}%</span>
        </div>`).join('') || '<p class="text-xs text-gray-600 italic px-2">No active exposure</p>';
    dashboardState.positionsHash = currentHash;
}

async function renderLogsTask(entries, botActive) {
    const currentHash = JSON.stringify(entries.slice(0, 20));
    if (dashboardState.logsHash === currentHash) return;
    
    const container = document.getElementById('log-container');
    const watchdogStatus = document.getElementById('ai-watchdog-status');
    
    const visibleEntries = entries.filter(e => !(e.action === 'WAIT' && (e.reasoning.includes('Quiet') || e.reasoning === 'N/A')));
    if (container) {
        container.innerHTML = visibleEntries.map((e, index) => {
            const statusColor = e.action === 'BUY' ? 'bg-green-500' : e.action === 'SELL' ? 'bg-red-500' : e.action === 'CLOSE' ? 'bg-white' : 'bg-blue-500';
            const modelBadgeColor = e.model_name && e.model_name.includes('gemini') ? 'border-blue-500/30 text-blue-400 bg-blue-500/10' : 
                                  (e.model_name && e.model_name.includes('deepseek') ? 'border-purple-500/30 text-purple-400 bg-purple-500/10' : 'border-green-500/30 text-green-400 bg-green-500/10');
                                  
            return `
            <div onclick="openModal(${index})" class="glass-panel p-4 bg-white/5 hover:bg-white/10 transition-all border-l-4 cursor-pointer ${e.action === 'BUY' ? 'border-green-500' : e.action === 'SELL' ? 'border-red-500' : 'border-gray-500'}">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-1 rounded text-[10px] font-bold text-black ${statusColor}">${e.action}</span>
                        <span class="text-xs text-gray-500 font-medium">${e.timestamp}</span>
                    </div>
                    <div class="flex flex-col items-end gap-1">
                        <span class="text-orbitron text-xs font-bold ${e.score >= 8 ? 'text-green-400' : e.score <= 3 ? 'text-red-400' : 'text-blue-400'}">S: ${e.score}/10</span>
                        <span class="text-[8px] font-bold px-1.5 py-0.5 rounded border uppercase ${modelBadgeColor}">${e.model_name || 'Gemini'}</span>
                    </div>
                </div>
                <p class="text-xs text-gray-300 italic line-clamp-2">"${e.reasoning}"</p>
            </div>`;
        }).join('') || '<div class="text-center py-10 text-gray-500 italic text-xs">Waiting for market signals...</div>';
    }
    dashboardState.logsHash = currentHash;
}

async function renderAnalyticsTask(data) {
    const a = data.analytics;
    const h = data.system_health;
    if (!a) return;

    safeSetText('analytics-profit', `${a.net_profit > 0 ? '+' : ''}${a.net_profit.toFixed(2)} USDT`);
    const roiEl = document.getElementById('analytics-roi');
    if (roiEl) {
        roiEl.innerText = `${a.roi_pct > 0 ? '+' : ''}${a.roi_pct.toFixed(2)}% ROI`;
        roiEl.className = `text-[10px] font-bold mt-1 ${a.roi_pct >= 0 ? 'text-green-400' : 'text-red-400'}`;
    }
    safeSetText('analytics-initial', `${a.initial_balance.toFixed(2)} USDT`);
    
    // Pro Metrics
    safeSetText('analytics-calmar', a.calmar_ratio.toFixed(2));
    safeSetText('analytics-vol', `${a.daily_volatility.toFixed(2)}%`);
    safeSetText('analytics-profit-factor', a.profit_factor.toFixed(2));
    safeSetText('analytics-recovery', a.recovery_factor.toFixed(2));
    safeSetText('analytics-winrate', `Win Rate: ${a.win_rate}%`);
    safeSetText('analytics-start-date', `Started on ${new Date(a.start_time).toLocaleDateString()}`);

    // System Health
    if (h) {
        safeSetText('health-reliability', `${h.ai_reliability_pct}%`);
        safeSetText('health-latency', `${Math.round(h.avg_cycle_latency_ms)}ms`);
        const hCard = document.getElementById('health-card');
        if (hCard) {
            hCard.className = `glass-panel p-4 border-${h.status === 'HEALTHY' ? 'green' : (h.status === 'WARNING' ? 'orange' : 'red')}-500/10 bg-${h.status === 'HEALTHY' ? 'green' : (h.status === 'WARNING' ? 'orange' : 'red')}-500/5 transition-all`;
        }
    }

    // Kaizen Insight Simulation/Fetch (assuming it comes from the last analysis reasoning for now or a dedicated field)
    const logContainer = document.getElementById('log-container');
    if (logContainer && data.entries && data.entries.length > 0) {
        // Find the latest Kaizen report if available (marked by specific keywords in reasoning or separate field)
        const kaizenEntry = data.entries.find(e => e.reasoning && e.reasoning.includes('Kaizen'));
        if (kaizenEntry) {
            safeSetText('kaizen-insight', kaizenEntry.reasoning);
        }
    }
}

async function updateChartsTask(entries) {
    // Basic Sentiment Chart Update
    const chartLabels = entries.slice(0, 10).reverse().map(e => e.timestamp.split(' ')[1]);
    const chartData = entries.slice(0, 10).reverse().map(e => e.score);

    if (!sentimentChart) {
        const ctx = document.getElementById('sentimentChart')?.getContext('2d');
        if (ctx) {
            sentimentChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        data: chartData,
                        borderColor: '#60a5fa',
                        backgroundColor: 'rgba(96, 165, 250, 0.1)',
                        fill: true, tension: 0.4
                    }]
                },
                options: { responsive: true, plugins: { legend: { display: false } }, maintainAspectRatio: false }
            });
        }
    } else {
        sentimentChart.data.labels = chartLabels;
        sentimentChart.data.datasets[0].data = chartData;
        sentimentChart.update('none');
    }
}

// Control Logic
async function toggleBot() {
    try {
        const res = await fetch('/api/toggle_bot', { method: 'POST' });
        const data = await res.json();
        updatePowerUI(data.active, data.is_trading_day);
    } catch (e) { alert("Backend Unreachable!"); }
}

function updatePowerUI(isActive, isTradingDay) {
    const txt = document.getElementById('power-text');
    const ind = document.getElementById('power-indicator');
    const btn = document.getElementById('btn-power');
    
    if (!isTradingDay) {
        if(txt) txt.innerText = "SCHEDULE LOCK";
        if(ind) ind.className = "w-3 h-3 bg-orange-500 rounded-full shadow-[0_0_10px_rgba(249,115,22,0.5)]";
        if(btn) btn.classList.add('opacity-50');
        return;
    }
    
    if(btn) btn.classList.remove('opacity-50');
    if(txt) txt.innerText = isActive ? "ONLINE" : "PAUSED";
    if(ind) ind.className = isActive ? "w-3 h-3 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.5)]" : "w-3 h-3 bg-red-500 rounded-full shadow-[0_0_10px_rgba(239,68,68,0.5)]";
    if(txt) txt.className = isActive ? "text-sm font-semibold text-white" : "text-sm font-semibold text-red-500";
}

async function updateScheduleUI(tradingDays, isTradingDay, startHour, endHour) {
    dashboardState.isTradingDay = isTradingDay;
    dashboardState.tradingDays = tradingDays;
    
    for (let i = 0; i <= 6; i++) {
        const dayBtn = document.getElementById(`day-${i}`);
        if (!dayBtn) continue;
        if (tradingDays.includes(i)) {
            dayBtn.className = "flex-1 py-1.5 rounded bg-blue-600/20 border border-blue-500/50 text-[10px] font-bold text-blue-400";
        } else {
            dayBtn.className = "flex-1 py-1.5 rounded bg-black/40 border border-white/5 text-[10px] font-bold text-gray-600";
        }
    }

    const sInp = document.getElementById('sched-start');
    const eInp = document.getElementById('sched-end');
    if (sInp && sInp.value === '') sInp.value = startHour;
    if (eInp && eInp.value === '') eInp.value = endHour;
}

async function toggleDay(dayIndex) {
    let currentDays = [...dashboardState.tradingDays];
    if (currentDays.includes(dayIndex)) {
        currentDays = currentDays.filter(d => d !== dayIndex);
    } else {
        currentDays.push(dayIndex);
        currentDays.sort();
    }
    saveSchedule(currentDays, document.getElementById('sched-start').value, document.getElementById('sched-end').value);
}

async function updateHours() {
    saveSchedule(dashboardState.tradingDays, document.getElementById('sched-start').value, document.getElementById('sched-end').value);
}

async function saveSchedule(days, start, end) {
    try {
        const res = await fetch('/api/update_schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trading_days: days, start_hour: start, end_hour: end })
        });
        const data = await res.json();
        if (data.status === "success") updateScheduleUI(data.trading_days, data.is_trading_day, data.start_hour, data.end_hour);
    } catch (e) { console.error("Schedule error:", e); }
}

async function addSymbol() {
    const input = document.getElementById('new-symbol');
    const symbol = input.value.trim().toUpperCase();
    if(!symbol) return;
    try {
        const res = await fetch('/api/symbols/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        if(res.ok) { input.value = ''; updateDashboard(); }
        else { const r = await res.json(); alert(r.message); }
    } catch (e) { alert("Network error"); }
}

async function deleteSymbol(symbol) {
    if(!confirm(`Delete ${symbol}?`)) return;
    try {
        await fetch('/api/symbols/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        updateDashboard();
    } catch (e) { console.error(e); }
}

async function saveAPIKeys() {
    const payload = {
        exchange: document.getElementById('exchange-select').value,
        ai_provider: document.getElementById('ai-provider-select').value,
        gemini_key: document.getElementById('gemini-key-input').value,
        key: document.getElementById('api-key-input').value,
        secret: document.getElementById('api-secret-input').value,
        passphrase: document.getElementById('api-pass-input').value
    };

    try {
        const res = await fetch('/api/settings/keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if(res.ok) { alert("Connected!"); closeAPIModal(); updateDashboard(); }
    } catch (e) { alert("Error saving keys"); }
}

function toggleAIInputs() {
    const provider = document.getElementById('ai-provider-select').value;
    document.querySelectorAll('.ai-input-group').forEach(el => el.classList.add('hidden'));
    const target = document.getElementById(`input-${provider}`);
    if(target) target.classList.remove('hidden');
}

async function updatePerformanceChart() {
    try {
        const res = await fetch('/api/portfolio/history');
        const history = await res.json();
        const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString());
        const data = history.map(h => h.balance);

        if (!performanceChart) {
            const ctx = document.getElementById('performanceChart')?.getContext('2d');
            if(ctx) {
                performanceChart = new Chart(ctx, {
                    type: 'line',
                    data: { labels, datasets: [{ label: 'Equity', data: data, borderColor: '#10b981', fill: true, backgroundColor: 'rgba(16,185,129,0.1)' }] },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            }
        } else {
            performanceChart.data.labels = labels;
            performanceChart.data.datasets[0].data = data;
            performanceChart.update();
        }
    } catch (e) { console.warn(e); }
}

// Exports
function downloadLatestMD() { window.location.href = '/api/reports/download/md'; }
async function exportToPDF() {
    const opt = { margin: 10, filename: 'ASTRA_Report.pdf', image: { type: 'jpeg', quality: 0.98 }, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a4' } };
    html2pdf().set(opt).from(document.getElementById('log-container')).save();
}

function confirmDeleteReports() { document.getElementById('delete-modal').classList.remove('hidden'); }
function closeDeleteModal() { document.getElementById('delete-modal').classList.add('hidden'); }
async function executeDeleteReports() {
    await fetch('/api/reports/delete_all', { method: 'POST' });
    closeDeleteModal();
    updateDashboard();
}

function openResetModal() { 
    const input = document.getElementById('manual-init-balance');
    if (input && dashboardState.balance !== null) {
        input.value = dashboardState.balance.toFixed(2);
    }
    document.getElementById('reset-modal').classList.remove('hidden'); 
}
function closeResetModal() { document.getElementById('reset-modal').classList.add('hidden'); }
async function executeManualReset() {
    const balance = document.getElementById('manual-init-balance').value;
    await fetch('/api/portfolio/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ balance: parseFloat(balance) })
    });
    closeResetModal();
    updateDashboard();
}

function switchTab(tabId) {
    ['flow', 'history', 'analytics', 'pro', 'chart'].forEach(id => {
        const el = document.getElementById(`tab-${id}`);
        if(el) el.classList.add('hidden');
        const btn = document.getElementById(`btn-tab-${id}`);
        if(btn) btn.className = "text-xs font-bold uppercase tracking-widest text-gray-500 hover:text-white pb-2 transition-all";
    });

    const activeEl = document.getElementById(`tab-${tabId}`);
    if(activeEl) activeEl.classList.remove('hidden');
    const activeBtn = document.getElementById(`btn-tab-${tabId === 'flow' ? 'flow' : tabId}`);
    if(activeBtn) activeBtn.className = "text-xs font-bold uppercase tracking-widest text-blue-400 border-b-2 border-blue-500 pb-2 transition-all";

    if (tabId === 'analytics') updatePerformanceChart();
}

function safeSetText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

// Modals
// Modals
function calculateRisk(details) {
    const leverage = details.leverage || 1;
    const sl = details.sl_pct || 0.2;
    const totalRisk = (sl * leverage * 100);
    
    if (totalRisk >= 100) return { label: 'EXTREME', color: 'text-red-600' };
    if (totalRisk >= 50) return { label: 'HIGH', color: 'text-red-400' };
    if (totalRisk >= 20) return { label: 'MODERATE', color: 'text-yellow-400' };
    return { label: 'LOW', color: 'text-green-400' };
}

function openModal(index) {
    const entry = lastFullData[index];
    const details = entry.details || {};
    const risk = calculateRisk(details);
    const cleanAsset = (details.target_symbol || 'N/A').replace(/:USDT/g, '');

    document.getElementById('modal-title').innerText = `DEAL: ${cleanAsset}`;
    safeSetText('modal-asset', cleanAsset);
    safeSetText('modal-exchange', (entry.exchange || dashboardState.currentExchange || 'OKX').toUpperCase());
    safeSetText('modal-amount', `${details.budget_usdt || 0} USDT`);
    
    const riskEl = document.getElementById('modal-risk');
    if(riskEl) {
        riskEl.innerText = risk.label;
        riskEl.className = `text-sm font-bold ${risk.color}`;
    }

    document.getElementById('modal-reasoning').innerText = entry.reasoning;
    
    // Model Badge in Modal
    const modelEl = document.getElementById('modal-model');
    if (modelEl) {
        const modelName = entry.model_name || 'GEMINI-FLASH';
        modelEl.innerText = modelName.toUpperCase();
        const modelClass = modelName.includes('gemini') ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' : 
                          (modelName.includes('deepseek') ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' : 'bg-green-500/20 text-green-400 border-green-500/30');
        modelEl.className = `text-[9px] font-bold px-2 py-0.5 rounded border uppercase font-mono ${modelClass}`;
    }

    // Display percentages correctly regardless of format (0.03 vs 3.0)
    let tpVal = details.tp_pct || 0;
    let slVal = details.sl_pct || 0;
    
    // Normalize: if 0.085 -> 8.5%, if 8.5 -> 8.5%
    if (tpVal > 0 && tpVal < 0.5) tpVal = tpVal * 100;
    if (slVal > 0 && slVal < 0.5) slVal = slVal * 100;
    
    safeSetText('modal-tp', `+${tpVal.toFixed(1)}%`);
    safeSetText('modal-sl', `-${slVal.toFixed(1)}%`);

    // Add Margin Risk info to reasoning
    const marginRisk = (slVal * (details.leverage || 1)).toFixed(1);
    const reasoningEl = document.getElementById('modal-reasoning');
    if (reasoningEl) {
        reasoningEl.innerHTML = `<div class="mb-3 text-gray-200">"${entry.reasoning}"</div>
                                 <div class="mt-4 pt-3 border-t border-white/10 flex justify-between items-center">
                                    <span class="text-[10px] text-gray-400 font-bold uppercase">Collateral Risk (SL x LVG)</span>
                                    <span class="text-xs font-bold ${marginRisk >= 50 ? 'text-red-500' : 'text-yellow-400'}">${marginRisk}% of Margin</span>
                                 </div>`;
    }
    
    document.getElementById('detail-modal').classList.remove('hidden');
}
function closeModal() { document.getElementById('detail-modal').classList.add('hidden'); }
function openAPIModal() { document.getElementById('api-modal').classList.remove('hidden'); }
function closeAPIModal() { document.getElementById('api-modal').classList.add('hidden'); }
function openBalanceModal() { 
    const list = document.getElementById('balance-breakdown-list');
    list.innerHTML = Object.entries(exchangeBalances).map(([ex, bal]) => `<div class="flex justify-between"><span>${ex}</span><span>${bal.toFixed(2)} USDT</span></div>`).join('');
    document.getElementById('balance-modal').classList.remove('hidden'); 
}
function closeBalanceModal() { document.getElementById('balance-modal').classList.add('hidden'); }

// Init
setInterval(updateDashboard, 3000);
updateDashboard();
