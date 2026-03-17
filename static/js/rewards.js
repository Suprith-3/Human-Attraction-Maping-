const BADGES = [
    { id: 'focus_starter',   icon: '🌱', name: 'Focus Starter', desc: 'Complete your first session', unlocked: true },
    { id: 'deep_work_master', icon: '🎓', name: 'Deep Work Master', desc: '60 min uninterrupted focus', unlocked: false },
    { id: 'flow_achiever',   icon: '🌊', name: 'Flow State Achiever', desc: '45 min with zero tab shifts', unlocked: false },
    { id: 'switch_slayer',   icon: '⚔️', name: 'Context Switch Slayer', desc: '1 hour with adaptive blocking', unlocked: false }
];

async function initRewards() {
    try {
        const res = await fetch('/api/rewards');
        const data = await res.json();
        
        const elWallet = document.getElementById('wallet-coins');
        if (elWallet) elWallet.textContent = data.coins;
        const elStreak = document.getElementById('streak-display');
        if (elStreak) elStreak.textContent = `🔥 Streak: ${data.streak} Days`;

        // Update badge UI
        const container = document.getElementById('badge-container');
        if(container) {
            container.innerHTML = '';
            BADGES.forEach(b => {
                const isUnlocked = data.badges.includes(b.id) || b.unlocked; // using mock condition for UI
                const div = document.createElement('div');
                div.className = `badge-item ${isUnlocked ? 'unlocked' : ''}`;
                div.innerHTML = `
                    <span class="icon">${b.icon}</span>
                    <h4>${b.name}</h4>
                    <p>${b.desc}</p>
                `;
                container.appendChild(div);
            });
        }
    } catch(e) {}
}

function unlockTheme(themeName, cost) {
    const elWallet = document.getElementById('wallet-coins');
    if(!elWallet) return;
    const currentCoins = parseInt(elWallet.textContent);
    const unlockedThemes = JSON.parse(localStorage.getItem('focusos_unlocked_themes') || '[]');

    if (unlockedThemes.includes(themeName)) {
        applyTheme(themeName);
        return;
    }

    if (currentCoins >= cost) {
        if(confirm(`Unlock ${themeName} theme for ${cost} coins?`)) {
            unlockedThemes.push(themeName);
            localStorage.setItem('focusos_unlocked_themes', JSON.stringify(unlockedThemes));
            
            // Deduct mock
            elWallet.textContent = currentCoins - cost;
            // Server should sync this but we'll do local for now
            applyTheme(themeName);
            alert('Theme unlocked and applied!');
        }
    } else {
        alert('Not enough coins!');
    }
}

function applyTheme(themeName) {
    document.body.className = `theme-${themeName}`;
}

// Check saved theme
const savedThemes = JSON.parse(localStorage.getItem('focusos_unlocked_themes') || '[]');
if (savedThemes.length > 0) {
    applyTheme(savedThemes[savedThemes.length - 1]);
}

setTimeout(initRewards, 1000);
