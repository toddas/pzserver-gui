tailwind.config = {
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                'pz-green': '#5d9241',
                'pz-dark': '#1e293b',
            }
        }
    }
}

const BASE_URL = '';
let detailsOutput;
let statusText;
let serverStatusBadge;
let messagePanel;
let loadingIndicator;
let initialLoadMessage;
let newModsTableContainer; // For 'new-mods-table-container'
let refreshModsBtn;       // For 'refresh-mods-btn'
let saveModsBtn;          // For 'save-mods-btn'

const STORAGE_KEY = 'pz_persistent_mods';
const REFRESH_BTN_HTML = '<i data-lucide="rotate-cw" class="w-5 h-5"></i>';



//MODS VARS
const NEW_MOD_ROW_HTML = `
            <div class="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4 mb-3 p-3 bg-gray-700/50 rounded-lg new-mod-row">
                <input type="text" placeholder="Internal Mod ID (e.g., 'ModID1')" required
                       class="mod-internal-id flex-1 p-2 rounded-lg bg-gray-900 border border-gray-600 focus:ring-pz-green focus:border-pz-green text-gray-200" title="Internal Mod ID is mandatory">
                <input type="text" placeholder="Workshop ID (e.g., '123456789')" required
                       class="mod-workshop-id flex-1 p-2 rounded-lg bg-gray-900 border border-gray-600 focus:ring-pz-green focus:border-pz-green text-gray-200" title="Workshop ID is mandatory">
                <button onclick="this.closest('.new-mod-row').remove(); if (document.querySelectorAll('.new-mod-row').length === 0) addNewModRow();" 
                        class="p-2 sm:w-10 sm:h-10 w-full text-red-500 hover:text-red-300 transition duration-200 bg-gray-900 rounded-lg sm:bg-transparent sm:hover:bg-transparent" 
                        title="Remove Row">
                    <i data-lucide="x" class="w-5 h-5 mx-auto sm:mx-0"></i>
                </button>
            </div>
        `;



function initializeDomElements() {
    // Attempt to find all elements, which will return null if they don't exist on the current page
    detailsOutput = document.getElementById('details-output');
    statusText = document.getElementById('status-text');
    serverStatusBadge = document.getElementById('server-status');
    messagePanel = document.getElementById('message-panel');
    loadingIndicator = document.getElementById('loading-indicator');
    initialLoadMessage = document.getElementById('initial-load-message');
    
    // Mods-specific elements
    newModsTableContainer = document.getElementById('new-mods-table-container'); 
    refreshModsBtn = document.getElementById('refresh-mods-btn');
    saveModsBtn = document.getElementById('save-mods-btn');
    
    // Run initial functions only if their required elements exist
    if (detailsOutput) {
        fetchDetails(); // This function depends on statusText, serverStatusBadge, etc., which should be checked inside
    }

    if (newModsTableContainer) {
        // This suggests we are on the mods page
        fetchMods();
        addNewModRow(); 
    }
}
// ... (Your DOMContentLoaded listener goes here)

// Ensure the script only runs AFTER the HTML is loaded.
// If your <script> tag is in the <head>, use this:
document.addEventListener('DOMContentLoaded', initializeDomElements);

