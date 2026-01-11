function renderDetails(data) {
    let html = '';
    const createRow = (key, value) => {
        const displayKey = String(key).replace(/_/g, ' ');
        const displayValue = (value === null || value === '' || value === 'not set' || value === 'N/A') ? '-' : value;
        return `
                    <div class="flex justify-between py-1 border-b border-gray-700 last:border-b-0">
                        <span class="font-semibold text-gray-400 capitalize">${displayKey}:</span>
                        <span class="text-white font-mono">${displayValue}</span>
                    </div>
                `;
    };

    html += '<h3 class="text-xl font-bold text-pz-green mt-6 mb-3">SERVER DETAILS</h3>';
    html += '<div class="bg-gray-700/50 p-4 rounded-lg">';

    for (const key in data) {
        const value = data[key];
        if (key.toLowerCase() === 'status') {
            continue;
        }
        if (typeof value === 'string' || typeof value === 'number') {
            html += createRow(key, value);
        }
    }

    html += '</div>';

    if (html.length < 100) {
        html = `<p class="text-gray-500 text-center py-10">No detailed data received from API or data structure is unexpected.</p>`;
    }
    return html;
}

async function fetchDetails() {
    const detailsOutput = document.getElementById('details-output');
    const initialLoadMessage = document.getElementById('initial-load-message');

    if (initialLoadMessage) {
        initialLoadMessage.classList.add('hidden');
    }

    if (detailsOutput) {
        detailsOutput.innerHTML = '<p class="text-gray-500 text-center py-10"><i data-lucide="rotate-cw" class="w-5 h-5 inline-block mr-2 animate-spin"></i> Refreshing data...</p>';
    }
    updateStatusBadge('LOADING');

    try {
        const data = await apiCall('/details');

        if (data.status === 'success') {
            const serverStatus = data.server_status || 'UNKNOWN';
            updateStatusBadge(serverStatus);
            if (detailsOutput) detailsOutput.innerHTML = renderDetails(data.details);
        } else {
            updateStatusBadge('ERROR');
            if (detailsOutput) detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">API ERROR</h3><pre class="whitespace-pre-wrap text-red-400 bg-gray-900 p-4 rounded-lg">${data.message || 'Unknown error occurred.'}</pre>`;
            showMessage(`Failed to fetch details: ${data.message}`, 'error');
        }

    } catch (error) {
        console.error("Fetch/Render Error:", error);
        updateStatusBadge('FATAL_ERROR');
        if (detailsOutput) detailsOutput.innerHTML = `<p class="text-red-500 text-center py-10">Fatal network error. Check API connection. Error: ${error.message}</p>`;
        showMessage('Fatal Network/API error.', 'error');
    }

    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
}

async function controlServer(action) {
    const loadingIndicator = document.getElementById('loading-indicator');
    const messagePanel = document.getElementById('message-panel');
    const detailsOutput = document.getElementById('details-output');

    document.querySelectorAll('button').forEach(btn => btn.disabled = true);
    if (loadingIndicator) loadingIndicator.classList.remove('hidden');
    if (messagePanel) messagePanel.classList.add('hidden');

    const actionText = action.toUpperCase();
    updateStatusBadge(actionText + 'ING');

    try {
        const data = await apiCall('/control', 'POST', { action: action });

        if (data.status === 'success') {
            showMessage(`${actionText} command sent successfully.`, 'success');
            if (detailsOutput) detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-pz-green mb-3">${actionText} COMMAND OUTPUT</h3><pre class="whitespace-pre-wrap text-gray-300 bg-gray-900 p-4 rounded-lg">${data.details || 'No output details provided.'}</pre>`;
        } else {
            showMessage(`${actionText} failed: ${data.message}.`, 'error');
            if (detailsOutput) detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">${actionText} FAILED}</h3><pre class="whitespace-pre-wrap text-red-400 bg-gray-900 p-4 rounded-lg">${data.details || 'No output details provided.'}</pre>`;
        }

    } catch (error) {
        console.error("Control Command Error:", error);
        showMessage(`Network error during ${actionText}: ${error.message}`, 'error');
        if (detailsOutput) detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">${actionText} ERROR</h3><p class="text-red-400">Network connection failed.</p>`;
    } finally {
        document.querySelectorAll('button').forEach(btn => btn.disabled = false);
        if (loadingIndicator) loadingIndicator.classList.add('hidden');
        await fetchDetails();
    }
}

async function confirmReset(type) {
    const actionName = type === 'soft' ? 'SOFT RESET (Wipe Zombies)' : 'HARD RESET (WIPE WORLD)';
    const confirmMsg = `Are you sure you want to perform a ${actionName}?\n\nThis cannot be undone! Ensure you have a backup.`;

    if (!confirm(confirmMsg)) return;

    // Double confirmation for Hard Reset
    if (type === 'hard') {
        const doubleCheck = prompt("Type 'DELETE' to confirm wiping the entire world save:");
        if (doubleCheck !== 'DELETE') {
            alert("Action cancelled.");
            return;
        }
    }

    const btn = document.getElementById(`${type}-reset-btn`);
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Processing...';
    if (window.lucide) lucide.createIcons();

    try {
        const data = await apiCall('/reset', 'POST', { type: type });

        if (data.status === 'success') {
            showMessage(`${actionName} Successful! You can start the server now.`, 'success');
        } else {
            showMessage(`Reset Failed: ${data.message}`, 'error');
        }

    } catch (error) {
        showMessage(`Network Error: ${error.message}`, 'error');
    } finally {
        btn.innerHTML = originalText;
        if (window.lucide) lucide.createIcons();
        fetchDetails();
    }
}

function initializeDashboard() {
    fetchDetails();
    // Expose functions globally for onclick events
    window.fetchDetails = fetchDetails;
    window.controlServer = controlServer;
    window.confirmReset = confirmReset;
}
