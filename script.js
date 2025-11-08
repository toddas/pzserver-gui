// =====================================================================
// Configuration and Setup
// =====================================================================

const BASE_URL = ''; // Base URL for API calls.

// --- DOM Element References ---
const detailsOutput = document.getElementById('details-output');
const statusText = document.getElementById('status-text');
const serverStatusBadge = document.getElementById('server-status');
const messagePanel = document.getElementById('message-panel');
const loadingIndicator = document.getElementById('loading-indicator');
const initialLoadMessage = document.getElementById('initial-load-message');
const ALL_BUTTONS = document.querySelectorAll('button'); 


// =====================================================================
// Utility and DOM Management Functions
// =====================================================================

/**
 * Converts the structured JSON details data from the API into readable HTML.
 * @param {object} data - The server details object.
 * @returns {string} HTML string of the rendered details.
 */
function renderDetails(data) {
    let html = '';
    
    // Helper function to create a clean key-value row
    const createRow = (key, value) => {
        const displayKey = key.replace(/_/g, ' ');
        // Check for null/empty/placeholder values
        const displayValue = (value === null || value === '' || value === 'not set' || value === 'N/A') ? '-' : value;

        return `
            <div class="flex justify-between py-1 border-b border-gray-700 last:border-b-0">
                <span class="font-semibold text-gray-400 capitalize">${displayKey}:</span>
                <span class="text-white font-mono">${displayValue}</span>
            </div>
        `;
    };

    for (const sectionKey in data) {
        const sectionData = data[sectionKey];
        const cleanTitle = sectionKey.replace(/_/g, ' ').toUpperCase();

        // 1. Ports Array (Table format)
        if (sectionKey === 'ports' && Array.isArray(sectionData) && sectionData.length > 0) {
            html += `<h3 class="text-xl font-bold text-pz-green mt-6 mb-3">${cleanTitle}</h3>`;
            html += `
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-700">
                        <thead>
                            <tr>
                                <th class="px-2 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">DESCRIPTION</th>
                                <th class="px-2 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">PORT</th>
                                <th class="px-2 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">PROTOCOL</th>
                                <th class="px-2 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">LISTEN</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-800">
            `;
            sectionData.forEach(port => {
                html += `
                    <tr>
                        <td class="px-2 py-2 whitespace-nowrap text-sm text-gray-300">${port.description}</td>
                        <td class="px-2 py-2 whitespace-nowrap text-sm text-yellow-500 font-mono">${port.port}</td>
                        <td class="px-2 py-2 whitespace-nowrap text-sm text-gray-300">${port.protocol}</td>
                        <td class="px-2 py-2 whitespace-nowrap text-sm text-green-500">${port.listen}</td>
                    </tr>
                `;
            });
            html += `</tbody></table></div>`;

        // 2. Nested Object sections
        } else if (typeof sectionData === 'object' && sectionData !== null && !Array.isArray(sectionData)) {
            
            if (sectionKey === 'status') {
                html += `<h3 class="text-xl font-bold text-pz-green mt-6 mb-3">${cleanTitle} (LinuxGSM)</h3>`;
                html += `<div class="bg-gray-700/50 p-4 rounded-lg">`;
                for (const key in sectionData) {
                    if (key !== 'status') {
                        html += createRow(key, sectionData[key]);
                    }
                }
                html += `</div>`;
                continue;
            }

            const isNested = Object.values(sectionData).some(val => typeof val === 'object' && val !== null && !Array.isArray(val));

            html += `<h3 class="text-xl font-bold text-pz-green mt-6 mb-3">${cleanTitle}</h3>`;
            
            if (isNested) {
                for (const subSectionKey in sectionData) {
                    const subSectionData = sectionData[subSectionKey];
                    if (typeof subSectionData === 'object' && subSectionData !== null && !Array.isArray(subSectionData)) {
                        html += `<h4 class="text-lg font-semibold text-gray-300 mt-4 mb-2 ml-2">${subSectionKey.replace(/_/g, ' ').toUpperCase()}</h4>`;
                        html += `<div class="bg-gray-700/50 p-3 rounded-lg ml-4">`;
                        for (const key in subSectionData) {
                            html += createRow(key, subSectionData[key]);
                        }
                        html += `</div>`;
                    }
                }
            } else {
                html += `<div class="bg-gray-700/50 p-4 rounded-lg">`;
                for (const key in sectionData) {
                    html += createRow(key, sectionData[key]);
                }
                html += `</div>`;
            }
        }
    }
    if (!html) {
         html = `<p class="text-gray-500 text-center py-10">No detailed data received from API or data structure is unexpected.</p>`;
    }
    return html;
}

/**
 * Updates the main status badge style, icon, and text based on the server state.
 * @param {string} status - The raw status string (e.g., 'Started', 'Stopping', 'Unknown').
 */
