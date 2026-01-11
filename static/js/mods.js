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

const STORAGE_KEY = 'pz_persistent_mods';
const REFRESH_BTN_HTML = '<i data-lucide="rotate-cw" class="w-5 h-5"></i>';

function addNewModRow() {
    const container = document.getElementById('new-mods-table-container');
    const newRow = document.createElement('div');
    newRow.innerHTML = NEW_MOD_ROW_HTML;
    container.appendChild(newRow.firstElementChild);
    if (window.lucide) { lucide.createIcons(); }
}

function getPersistentMods() {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
}

function savePersistentMods(mods) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(mods));
}

function renderModList(mods) {
    const modsListOutput = document.getElementById('mods-list-output');

    if (mods.length === 0) {
        modsListOutput.innerHTML = `<p class="text-yellow-400 text-center py-10">No known mods. Use the section below to add some.</p>`;
        return;
    }

    mods.sort((a, b) => {
        if (a.enabled !== b.enabled) {
            return a.enabled ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
    });

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
    const newModsList = persistentMods.filter(mod => mod.internal_id !== internalId);

    savePersistentMods(newModsList);
    showMessage(`Mod ${internalId} removed. Click "Save Changes" to disable it on the server.`, 'info');

    renderModList(newModsList);
}

async function fetchMods() {
    const modsListOutput = document.getElementById('mods-list-output');
    const loadingMessage = document.getElementById('mods-loading-message');
    const refreshBtn = document.getElementById('refresh-mods-btn');

    // UI START LOADING
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>';
    if (window.lucide) { lucide.createIcons(); }

    loadingMessage.textContent = 'Syncing mod lists...';
    document.getElementById('mods-loading-wrapper').classList.remove('hidden');
    modsListOutput.innerHTML = '';

    try {
        const apiData = await apiCall('/mods');

        if (apiData.status !== 'success') {
            throw new Error(apiData.message || 'API failed to return mod list.');
        }
        const activeMods = apiData.data;

        let persistentMods = getPersistentMods();
        const activeModIds = new Set(activeMods.map(mod => mod.internal_id));
        const mergedModsMap = new Map();

        // A. Add/Update mods from server.ini (they are active)
        activeMods.forEach(mod => {
            const existing = persistentMods.find(p => p.internal_id === mod.internal_id);
            mergedModsMap.set(mod.internal_id, { ...mod, name: existing?.name || mod.internal_id, enabled: true });
        });

        // B. Add mods from localStorage that are NOT in server.ini (they are disabled)
        persistentMods.forEach(mod => {
            if (!mergedModsMap.has(mod.internal_id)) {
                mergedModsMap.set(mod.internal_id, { ...mod, enabled: false });
            }
        });

        const finalMods = Array.from(mergedModsMap.values());
        savePersistentMods(finalMods);
        renderModList(finalMods);

    } catch (error) {
        console.error("Mod Sync Error:", error);
        showMessage(`Mod sync failed: ${error.message}. Displaying cached list only.`, 'error');
        renderModList(getPersistentMods());
    }
    finally {
        document.getElementById('mods-loading-wrapper').classList.add('hidden');
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = REFRESH_BTN_HTML;
        if (window.lucide) { lucide.createIcons(); }
    }
}

async function saveMods() {
    const saveBtn = document.getElementById('save-mods-btn');

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 mr-2 animate-spin"></i> Saving...';
    if (window.lucide) { lucide.createIcons(); }

    const activeMods = [];
    let newModCount = 0;

    const modsListOutput = document.getElementById('mods-list-output');
    const newPersistentList = [];

    modsListOutput.querySelectorAll('tbody tr').forEach(row => {
        const checkbox = row.querySelector('.mod-checkbox');
        const nameCell = row.querySelector('td:nth-child(3)');
        const modData = {
            internal_id: row.dataset.internalId,
            workshop_id: row.dataset.workshopId,
            name: nameCell ? nameCell.textContent.trim() : row.dataset.internalId,
            enabled: checkbox.checked
        };

        newPersistentList.push(modData);

        if (checkbox.checked) {
            activeMods.push({
                internal_id: modData.internal_id,
                workshop_id: modData.workshop_id,
            });
        }
    });

    // Gather NEW mods
    const newModRows = document.querySelectorAll('#new-mods-table-container .new-mod-row');
    newModRows.forEach(row => {
        const internalIdInput = row.querySelector('.mod-internal-id');
        const workshopIdInput = row.querySelector('.mod-workshop-id');

        const internalId = internalIdInput ? internalIdInput.value.trim() : '';
        const workshopId = workshopIdInput ? workshopIdInput.value.trim() : '';

        if (internalId && workshopId) {
            if (!newPersistentList.some(mod => mod.internal_id === internalId)) {
                const newMod = {
                    internal_id: internalId,
                    workshop_id: workshopId,
                    name: internalId,
                    enabled: true
                };
                newPersistentList.push(newMod);
                activeMods.push({
                    internal_id: internalId,
                    workshop_id: workshopId,
                });
                newModCount++;
            } else {
                const existingMod = newPersistentList.find(mod => mod.internal_id === internalId);
                if (existingMod) {
                    existingMod.enabled = true;
                    if (!activeMods.some(mod => mod.internal_id === internalId)) {
                        activeMods.push({ internal_id: internalId, workshop_id: workshopId });
                    }
                }
            }
        }
    });

    savePersistentMods(newPersistentList);

    if (!confirm(`You are about to save changes, which will set the active mods to a list of ${activeMods.length} mods (including ${newModCount} newly enabled/added mods). A server restart will be required to apply these changes. Continue?`)) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i data-lucide="save" class="w-5 h-5 mr-2"></i> Save Changes';
        if (window.lucide) { lucide.createIcons(); }
        return;
    }

    try {
        const data = await apiCall('/mods/update', 'POST', { mods: activeMods });

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

        document.getElementById('new-mods-table-container').innerHTML = '';
        addNewModRow();
        fetchMods();
    }
}

function initializeMods() {
    // Expose for onclick
    window.addNewModRow = addNewModRow;
    window.fetchMods = fetchMods;
    window.saveMods = saveMods;
    window.deleteModFromList = deleteModFromList;

    addNewModRow();
    fetchMods();
}
