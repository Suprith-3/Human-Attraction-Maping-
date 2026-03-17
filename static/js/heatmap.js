// Heatmap Canvas
async function refreshHeatmap() {
    const canvas = document.getElementById('heatmapCanvas');
    if(!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    try {
        const res = await fetch('/api/stats/heatmap');
        const data = await res.json();
        data.forEach(p => {
            // scale down if canvas is smaller
            const x = (p.x / window.innerWidth) * canvas.width;
            const y = (p.y / window.innerHeight) * canvas.height;
            const grad = ctx.createRadialGradient(x, y, 0, x, y, 30);
            grad.addColorStop(0, 'rgba(255,0,0,0.4)');
            grad.addColorStop(1, 'rgba(255,0,0,0)');
            ctx.fillStyle = grad;
            ctx.fillRect(x-30, y-30, 60, 60);
        });
    } catch(e) {}
}

let intensityChart;
let distributionChart;

async function initAnalytics() {
    if(!navigator.onLine) return;
    try {
        // Intensity Bars
        const resInt = await fetch('/api/stats/intensity');
        const dataInt = await resInt.json();
        const intensityCanvas = document.getElementById('intensityCanvas');
        if(intensityChart) intensityChart.destroy();
        intensityChart = new Chart(intensityCanvas.getContext('2d'), {
            type: 'bar',
            data: { 
                labels: dataInt.hours.map(h => `${h}:00`), 
                datasets: [{ 
                    label: 'Activity', 
                    data: dataInt.intensity, 
                    backgroundColor: dataInt.intensity.map(v => `hsl(${120 - (v/1000)*120}, 100%, 50%)`) 
                }] 
            },
            options: { responsive: true }
        });

        // Distribution
        const resDist = await fetch('/api/stats/distribution');
        const dataDist = await resDist.json();
        const distributionCanvas = document.getElementById('distributionCanvas');
        if(distributionChart) distributionChart.destroy();
        distributionChart = new Chart(distributionCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Keyboard %', 'Mouse %', 'Idle %', 'Tab Shift %'],
                datasets: [{
                    data: [dataDist.keyboard, dataDist.mouse, dataDist.idle, dataDist.tab],
                    backgroundColor: ['#00ff88', '#0080ff', '#888899', '#ff4444']
                }]
            },
            options: { responsive: true, cutout: '70%', color: '#fff' }
        });

        // Flow SVG
        const resFlow = await fetch('/api/stats/flow');
        const flowData = await resFlow.json();
        renderFlowSVG(flowData);

        refreshHeatmap();
    } catch(e){}
}

function renderFlowSVG(data) {
    const svg = document.getElementById('flowSvg');
    if(!svg) return;
    svg.innerHTML = `
        <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#00ff88" />
            </marker>
        </defs>

        <circle cx="50" cy="150" r="20" fill="#2a2a3e" />
        <text x="50" y="150" fill="#fff" text-anchor="middle" dy="5" font-size="10">Start</text>

        <circle cx="200" cy="100" r="30" fill="#00ff88" />
        <text x="200" y="100" fill="#000" text-anchor="middle" dy="5" font-weight="bold">Deep Focus</text>
        
        <circle cx="200" cy="200" r="25" fill="#ff4444" />
        <text x="200" y="200" fill="#fff" text-anchor="middle" dy="5" font-size="10">Tab Switch</text>

        <path d="M 70 140 Q 130 100 170 100" stroke="#00ff88" stroke-width="${Math.max(1, data.start_deep)}" fill="none" marker-end="url(#arrow)" />
        <path d="M 200 130 L 200 175" stroke="#ff4444" stroke-width="${Math.max(1, data.deep_tab)}" fill="none" marker-end="url(#arrow)" />
    `;
}

// Ensure charts init once on load
setTimeout(initAnalytics, 1000);
