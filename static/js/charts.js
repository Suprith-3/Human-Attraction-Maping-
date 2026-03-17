const chartOptions = { 
    animation: { duration: 500 }, 
    responsive: true,
    scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#aaa' } } }
};

let keystrokeChart, clickBarChart, tabShiftLineChart, actionAreaChart, mousePathChart;

setTimeout(() => {
    const kbCtx = document.getElementById('keystrokeChart');
    if (!kbCtx) return;
    
    keystrokeChart = new Chart(kbCtx.getContext('2d'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Keystrokes/min', data: [], borderColor: '#00ff88', tension: 0.4, fill: false }] },
        options: chartOptions
    });

    clickBarChart = new Chart(document.getElementById('clickBarChart').getContext('2d'), {
        type: 'bar',
        data: { labels: [], datasets: [{ label: 'Clicks/min', data: [], backgroundColor: '#0080ff' }] },
        options: chartOptions
    });

    tabShiftLineChart = new Chart(document.getElementById('tabShiftLineChart').getContext('2d'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Tab Shifts/min', data: [], borderColor: '#ff4444', tension: 0.4, fill: false }] },
        options: chartOptions
    });

    actionAreaChart = new Chart(document.getElementById('actionAreaChart').getContext('2d'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Actions/min', data: [], borderColor: '#ff6b35', backgroundColor: 'rgba(255,107,53,0.2)', tension: 0.4, fill: true }] },
        options: chartOptions
    });

    mousePathChart = new Chart(document.getElementById('mousePathChart').getContext('2d'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Mouse Distance (cm)', data: [], borderColor: '#00cfff', tension: 0.4, fill: false }] },
        options: chartOptions
    });
}, 500);

setInterval(async () => {
    if(!navigator.onLine || !keystrokeChart) return;
    try {
        const res = await fetch('/api/stats/realtime');
        const data = await res.json();
        
        keystrokeChart.data.labels = data.labels;
        keystrokeChart.data.datasets[0].data = data.keystrokes;
        keystrokeChart.update();

        clickBarChart.data.labels = data.labels;
        clickBarChart.data.datasets[0].data = data.clicks;
        clickBarChart.update();

        tabShiftLineChart.data.labels = data.labels;
        tabShiftLineChart.data.datasets[0].data = data.tab_shifts;
        tabShiftLineChart.update();

        actionAreaChart.data.labels = data.labels;
        actionAreaChart.data.datasets[0].data = data.actions;
        actionAreaChart.update();

        mousePathChart.data.labels = data.labels;
        mousePathChart.data.datasets[0].data = data.mouse_cm;
        mousePathChart.update();
    } catch(e) {}
}, 5000);