function showMessage(text, type = 'info') {
    const panel = document.getElementById('message-panel');
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

function updateStatusBadge(status) {
    status = String(status).toUpperCase().trim();

    let displayStatus = 'LOADING';
    let colorClass = 'bg-gray-500 text-gray-900';
    let iconName = 'help-circle';
    let iconClass = 'w-4 h-4 mr-1';

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

    const iconContainer = document.getElementById('status-icon');
    iconContainer.innerHTML = '';
    if (window.lucide && typeof lucide.createIcons === 'function') {
        const icons = lucide.createIcons();
        if (icons && icons[iconName]) {
            const iconHtml = icons[iconName].toSvg({ class: iconClass });
            iconContainer.innerHTML = iconHtml;
        }
    }
}

async function fetchDetails() {
    if (initialLoadMessage) {
        initialLoadMessage.classList.add('hidden');
    }

    detailsOutput.innerHTML = '<p class="text-gray-500 text-center py-10"><i data-lucide="rotate-cw" class="w-5 h-5 inline-block mr-2 animate-spin"></i> Refreshing data...</p>';
    updateStatusBadge('LOADING');

    try {
        const response = await fetch(`${BASE_URL}/api/details`);
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
        detailsOutput.innerHTML = `<p class="text-red-500 text-center py-10">Fatal network error. Check API connection or Flask console. Error: ${error.message}</p>`;
        showMessage('Fatal Network/API error.', 'error');
    }

    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
}

async function controlServer(action) {
    document.querySelectorAll('button').forEach(btn => btn.disabled = true);
    loadingIndicator.classList.remove('hidden');
    messagePanel.classList.add('hidden');

    const actionText = action.toUpperCase();
    updateStatusBadge(actionText + 'ING');

    try {
        const response = await fetch(`${BASE_URL}/api/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });

        const data = await response.json();

        if (data.status === 'success') {
            showMessage(`${actionText} command sent successfully.`, 'success');
            detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-pz-green mb-3">${actionText} COMMAND OUTPUT</h3><pre class="whitespace-pre-wrap text-gray-300 bg-gray-900 p-4 rounded-lg">${data.details || 'No output details provided.'}</pre>`;
        } else {
            showMessage(`${actionText} failed: ${data.message}.`, 'error');
            detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">${actionText} FAILED}</h3><pre class="whitespace-pre-wrap text-red-400 bg-gray-900 p-4 rounded-lg">${data.details || 'No output details provided.'}</pre>`;
        }

    } catch (error) {
        console.error("Control Command Error:", error);
        showMessage(`Network error during ${actionText}: ${error.message}`, 'error');
        detailsOutput.innerHTML = `<h3 class="text-xl font-bold text-red-500 mb-3">${actionText} ERROR</h3><p class="text-red-400">Network connection failed.</p>`;
    } finally {
        document.querySelectorAll('button').forEach(btn => btn.disabled = false);
        loadingIndicator.classList.add('hidden');
        await fetchDetails();
    }
}




function addNewModRow() {
    const container = document.getElementById('new-mods-table-container');
    const newRow = document.createElement('div');
    newRow.innerHTML = NEW_MOD_ROW_HTML;
    container.appendChild(newRow.firstElementChild);
    // Re-render Lucide icons for the new row
    if (window.lucide) { lucide.createIcons(); }
}

function getPersistentMods() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
}

function savePersistentMods(mods) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(mods));
}

async function fetchMods() {
    const modsListOutput = document.getElementById('mods-list-output');
    const loadingMessage = document.getElementById('mods-loading-message');
    const refreshBtn = document.getElementById('refresh-mods-btn'); // Get button reference

    // --- UI START LOADING FEEDBACK ---
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>';
    if (window.lucide) { lucide.createIcons(); }

    // 1. Show Loading Message and Clear Old List
    loadingMessage.textContent = 'Syncing mod lists...';
    document.getElementById('mods-loading-wrapper').classList.remove('hidden');
    modsListOutput.innerHTML = ''; // Clear the previous mod list table safely

    try {
        // 2. Fetch current ACTIVE mods from server.ini (The source of truth for "enabled" state)
        const response = await fetch(`${BASE_URL}/api/mods`);
        const apiData = await response.json();

        if (apiData.status !== 'success') {
            throw new Error(apiData.message || 'API failed to return mod list.');
        }
        const activeMods = apiData.data; // List of {internal_id, workshop_id, enabled: true}

        // 3. Get the full persistent list from localStorage
        let persistentMods = getPersistentMods();

        // 4. Create a map of active mods for quick lookup
        const activeModIds = new Set(activeMods.map(mod => mod.internal_id));

        // 5. Merge the lists (Server INI is the source of truth for 'enabled')
        const mergedModsMap = new Map();

        // A. Add/Update mods from server.ini (they are active)
        activeMods.forEach(mod => {
            // Use mod.name from persistence if available, otherwise use mod.internal_id (placeholder)
            const existing = persistentMods.find(p => p.internal_id === mod.internal_id);
            mergedModsMap.set(mod.internal_id, { ...mod, name: existing?.name || mod.internal_id, enabled: true });
        });

        // B. Add mods from localStorage that are NOT in server.ini (they are disabled)
        persistentMods.forEach(mod => {
            if (!mergedModsMap.has(mod.internal_id)) {
                // Mark as disabled because it's in localStorage but not in the INI file
                mergedModsMap.set(mod.internal_id, { ...mod, enabled: false });
            }
        });

        const finalMods = Array.from(mergedModsMap.values());

        // 6. Save the final merged list back to localStorage
        savePersistentMods(finalMods);

        // 7. Render the list
        renderModList(finalMods);

    } catch (error) {
        console.error("Mod Sync Error:", error);
        showMessage(`Mod sync failed: ${error.message}. Displaying cached list only.`, 'error');
        // Fallback: Just render the persistent list if API fails
        renderModList(getPersistentMods());
    }
    finally {
        // --- UI END LOADING FEEDBACK ---
        document.getElementById('mods-loading-wrapper').classList.add('hidden'); // Hide wrapper
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = REFRESH_BTN_HTML; // Restore the icon HTML
        if (window.lucide) { lucide.createIcons(); } // Re-render the restored icon
    }
}

