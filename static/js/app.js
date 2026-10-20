/* ====================================================================
   PULSE-TWIN 2026 - Clinical Digital Twin Platform Frontend App
   ==================================================================== */

// Global State
let currentPatientId = null;
let currentPatientData = null;
let autoStreamInterval = null;
let isAutoStreaming = false;
let patientList = [];

// Chart Instances
let cgmChartInstance = null;
let wearableChartInstance = null;

// DOM Elements
const systemClockEl = document.getElementById('systemClock');
const patientListContainer = document.getElementById('patientListContainer');
const patientSearchInput = document.getElementById('patientSearchInput');
const patientCountBadge = document.getElementById('patientCountBadge');
const btnToggleStream = document.getElementById('btnToggleStream');
const btnStepNext = document.getElementById('btnStepNext');
const streamPlayIcon = document.getElementById('streamPlayIcon');
const streamPlayText = document.getElementById('streamPlayText');
const streamStatusText = document.getElementById('streamStatusText');

// Patient Banner Elements
const patientFullName = document.getElementById('patientFullName');
const twinIdBadge = document.getElementById('twinIdBadge');
const twinRiskBadge = document.getElementById('twinRiskBadge');
const patientDemographics = document.getElementById('patientDemographics');
const patientLocation = document.getElementById('patientLocation');
const pairedDeviceTag = document.getElementById('pairedDeviceTag');
const statBaselineHba1c = document.getElementById('statBaselineHba1c');
const statISF = document.getElementById('statISF');
const statICR = document.getElementById('statICR');

// Medical History Drawer
const toggleHistoryBtn = document.getElementById('toggleHistoryBtn');
const historyDrawer = document.getElementById('historyDrawer');
const historyChevron = document.getElementById('historyChevron');
const conditionsCountBadge = document.getElementById('conditionsCountBadge');
const medicationsCountBadge = document.getElementById('medicationsCountBadge');
const conditionsList = document.getElementById('conditionsList');
const medicationsList = document.getElementById('medicationsList');

// Metric Cards
const metricCurrentGlucose = document.getElementById('metricCurrentGlucose');
const glucoseTrendIcon = document.getElementById('glucoseTrendIcon');
const glucoseTrendText = document.getElementById('glucoseTrendText');
const metricRecordedAt = document.getElementById('metricRecordedAt');
const metricPredictedGlucose = document.getElementById('metricPredictedGlucose');
const forecastDeltaBadge = document.getElementById('forecastDeltaBadge');
const metricConfidenceBand = document.getElementById('metricConfidenceBand');
const metricTIR = document.getElementById('metricTIR');
const tirBadge = document.getElementById('tirBadge');
const metricGMI = document.getElementById('metricGMI');
const metricHeartRate = document.getElementById('metricHeartRate');
const metricSkinTemp = document.getElementById('metricSkinTemp');
const metricGSR = document.getElementById('metricGSR');
const metricStressLevel = document.getElementById('metricStressLevel');

// ADA Alert Banner
const clinicalAlertBanner = document.getElementById('clinicalAlertBanner');
const alertIcon = document.getElementById('alertIcon');
const alertHeadline = document.getElementById('alertHeadline');
const alertCodeTag = document.getElementById('alertCodeTag');
const alertMessageText = document.getElementById('alertMessageText');
const alertRecommendationText = document.getElementById('alertRecommendationText');

// What-If Sandbox
const sandboxResultBanner = document.getElementById('sandboxResultBanner');
const sandboxResultText = document.getElementById('sandboxResultText');

// Modal Elements
const btnOpenModelModal = document.getElementById('btnOpenModelModal');
const btnCloseModal = document.getElementById('btnCloseModal');
const modelModal = document.getElementById('modelModal');
const modalBodyContent = document.getElementById('modalBodyContent');

// ====================================================================
// INITIALIZATION
// ====================================================================
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    setupEventListeners();
    initCharts();
    loadPatientCohort();
    loadOverviewDynamicMetrics();
    initDatasetPredictorStudio();
});

function initClock() {
    function update() {
        const now = new Date();
        systemClockEl.textContent = now.toLocaleTimeString();
    }
    update();
    setInterval(update, 1000);
}

function setupEventListeners() {
    // Search input
    patientSearchInput.addEventListener('input', (e) => {
        renderPatientList(e.target.value);
    });

    // Patient filter tabs
    document.querySelectorAll('.patient-filter-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.patient-filter-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderPatientList(patientSearchInput.value, btn.dataset.filter);
        });
    });

    // Stream Controls
    btnToggleStream.addEventListener('click', toggleAutoStream);
    btnStepNext.addEventListener('click', () => requestStreamTick(true));

    // History Accordion Toggle
    if (toggleHistoryBtn && historyDrawer) {
        toggleHistoryBtn.addEventListener('click', () => {
            const isCollapsed = historyDrawer.classList.toggle('collapsed');
            if (historyChevron) {
                historyChevron.classList.toggle('expanded', !isCollapsed);
            }
        });
    }

    // Sandbox Buttons
    document.querySelectorAll('.btn-sandbox').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            const params = {};
            if (btn.dataset.carbs) params.carbs = parseInt(btn.dataset.carbs);
            if (btn.dataset.units) params.units = parseFloat(btn.dataset.units);
            if (btn.dataset.steps) params.steps = parseInt(btn.dataset.steps);
            if (btn.dataset.intensity) params.intensity = btn.dataset.intensity;
            if (btn.dataset.stress) params.stress_level = parseInt(btn.dataset.stress);
            triggerSandboxEvent(action, params);
        });
    });

    // Model Modal
    btnOpenModelModal.addEventListener('click', openModelModal);
    btnCloseModal.addEventListener('click', () => modelModal.classList.add('hidden'));
    modelModal.addEventListener('click', (e) => {
        if (e.target === modelModal) modelModal.classList.add('hidden');
    });
}

// ====================================================================
// PATIENT COHORT MANAGEMENT
// ====================================================================
async function loadPatientCohort() {
    try {
        const resp = await fetch('/api/patients?limit=108');
        const data = await resp.json();
        if (data.status === 'success') {
            patientList = data.patients;
            patientCountBadge.textContent = patientList.length;
            renderPatientList();

            // Select first active twin by default
            const firstActive = patientList.find(p => p.paired_cgm_user_id) || patientList[0];
            if (firstActive) {
                await selectPatient(firstActive.id);
                // Dynamically start streaming dataset records
                if (!isAutoStreaming) {
                    toggleAutoStream();
                }
            }
        }
    } catch (err) {
        console.error('Failed to load patient cohort:', err);
        patientListContainer.innerHTML = '<div class="muted-text" style="padding:16px;">Failed to load patient cohort.</div>';
    }
}

