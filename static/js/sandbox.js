let currentSandboxData = {};

function renderSandboxEditor(values, descriptions, container) {
    container.innerHTML = '';

    const createSection = (title, contentDiv) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'mb-6 border-b border-gray-700 pb-6 last:border-0';
        const header = document.createElement('h3');
        header.className = 'text-xl font-bold text-pz-green mb-4 capitalize';
        header.textContent = title;
        wrapper.appendChild(header);
        wrapper.appendChild(contentDiv);
        return wrapper;
    };

    // 1. Root Properties
    const rootGrid = document.createElement('div');
    rootGrid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4';

    const keys = Object.keys(values).sort();
    const objects = [];

    keys.forEach(key => {
        const val = values[key];
        if (typeof val === 'object' && val !== null) {
            objects.push(key);
            return;
        }
        const desc = descriptions[key];
        rootGrid.appendChild(createInputCard(key, val, [], desc));
    });

    container.appendChild(createSection('General Settings', rootGrid));

    // 2. Nested Tables
    objects.forEach(objKey => {
        const subData = values[objKey];
        const subDesc = descriptions[objKey] || {};

        const subGrid = document.createElement('div');
        subGrid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4';

        Object.keys(subData).forEach(subKey => {
            const desc = subDesc[subKey];
            subGrid.appendChild(createInputCard(subKey, subData[subKey], [objKey], desc));
        });

        container.appendChild(createSection(objKey.replace(/([A-Z])/g, ' $1').trim(), subGrid));
    });

    if (window.lucide) lucide.createIcons();
}

function createInputCard(key, value, path, description) {
    const wrapper = document.createElement('div');
    wrapper.className = 'bg-gray-900/50 p-3 rounded border border-gray-700 flex flex-col h-full';

    const label = document.createElement('label');
    label.className = 'text-gray-400 text-xs font-mono mb-1 font-bold';
    label.textContent = key;
    wrapper.appendChild(label);

    let input;
    if (typeof value === 'boolean') {
        const toggleWrapper = document.createElement('div');
        toggleWrapper.className = "flex items-center mb-2";
        input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = value;
        input.className = "w-5 h-5 text-pz-green bg-gray-700 border-gray-600 rounded focus:ring-pz-green focus:ring-2 cursor-pointer";
        const statusSpan = document.createElement('span');
        statusSpan.className = "ml-2 text-sm text-gray-300";
        statusSpan.textContent = value ? 'True' : 'False';

        input.addEventListener('change', (e) => {
            statusSpan.textContent = e.target.checked ? 'True' : 'False';
            updateLocalData(path, key, e.target.checked);
        });
        toggleWrapper.appendChild(input);
        toggleWrapper.appendChild(statusSpan);
        wrapper.appendChild(toggleWrapper);
    } else {
        input = document.createElement('input');
        input.type = typeof value === 'number' ? 'number' : 'text';
        input.value = value;
        if (typeof value === 'number') input.step = value % 1 !== 0 ? "0.1" : "1";
        input.className = "bg-gray-800 text-white text-sm rounded p-2 border border-gray-600 focus:border-pz-green focus:outline-none w-full mb-2";

        input.addEventListener('input', (e) => {
            let val = e.target.value;
            if (e.target.type === 'number') val = parseFloat(val);
            if (e.target.type === 'number' && isNaN(val)) val = 0;
            updateLocalData(path, key, val);
        });
        wrapper.appendChild(input);
    }

    if (description) {
        const descDiv = document.createElement('div');
        descDiv.className = 'mt-auto pt-2 border-t border-gray-800 text-xs text-gray-500 font-mono whitespace-pre-wrap leading-tight';
        descDiv.textContent = description;
        wrapper.appendChild(descDiv);
    }

    return wrapper;
}

function updateLocalData(path, key, newValue) {
    if (path.length === 0) {
        currentSandboxData[key] = newValue;
    } else {
        if (!currentSandboxData[path[0]]) currentSandboxData[path[0]] = {};
        currentSandboxData[path[0]][key] = newValue;
    }
}

async function fetchSandboxSettings() {
    const container = document.getElementById('sandbox-container');
    container.innerHTML = '<p class="text-center text-gray-500 py-10"><i data-lucide="loader-2" class="w-6 h-6 animate-spin inline-block"></i> Loading Lua settings...</p>';
    if (window.lucide) lucide.createIcons();

    try {
        const json = await apiCall('/sandbox');

        if (json.status === 'success') {
            currentSandboxData = json.data.values;
            renderSandboxEditor(json.data.values, json.data.descriptions || {}, container);
        } else {
            throw new Error(json.message);
        }
    } catch (e) {
        container.innerHTML = `<p class="text-red-500 text-center">Error loading settings: ${e.message}</p>`;
        showMessage(`Error: ${e.message}`, 'error');
    }
}

async function saveSandboxSettings() {
    if (!confirm("Are you sure you want to overwrite SandboxVars.lua? A server restart is required.")) return;

    try {
        const json = await apiCall('/sandbox', 'POST', currentSandboxData);

        if (json.status === 'success') {
            showMessage("Settings saved successfully!", 'success');
        } else {
            throw new Error(json.message);
        }
    } catch (e) {
        showMessage(`Save failed: ${e.message}`, 'error');
    }
}

// Expose functions
window.fetchSandboxSettings = fetchSandboxSettings;
window.saveSandboxSettings = saveSandboxSettings;
