// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadOverlay = document.getElementById('uploadOverlay');
const successOverlay = document.getElementById('successOverlay');
const previewImg = document.getElementById('previewImg');
const statusText = document.getElementById('statusText');
const resetBtn = document.getElementById('resetBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeSettings = document.getElementById('closeSettings');
const saveSettings = document.getElementById('saveSettings');
const geminiKeyInput = document.getElementById('geminiKey');
const supabaseUrlInput = document.getElementById('supabaseUrl');
const supabaseKeyInput = document.getElementById('supabaseKey');

// OOTD Elements
const ootdBtn = document.getElementById('ootdBtn');
const ootdModal = document.getElementById('ootdModal');
const closeOOTD = document.getElementById('closeOOTD');
const generateOOTD = document.getElementById('generateOOTD');
const ootdResultOverlay = document.getElementById('ootdResultOverlay');
const closeResult = document.getElementById('closeResult');
const ootdOccasion = document.getElementById('ootdOccasion');
const ootdWeather = document.getElementById('ootdWeather');

// Constants
const STORAGE_KEY_GEMINI = 'vca_gemini_key';
const STORAGE_KEY_SUPABASE_URL = 'vca_supabase_url';
const STORAGE_KEY_SUPABASE_KEY = 'vca_supabase_key';

// Default Key provided by user (Pre-filled for convenience)
const DEFAULT_GEMINI_KEY = ''; // Security: Key removed for public repo
const DEFAULT_SUPABASE_URL = 'https://[YOUR-PROJECT-ID].supabase.co';

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    checkFirstRun();
    fetchItems(); // Fetch items on load
});

function loadSettings() {
    const geminiKey = localStorage.getItem(STORAGE_KEY_GEMINI);
    const supabaseUrl = localStorage.getItem(STORAGE_KEY_SUPABASE_URL);
    const supabaseKey = localStorage.getItem(STORAGE_KEY_SUPABASE_KEY);

    if (geminiKey) geminiKeyInput.value = geminiKey;
    else geminiKeyInput.value = DEFAULT_GEMINI_KEY;

    if (supabaseUrl) supabaseUrlInput.value = supabaseUrl;
    else supabaseUrlInput.value = DEFAULT_SUPABASE_URL;

    if (supabaseKey) supabaseKeyInput.value = supabaseKey;
}

function checkFirstRun() {
    if (!localStorage.getItem(STORAGE_KEY_SUPABASE_KEY)) {
        // setTimeout(() => openSettings(), 500); 
    }
}

// Settings Modal Logic
function openSettings() {
    settingsModal.classList.remove('hidden');
}

function closeSettingsModal() {
    settingsModal.classList.add('hidden');
}

settingsBtn.addEventListener('click', openSettings);
closeSettings.addEventListener('click', closeSettingsModal);

saveSettings.addEventListener('click', () => {
    const gKey = geminiKeyInput.value.trim();
    const sUrl = supabaseUrlInput.value.trim();
    const sKey = supabaseKeyInput.value.trim();

    if (gKey) localStorage.setItem(STORAGE_KEY_GEMINI, gKey);
    if (sUrl) localStorage.setItem(STORAGE_KEY_SUPABASE_URL, sUrl);
    if (sKey) localStorage.setItem(STORAGE_KEY_SUPABASE_KEY, sKey);

    alert('設定已儲存！');
    closeSettingsModal();
    fetchItems(); // Refresh items after settings change
});

// OOTD Modal Logic
ootdBtn.addEventListener('click', () => ootdModal.classList.remove('hidden'));
closeOOTD.addEventListener('click', () => ootdModal.classList.add('hidden'));
closeResult.addEventListener('click', () => ootdResultOverlay.classList.add('hidden'));

generateOOTD.addEventListener('click', async () => {
    const occasion = ootdOccasion.value || '日常休閒';
    const weather = ootdWeather.value || '舒適';

    // UI Feedback
    generateOOTD.innerText = '正在思考中...';
    generateOOTD.disabled = true;

    try {
        await runOOTDGeneration(occasion, weather);
        ootdModal.classList.add('hidden');
        ootdResultOverlay.classList.remove('hidden');
    } catch (error) {
        console.error(error);
        alert('生成失敗: ' + error.message);
    } finally {
        generateOOTD.innerText = '開始生成';
        generateOOTD.disabled = false;
    }
});

