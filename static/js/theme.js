// Theme handling
function initTheme() {
    const theme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
    
    // Update chart colors if exists
    if (window.priceChart) {
        const gridColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--chart-grid').trim();
        const textColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--text-primary').trim();
        
        window.priceChart.options.scales.y.grid.color = gridColor;
        window.priceChart.options.scales.x.grid.color = gridColor;
        window.priceChart.options.scales.y.ticks.color = textColor;
        window.priceChart.options.scales.x.ticks.color = textColor;
        window.priceChart.update();
    }
}

function updateThemeIcon(theme) {
    const moonIcon = document.getElementById('moon-icon');
    const sunIcon = document.getElementById('sun-icon');
    
    if (theme === 'dark') {
        moonIcon.classList.add('hidden');
        sunIcon.classList.remove('hidden');
    } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', initTheme);
