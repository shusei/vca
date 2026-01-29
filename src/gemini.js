import { getSettings } from './config.js';

export async function analyzeImage(blob) {
    const { geminiKey } = getSettings();
    if (!geminiKey) {
        console.warn('No Gemini Key found');
        return null;
    }

    const reader = new FileReader();
    return new Promise((resolve, reject) => {
        reader.readAsDataURL(blob);
        reader.onloadend = async () => {
            try {
                const base64data = reader.result.split(',')[1];
                const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${geminiKey}`;

                const prompt = `
                Analyze this clothing item image. Return a JSON object with these fields:
                - type: (e.g., T-Shirt, Dress, Jeans)
                - color: (Main color)
                - category: (Top, Bottom, Shoes, Accessory, One-Piece)
                - tags: (Array of style tags, e.g., Casual, Formal, Vintage)
                - description: (Short description)
                IMPORTANT: Output PURE JSON only.
                `;

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

                if (!response.ok) throw new Error(await response.text());
                const result = await response.json();

                const text = result.candidates[0].content.parts[0].text;
                const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
                resolve(JSON.parse(cleanText));
            } catch (e) {
                reject(e);
            }
        };
    });
}

export async function generateOOTD(occasion, weather, items) {
    const { geminiKey } = getSettings();
    if (!geminiKey) throw new Error('No Gemini Key');

    const wardrobeJson = items.map(item => ({
        id: item.id,
        name: item.name,
        type: item.ai_data?.type || 'Unknown',
        color: item.ai_data?.color || 'Unknown',
        tags: item.ai_data?.tags || [],
        category: item.ai_data?.category || 'Unknown'
    }));

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

    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${geminiKey}`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    });

    if (!response.ok) throw new Error('Gemini API Error');
    const result = await response.json();

    const text = result.candidates[0].content.parts[0].text;
    const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
    return JSON.parse(cleanText);
}