function renderPatientList(query = '', filter = 'all') {
    let filtered = patientList;

    if (query.trim()) {
        const q = query.toLowerCase();
        filtered = filtered.filter(p => {
            const name = `${p.first_name} ${p.last_name}`.toLowerCase();
            const conds = (p.top_conditions || []).map(c => c.display_name.toLowerCase()).join(' ');
            return name.includes(q) || conds.includes(q);
        });
    }

    if (filter === 'paired') {
        filtered = filtered.filter(p => p.paired_cgm_user_id);
    } else if (filter === 'risk') {
        filtered = filtered.filter(p => p.risk_level && p.risk_level !== 'normal');
    }

    if (filtered.length === 0) {
        patientListContainer.innerHTML = '<div class="muted-text" style="padding:16px; font-size:12px;">No matching patients found.</div>';
        return;
    }

    patientListContainer.innerHTML = filtered.map(p => {
        const isSelected = p.id === currentPatientId ? 'selected' : '';
        const pairedTag = p.paired_cgm_user_id ? `<span class="badge badge-twin">CGM: ${p.paired_cgm_user_id}</span>` : '<span class="mini-tag">Unpaired</span>';
        const riskClass = p.risk_level === 'critical' ? 'critical' : (p.risk_level === 'warning' ? 'warning' : '');
        const riskBadge = p.paired_cgm_user_id ? `<span class="badge badge-risk ${riskClass}">${p.risk_level || 'normal'}</span>` : '';

        const condsPreview = (p.top_conditions || []).slice(0, 2).map(c => {
            const cleanName = c.display_name.replace(/\s*\(finding\)|\s*\(disorder\)|\s*\(situation\)/gi, '');
            return `<span class="mini-tag">${cleanName}</span>`;
        }).join('');

        return `
            <div class="patient-card ${isSelected}" onclick="selectPatient(${p.id})">
                <div class="p-card-top">
                    <span class="p-name">${p.first_name} ${p.last_name}</span>
                    ${riskBadge}
                </div>
                <div class="p-tags-row">
                    <span class="p-meta">${p.gender}, ${p.age || '--'}y</span>
                    ${pairedTag}
                </div>
                <div class="p-conditions-preview">
                    ${condsPreview}
                </div>
            </div>
        `;
    }).join('');
}

async function selectPatient(patientId) {
    if (currentPatientId === patientId) return;
    currentPatientId = patientId;

    // Highlight card
    document.querySelectorAll('.patient-card').forEach(c => c.classList.remove('selected'));
    const selectedCard = [...document.querySelectorAll('.patient-card')].find(c => c.getAttribute('onclick')?.includes(`selectPatient(${patientId})`));
    if (selectedCard) selectedCard.classList.add('selected');

    // Fetch patient details & telemetry
    await loadPatientDetails(patientId);
    await loadPatientTelemetry(patientId);
    // Initial live tick
    await requestStreamTick(false);
}

// ====================================================================
// PATIENT DETAILS & CLINICAL HISTORY
// ====================================================================
async function loadPatientDetails(patientId) {
    try {
        const resp = await fetch(`/api/patients/${patientId}`);
        const data = await resp.json();
        if (data.status === 'success') {
            currentPatientData = data.patient;
            updatePatientBanner(currentPatientData);
        }
    } catch (err) {
        console.error('Failed to load patient details:', err);
    }
}

