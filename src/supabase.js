import { getSettings } from './config.js';

const getClient = () => {
    const { supabaseUrl, supabaseKey } = getSettings();
    if (!supabaseUrl || !supabaseKey) return null;
    return window.supabase.createClient(supabaseUrl, supabaseKey);
};

export async function uploadToSupabase(blob, originalName) {
    const supabase = getClient();
    if (!supabase) throw new Error('Supabase not configured');

    const timestamp = new Date().getTime();
    const cleanName = originalName.replace(/[^a-zA-Z0-9]/g, '_');
    const fileName = `${timestamp}_${cleanName}.webp`;

    const { error: uploadError } = await supabase.storage
        .from('wardrobe_images')
        .upload(fileName, blob, { cacheControl: '3600', upsert: false });

    if (uploadError) throw new Error('圖片上傳失敗: ' + uploadError.message);

    const { data: { publicUrl } } = supabase.storage
        .from('wardrobe_images')
        .getPublicUrl(fileName);

    const { data: insertData, error: dbError } = await supabase
        .from('items')
        .insert([{
            name: originalName.split('.')[0],
            image_path: publicUrl,
            status: 'processing',
            created_at: new Date().toISOString()
        }])
        .select();

    if (dbError) throw new Error('資料庫寫入失敗: ' + dbError.message);
    return insertData[0].id;
}

export async function updateItemAI(id, aiData) {
    const supabase = getClient();
    if (!supabase) return;

    const { error } = await supabase
        .from('items')
        .update({
            status: 'available',
            category: aiData.category || 'Unknown',
            tags: aiData.tags || [],
            ai_data: aiData
        })
        .eq('id', id);

    if (error) throw new Error(error.message);
}

export async function fetchItems() {
    const supabase = getClient();
    if (!supabase) return [];

    const { data, error } = await supabase
        .from('items')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50);

    if (error) {
        console.error('Fetch error:', error);
        return [];
    }
    return data;
}

export async function fetchAvailableItems() {
    const supabase = getClient();
    if (!supabase) return [];

    const { data, error } = await supabase
        .from('items')
        .select('id, name, ai_data, image_path')
        .eq('status', 'available');

    if (error) throw new Error('Fetch items failed: ' + error.message);
    return data;
}
