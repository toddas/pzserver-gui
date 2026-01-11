let currentIniData = {};

function renderIniEditor(values, descriptions, container) {
    container.innerHTML = '';

    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-1 md:grid-cols-2 gap-4';

    Object.keys(values).sort().forEach(key => {
        const value = values[key];
        const description = descriptions[key] || "";
        const wrapper = document.createElement('div');
        wrapper.className = 'bg-gray-900/50 p-3 rounded border border-gray-700 flex flex-col h-full';

        const label = document.createElement('label');
        label.className = 'text-gray-400 text-xs font-mono mb-1 font-bold block';
        label.textContent = key;
        wrapper.appendChild(label);

        let input;

        if (value.toLowerCase() === 'true' || value.toLowerCase() === 'false') {
            const toggleWrapper = document.createElement('div');
            toggleWrapper.className = "flex items-center mb-2";

            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = value.toLowerCase() === 'true';
            input.className = "w-5 h-5 text-pz-green bg-gray-700 border-gray-600 rounded focus:ring-pz-green focus:ring-2 cursor-pointer";

            const statusSpan = document.createElement('span');
            statusSpan.className = "ml-2 text-sm text-gray-300";
            statusSpan.textContent = input.checked ? 'True' : 'False';

            input.addEventListener('change', (e) => {
                statusSpan.textContent = e.target.checked ? 'True' : 'False';
                currentIniData[key] = e.target.checked;
            });

            toggleWrapper.appendChild(input);
            toggleWrapper.appendChild(statusSpan);
            wrapper.appendChild(toggleWrapper);

        } else if (!isNaN(value) && value.trim() !== "") {
            input = document.createElement('input');
            input.type = 'number';
            input.value = value;
            input.className = "bg-gray-800 text-white text-sm rounded p-2 border border-gray-600 focus:border-pz-green focus:outline-none w-full mb-2";
            input.addEventListener('input', (e) => {
                currentIniData[key] = e.target.value;
            });
            wrapper.appendChild(input);
        } else {
            input = document.createElement('textarea');
            input.rows = 2;
            input.value = value;
            input.className = "bg-gray-800 text-white text-sm rounded p-2 border border-gray-600 focus:border-pz-green focus:outline-none w-full mb-2";
            input.addEventListener('input', (e) => {
                currentIniData[key] = e.target.value;
            });
            wrapper.appendChild(input);
        }

        if (description) {
            const descDiv = document.createElement('div');
            descDiv.className = 'mt-auto pt-2 border-t border-gray-800 text-xs text-gray-500 font-mono whitespace-pre-wrap leading-tight';
            descDiv.textContent = description;
            wrapper.appendChild(descDiv);
        }

        grid.appendChild(wrapper);
    });

    container.appendChild(grid);
    if (window.lucide) lucide.createIcons();
}

async function fetchIniSettings() {
    const container = document.getElementById('config-container');
    if (!container) return;

    container.innerHTML = '<p class="text-center text-gray-500 py-10"><i data-lucide="loader-2" class="w-6 h-6 animate-spin inline-block"></i> Loading server.ini...</p>';
    if (window.lucide) lucide.createIcons();

    try {
        const json = await apiCall('/config');

        if (json.status === 'success') {
            currentIniData = json.data.values;
            renderIniEditor(json.data.values, json.data.descriptions, container);
        } else {
            throw new Error(json.message);
        }
    } catch (e) {
        container.innerHTML = `<p class="text-red-500 text-center">Error loading config: ${e.message}</p>`;
        showMessage(`Error: ${e.message}`, 'error');
    }
}

async function saveIniSettings() {
    if (!confirm("Are you sure you want to overwrite server.ini? A server restart is required.")) return;

    try {
        const json = await apiCall('/config', 'POST', currentIniData);

        if (json.status === 'success') {
            showMessage("Configuration saved! Restart server to apply.", 'success');
        } else {
            throw new Error(json.message);
        }
    } catch (e) {
        showMessage(`Save failed: ${e.message}`, 'error');
    }
}

// Expose functions
window.fetchIniSettings = fetchIniSettings;
window.saveIniSettings = saveIniSettings;
