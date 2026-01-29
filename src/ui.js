export const elements = {
    fileInput: document.getElementById('fileInput'),
    uploadOverlay: document.getElementById('uploadOverlay'),
    successOverlay: document.getElementById('successOverlay'),
    previewImg: document.getElementById('previewImg'),
    statusText: document.getElementById('statusText'),
    resetBtn: document.getElementById('resetBtn'),
    settingsBtn: document.getElementById('settingsBtn'),
    settingsModal: document.getElementById('settingsModal'),
    closeSettings: document.getElementById('closeSettings'),
    saveSettings: document.getElementById('saveSettings'),
    geminiKeyInput: document.getElementById('geminiKey'),
    supabaseUrlInput: document.getElementById('supabaseUrl'),
    supabaseKeyInput: document.getElementById('supabaseKey'),
    ootdBtn: document.getElementById('ootdBtn'),
    ootdModal: document.getElementById('ootdModal'),
    closeOOTD: document.getElementById('closeOOTD'),
    generateOOTD: document.getElementById('generateOOTD'),
    ootdResultOverlay: document.getElementById('ootdResultOverlay'),
    closeResult: document.getElementById('closeResult'),
    ootdOccasion: document.getElementById('ootdOccasion'),
    ootdWeather: document.getElementById('ootdWeather'),
    recentGrid: document.getElementById('recentGrid'),
    ootdItemsGrid: document.getElementById('ootdItemsGrid'),
    ootdReason: document.getElementById('ootdReason'),
    ootdNotes: document.getElementById('ootdNotes')
};

export function renderItems(items) {
    elements.recentGrid.innerHTML = '';
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'bg-gray-800 rounded-xl p-3 border border-gray-700 hover:border-yellow-500 transition group relative';

        const img = document.createElement('img');
        img.src = item.image_path;
        img.className = 'w-full h-32 object-cover rounded-lg mb-2 bg-gray-900';

        const title = document.createElement('h4');
        title.className = 'text-sm font-semibold text-white truncate';
        title.innerText = item.name || '未命名';

        const meta = document.createElement('p');
        meta.className = 'text-xs text-gray-400 truncate';
        meta.innerText = item.category || '分析中...';

        div.appendChild(img);
        div.appendChild(title);
        div.appendChild(meta);
        elements.recentGrid.appendChild(div);
    });
}

export function renderOOTD(ootdData, allItems) {
    elements.ootdReason.innerText = ootdData.reason;
    elements.ootdNotes.innerText = ootdData.notes;
    elements.ootdItemsGrid.innerHTML = '';

    ootdData.itemIds.forEach(id => {
        const item = allItems.find(i => i.id === id);
        if (item) {
            const div = document.createElement('div');
            div.className = 'bg-gray-800 rounded-xl p-2 border border-pink-500/30';

            const img = document.createElement('img');
            img.src = item.image_path;
            img.className = 'w-full h-40 object-cover rounded-lg mb-2';

            const name = document.createElement('p');
            name.className = 'text-sm text-white font-medium truncate';
            name.innerText = item.name;

            div.appendChild(img);
            div.appendChild(name);
            elements.ootdItemsGrid.appendChild(div);
        }
    });
}
