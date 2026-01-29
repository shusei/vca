export const STORAGE_KEY_GEMINI = 'vca_gemini_key';
export const STORAGE_KEY_SUPABASE_URL = 'vca_supabase_url';
export const STORAGE_KEY_SUPABASE_KEY = 'vca_supabase_key';

export const DEFAULT_GEMINI_KEY = '';
export const DEFAULT_SUPABASE_URL = 'https://[YOUR-PROJECT-ID].supabase.co';

export const getSettings = () => ({
    geminiKey: localStorage.getItem(STORAGE_KEY_GEMINI) || DEFAULT_GEMINI_KEY,
    supabaseUrl: localStorage.getItem(STORAGE_KEY_SUPABASE_URL) || DEFAULT_SUPABASE_URL,
    supabaseKey: localStorage.getItem(STORAGE_KEY_SUPABASE_KEY)
});

export const saveSettings = (geminiKey, supabaseUrl, supabaseKey) => {
    if (geminiKey) localStorage.setItem(STORAGE_KEY_GEMINI, geminiKey);
    if (supabaseUrl) localStorage.setItem(STORAGE_KEY_SUPABASE_URL, supabaseUrl);
    if (supabaseKey) localStorage.setItem(STORAGE_KEY_SUPABASE_KEY, supabaseKey);
};