// File Upload Logic
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check for Supabase Config
    const supabaseUrl = localStorage.getItem(STORAGE_KEY_SUPABASE_URL) || DEFAULT_SUPABASE_URL;
    const supabaseKey = localStorage.getItem(STORAGE_KEY_SUPABASE_KEY);

    if (!supabaseKey) {
        alert('請先至設定頁面輸入 Supabase Anon Key！');
        openSettings();
        return;
    }

    // Show Overlay
    uploadOverlay.classList.remove('hidden');
    statusText.innerText = '正在壓縮圖片...';

    try {
        // 1. Client-side Compression
        const compressedBlob = await compressImage(file);

        // Show Preview
        const previewUrl = URL.createObjectURL(compressedBlob);
        previewImg.src = previewUrl;

        // 2. Upload to Supabase
        statusText.innerText = '正在上傳至雲端...';

        // Initialize Client
        const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);

        // Start Upload & Insert (Await this to ensure data safety)
        const recordId = await uploadToSupabase(supabase, compressedBlob, file.name);

        // 3. Success (UI Feedback)
        uploadOverlay.classList.add('hidden');
        successOverlay.classList.remove('hidden');

        // 4. Background AI Analysis
        analyzeImageWithGemini(compressedBlob, recordId, supabaseUrl, supabaseKey);

    } catch (error) {
        console.error(error);
        alert('發生錯誤：' + error.message);
        uploadOverlay.classList.add('hidden');
    }
});

resetBtn.addEventListener('click', () => {
    successOverlay.classList.add('hidden');
    fileInput.value = ''; // Reset input
    previewImg.src = '';
});

// Helper: Image Compression
function compressImage(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                // Max width 1000px
                const maxWidth = 1000;
                let width = img.width;
                let height = img.height;

                if (width > maxWidth) {
                    height *= maxWidth / width;
                    width = maxWidth;
                }

                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);

                // Compress to WebP 0.8
                canvas.toBlob((blob) => {
                    resolve(blob);
                }, 'image/webp', 0.8);
            };
            img.onerror = (err) => reject(new Error('Image load failed'));
        };
        reader.onerror = (err) => reject(new Error('File read failed'));
    });
}

// Helper: Real Upload to Supabase (Returns Record ID)
async function uploadToSupabase(supabase, blob, originalName) {
    // 1. Generate Unique Filename
    const timestamp = new Date().getTime();
    const cleanName = originalName.replace(/[^a-zA-Z0-9]/g, '_');
    const fileName = `${timestamp}_${cleanName}.webp`;

    // 2. Upload Image
    const { data: uploadData, error: uploadError } = await supabase.storage
        .from('wardrobe_images')
        .upload(fileName, blob, {
            cacheControl: '3600',
            upsert: false
        });

    if (uploadError) throw new Error('圖片上傳失敗: ' + uploadError.message);

    // 3. Get Public URL
    const { data: { publicUrl } } = supabase.storage
        .from('wardrobe_images')
        .getPublicUrl(fileName);

    // 4. Insert Record to DB
    const { data: insertData, error: dbError } = await supabase
        .from('items')
        .insert([
            {
                name: originalName.split('.')[0], // Initial name
                image_path: publicUrl,
                status: 'processing', // Mark as processing for AI
                created_at: new Date().toISOString()
            }
        ])
        .select(); // Return the inserted record

    if (dbError) throw new Error('資料庫寫入失敗: ' + dbError.message);

    console.log('Upload success:', publicUrl);
    return insertData[0].id;
}

// Helper: Gemini Analysis
async function analyzeImageWithGemini(blob, recordId, supabaseUrl, supabaseKey) {
    const geminiKey = localStorage.getItem(STORAGE_KEY_GEMINI) || DEFAULT_GEMINI_KEY;
    if (!geminiKey) {
        console.warn('No Gemini Key found, skipping analysis.');
        return;
    }

    // Update UI status
    const statusText = document.getElementById('statusText');
    if (statusText) statusText.innerText = 'AI 正在分析中...';

    console.log('Starting AI analysis for:', recordId);

    try {
        // Convert Blob to Base64
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = async () => {
            const base64data = reader.result.split(',')[1];

            // Call Gemini API (REST)
            // Using user-specified model: 'gemini-flash-latest'
            const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${geminiKey}`;

            const prompt = `
            Analyze this clothing item image. Return a JSON object with these fields:
            - type: (e.g., T-Shirt, Dress, Jeans)
            - color: (Main color)
            - category: (Top, Bottom, Shoes, Accessory, One-Piece)
            - tags: (Array of style tags, e.g., Casual, Formal, Vintage)
            - description: (Short description)
            
            IMPORTANT: Output PURE JSON only. Do not use Markdown code blocks.
            `;

            console.log('Sending request to Gemini...');
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{
                        parts: [
                            { text: prompt },
                            { inline_data: { mime_type: "image/webp", data: base64data } }
                        ]
                    }]
                })
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Gemini API Error (${response.status}): ${errText}`);
            }

            const result = await response.json();
            console.log('Gemini Raw Response:', result);

            // Parse AI Response
            let aiJson = {};
            try {
                const text = result.candidates[0].content.parts[0].text;
                // Remove markdown code blocks if present
                const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
                aiJson = JSON.parse(cleanText);
            } catch (e) {
                console.error('Failed to parse AI response:', e);
                console.log('Raw text was:', result.candidates?.[0]?.content?.parts?.[0]?.text);
                alert('AI 分析成功但解析 JSON 失敗，請查看 Console');
            }

            console.log('Parsed AI Result:', aiJson);

            // Update Supabase
            const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
            const { error: updateError } = await supabase
                .from('items')
                .update({
                    status: 'available',
                    category: aiJson.category || 'Unknown',
                    tags: aiJson.tags || [],
                    ai_data: aiJson
                })
                .eq('id', recordId);

            if (updateError) {
                console.error('Supabase Update Error:', updateError);
                alert('AI 分析完成但寫入資料庫失敗: ' + updateError.message);
            } else {
                console.log('Database updated with AI data.');
                if (statusText) statusText.innerText = 'AI 分析完成！';

                // Refresh Grid
                fetchItems();
            }
        };
    } catch (error) {
        console.error('AI Analysis failed:', error);
        alert('AI 分析失敗: ' + error.message);
        if (statusText) statusText.innerText = 'AI 分析失敗';
    }
}