function renderModList(mods) {
    const modsListOutput = document.getElementById('mods-list-output');

    if (mods.length === 0) {
        modsListOutput.innerHTML = `<p class="text-yellow-400 text-center py-10">No known mods. Use the section below to add some.</p>`;
        return;
    }

    // Sort mods: Active first, then alphabetically by name
    mods.sort((a, b) => {
        if (a.enabled !== b.enabled) {
            return a.enabled ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
    });

    // Generate the Mod List Table HTML
    const tableHtml = `
                <table class="min-w-full text-sm divide-y divide-gray-700 mod-table">
                    <thead>
                        <tr class="text-gray-400">
                            <th class="py-2 text-left w-1/12">Active</th>
                            <th class="py-2 text-left w-5/12 hidden sm:table-cell">Internal Mod ID</th>
                            <th class="py-2 text-left w-4/12 sm:w-3/12">Display Name</th>
                            <th class="py-2 text-left w-2/12 sm:w-2/12">Workshop ID</th>
                            <th class="py-2 text-left w-1/12"></th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-800">
                        ${mods.map(mod => `
                            <tr class="hover:bg-gray-700 transition-colors" 
                                data-internal-id="${mod.internal_id}" 
                                data-workshop-id="${mod.workshop_id}">
                                <td class="py-2">
                                    <input 
                                        type="checkbox" 
                                        class="mod-checkbox h-5 w-5 text-pz-green bg-gray-700 border-gray-600 rounded cursor-pointer transition duration-150 ease-in-out" 
                                        ${mod.enabled ? 'checked' : ''}
                                        title="${mod.enabled ? 'Enabled in server.ini' : 'Disabled'}"
                                    >
                                </td>
                                <td class="py-2 font-mono text-gray-400 hidden sm:table-cell">${mod.internal_id}</td>
                                <td class="py-2 font-medium text-gray-200">${mod.name}</td>
                                <td class="py-2">
                                    ${mod.workshop_id && mod.workshop_id !== 'N/A' ?
            `<a href="https://steamcommunity.com/sharedfiles/filedetails/?id=${mod.workshop_id}" target="_blank" class="text-blue-400 hover:text-blue-300 transition-colors">${mod.workshop_id}</a>` :
            '<span class="text-gray-500">N/A</span>'
        }
                                </td>
                                <td class="py-2">
                                    <button onclick="deleteModFromList('${mod.internal_id}')" title="Permanently delete mod from list" class="text-red-500 hover:text-red-300 p-1 rounded transition duration-200">
                                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
    modsListOutput.innerHTML = tableHtml;
    if (window.lucide) { lucide.createIcons(); }
}

function deleteModFromList(internalId) {
    if (!confirm(`Are you sure you want to permanently delete mod ${internalId} from this list? This will also disable it on the server when you save.`)) {
        return;
    }

    let persistentMods = getPersistentMods();
    // Filter out the mod with the matching internalId
    const newModsList = persistentMods.filter(mod => mod.internal_id !== internalId);

    savePersistentMods(newModsList);
    showMessage(`Mod ${internalId} removed. Click "Save Changes" to disable it on the server.`, 'info');

    // Re-render the list immediately
    renderModList(newModsList);
}

async function saveMods() {
    const saveBtn = document.getElementById('save-mods-btn');

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 mr-2 animate-spin"></i> Saving...';
    if (window.lucide) { lucide.createIcons(); }

    const activeMods = [];
    let newModCount = 0;

    // 1. Collect all *checked* mods from the persistent table
    const modsListOutput = document.getElementById('mods-list-output');
    const newPersistentList = []; // Will store all mods (checked or not)

    modsListOutput.querySelectorAll('tbody tr').forEach(row => {
        const checkbox = row.querySelector('.mod-checkbox');
        // The name is pulled from the table cell (index 3, but the second hidden one doesn't count in CSS so it's the third visible column, the 4th child)
        const nameCell = row.querySelector('td:nth-child(3)');
        const modData = {
            internal_id: row.dataset.internalId,
            workshop_id: row.dataset.workshopId,
            name: nameCell ? nameCell.textContent.trim() : row.dataset.internalId,
            enabled: checkbox.checked
        };

        newPersistentList.push(modData);

        // This is the list sent to the API
        if (checkbox.checked) {
            activeMods.push({
                internal_id: modData.internal_id,
                workshop_id: modData.workshop_id,
            });
        }
    });

    // 2. Gather NEW mods from the input fields and merge into persistent list
    const newModRows = document.querySelectorAll('#new-mods-table-container .new-mod-row');
    newModRows.forEach(row => {
        const internalIdInput = row.querySelector('.mod-internal-id');
        const workshopIdInput = row.querySelector('.mod-workshop-id');

        const internalId = internalIdInput ? internalIdInput.value.trim() : '';
        const workshopId = workshopIdInput ? workshopIdInput.value.trim() : '';

        // Only include if both mandatory IDs are present and not already in the list
        if (internalId && workshopId) {
            // Check if this mod is already known (either enabled or disabled)
            if (!newPersistentList.some(mod => mod.internal_id === internalId)) {
                const newMod = {
                    internal_id: internalId,
                    workshop_id: workshopId,
                    name: internalId, // Use ID as placeholder name
                    enabled: true // Default to active when newly added
                };
                newPersistentList.push(newMod);
                activeMods.push({
                    internal_id: internalId,
                    workshop_id: workshopId,
                });
                newModCount++;
            } else {
                // If it exists, but was in the NEW mod input, force it to be active
                const existingMod = newPersistentList.find(mod => mod.internal_id === internalId);
                if (existingMod) {
                    existingMod.enabled = true;
                    // Make sure it's in the list to be sent to the API
                    if (!activeMods.some(mod => mod.internal_id === internalId)) {
                        activeMods.push({ internal_id: internalId, workshop_id: workshopId });
                    }
                }
            }
        }
    });

    // 3. Save the *full* list back to localStorage for persistence
    savePersistentMods(newPersistentList);

    // 4. Send *only* the active mods to the API
    if (!confirm(`You are about to save changes, which will set the active mods to a list of ${activeMods.length} mods (including ${newModCount} newly enabled/added mods). A server restart will be required to apply these changes. Continue?`)) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i data-lucide="save" class="w-5 h-5 mr-2"></i> Save Changes';
        if (window.lucide) { lucide.createIcons(); }
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/api/mods/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mods: activeMods })
        });

        const data = await response.json();

        if (data.status === 'success') {
            showMessage("Mod changes saved! **Restart server to apply new configuration.**", 'success');
        } else {
            showMessage(`Mod save failed: ${data.message}`, 'error');
        }

    } catch (error) {
        console.error("Mod Save Error:", error);
        showMessage("Network error during mod save.", 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i data-lucide="save" class="w-5 h-5 mr-2"></i> Save Changes';
        if (window.lucide) { lucide.createIcons(); }

        // Clear and reset the New Mods input section
        document.getElementById('new-mods-table-container').innerHTML = '';
        addNewModRow();

        // Refresh the list from the server to confirm the changes were written
        fetchMods();
    }
}


