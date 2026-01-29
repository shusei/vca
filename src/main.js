import { elements, renderItems, renderOOTD } from './ui.js';
import { getSettings, saveSettings } from './config.js';
import { compressImage } from './utils.js';
import { uploadToSupabase, updateItemAI, fetchItems, fetchAvailableItems } from './supabase.js';
import { analyzeImage, generateOOTD } from './gemini.js';

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    loadSettingsUI();
    refreshGrid();
});

function loadSettingsUI() {
    const settings = getSettings();
    if (settings.geminiKey) elements.geminiKeyInput.value = settings.geminiKey;
    if (settings.supabaseUrl) elements.supabaseUrlInput.value = settings.supabaseUrl;
    if (settings.supabaseKey) elements.supabaseKeyInput.value = settings.supabaseKey;
}

async function refreshGrid() {
    const items = await fetchItems();
    renderItems(items);
}

// Settings Events
elements.settingsBtn.addEventListener('click', () => elements.settingsModal.classList.remove('hidden'));
elements.closeSettings.addEventListener('click', () => elements.settingsModal.classList.add('hidden'));

elements.saveSettings.addEventListener('click', () => {
    saveSettings(
        elements.geminiKeyInput.value.trim(),
        elements.supabaseUrlInput.value.trim(),
        elements.supabaseKeyInput.value.trim()
    );
    alert('設定已儲存！');
    elements.settingsModal.classList.add('hidden');
    refreshGrid();
});

// Upload Events
elements.fileInput.addEventListener('change', async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const { supabaseKey } = getSettings();
    if (!supabaseKey) {
        alert('請先至設定頁面輸入 Supabase Anon Key！');
        elements.settingsModal.classList.remove('hidden');
        return;
    }

    elements.uploadOverlay.classList.remove('hidden');
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        elements.statusText.innerText = `正在處理第 ${i + 1} / ${files.length} 張圖片...`;

        try {
            const compressedBlob = await compressImage(file);
            elements.previewImg.src = URL.createObjectURL(compressedBlob);

            elements.statusText.innerText = `正在上傳第 ${i + 1} / ${files.length} 張...`;
            const recordId = await uploadToSupabase(compressedBlob, file.name);

            elements.statusText.innerText = `AI 正在分析第 ${i + 1} / ${files.length} 張...`;
            const aiData = await analyzeImage(compressedBlob);

            if (aiData) {
                await updateItemAI(recordId, aiData);
            }
            successCount++;
        } catch (error) {
            console.error(error);
            failCount++;
        }
    }

    elements.uploadOverlay.classList.add('hidden');
    elements.successOverlay.classList.remove('hidden');
    const resultMsg = document.querySelector('#successOverlay h3');
    if (resultMsg) resultMsg.innerText = `上傳完成！成功 ${successCount} 張，失敗 ${failCount} 張`;

    refreshGrid();
});

elements.resetBtn.addEventListener('click', () => {
    elements.successOverlay.classList.add('hidden');
    elements.fileInput.value = '';
    elements.previewImg.src = '';
});

// OOTD Events
elements.ootdBtn.addEventListener('click', () => elements.ootdModal.classList.remove('hidden'));
elements.closeOOTD.addEventListener('click', () => elements.ootdModal.classList.add('hidden'));
elements.closeResult.addEventListener('click', () => elements.ootdResultOverlay.classList.add('hidden'));

elements.generateOOTD.addEventListener('click', async () => {
    const occasion = elements.ootdOccasion.value || '日常休閒';
    const weather = elements.ootdWeather.value || '舒適';

    elements.generateOOTD.innerText = '正在思考中...';
    elements.generateOOTD.disabled = true;

    try {
        const items = await fetchAvailableItems();
        if (items.length === 0) throw new Error('衣櫃是空的，請先上傳一些衣服！');

        const ootdData = await generateOOTD(occasion, weather, items);
        renderOOTD(ootdData, items);

        elements.ootdModal.classList.add('hidden');
        elements.ootdResultOverlay.classList.remove('hidden');
    } catch (error) {
        console.error(error);
        alert('生成失敗: ' + error.message);
    } finally {
        elements.generateOOTD.innerText = '開始生成';
        elements.generateOOTD.disabled = false;
    }
});