function updatePatientBanner(p) {
    patientFullName.textContent = `${p.first_name} ${p.last_name}`;
    patientDemographics.innerHTML = `<i class="fa-solid fa-venus-mars"></i> ${p.gender} | <i class="fa-solid fa-cake-candles"></i> ${p.age || '--'} yrs (DOB: ${p.birth_date || 'N/A'})`;
    patientLocation.innerHTML = `<i class="fa-solid fa-location-dot"></i> ${p.city || 'Unknown'}, ${p.state || 'MA'}`;
    
    if (p.paired_cgm_user_id) {
        pairedDeviceTag.innerHTML = `<i class="fa-solid fa-satellite-dish"></i> CGM: ${p.paired_cgm_user_id} & ${p.paired_wearable_subject_id || 'E4'}`;
        twinIdBadge.textContent = p.twin_name || `Twin-${p.id}`;
        twinIdBadge.className = 'badge badge-twin';
    } else {
        pairedDeviceTag.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> Unpaired (Simulated EHR Profile)`;
        twinIdBadge.textContent = 'Twin-Standby';
        twinIdBadge.className = 'badge badge-count';
    }

    statBaselineHba1c.textContent = `${p.baseline_hba1c ? Number(p.baseline_hba1c).toFixed(1) : '5.7'}%`;
    statISF.textContent = `${p.insulin_sensitivity ? Number(p.insulin_sensitivity).toFixed(0) : '40'} mg/dL/U`;
    statICR.textContent = `${p.carb_ratio ? Number(p.carb_ratio).toFixed(0) : '12'} g/U`;

    // Populate conditions list
    const conds = p.conditions || [];
    conditionsCountBadge.textContent = `${conds.length} Conditions`;
    if (conds.length === 0) {
        conditionsList.innerHTML = '<li class="muted-text">No active conditions recorded in EHR.</li>';
    } else {
        conditionsList.innerHTML = conds.map(c => `
            <li>
                <strong>${c.display_name}</strong>
                <small>[SNOMED: ${c.code || 'N/A'}]</small>
            </li>
        `).join('');
    }

    // Populate medications list
    const meds = p.medications || [];
    conditionsCountBadge.textContent = `${conds.length} Conditions`;
    medicationsCountBadge.textContent = `${meds.length} Medications`;
    if (meds.length === 0) {
        medicationsList.innerHTML = '<li class="muted-text">No active medications recorded in EHR.</li>';
    } else {
        medicationsList.innerHTML = meds.map(m => `
            <li>
                <strong>${m.medication_name}</strong>
                <small>[RxNorm: ${m.rxnorm_code || 'N/A'}]</small>
            </li>
        `).join('');
    }

    // Update Simulation Lab view patient header
    const simName = document.getElementById('simPatientName');
    if (simName) simName.textContent = `Active Twin: ${p.first_name} ${p.last_name} (${p.twin_name || 'Twin-' + p.id})`;
    const simMeta = document.getElementById('simPatientMeta');
    if (simMeta) simMeta.textContent = `ISF: ${p.insulin_sensitivity ? Number(p.insulin_sensitivity).toFixed(0) : 40} mg/dL/U | ICR: ${p.carb_ratio ? Number(p.carb_ratio).toFixed(0) : 12} g/U | Target: 70-180 mg/dL`;

    // Update EHR view KPI cards
    const ehrHba1c = document.getElementById('ehrKpiHba1c');
    if (ehrHba1c) ehrHba1c.textContent = `${p.baseline_hba1c ? Number(p.baseline_hba1c).toFixed(1) : '5.7'}%`;
    const ehrConds = document.getElementById('ehrKpiConditionsCount');
    if (ehrConds) ehrConds.textContent = conds.length;
}

// ====================================================================
// TELEMETRY HISTORY & CHARTS
// ====================================================================
async function loadPatientTelemetry(patientId) {
    try {
        const resp = await fetch(`/api/twins/${patientId}/telemetry?limit=48`);
        const data = await resp.json();
        if (data.status === 'success' && data.data) {
            const telemetry = data.data;
            updateGlycemicMetrics(telemetry.metrics);
            renderChartsData(telemetry.readings);
        }
    } catch (err) {
        console.error('Failed to load telemetry:', err);
    }
}

function updateGlycemicMetrics(m) {
    if (!m) {
        metricTIR.textContent = '--%';
        metricGMI.textContent = '--%';
        return;
    }
    metricTIR.textContent = `${m.time_in_range_pct}%`;
    tirBadge.textContent = `${m.time_in_range_pct}% TIR`;
    tirBadge.className = m.time_in_range_pct >= 70 ? 'badge badge-risk' : 'badge badge-risk warning';
    metricGMI.textContent = `${m.estimated_hba1c}%`;
}

// ====================================================================
// REAL-TIME STREAMING & ML INFERENCE
// ====================================================================
async function requestStreamTick(stepForward = true) {
    if (!currentPatientId) return;

    try {
        const resp = await fetch(`/api/twins/${currentPatientId}/tick?step=${stepForward}`);
        const json = await resp.json();
        if (json.status === 'success' && json.data) {
            updateDashboardWithTick(json.data);
        }
    } catch (err) {
        console.error('Error fetching stream tick:', err);
    }
}

function updateDashboardWithTick(tick) {
    if (tick.status === 'unpaired') {
        metricCurrentGlucose.textContent = '--';
        metricPredictedGlucose.textContent = '--';
        alertHeadline.textContent = 'Unpaired Digital Twin';
        alertMessageText.textContent = 'This patient has no active continuous monitoring device paired. Telemetry is in standby.';
        clinicalAlertBanner.className = 'clinical-alert-banner alert-normal';
        return;
    }

    const tel = tick.telemetry;
    const pred = tick.prediction;
    const risk = pred.risk_assessment;

    // 1. Current Glucose
    const currentG = tel.glucose;
    metricCurrentGlucose.textContent = currentG.toFixed(1);
    metricRecordedAt.textContent = tick.recorded_at.split(' ')[1] || tick.recorded_at;

    // Trend Direction
    updateTrendIndicator(risk.trend_direction, risk.rate_per_minute);

    // Color State for current glucose
    metricCurrentGlucose.className = 'hero-number';
    if (currentG < 54 || currentG > 250) {
        metricCurrentGlucose.classList.add('state-red');
    } else if (currentG < 70 || currentG > 180) {
        metricCurrentGlucose.classList.add('state-amber');
    } else {
        metricCurrentGlucose.classList.add('state-green');
    }

    // 2. Predicted Glucose (30m)
    const predG = pred.predicted_glucose_30m;
    metricPredictedGlucose.textContent = predG.toFixed(1);
    const delta = pred.delta_mg_dl;
    forecastDeltaBadge.textContent = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)} mg/dL`;
    forecastDeltaBadge.className = delta > 0 ? 'badge badge-ai' : 'badge badge-risk warning';

    const ci = pred.confidence_interval_95;
    metricConfidenceBand.textContent = `[${ci.lower} - ${ci.upper}]`;

    // 3. Wearable telemetry
    metricHeartRate.innerHTML = `${Math.round(tel.heart_rate)} <small>BPM</small>`;
    metricSkinTemp.innerHTML = `${tel.skin_temp.toFixed(1)} <small>°C</small>`;
    metricGSR.innerHTML = `${tel.gsr.toFixed(2)} <small>µS</small>`;
    metricStressLevel.innerHTML = `${tel.stress_level} <small>/5</small>`;

    // 4. ADA Clinical Risk Alert Banner
    updateAlertBanner(risk);

    // 5. Update Live Dataset Stream Ingestion Status Bar
    const liveSourceEl = document.getElementById('liveDatasetSourceText');
    if (liveSourceEl && tel.dataset_source) {
        liveSourceEl.textContent = tel.dataset_source;
    }
    const liveRowEl = document.getElementById('liveDatasetRowText');
    if (liveRowEl && tel.cursor_index !== undefined) {
        liveRowEl.textContent = `Row ${tel.cursor_index + 1} / ${tel.total_dataset_rows}`;
    }
    const liveLag1El = document.getElementById('liveLag1Text');
    if (liveLag1El && tick.ml_input_features) {
        liveLag1El.textContent = `${Number(tick.ml_input_features.glucose_lag_1).toFixed(1)} mg/dL`;
    }
    const liveRollEl = document.getElementById('liveRollMeanText');
    if (liveRollEl && tick.ml_input_features) {
        liveRollEl.textContent = `${Number(tick.ml_input_features.glucose_roll_mean_1h).toFixed(1)} mg/dL`;
    }
    const livePredDeltaEl = document.getElementById('livePredDeltaText');
    if (livePredDeltaEl) {
        livePredDeltaEl.textContent = `${pred.predicted_glucose_30m.toFixed(1)} mg/dL (${pred.delta_mg_dl >= 0 ? '+' : ''}${pred.delta_mg_dl.toFixed(1)})`;
    }

    // 6. Update Real-time Data Point on Charts
    appendLivePointToCharts(tick.recorded_at, currentG, predG, tel);
}

function updateTrendIndicator(direction, rate) {
    let iconClass = 'fa-solid fa-arrow-right';
    let text = 'Stable trend';

    if (direction === 'rapidly_rising') {
        iconClass = 'fa-solid fa-arrow-up';
        text = `Rapidly rising (+${rate} mg/dL/min)`;
    } else if (direction === 'rising') {
        iconClass = 'fa-solid fa-arrow-trend-up';
        text = `Rising (+${rate} mg/dL/min)`;
    } else if (direction === 'rapidly_falling') {
        iconClass = 'fa-solid fa-arrow-down';
        text = `Rapidly falling (${rate} mg/dL/min)`;
    } else if (direction === 'falling') {
        iconClass = 'fa-solid fa-arrow-trend-down';
        text = `Falling (${rate} mg/dL/min)`;
    }
    glucoseTrendIcon.innerHTML = `<i class="${iconClass}"></i>`;
    glucoseTrendText.textContent = text;
}

function updateAlertBanner(risk) {
    alertCodeTag.textContent = risk.alert_code;
    alertMessageText.textContent = risk.alert_message;
    alertRecommendationText.innerHTML = `<i class="fa-solid fa-hand-holding-medical"></i> <strong>Recommendation:</strong> ${risk.clinical_recommendation}`;

    if (risk.risk_level === 'Critical') {
        clinicalAlertBanner.className = 'clinical-alert-banner alert-critical';
        alertIcon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        alertHeadline.textContent = 'CRITICAL CLINICAL ALERT';
        twinRiskBadge.className = 'badge badge-risk critical';
        twinRiskBadge.textContent = 'Critical Alert';
    } else if (risk.risk_level === 'Warning') {
        clinicalAlertBanner.className = 'clinical-alert-banner alert-warning';
        alertIcon.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i>';
        alertHeadline.textContent = 'Clinical Glycemic Warning';
        twinRiskBadge.className = 'badge badge-risk warning';
        twinRiskBadge.textContent = 'Warning';
    } else {
        clinicalAlertBanner.className = 'clinical-alert-banner alert-normal';
        alertIcon.innerHTML = '<i class="fa-solid fa-shield-heart"></i>';
        alertHeadline.textContent = 'Optimal Glycemic State';
        twinRiskBadge.className = 'badge badge-risk';
        twinRiskBadge.textContent = 'Normal';
    }
}

function toggleAutoStream() {
    isAutoStreaming = !isAutoStreaming;
    if (isAutoStreaming) {
        streamPlayIcon.className = 'fa-solid fa-pause';
        streamPlayText.textContent = 'Pause Stream';
        streamStatusText.textContent = 'Auto-Streaming Active';
        autoStreamInterval = setInterval(() => {
            requestStreamTick(true);
        }, 2500);
    } else {
        clearInterval(autoStreamInterval);
        streamPlayIcon.className = 'fa-solid fa-play';
        streamPlayText.textContent = 'Auto-Stream';
        streamStatusText.textContent = 'Stream Paused';
    }
}

// ====================================================================
// WHAT-IF CLINICAL INTERVENTION SANDBOX
// ====================================================================
async function triggerSandboxEvent(eventType, params) {
    if (!currentPatientId) return;

    try {
        const resp = await fetch(`/api/twins/${currentPatientId}/simulate-event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_type: eventType, params })
        });
        const data = await resp.json();
        if (data.status === 'success' && data.result) {
            const res = data.result;
            sandboxResultBanner.classList.remove('hidden');
            sandboxResultText.textContent = `${res.event_summary} -> Forecasted Glucose: ${res.new_prediction.predicted_glucose_30m} mg/dL (${res.new_prediction.risk_assessment.risk_level})`;

            // Update dashboard with new perturbed state
            const pseudoTick = {
                status: 'success',
                recorded_at: 'Now (Simulated)',
                telemetry: res.updated_telemetry,
                prediction: res.new_prediction
            };
            updateDashboardWithTick(pseudoTick);

            setTimeout(() => {
                sandboxResultBanner.classList.add('hidden');
            }, 6000);
        }
    } catch (err) {
        console.error('Error in sandbox simulation:', err);
    }
}

// ====================================================================
// CHART.JS INITIALIZATION & REAL-TIME UPDATES
// ====================================================================
function initCharts() {
    // 1. Continuous Glucose Monitoring Chart
    const cgmCanvas = document.getElementById('cgmChart');
    if (cgmCanvas) {
        const cgmCtx = cgmCanvas.getContext('2d');
        cgmChartInstance = new Chart(cgmCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Historical CGM',
                        data: [],
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: false,
                        pointRadius: 2,
                        pointHoverRadius: 5
                    },
                    {
                        label: '30-Min AI Forecast',
                        data: [],
                        borderColor: '#A855F7',
                        borderDash: [5, 5],
                        borderWidth: 2.5,
                        pointRadius: 4,
                        pointBackgroundColor: '#A855F7',
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#F8FAFC',
                        bodyColor: '#CBD5E1',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#64748B', font: { size: 10 }, maxRotation: 0 }
                    },
                    y: {
                        min: 50,
                        max: 260,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: {
                            color: '#94A3B8',
                            font: { size: 10 },
                            callback: (v) => `${v} mg/dL`
                        }
                    }
                }
            }
        });
    }

    // 2. Wearable Multi-Signal Chart
    const wearCanvas = document.getElementById('wearableChart') || document.getElementById('wearableChartAlt');
    if (wearCanvas) {
        const wearCtx = wearCanvas.getContext('2d');
        wearableChartInstance = new Chart(wearCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Heart Rate (BPM)',
                    data: [],
                    borderColor: '#EF4444',
                    borderWidth: 1.5,
                    tension: 0.3,
                    pointRadius: 0,
                    yAxisID: 'yHR'
                },
                {
                    label: 'Skin Temp (°C)',
                    data: [],
                    borderColor: '#F59E0B',
                    borderWidth: 1.5,
                    tension: 0.3,
                    pointRadius: 0,
                    yAxisID: 'yTemp'
                },
                {
                    label: 'GSR (µS)',
                    data: [],
                    borderColor: '#06B6D4',
                    borderWidth: 1.5,
                    tension: 0.3,
                    pointRadius: 0,
                    yAxisID: 'yGSR'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.95)'
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { color: '#64748B', font: { size: 10 }, maxRotation: 0 }
                },
                yHR: {
                    type: 'linear',
                    position: 'left',
                    min: 50,
                    max: 150,
                    ticks: { color: '#EF4444', font: { size: 9 } },
                    grid: { color: 'rgba(255, 255, 255, 0.03)' }
                },
                yTemp: {
                    type: 'linear',
                    position: 'right',
                    min: 34.0,
                    max: 39.0,
                    ticks: { color: '#F59E0B', font: { size: 9 } },
                    grid: { drawOnChartArea: false }
                },
                yGSR: {
                    type: 'linear',
                    position: 'right',
                    min: 0.0,
                    max: 10.0,
                    ticks: { color: '#06B6D4', font: { size: 9 } },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

function renderChartsData(readings) {
    if (!readings || readings.length === 0) return;

    const labels = readings.map(r => r.recorded_at.split(' ')[1] || r.recorded_at);
    const glucose = readings.map(r => r.glucose_level);
    const hr = readings.map(r => r.heart_rate || 75.0);
    const temp = readings.map(r => r.skin_temp || 36.5);
    const gsr = readings.map(r => r.gsr || 1.5);

    // CGM Chart update
    if (cgmChartInstance) {
        cgmChartInstance.data.labels = labels;
        cgmChartInstance.data.datasets[0].data = glucose;
        cgmChartInstance.data.datasets[1].data = []; // Clear prediction line initially
        cgmChartInstance.update();
    }

    // Wearable Chart update
    if (wearableChartInstance) {
        wearableChartInstance.data.labels = labels;
        wearableChartInstance.data.datasets[0].data = hr;
        wearableChartInstance.data.datasets[1].data = temp;
        wearableChartInstance.data.datasets[2].data = gsr;
        wearableChartInstance.update();
    }
}

function appendLivePointToCharts(timeStr, currentG, predG, telemetry) {
    const timeLabel = timeStr.includes(' ') ? timeStr.split(' ')[1] : timeStr;

    // Append to CGM Chart
    if (cgmChartInstance) {
        const labels = cgmChartInstance.data.labels;
        const histData = cgmChartInstance.data.datasets[0].data;

        labels.push(timeLabel);
        histData.push(currentG);

        // Keep max 40 points in chart view
        if (labels.length > 40) {
            labels.shift();
            histData.shift();
        }

        // Set prediction forecast marker (+30m ahead)
        const forecastData = new Array(labels.length).fill(null);
        forecastData[labels.length - 1] = currentG; // connect current to forecast
        labels.push('+30m');
        forecastData.push(predG);
        cgmChartInstance.data.datasets[1].data = forecastData;

        cgmChartInstance.update();

        // Pop the '+30m' from labels for the next historical iteration
        labels.pop();
    }

    // Append to Wearable Chart
    if (wearableChartInstance && telemetry) {
        const wLabels = wearableChartInstance.data.labels;
        const hrData = wearableChartInstance.data.datasets[0].data;
        const tempData = wearableChartInstance.data.datasets[1].data;
        const gsrData = wearableChartInstance.data.datasets[2].data;

        wLabels.push(timeLabel);
        hrData.push(telemetry.heart_rate);
        tempData.push(telemetry.skin_temp);
        gsrData.push(telemetry.gsr);

        if (wLabels.length > 40) {
            wLabels.shift();
            hrData.shift();
            tempData.shift();
            gsrData.shift();
        }
        wearableChartInstance.update();

        // Update Wearables View live KPI cards if present
        const wearKpiHr = document.getElementById('wearKpiHeartRate');
        if (wearKpiHr && telemetry.heart_rate) {
            wearKpiHr.innerHTML = `${Math.round(telemetry.heart_rate)} <small style="font-size:13px; color:#94a3b8;">BPM</small>`;
        }
        const wearKpiTemp = document.getElementById('wearKpiTemp');
        if (wearKpiTemp && telemetry.skin_temp) {
            wearKpiTemp.innerHTML = `${Number(telemetry.skin_temp).toFixed(1)} <small style="font-size:13px; color:#94a3b8;">°C</small>`;
        }
        const wearKpiGsr = document.getElementById('wearKpiGSR');
        if (wearKpiGsr && telemetry.gsr) {
            wearKpiGsr.innerHTML = `${Number(telemetry.gsr).toFixed(2)} <small style="font-size:13px; color:#94a3b8;">µS</small>`;
        }
        const wearKpiStress = document.getElementById('wearKpiStress');
        if (wearKpiStress && telemetry.stress_level) {
            wearKpiStress.innerHTML = `${telemetry.stress_level} <small style="font-size:13px; color:#94a3b8;">/ 5</small>`;
        }
    }
}

// ====================================================================
// ML MODEL SPECS & LIMITATIONS MODAL
// ====================================================================
async function openModelModal() {
    modelModal.classList.remove('hidden');
    modalBodyContent.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Fetching model metadata...</div>';

    try {
        const resp = await fetch('/api/analytics/model-info');
        const data = await resp.json();
        if (data.status === 'success' && data.metadata) {
            renderModalContent(data.metadata);
        }
    } catch (err) {
        modalBodyContent.innerHTML = '<div class="muted-text">Failed to load model specifications.</div>';
    }
}

function renderModalContent(meta) {
    const comp = meta.model_comparison || {};
    const rows = Object.entries(comp).map(([model, metrics]) => `
        <tr>
            <td><strong>${model.replace('_', ' ')}</strong> ${model === meta.champion_model ? '<span class="badge badge-twin">Champion</span>' : ''}</td>
            <td>${metrics.rmse} mg/dL</td>
            <td>${metrics.mae} mg/dL</td>
            <td>${metrics.mape}%</td>
            <td>${metrics.r2}</td>
            <td><strong style="color:#10B981;">${metrics.clarke.clinically_acceptable_pct.toFixed(1)}%</strong></td>
        </tr>
    `).join('');

    const topFeatures = Object.entries(meta.feature_importance || {}).slice(0, 5).map(([f, imp]) => `
        <span class="mini-tag" style="padding:4px 8px; font-size:11px;">${f}: ${(imp * 100).toFixed(1)}%</span>
    `).join(' ');

    const limitationsHtml = (meta.clinical_limitations || []).map(l => `<li>${l}</li>`).join('');

    modalBodyContent.innerHTML = `
        <div style="margin-bottom:16px;">
            <h4 style="font-size:14px; font-weight:700; color:#FFF; margin-bottom:4px;">Cross-Subject Benchmark (Evaluated on Unseen Patients U009-U010)</h4>
            <p style="font-size:12px; color:#94A3B8;">Models were trained on subjects U001-U008 and tested exclusively on unseen cohorts to guarantee clinical generalization.</p>
        </div>

        <table class="metrics-summary-table">
            <thead>
                <tr>
                    <th>Model Architecture</th>
                    <th>RMSE</th>
                    <th>MAE</th>
                    <th>MAPE</th>
                    <th>R² Score</th>
                    <th>Clarke Zone A+B</th>
                </tr>
            </thead>
            <tbody>
                ${rows}
            </tbody>
        </table>

        <div style="margin: 16px 0;">
            <h4 style="font-size:13px; font-weight:700; color:#FFF; margin-bottom:8px;">Top Predictive Feature Drivers:</h4>
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
                ${topFeatures}
            </div>
        </div>

        <div style="margin-top: 18px; padding: 12px; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 8px;">
            <h4 style="font-size:13px; font-weight:700; color:#F59E0B; margin-bottom:6px;"><i class="fa-solid fa-triangle-exclamation"></i> Known Clinical & Physiological Limitations:</h4>
            <ul class="limitations-list">
                ${limitationsHtml}
            </ul>
        </div>
    `;
}

// ====================================================================
// PLATFORM VIEW NAVIGATION & INTERACTIVE VIEWS
// ====================================================================
let currentAlertsData = [];
let currentAlertFilterLevel = 'all';
let currentAlertFilterStatus = 'all';

function switchPlatformView(viewId) {
    if (!viewId) return;

    // 1. Highlight clicked navigation item
    document.querySelectorAll('.side-nav-menu .side-nav-item').forEach(item => {
        if (item.dataset.view === viewId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // 2. Hide all app views, reveal target view
    document.querySelectorAll('.app-view').forEach(view => {
        view.classList.add('hidden-view');
    });

    const targetView = document.getElementById(`view-${viewId}`);
    if (targetView) {
        targetView.classList.remove('hidden-view');
    }

    // 3. View-specific behavior & lazy loading
    if (viewId === 'overview') {
        loadOverviewDynamicMetrics();
        loadSystemHealthStats();
    } else if (viewId === 'patients') {
        renderPatientDirectoryGrid(patientSearchInput ? patientSearchInput.value : '');
    } else if (viewId === 'predictions') {
        if (cgmChartInstance) {
            setTimeout(() => {
                cgmChartInstance.resize();
            }, 50);
        }
    } else if (viewId === 'alerts') {
        loadAlertsView();
    } else if (viewId === 'wearables') {
        if (wearableChartInstance) {
            setTimeout(() => {
                wearableChartInstance.resize();
            }, 50);
        }
    } else if (viewId === 'models') {
        loadSystemHealthStats();
    }

    // Scroll container to top
    const workspaceBody = document.querySelector('.workspace-body');
    if (workspaceBody) workspaceBody.scrollTop = 0;
    const dashboardMain = document.querySelector('.dashboard-main');
    if (dashboardMain) dashboardMain.scrollTop = 0;
}
window.switchPlatformView = switchPlatformView;

// ====================================================================
// PATIENT DIRECTORY (VIEW 2)
// ====================================================================
function renderPatientDirectoryGrid(query = '', filter = 'all') {
    const container = document.getElementById('patientListContainerAlt');
    if (!container) return;

    let filtered = patientList;
    if (query.trim()) {
        const q = query.toLowerCase();
        filtered = filtered.filter(p => {
            const name = `${p.first_name} ${p.last_name}`.toLowerCase();
            const city = (p.city || '').toLowerCase();
            const conds = (p.top_conditions || []).map(c => c.display_name.toLowerCase()).join(' ');
            return name.includes(q) || city.includes(q) || conds.includes(q);
        });
    }

    if (filter === 'paired') {
        filtered = filtered.filter(p => p.paired_cgm_user_id);
    } else if (filter === 'risk') {
        filtered = filtered.filter(p => p.risk_level && p.risk_level !== 'normal');
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div style="grid-column: 1 / -1; padding:30px; text-align:center; color:#94a3b8;"><i class="fa-solid fa-user-slash"></i> No matching patients found in this cohort filter.</div>';
        return;
    }

    container.innerHTML = filtered.map(p => {
        const isSelected = p.id === currentPatientId ? 'selected' : '';
        const pairedTag = p.paired_cgm_user_id 
            ? `<span class="badge badge-twin"><i class="fa-solid fa-satellite-dish"></i> CGM: ${p.paired_cgm_user_id}</span>` 
            : '<span class="mini-tag">Unpaired</span>';
        const riskClass = p.risk_level === 'critical' ? 'critical' : (p.risk_level === 'warning' ? 'warning' : '');
        const riskBadge = p.paired_cgm_user_id ? `<span class="badge badge-risk ${riskClass}">${p.risk_level || 'normal'}</span>` : '';

        const condsPreview = (p.top_conditions || []).slice(0, 3).map(c => {
            const cleanName = c.display_name.replace(/\s*\(finding\)|\s*\(disorder\)|\s*\(situation\)/gi, '');
            return `<span class="mini-tag">${cleanName}</span>`;
        }).join('');

        return `
            <div class="patient-card ${isSelected}" style="padding:14px; background:rgba(15,23,42,0.6); border:1px solid var(--border-color); border-radius:10px; display:flex; flex-direction:column; justify-content:space-between; gap:10px;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="font-size:14px; color:#fff;">${p.first_name} ${p.last_name}</strong>
                        ${riskBadge}
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-bottom:8px; display:flex; gap:10px; align-items:center;">
                        <span><i class="fa-solid fa-venus-mars"></i> ${p.gender}, ${p.age || '--'} yrs</span>
                        <span><i class="fa-solid fa-location-dot"></i> ${p.city || 'MA'}</span>
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
                        ${condsPreview}
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; padding-top:8px; border-top:1px solid rgba(255,255,255,0.06);">
                    ${pairedTag}
                    <button class="btn btn-primary btn-sm" onclick="selectPatientAndOpen(${p.id})">
                        <i class="fa-solid fa-person-rays"></i> View Twin
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function syncPatientSearch(val) {
    if (patientSearchInput) patientSearchInput.value = val;
    const patientSearchInputAlt = document.getElementById('patientSearchInputAlt');
    if (patientSearchInputAlt && patientSearchInputAlt.value !== val) patientSearchInputAlt.value = val;
    renderPatientList(val);
    renderPatientDirectoryGrid(val);
}
window.syncPatientSearch = syncPatientSearch;

function selectPatientAndOpen(patientId) {
    selectPatient(patientId);
    switchPlatformView('predictions');
}
window.selectPatientAndOpen = selectPatientAndOpen;

// ====================================================================
// ALERTS MONITORING CENTER (VIEW 5 - IMAGE 2 MATCH)
// ====================================================================
async function loadAlertsView() {
    const tableBody = document.getElementById('alertTableBody');
    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;"><i class="fa-solid fa-circle-notch fa-spin"></i> Fetching real-time clinical alert records...</td></tr>';
    }

    try {
        const resp = await fetch('/api/alerts');
        const data = await resp.json();
        if (data.status === 'success') {
            const summary = data.summary;
            currentAlertsData = data.alerts;

            const totalEl = document.getElementById('alertStatTotal');
            if (totalEl) totalEl.textContent = summary.total_alerts;

            const pendingEl = document.getElementById('alertStatPending');
            if (pendingEl) pendingEl.textContent = summary.pending_alerts;

            const confEl = document.getElementById('alertStatConfirmed');
            if (confEl) confEl.textContent = summary.confirmed_alerts;

            const resEl = document.getElementById('alertStatResolved');
            if (resEl) resEl.textContent = summary.resolved_alerts;

            const badgeEl = document.getElementById('navAlertBadge');
            if (badgeEl) badgeEl.textContent = summary.level2_alerts;

            renderAlertsTable(currentAlertsData);
        }
    } catch (err) {
        console.error('Failed to load alerts:', err);
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:#ef4444;">Failed to load alerts from database.</td></tr>';
        }
    }
}
window.loadAlertsView = loadAlertsView;

function renderAlertsTable(alerts) {
    const tableBody = document.getElementById('alertTableBody');
    const countText = document.getElementById('alertTableCountText');
    if (!tableBody) return;

    if (countText) {
        countText.textContent = `Total ${alerts.length} records`;
    }

    if (!alerts || alerts.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;">No matching alert records found.</td></tr>';
        return;
    }

    tableBody.innerHTML = alerts.map(a => {
        const isCritical = a.alert_level.includes('Level 2') || a.alert_level.includes('Critical');
        const levelBadge = isCritical 
            ? '<span class="status-badge-pending" style="background:rgba(239,68,68,0.2);"><i class="fa-solid fa-triangle-exclamation"></i> Level 2 (Critical)</span>'
            : '<span class="status-badge-confirmed" style="background:rgba(245,158,11,0.2);"><i class="fa-solid fa-circle-exclamation"></i> Level 1 (Warning)</span>';

        const statusLower = a.status.toLowerCase();
        let statusBadge = '<span class="status-badge-pending">Pending</span>';
        if (statusLower === 'confirmed') statusBadge = '<span class="status-badge-confirmed">Confirmed</span>';
        if (statusLower === 'resolved') statusBadge = '<span class="status-badge-resolved">Resolved</span>';

        return `
            <tr id="alert-row-${a.id}">
                <td>
                    <strong style="color:#38bdf8; cursor:pointer;" onclick="selectPatientAndOpen(${a.raw_patient_id})">
                        ${a.patient_id}
                    </strong>
                    <div style="font-size:10px; color:#94a3b8;">${a.patient_name}</div>
                </td>
                <td style="font-size:11.5px; color:#cbd5e1;">${a.alert_time}</td>
                <td>
                    <div style="font-weight:600; color:#fff;">${a.alert_type}</div>
                    <div style="font-size:10.5px; color:#94a3b8;">${a.reason} (${a.glucose} mg/dL)</div>
                </td>
                <td>${levelBadge}</td>
                <td id="status-cell-${a.id}">${statusBadge}</td>
                <td>
                    <div style="display:flex; gap:6px;">
                        <button class="btn btn-outline btn-sm" onclick="handleAlertAction(${a.id}, 'Confirmed', this)" title="Confirm clinical review"><i class="fa-solid fa-check"></i></button>
                        <button class="btn btn-outline btn-sm" onclick="handleAlertAction(${a.id}, 'Resolved', this)" title="Mark resolved"><i class="fa-solid fa-circle-check" style="color:#34d399;"></i></button>
                        <button class="btn btn-primary btn-sm" onclick="selectPatientAndOpen(${a.raw_patient_id})" title="Open Patient Digital Twin"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAlerts(type, val, btn) {
    if (btn) {
        const parent = btn.parentElement;
        parent.querySelectorAll('.filter-pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    if (type === 'level') currentAlertFilterLevel = val;
    if (type === 'status') currentAlertFilterStatus = val;

    let filtered = currentAlertsData;
    if (currentAlertFilterLevel === 'level1') {
        filtered = filtered.filter(a => a.alert_level.includes('Level 1'));
    } else if (currentAlertFilterLevel === 'level2') {
        filtered = filtered.filter(a => a.alert_level.includes('Level 2'));
    }

    if (currentAlertFilterStatus !== 'all') {
        filtered = filtered.filter(a => a.status.toLowerCase() === currentAlertFilterStatus.toLowerCase());
    }

    renderAlertsTable(filtered);
}
window.filterAlerts = filterAlerts;

function handleAlertAction(alertId, newStatus, btn) {
    const statusCell = document.getElementById(`status-cell-${alertId}`);
    if (statusCell) {
        if (newStatus === 'Confirmed') {
            statusCell.innerHTML = '<span class="status-badge-confirmed">Confirmed</span>';
        } else if (newStatus === 'Resolved') {
            statusCell.innerHTML = '<span class="status-badge-resolved">Resolved</span>';
        }
    }
    // Update local data
    const item = currentAlertsData.find(a => a.id === alertId);
    if (item) item.status = newStatus;

    if (btn) {
        btn.style.transform = 'scale(1.15)';
        btn.style.borderColor = '#10b981';
        setTimeout(() => {
            btn.style.transform = '';
            btn.style.borderColor = '';
        }, 500);
    }
}
window.handleAlertAction = handleAlertAction;

// ====================================================================
// POPULATION OVERVIEW DYNAMIC METRICS
// ====================================================================
async function loadOverviewDynamicMetrics() {
    try {
        const resp = await fetch('/api/analytics/overview');
        const json = await resp.json();
        if (json.status === 'success' && json.overview) {
            const ov = json.overview;
            
            const totalEl = document.getElementById('overviewTotalPatients');
            if (totalEl) totalEl.textContent = ov.total_patients;

            const activeEl = document.getElementById('overviewActiveTwins');
            if (activeEl) activeEl.textContent = ov.active_twins;

            const meanGEl = document.getElementById('overviewMeanGlucose');
            if (meanGEl && ov.glucose_stats) {
                meanGEl.innerHTML = `${ov.glucose_stats.mean} <small style="font-size:14px; color:#94a3b8;">mg/dL</small>`;
            }

            const rangeMetaEl = document.getElementById('overviewGlucoseRangeMeta');
            if (rangeMetaEl && ov.glucose_stats) {
                rangeMetaEl.innerHTML = `<i class="fa-solid fa-bullseye"></i> Range: ${ov.glucose_stats.min} - ${ov.glucose_stats.max} mg/dL`;
            }

            // Top conditions dynamic bars
            const condsContainer = document.getElementById('overviewConditionsContainer');
            if (condsContainer && ov.top_conditions && ov.top_conditions.length > 0) {
                const maxCount = Math.max(...ov.top_conditions.map(c => c.count));
                condsContainer.innerHTML = ov.top_conditions.map((c, idx) => {
                    const cleanName = c.display_name.replace(/\s*\(finding\)|\s*\(disorder\)|\s*\(situation\)/gi, '');
                    const pct = Math.min(100, Math.round((c.count / maxCount) * 100));
                    const grad = idx === 0 ? 'linear-gradient(90deg, #0ea5e9, #0d9488)' :
                                 (idx === 1 ? 'linear-gradient(90deg, #38bdf8, #0ea5e9)' :
                                 (idx === 2 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #0ea5e9, #6366f1)'));
                    return `
                        <div>
                            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                                <span>${cleanName}</span>
                                <strong>${c.count} Encounters</strong>
                            </div>
                            <div style="height:6px; background:#1e293b; border-radius:3px; overflow:hidden;">
                                <div style="width:${pct}%; height:100%; background:${grad}; transition: width 0.6s ease;"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        }
    } catch (err) {
        console.error('Failed to load overview dynamic metrics:', err);
    }
}
window.loadOverviewDynamicMetrics = loadOverviewDynamicMetrics;

// ====================================================================
// INTERACTIVE DYNAMIC ML PREDICTOR FROM DATASETS
// ====================================================================
let currentDatasetRow = 715;
let currentDatasetScenario = 'postprandial_spike';
let currentDatasetResult = null;

function openDatasetPredictorStudio() {
    switchPlatformView('predictions');
    setTimeout(() => {
        const studioEl = document.getElementById('datasetPredictorStudio');
        if (studioEl) {
            studioEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            studioEl.style.transition = 'box-shadow 0.4s ease';
            studioEl.style.boxShadow = '0 0 32px rgba(14, 165, 233, 0.4)';
            setTimeout(() => {
                studioEl.style.boxShadow = '';
            }, 1500);
        }
    }, 120);
}
window.openDatasetPredictorStudio = openDatasetPredictorStudio;

async function initDatasetPredictorStudio() {
    fetchDatasetPrediction({ scenario: 'postprandial_spike' });
}
window.initDatasetPredictorStudio = initDatasetPredictorStudio;

function loadDatasetScenario(scenarioId, btn) {
    currentDatasetScenario = scenarioId;
    document.querySelectorAll('.dataset-preset-chips .btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    fetchDatasetPrediction({ scenario: scenarioId });
}
window.loadDatasetScenario = loadDatasetScenario;

function loadDatasetRowFromInput() {
    const input = document.getElementById('datasetRowInput');
    const rowId = parseInt(input?.value || '715');
    if (isNaN(rowId) || rowId < 1 || rowId > 15731) {
        alert('Please enter a valid row index between 1 and 15,731.');
        return;
    }
    document.querySelectorAll('.dataset-preset-chips .btn').forEach(b => b.classList.remove('active'));
    fetchDatasetPrediction({ row_id: rowId });
}
window.loadDatasetRowFromInput = loadDatasetRowFromInput;

async function fetchDatasetPrediction(options = {}) {
    const runBtn = document.getElementById('btnExecuteDatasetPrediction');
    if (runBtn) {
        runBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Ingesting Dataset...';
        runBtn.disabled = true;
    }

    try {
        const payload = {
            patient_id: currentPatientId || 1,
            ...options
        };

        const resp = await fetch('/api/ml/predict-from-dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const json = await resp.json();
        if (json.status === 'success') {
            currentDatasetResult = json;
            currentDatasetRow = json.provenance.row_id;
            renderDatasetPredictionResult(json);
        } else {
            console.error('Dataset prediction error:', json.message);
        }
    } catch (err) {
        console.error('Failed to run dataset prediction:', err);
    } finally {
        if (runBtn) {
            runBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Run Model Prediction';
            runBtn.disabled = false;
        }
    }
}
window.fetchDatasetPrediction = fetchDatasetPrediction;

function renderDatasetPredictionResult(data) {
    const prov = data.provenance;
    const pred = data.prediction;
    const gt = data.ground_truth;
    const risk = pred.risk_assessment;

    // 1. Update provenance text & row input
    const provEl = document.getElementById('datasetRowProvenanceText');
    if (provEl) {
        provEl.innerHTML = `<i class="fa-solid fa-database"></i> Ingested: <strong>${prov.dataset_source}</strong> (Row ${prov.row_id} / ${prov.cgm_user_id}, ${prov.recorded_at})`;
    }
    const input = document.getElementById('datasetRowInput');
    if (input) input.value = prov.row_id;

    // 2. Render 19 Features Grid
    const grid = document.getElementById('datasetFeaturesGrid');
    if (grid && data.features) {
        grid.innerHTML = data.features.map(f => {
            const isGlucose = f.key.includes('glucose');
            const isWearable = f.source.includes('Empatica');
            const badgeBg = isGlucose ? 'rgba(14, 165, 233, 0.15)' : (isWearable ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)');
            const badgeColor = isGlucose ? '#38bdf8' : (isWearable ? '#34d399' : '#fbbf24');
            const numVal = typeof f.value === 'number' ? (f.value % 1 === 0 ? f.value : f.value.toFixed(1)) : f.value;

            return `
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 7px 9px;">
                    <div style="font-size: 10px; color: #94a3b8; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${f.name}">
                        ${f.name}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <strong style="font-size: 13px; color: #fff;">${numVal} <small style="font-size: 10px; color: #94a3b8;">${f.unit}</small></strong>
                        <span style="font-size: 8.5px; background: ${badgeBg}; color: ${badgeColor}; padding: 1px 4px; border-radius: 3px;">
                            ${isGlucose ? 'CGM' : (isWearable ? 'E4' : 'EHR')}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 3. Update Hero Predicted vs Ground Truth
    const predValEl = document.getElementById('datasetPredValue');
    if (predValEl) {
        predValEl.innerHTML = `${pred.predicted_glucose_30m.toFixed(1)} <small style="font-size: 12px; color: #94a3b8;">mg/dL</small>`;
    }
    const ciEl = document.getElementById('datasetConfidenceBandText');
    if (ciEl) {
        ciEl.textContent = `95% CI: [${pred.confidence_interval_95.lower} - ${pred.confidence_interval_95.upper}]`;
    }

    const gtValEl = document.getElementById('datasetGroundTruthValue');
    if (gtValEl) {
        gtValEl.innerHTML = `${gt.actual_future_glucose_30m.toFixed(1)} <small style="font-size: 12px; color: #94a3b8;">mg/dL</small>`;
    }

    const resEl = document.getElementById('datasetResidualErrorText');
    if (resEl) {
        resEl.innerHTML = `Residual Error: <strong style="color:${gt.residual_error <= 5 ? '#34d399' : '#fbbf24'};">${gt.residual_error} mg/dL (${gt.percent_error}%)</strong>`;
    }

    const clarkeBadge = document.getElementById('datasetClarkeBadge');
    if (clarkeBadge) {
        clarkeBadge.textContent = gt.clarke_zone;
        clarkeBadge.title = gt.clarke_description;
    }

    const latencyEl = document.getElementById('datasetLatencyText');
    if (latencyEl) {
        latencyEl.textContent = `${data.inference_metrics.latency_ms} ms`;
    }

    // 4. Clinical Alert Box
    const headline = document.getElementById('datasetAlertHeadline');
    if (headline) headline.textContent = risk.alert_message.split('Alert')[0] + ' Alert';
    const codeBadge = document.getElementById('datasetAlertCodeBadge');
    if (codeBadge) codeBadge.textContent = risk.alert_code;
    const msgEl = document.getElementById('datasetAlertMessage');
    if (msgEl) msgEl.textContent = risk.alert_message;
    const recEl = document.getElementById('datasetAlertRecommendation');
    if (recEl) {
        recEl.innerHTML = `<i class="fa-solid fa-hand-holding-medical"></i> <strong>Protocol:</strong> ${risk.clinical_recommendation}`;
    }

    const box = document.getElementById('datasetRiskAlertBox');
    if (box) {
        if (risk.risk_level === 'Critical') {
            box.style.background = 'rgba(239, 68, 68, 0.12)';
            box.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        } else if (risk.risk_level === 'Warning') {
            box.style.background = 'rgba(245, 158, 11, 0.12)';
            box.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        } else {
            box.style.background = 'rgba(16, 185, 129, 0.12)';
            box.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        }
    }
}

function runDatasetPrediction(applyOverrides = false) {
    const overrides = {};
    if (applyOverrides) {
        const carbs = parseInt(document.getElementById('overrideCarbs')?.value || '');
        if (!isNaN(carbs)) overrides.carbs = carbs;

        const bolus = parseFloat(document.getElementById('overrideBolus')?.value || '');
        if (!isNaN(bolus)) overrides.insulin_bolus = bolus;

        const hr = parseFloat(document.getElementById('overrideHR')?.value || '');
        if (!isNaN(hr)) overrides.heart_rate = hr;
    }

    fetchDatasetPrediction({
        row_id: currentDatasetRow,
        overrides: Object.keys(overrides).length > 0 ? overrides : undefined
    });
}
window.runDatasetPrediction = runDatasetPrediction;

function resetDatasetOverrides() {
    const c = document.getElementById('overrideCarbs');
    if (c) c.value = '';
    const b = document.getElementById('overrideBolus');
    if (b) b.value = '';
    const h = document.getElementById('overrideHR');
    if (h) h.value = '';
    runDatasetPrediction(false);
}
window.resetDatasetOverrides = resetDatasetOverrides;

async function loadSystemHealthStats() {
    try {
        const resp = await fetch('/api/analytics/system-health');
        const data = await resp.json();
        if (data.status === 'success' && data.system_health) {
            // Updated stats
        }
    } catch (err) {
        console.warn('System health load note:', err);
    }
}

// ---------------------------------------------------------------------
// Presentation Navigation & Interactive Sidebar Handlers
// ---------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // 1. Sidebar link view switcher
    const sideLinks = document.querySelectorAll('.side-nav-menu .side-nav-item');
    sideLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const view = this.getAttribute('data-view');
            if (view) {
                e.preventDefault();
                switchPlatformView(view);
            }
        });
    });

    // 2. Patient Directory filter tabs
    document.querySelectorAll('#view-patients .patient-filter-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#view-patients .patient-filter-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const searchVal = document.getElementById('patientSearchInputAlt')?.value || '';
            renderPatientDirectoryGrid(searchVal, btn.dataset.filter);
        });
    });

    // 3. Settings Save Thresholds Button
    const btnSaveThresholds = document.getElementById('btnSaveThresholds');
    if (btnSaveThresholds) {
        btnSaveThresholds.addEventListener('click', () => {
            const notice = document.getElementById('settingsSaveNotice');
            if (notice) {
                notice.style.display = 'block';
                setTimeout(() => {
                    notice.style.display = 'none';
                }, 3000);
            }
        });
    }

    // 4. Settings Speed Multiplier Buttons
    document.querySelectorAll('#speedMultiplierGroup .btn-speed').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#speedMultiplierGroup .btn-speed').forEach(b => {
                b.classList.remove('active');
                b.classList.add('btn-outline');
                b.classList.remove('btn-primary');
            });
            btn.classList.add('active');
            btn.classList.remove('btn-outline');
            btn.classList.add('btn-primary');
            
            const speed = parseInt(btn.dataset.speed || '1');
            if (isAutoStreaming) {
                clearInterval(autoStreamInterval);
                const intervalMs = Math.max(250, Math.round(1500 / speed));
                autoStreamInterval = setInterval(() => requestStreamTick(true), intervalMs);
            }
        });
    });

    // 5. Alert Bell Button switches to Alerts View
    const btnBellAlert = document.getElementById('btnBellAlert');
    if (btnBellAlert) {
        btnBellAlert.addEventListener('click', () => {
            switchPlatformView('alerts');
        });
    }

    // 6. Cohort Filter Select in Top Nav
    const topCohortSelect = document.getElementById('topCohortSelect');
    if (topCohortSelect) {
        topCohortSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            const tabBtn = document.querySelector(`.patient-filter-tabs .tab-btn[data-filter="${val}"]`) ||
                           document.querySelector(`.patient-filter-tabs .tab-btn[data-filter="all"]`);
            if (tabBtn) tabBtn.click();
        });
    }
});