function updateStatusBadge(status) {
    status = String(status).toUpperCase().trim();
    
    let displayStatus = 'LOADING';
    let colorClass = 'bg-gray-500 text-gray-900';
    let iconName = 'help-circle';
    let iconClass = 'w-4 h-4 mr-1';

    if (status === 'STARTED' || status === 'RUNNING' || status === 'ON') {
        displayStatus = 'ON';
        colorClass = 'bg-green-600 text-white';
        iconName = 'circle-dot';
    } else if (status === 'STOPPED' || status.includes('NOT')) {
        displayStatus = 'OFF';
        colorClass = 'bg-red-600 text-white';
        iconName = 'circle';
    } else if (status.includes('ING')) { // STARTING, STOPPING, RESTARTING
        displayStatus = status; 
        colorClass = 'bg-yellow-500 text-gray-900';
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
    
    // Render icon using Lucide dynamically
    const iconContainer = document.getElementById('status-icon');
    iconContainer.innerHTML = '';
    if (window.lucide && lucide.createIcons()[iconName]) {
        const iconHtml = lucide.createIcons()[iconName].toSvg({ class: iconClass });
        iconContainer.innerHTML = iconHtml;
    }
}

/**
 * Shows a transient message (success or error) in the dedicated panel.
 * @param {string} message - The text to display.
 * @param {('success'|'error')} type - The type of message to determine color.
 */
function showMessage(message, type) {
    messagePanel.textContent = message;
    
    // Reset and apply new classes
    messagePanel.classList.remove('hidden', 'bg-red-900/50', 'text-red-300', 'bg-green-900/50', 'text-green-300');
    
    if (type === 'success') {
        messagePanel.classList.add('bg-green-900/50', 'text-green-300');
    } else if (type === 'error') {
        messagePanel.classList.add('bg-red-900/50', 'text-red-300');
    }
    messagePanel.classList.remove('hidden');
    
    // Hide the message after 5 seconds
    setTimeout(() => {
        messagePanel.classList.add('hidden');
    }, 5000);
}


// =====================================================================
// API Interaction Functions (using native fetch)
// =====================================================================

/**
 * Fetches and displays the server details from the API.
 */
async function fetchDetails() {
    if (initialLoadMessage) {
        initialLoadMessage.classList.add('hidden');
    }
    
    detailsOutput.innerHTML = '<p class="text-gray-500 text-center py-10"><i data-lucide="rotate-cw" class="w-5 h-5 inline-block mr-2 animate-spin"></i> Refreshing data...</p>';
    updateStatusBadge('LOADING');

    try {
        const response = await fetch(`${BASE_URL}/api/details`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json(); 

        if (data.status === 'success') {
            const serverStatus = data.server_status || 'UNKNOWN'; 
            
            updateStatusBadge(serverStatus);
            detailsOutput.innerHTML = renderDetails(data.details);
            
        } else {
            updateStatusBadge('ERROR');
            detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">API ERROR</h3><pre class="whitespace-pre-wrap text-red-400 bg-gray-900 p-4 rounded-lg">${data.message || 'Unknown error occurred.'}</pre>`;
            showMessage(`Failed to fetch details: ${data.message}`, 'error');
        }

    } catch (error) {
        console.error("Fetch/Render Error:", error);
        updateStatusBadge('FATAL_ERROR');
        detailsOutput.innerHTML = `<p class="text-red-500 text-center py-10">Fatal network error. Check API connection or console. Error: ${error.message}</p>`;
        showMessage('Fatal Network/API error.', 'error');
    }
    
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Sends a control command (start, stop, or restart) to the server API.
 * @param {('start'|'stop'|'restart')} action - The server action to perform.
 */
async function controlServer(action) {
    // Disable buttons and show loading indicator
    ALL_BUTTONS.forEach(btn => btn.disabled = true);
    loadingIndicator.classList.remove('hidden');
    messagePanel.classList.add('hidden');
    
    const actionText = action.toUpperCase();
    updateStatusBadge(actionText + 'ING');

    try {
        const response = await fetch(`${BASE_URL}/api/control`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: action })
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            showMessage(`${actionText} command sent successfully.`, 'success');
            detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-pz-green mb-3">${actionText} COMMAND OUTPUT</h3><pre class="whitespace-pre-wrap text-gray-300 bg-gray-900 p-4 rounded-lg">${data.details || 'No output details provided.'}</pre>`;
        } else {
            showMessage(`${actionText} failed: ${data.message}.`, 'error');
            detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">${actionText} FAILED</h3><pre class="whitespace-pre-wrap text-red-400 bg-gray-900 p-4 rounded-lg">${data.details || 'No output details provided.'}</pre>`;
        }
        
    } catch (error) {
        console.error("Control Command Error:", error);
        showMessage(`Network error during ${actionText}: ${error.message}`, 'error');
        detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">${actionText} ERROR</h3><p class="text-red-400">Network connection failed.</p>`;
    } finally {
        // Re-enable buttons and hide loading indicator whether the command succeeded or failed
        ALL_BUTTONS.forEach(btn => btn.disabled = false);
        loadingIndicator.classList.add('hidden');
        
        // Fetch new details to update the status badge and details panel
        await fetchDetails();
    }
}


// =====================================================================
// Initialization
// =====================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    if (window.lucide) {
        lucide.createIcons();
    }

    updateStatusBadge('LOADING');
    fetchDetails();
});