// Fetch and Display Items
async function fetchItems() {
    const supabaseUrl = localStorage.getItem(STORAGE_KEY_SUPABASE_URL);
    const supabaseKey = localStorage.getItem(STORAGE_KEY_SUPABASE_KEY);

    if (!supabaseUrl || !supabaseKey) return;

    const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);

    const { data, error } = await supabase
        .from('items')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50); // Increased limit for OOTD context

    if (error) {
        console.error('Fetch error:', error);
        return;
    }

    const grid = document.getElementById('recentGrid');
    if (!grid) return;

    grid.innerHTML = '';

    data.forEach(item => {
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
        grid.appendChild(div);
    });
}

// Core OOTD Logic
async function runOOTDGeneration(occasion, weather) {
    const geminiKey = localStorage.getItem(STORAGE_KEY_GEMINI) || DEFAULT_GEMINI_KEY;
    const supabaseUrl = localStorage.getItem(STORAGE_KEY_SUPABASE_URL);
    const supabaseKey = localStorage.getItem(STORAGE_KEY_SUPABASE_KEY);

    if (!supabaseUrl || !supabaseKey) throw new Error('Missing Supabase Config');

    // 1. Fetch Wardrobe Data
    const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
    const { data: items, error } = await supabase
        .from('items')
        .select('id, name, ai_data, image_path') // Need image_path for display
        .eq('status', 'available');

    if (error) throw new Error('Fetch items failed: ' + error.message);
    if (!items || items.length === 0) throw new Error('衣櫃是空的，請先上傳一些衣服！');

    // 2. Prepare JSON for AI
    const wardrobeJson = items.map(item => ({
        id: item.id,
        name: item.name,
        type: item.ai_data?.type || 'Unknown',
        color: item.ai_data?.color || 'Unknown',
        tags: item.ai_data?.tags || [],
        category: item.ai_data?.category || 'Unknown'
    }));

    // 3. Construct Prompt
    const prompt = `
    你是一位頂尖的時尚穿搭顧問。
    請根據以下的情境條件，以及使用者的衣櫃庫存，推薦一套最棒的 OOTD (Outfit of the Day)。

    ### 1. 今天的情境條件
    - 天氣狀況: ${weather}
    - 出席場合: ${occasion}

    ### 2. 衣櫃庫存 (Wardrobe)
    \`\`\`json
    ${JSON.stringify(wardrobeJson)}
    \`\`\`

    ### 3. 你的任務
    請從衣櫃中挑選適合的單品組合成一套穿搭。
    請考量天氣、場合與風格搭配。

    ### 4. 回傳格式規定 (CRITICAL)
    請 **只回傳一個 JSON 物件**，不要有其他廢話。
    格式如下：
    \`\`\`json
    {
      "title": "穿搭主題名稱",
      "reason": "為什麼這樣搭適合今天 (2-3句)",
      "itemIds": ["id1", "id2", ...],
      "notes": "穿搭小撇步"
    }
    \`\`\`
    `;

    // 4. Call Gemini
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${geminiKey}`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }]
        })
    });

    if (!response.ok) throw new Error('Gemini API Error');
    const result = await response.json();

    // 5. Parse Result
    let ootdData = {};
    try {
        const text = result.candidates[0].content.parts[0].text;
        const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
        ootdData = JSON.parse(cleanText);
    } catch (e) {
        console.error(e);
        throw new Error('AI 回傳格式錯誤，請重試');
    }

    // 6. Render Result
    renderOOTDResult(ootdData, items);
}

function renderOOTDResult(ootdData, allItems) {
    document.getElementById('ootdReason').innerText = ootdData.reason;
    document.getElementById('ootdNotes').innerText = ootdData.notes;

    const grid = document.getElementById('ootdItemsGrid');
    grid.innerHTML = '';

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
            grid.appendChild(div);
        }
    });
}
