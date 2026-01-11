function showMessage(text, type = 'info') {
    const panel = document.getElementById('message-panel');
    if (!panel) return;

    panel.textContent = text;
    panel.classList.remove('hidden', 'bg-red-900/50', 'bg-green-900/50', 'text-red-300', 'text-green-300', 'bg-blue-900/50', 'text-blue-300');

    if (type === 'error') {
        panel.classList.add('bg-red-900/50', 'text-red-300');
    } else if (type === 'success') {
        panel.classList.add('bg-green-900/50', 'text-green-300');
    } else {
        panel.classList.add('bg-blue-900/50', 'text-blue-300');
    }

    // Hide the message after 5 seconds
    setTimeout(() => {
        panel.classList.add('hidden');
    }, 5000);
}

function updateStatusBadge(status) {
    const statusText = document.getElementById('status-text');
    const serverStatusBadge = document.getElementById('server-status');
    const iconContainer = document.getElementById('status-icon');

    if (!statusText || !serverStatusBadge) return;

    status = String(status).toUpperCase().trim();

    let displayStatus = 'LOADING';
    let colorClass = 'bg-gray-500 text-gray-900';
    let iconName = 'help-circle';
    let iconClass = 'w-4 h-4 mr-1';

    // Logic for Danger Zone buttons (only on Dashboard)
    const softBtn = document.getElementById('soft-reset-btn');
    const hardBtn = document.getElementById('hard-reset-btn');
    const isStopped = (status === 'STOPPED' || status.includes('NOT'));

    if (softBtn && hardBtn) {
        softBtn.disabled = !isStopped;
        hardBtn.disabled = !isStopped;
    }

    if (status === 'STARTED' || status === 'RUNNING') {
        displayStatus = 'ON';
        colorClass = 'bg-green-600 text-white';
        iconName = 'circle-dot';
    } else if (status === 'STOPPED' || status.includes('NOT')) {
        displayStatus = 'OFF';
        colorClass = 'bg-red-600 text-white';
        iconName = 'circle';
    } else if (status.includes('ING')) {
        displayStatus = status;
        colorClass = 'bg-yellow-600 text-gray-900';
        iconName = 'loader-2';
        iconClass += ' animate-spin';
    } else if (status.includes('ERROR') || status.includes('FATAL')) {
        displayStatus = 'ERROR';
        colorClass = 'bg-red-600 text-white';
        iconName = 'alert-triangle';
    } else {
        displayStatus = 'UNKNOWN';
        colorClass = 'bg-gray-500 text-gray-900';
        iconName = 'help-circle';
    }

    statusText.textContent = displayStatus;
    serverStatusBadge.className = `px-4 py-2 rounded-full text-sm font-semibold transition-colors duration-300 shadow-md ${colorClass}`;

    if (iconContainer) {
        iconContainer.innerHTML = '';
        if (window.lucide && typeof lucide.createIcons === 'function') {
            const icons = lucide.createIcons();
            if (icons && icons[iconName]) {
                const iconHtml = icons[iconName].toSvg({ class: iconClass });
                iconContainer.innerHTML = iconHtml;
            }
        }
    }
}
