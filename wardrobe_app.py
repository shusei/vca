import FreeSimpleGUI as sg
import json
import os
import datetime
import re
import io
import urllib.request
from typing import Optional, Dict, List, Any, Union

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# =============================================================================
# 設定與常數
# =============================================================================

PROFILE_FILE = 'user_profile.json'
WARDROBE_FILE = 'wardrobe.json'
OOTD_LOG_FILE = 'ootd_log.json'
IMAGE_DIR = 'images'

# Ensure image directory exists
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- Premium Theme Definition ---
THEME_NAME = 'LuxuryDark'
THEME_COLORS = {
    'BACKGROUND': '#121212',
    'TEXT': '#E0E0E0',
    'INPUT': '#2C2C2C',
    'TEXT_INPUT': '#FFFFFF',
    'SCROLL': '#2C2C2C',
    'BUTTON': ('#D4AF37', '#1E1E1E'), # Gold text on Black
    'PROGRESS': ('#00897B', '#1E1E1E'),
    'BORDER': 0,
    'SLIDER_DEPTH': 0,
    'PROGRESS_DEPTH': 0,
}

# Fonts - Windows Standard Premium
FONT_TITLE = ('Segoe UI', 24, 'bold')
FONT_HEADER = ('Segoe UI', 14, 'bold')
FONT_NORMAL = ('Segoe UI', 11)
FONT_SMALL = ('Segoe UI', 9)

# Helper for Card Style
def card_frame(title, layout, font=FONT_HEADER):
    return sg.Frame(title, layout, font=font, title_color='#D4AF37', 
                   background_color='#1E1E1E', pad=((0,0), (10, 10)), 
                   border_width=0, element_justification='left', expand_x=True)

# Try importing rembg
HAS_REMBG = False
try:
    from rembg import remove, new_session
    HAS_REMBG = True
except ImportError:
    pass

# Cache for rembg sessions
REMBG_SESSIONS = {}

def get_rembg_session(model_name):
    if not HAS_REMBG:
        return None
    if model_name not in REMBG_SESSIONS:
        try:
            print(f"Loading rembg model: {model_name}...")
            REMBG_SESSIONS[model_name] = new_session(model_name)
        except Exception as e:
            print(f"Error loading model {model_name}: {e}")
            return None
    return REMBG_SESSIONS.get(model_name)

def perform_background_removal_flow(img_path):
    """
    執行去背流程，包含預覽與模型切換
    """
    if not HAS_REMBG:
        return None

    current_model = 'u2net' # Default
    use_alpha = False # Default alpha matting setting
    alpha_erode = 10
    alpha_fg = 240
    alpha_bg = 10
    
    # 讀取原始圖片
    try:
        with open(img_path, 'rb') as i:
            input_data = i.read()
    except Exception as e:
        sg.popup_error(f'讀取圖片失敗: {e}')
        return None

    while True:
        sg.popup_quick_message(f'正在使用 {current_model} 模型去背中...\n(Alpha: {use_alpha}, Erode: {alpha_erode})', background_color='#1E1E1E', text_color='#D4AF37', font=FONT_HEADER)
        
        try:
            session = get_rembg_session(current_model)
            if not session:
                sg.popup_error(f'無法載入模型: {current_model}')
                return None
                
            output_data = remove(input_data, session=session, 
                               alpha_matting=use_alpha, 
                               alpha_matting_foreground_threshold=alpha_fg, 
                               alpha_matting_background_threshold=alpha_bg,
                               alpha_matting_erode_size=alpha_erode)
            
            # 暫存去背結果
            dir_name = os.path.dirname(img_path)
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            new_path = os.path.join(dir_name, f"{base_name}_nobg.png")
            
            with open(new_path, 'wb') as o:
                o.write(output_data)
                
            # --- 預覽視窗 ---
            orig_bytes = resize_image_to_bytes(img_path, (300, 300))
            nobg_bytes = resize_image_to_bytes(new_path, (300, 300))
            
            preview_layout = [
                [sg.Text(f'✨ 去背完成 (模型: {current_model})', font=FONT_HEADER, text_color='#D4AF37', background_color='#121212', justification='center')],
                [sg.Text('如果不滿意，請嘗試切換其他模型或調整參數', font=FONT_SMALL, text_color='#9E9E9E', background_color='#121212', justification='center')],
                [sg.Column([
                    [sg.Text('原始圖片 (點擊放大)', font=FONT_NORMAL, text_color='white', background_color='#121212')],
                    [sg.Image(data=orig_bytes, background_color='#2C2C2C', key='-PREVIEW-ORIG-', enable_events=True, tooltip='點擊放大')]
                ], background_color='#121212', element_justification='center'),
                 sg.Column([
                    [sg.Text('去背圖片 (點擊放大)', font=FONT_NORMAL, text_color='white', background_color='#121212')],
                    [sg.Image(data=nobg_bytes, background_color='#2C2C2C', key='-PREVIEW-NOBG-', enable_events=True, tooltip='點擊放大')]
                ], background_color='#121212', element_justification='center')],
                
                [sg.HorizontalSeparator(color='#424242')],
                [sg.Text('1. 選擇模型:', font=FONT_NORMAL, text_color='#E0E0E0', background_color='#121212')],
                [sg.Button('👤 人像模式 (Human)', key='-RETRY-HUMAN-', font=FONT_SMALL, button_color=('white', '#1565C0'), size=(18,1)),
                 sg.Button('🧥 通用模式 (General)', key='-RETRY-GENERAL-', font=FONT_SMALL, button_color=('white', '#424242'), size=(18,1)),
                 sg.Button('🔄 標準模式 (Default)', key='-RETRY-DEFAULT-', font=FONT_SMALL, button_color=('white', '#424242'), size=(18,1))],
                
                [sg.Text('2. 進階參數 (Alpha Matting):', font=FONT_NORMAL, text_color='#E0E0E0', background_color='#121212')],
                [sg.Checkbox('啟用精細邊緣 (Alpha Matting)', default=use_alpha, key='-USE-ALPHA-', font=FONT_SMALL, text_color='#FFB74D', background_color='#121212')],
                [sg.Text('侵蝕大小 (Erode Size):', size=(20,1), background_color='#121212', text_color='#B0BEC5'), 
                 sg.Slider(range=(0, 40), default_value=alpha_erode, orientation='h', size=(20, 10), key='-ALPHA-ERODE-', background_color='#121212', text_color='white')],
                [sg.Text('前景閾值 (FG Threshold):', size=(20,1), background_color='#121212', text_color='#B0BEC5'), 
                 sg.Slider(range=(0, 255), default_value=alpha_fg, orientation='h', size=(20, 10), key='-ALPHA-FG-', background_color='#121212', text_color='white')],
                [sg.Text('背景閾值 (BG Threshold):', size=(20,1), background_color='#121212', text_color='#B0BEC5'), 
                 sg.Slider(range=(0, 255), default_value=alpha_bg, orientation='h', size=(20, 10), key='-ALPHA-BG-', background_color='#121212', text_color='white')],
                [sg.Text('💡 提示: 若邊緣被切掉，試著減少侵蝕大小或降低前景閾值', font=FONT_SMALL, text_color='#757575', background_color='#121212')],

                [sg.HorizontalSeparator(color='#424242')],
                [sg.Button('✅ 使用此圖', key='-USE-NOBG-', font=FONT_HEADER, button_color=('white', '#00897B'), size=(15,1)),
                 sg.Button('↩️ 取消/用原圖', key='-USE-ORIG-', font=FONT_NORMAL, button_color=('white', '#D32F2F'), size=(15,1))]
            ]
            
            preview_win = sg.Window('去背預覽與調整', preview_layout, modal=True, background_color='#121212', finalize=True)
            
            # Bind events just in case
            preview_win['-PREVIEW-ORIG-'].bind('<Button-1>', '')
            preview_win['-PREVIEW-NOBG-'].bind('<Button-1>', '')
            
            while True:
                event_p, values_p = preview_win.read()
                
                if event_p in (sg.WIN_CLOSED, '-USE-ORIG-'):
                    preview_win.close()
                    return None
                
                if event_p == '-USE-NOBG-':
                    preview_win.close()
                    return new_path
                
                # Retry Logic
                if event_p in ('-RETRY-HUMAN-', '-RETRY-GENERAL-', '-RETRY-DEFAULT-'):
                    if event_p == '-RETRY-HUMAN-': current_model = 'u2net_human_seg'
                    elif event_p == '-RETRY-GENERAL-': current_model = 'isnet-general-use'
                    elif event_p == '-RETRY-DEFAULT-': current_model = 'u2net'
                    
                    # Update Alpha Settings
                    use_alpha = values_p['-USE-ALPHA-']
                    alpha_erode = int(values_p['-ALPHA-ERODE-'])
                    alpha_fg = int(values_p['-ALPHA-FG-'])
                    alpha_bg = int(values_p['-ALPHA-BG-'])
                    
                    preview_win.close()
                    break # Break inner loop to restart outer loop
                
                # Zoom Logic
                if event_p == '-PREVIEW-ORIG-' or (isinstance(event_p, str) and '-PREVIEW-ORIG-' in event_p):
                    large_bytes = resize_image_to_bytes(img_path, (800, 800))
                    if large_bytes:
                        sg.Window('檢視原始圖片', [[sg.Image(data=large_bytes)], [sg.Button('關閉')]], modal=True, background_color='#121212').read(close=True)
                
                if event_p == '-PREVIEW-NOBG-' or (isinstance(event_p, str) and '-PREVIEW-NOBG-' in event_p):
                    large_bytes = resize_image_to_bytes(new_path, (800, 800))
                    if large_bytes:
                        sg.Window('檢視去背圖片', [[sg.Image(data=large_bytes)], [sg.Button('關閉')]], modal=True, background_color='#121212').read(close=True)

        except Exception as e:
            sg.popup_error(f'去背失敗: {e}')
            return None

def remove_bg_silent(img_path):
    """
    靜默去背 (不顯示預覽視窗)，用於批次處理。
    回傳去背後的圖片路徑，若失敗則回傳 None。
    """
    if not HAS_REMBG:
        return None

    try:
        with open(img_path, 'rb') as i:
            input_data = i.read()
            
        session = get_rembg_session('u2net')
        if not session:
            return None
            
        output_data = remove(input_data, session=session)
        
        dir_name = os.path.dirname(img_path)
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        new_path = os.path.join(dir_name, f"{base_name}_nobg.png")
        
        with open(new_path, 'wb') as o:
            o.write(output_data)
            
        return new_path
    except Exception as e:
        print(f"Silent remove bg failed: {e}")
        return None

def call_ai_api(prompt, image_path=None, api_key=None):
    """
    呼叫 Google Gemini API 進行分析。
    """
    if not api_key:
        print("API Key is missing.")
        return None

    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        
        # 使用 gemini-flash-latest 模型
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        content = [prompt]
        
        if image_path:
            if not HAS_PIL:
                print("PIL not installed, cannot process image for Gemini.")
                return None
            
            try:
                img = Image.open(image_path)
                content.append(img)
            except Exception as e:
                print(f"Error opening image for Gemini: {e}")
                return None

        # 設定 generation config 以確保回傳 JSON
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )

        response = model.generate_content(
            content,
            generation_config=generation_config
        )
        
        return response.text
        
    except ImportError:
        print("google-generativeai module not found.")
        return None
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None



# =============================================================================
# 核心工具函式
# =============================================================================

def extract_json(raw_text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    從 GPT 回傳的文字中提取 JSON 物件或陣列。
    1. 優先嘗試直接解析 (若 raw_text 本身就是 JSON)。
    2. 嘗試抓取 ```json ... ``` 區塊 (支援 {} 與 [])。
    3. 嘗試抓取最外層的 {} 或 []。
    4. 若都失敗或解析錯誤，回傳 None。
    """
    if not raw_text:
        return None

    # 0. 嘗試直接解析
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # 1. 嘗試 Markdown Code Block
    # 支援 { ... } 或 [ ... ]
    code_block_pattern = r"```(?:json)?\s*(\{|\[)(.*?)(\}|\])\s*```"
    match = re.search(code_block_pattern, raw_text, re.DOTALL)
    
    json_str = ""
    if match:
        # 重組抓到的內容: group(1)是開頭, group(2)是內容, group(3)是結尾
        json_str = match.group(1) + match.group(2) + match.group(3)
    else:
        # 2. 嘗試尋找最外層的 {} 或 []
        # 找出第一個 { 或 [
        start_brace = raw_text.find('{')
        start_bracket = raw_text.find('[')
        
        start = -1
        end = -1
        is_array = False
        
        # 決定是物件還是陣列 (誰先出現)
        if start_brace != -1 and start_bracket != -1:
            if start_brace < start_bracket:
                start = start_brace
                is_array = False
            else:
                start = start_bracket
                is_array = True
        elif start_brace != -1:
            start = start_brace
            is_array = False
        elif start_bracket != -1:
            start = start_bracket
            is_array = True
            
        if start != -1:
            if is_array:
                end = raw_text.rfind(']')
            else:
                end = raw_text.rfind('}')
                
            if end != -1 and end > start:
                json_str = raw_text[start:end+1]
    
    if not json_str:
        return None

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print("JSON Decode Error in extract_json")
        return None

# =============================================================================
# 資料管理類別
# =============================================================================

class UserProfileManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.filepath):
            return self.default_profile()
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            sg.popup_error(f"讀取使用者資料失敗: {e}\n將使用預設值。")
            return self.default_profile()

    def save(self, data: Dict[str, Any]):
        self.data = data
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            sg.popup_error(f"儲存使用者資料失敗: {e}")
            return False

    def default_profile(self) -> Dict[str, Any]:
        return {
            "name": "使用者",
            "height_cm": 160,
            "weight_kg": 50,
            "gender_identity": "cis_female",
            "gender_expression": "feminine",
            "body_shape_notes": "",
            "measurements": {
                "shoulder_width_cm": 0,
                "bust_cm": 0,
                "underbust_cm": 0,
                "waist_cm": 0,
                "abdomen_cm": 0,
                "hip_cm": 0,
                "thigh_circ_cm": 0,
                "calf_circ_cm": 0,
                "ankle_circ_cm": 0
            },
            "style_preferences": [],
            "style_avoid": [],
            "workplace_rules": "",
            "climate_notes": ""
        }

class WardrobeManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.items = self.load()

    def load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"Warning: {self.filepath} content is not a list. Returning empty.")
                    return []
                return data
        except json.JSONDecodeError:
            print(f"Error: {self.filepath} is corrupted (JSON decode error). Returning empty list but NOT overwriting yet.")
            return []
        except Exception as e:
            sg.popup_error(f"讀取衣櫃資料失敗: {e}")
            return []

    def save(self):
        try:
            # Create a backup first
            if os.path.exists(self.filepath):
                backup_path = f"{self.filepath}.bak"
                try:
                    import shutil
                    shutil.copy2(self.filepath, backup_path)
                except Exception as e:
                    print(f"Warning: Failed to create backup: {e}")

            # Write to a temp file first
            temp_path = f"{self.filepath}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
            
            # Atomic rename (replace)
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            os.rename(temp_path, self.filepath)
            
            return True
        except Exception as e:
            sg.popup_error(f"儲存衣櫃資料失敗: {e}")
            return False

    def add_item(self, item: Dict[str, Any]):
        # 預設狀態為 'available' (在衣櫃中)
        if 'status' not in item:
            item['status'] = 'available'
        self.items.append(item)
        self.save()

    def set_status(self, item_id: str, status: str):
        """
        設定衣服狀態: available, laundry, lent, repair
        """
        for item in self.items:
            if item['id'] == item_id:
                item['status'] = status
                break
        self.save()

    def delete_item(self, item_id: str) -> bool:
        original_count = len(self.items)
        self.items = [item for item in self.items if item['id'] != item_id]
        if len(self.items) < original_count:
            self.save()
            return True
        return False

    def update_item(self, item_id: str, updates: Dict[str, Any]):
        for item in self.items:
            if item['id'] == item_id:
                item.update(updates)
                break
        self.save()

    def generate_id(self, item_type: str) -> str:
        # 簡單的 ID 產生邏輯: type_date_seq
        # 例如: coat_20251201_001
        today = datetime.datetime.now().strftime("%Y%m%d")
        prefix = f"{item_type}_{today}"
        
        # 找出當天同類型的最大序號
        max_seq = 0
        for item in self.items:
            if item['id'].startswith(prefix):
                try:
                    seq = int(item['id'].split('_')[-1])
                    if seq > max_seq:
                        max_seq = seq
                except:
                    pass
        
        return f"{prefix}_{max_seq + 1:03d}"

class OOTDLogManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.logs = self.load()

    def load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            sg.popup_error(f"儲存穿搭紀錄失敗: {e}")

    def add_log(self, log: Dict[str, Any]):
        self.logs.append(log)
        self.save()

class CurrencyManager:
    def __init__(self):
        self.base_currency = 'TWD'
        self.rates = {
            'TWD': 1.0,
            'USD': 32.5,
            'CNY': 4.5,
            'EUR': 35.0,
            'JPY': 0.22,
            'KRW': 0.024
        }
        self.last_updated = None
        self.update_rates()

    def update_rates(self):
        """嘗試從網路更新匯率 (使用 open.er-api.com)"""
        try:
            url = f"https://open.er-api.com/v6/latest/{self.base_currency}"
            with urllib.request.urlopen(url, timeout=3) as response:
                data = json.loads(response.read().decode())
                if data and 'rates' in data:
                    self.rates = data['rates']
                    self.last_updated = datetime.datetime.now()
                    # 確保常用貨幣存在 (API 回傳的 key 通常是大寫)
                    print("匯率更新成功！")
        except Exception as e:
            print(f"匯率更新失敗，使用預設值: {e}")

    def convert(self, amount: float, from_curr: str, to_curr: str = 'TWD') -> float:
        if from_curr == to_curr:
            return amount
        
        # 先轉成 Base (TWD) -> 其實 API 是以 TWD 為 Base 抓的，所以 rates[CURR] 代表 1 TWD = ? CURR
        # 等等，open.er-api.com/v6/latest/TWD 回傳的是 1 TWD 對換多少其他貨幣
        # 所以 1 USD = (1 / rates['USD']) TWD
        
        # 如果 rates 是以 TWD 為基準 (1 TWD = x Other)
        # Amount (Other) * (1/x) = Amount (TWD)
        
        try:
            rate_from = self.rates.get(from_curr, 1.0)
            rate_to = self.rates.get(to_curr, 1.0)
            
            # 轉換公式: Amount * (Rate_To / Rate_From) ???
            # 假設 Base 是 TWD. 
            # 1 TWD = 0.03 USD (rate_from)
            # 1 TWD = 1.0 TWD (rate_to)
            # 100 USD -> ? TWD
            # 100 USD / 0.03 = 3333 TWD
            
            # 正確邏輯:
            # Value in Base = Amount / Rate_From
            # Value in Target = Value in Base * Rate_To
            
            val_in_base = amount / rate_from
            return val_in_base * rate_to
            
        except Exception:
            return amount

# =============================================================================
# Prompt 產生器
# =============================================================================

def build_add_item_prompt(profile: Dict[str, Any], item_info: Dict[str, str]) -> str:
    """
    產生「新增衣服入庫」用的 Prompt。
    """
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    
    prompt = f"""
你是一位專業的個人造型師與服裝管理員。
我會提供你一位使用者的詳細身體數據與風格偏好 (JSON)，以及一件衣服的照片與基本資訊。

請你幫我分析這件衣服，並回傳一個符合規定格式的 JSON 資料，讓我存入衣櫃資料庫。

---
### 1. 使用者資料 (User Profile)
```json
{profile_json}
```

### 2. 衣服基本資訊
- 品名: {item_info.get('name', '')}
- 尺寸: {item_info.get('size', '')}
- 使用者備註: {item_info.get('notes', '')}
- (請參考附上的圖片)

---
### 3. 你的任務
請分析這件衣服的：
1. **基本屬性**：類型 (Type)、顏色 (Color)。
2. **風格標籤 (Style Tags)**：例如「溫柔」、「俐落」、「可愛」等，請給 3-5 個。
3. **適合季節 (Seasons)**：春、夏、秋、冬。
4. **適合場合 (Occasions)**：上班、約會、休閒、正式等。
5. **衣長描述 (Length Desc)**：根據使用者的身高 ({profile.get('height_cm', '未知')}cm)，預估這件衣服穿起來會到哪裡（例如：膝上 5 公分、蓋住腳踝等）。
6. **修飾效果 (Body Effect)**：根據使用者的身形特徵（{profile.get('body_shape_notes', '')}），分析這件衣服的修飾或顯胖風險。
7. **穿搭建議 (Notes)**：簡單一句話建議如何搭配。

---
### 4. 回傳格式規定 (CRITICAL)
請 **只回傳一個 JSON 物件**，不要有任何開場白或結尾文字。

**重要提示：**
如果使用者**沒有上傳圖片**，請回傳以下 JSON，提醒使用者上傳圖片：
```json
{{
  "ok": false,
  "message": "⚠️ 請記得上傳衣服的照片，我才能幫您分析喔！",
  "data": {{}}
}}
```

如果圖片已上傳，請分析並回傳以下 JSON 結構：

```json
{{
  "ok": true,
  "message": "給使用者的簡短建議或鼓勵",
  "data": {{
    "type": "衣服類型 (如: 外套, 洋裝, 襯衫)",
    "color": "主色系",
    "styleTags": ["標籤1", "標籤2", ...],
    "seasons": ["季節1", ...],
    "occasions": ["場合1", ...],
    "lengthDesc": "長度描述...",
    "bodyEffect": "修飾效果分析...",
    "notes": "搭配建議..."
  }}
}}
```
"""
    return prompt.strip()

def resize_image_to_bytes(image_path: str, size: tuple) -> Optional[bytes]:
    """
    讀取圖片並縮放，回傳 PNG bytes 給 sg.Image 使用。
    如果沒有安裝 Pillow 或讀取失敗，回傳 None。
    """
    if not HAS_PIL:
        return None
    
    try:
        if not os.path.exists(image_path):
            return None
            
        img = Image.open(image_path)
        img.thumbnail(size)
        
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        return bio.getvalue()
    except Exception as e:
        print(f"Image resize error: {e}")
        return None

def get_category(item_type: str) -> str:
    """
    根據 AI 回傳的 type 判斷大分類
    """
    t = item_type.lower()
    if any(x in t for x in ['褲', '裙', 'bottom', 'skirt', 'pants', 'jeans']): return '下身'
    if any(x in t for x in ['洋裝', '連身', 'dress']): return '洋裝'
    if any(x in t for x in ['外套', '大衣', '夾克', '西裝', '風衣', 'coat', 'jacket', 'blazer']): return '外套'
    if any(x in t for x in ['鞋', '靴', 'shoe', 'boot', 'sneaker', 'sandal', 'heel']): return '鞋靴'
    if any(x in t for x in ['包', '帽', '巾', '飾', '鍊', '環', '帶', '鏡', '錶', 
                            'bag', 'hat', 'scarf', 'accessory', 'necklace', 'earring', 'ring', 'belt', 'glasses', 'watch']): return '配件'
    if any(x in t for x in ['內衣', '胸罩', '內褲', 'bra', 'underwear', 'lingerie', 'panties', 'briefs', 'boxers']): return '內著'
    if any(x in t for x in ['上衣', 't-shirt', 'shirt', 'blouse', 'top', 'polo', 'vest', 'sweater', 'hoodie']): return '上身'
    # Fallback: 若不在上述規則中，直接使用 AI 回傳的類型 (首字大寫)
    return item_type.title() if item_type else '未分類'

def get_unique_categories(items: List[Dict[str, Any]]) -> List[str]:
    """
    取得目前衣櫃中所有出現過的分類，並排序
    """
    categories = set()
    for item in items:
        item_type = item.get('ai', {}).get('type', '')
        categories.add(get_category(item_type))
    
    # 確保基本分類存在 (可選)
    # categories.update(['上身', '下身', '洋裝', '外套', '鞋靴', '配件', '內著'])
    
    sorted_cats = sorted(list(categories))
    return ['全部'] + sorted_cats

def build_ootd_prompt(profile: Dict[str, Any], wardrobe_items: List[Dict[str, Any]], context: Dict[str, str]) -> str:
    """
    產生「OOTD 穿搭建議」用的 Prompt。
    """
    # 簡化衣櫃資料，減少 Token 消耗
    # 只包含狀態為 'available' 的衣服
    simple_wardrobe = []
    for item in wardrobe_items:
        # 過濾掉不在衣櫃的衣服
        if item.get('status', 'available') != 'available':
            continue
            
        ai_data = item.get('ai', {})
        simple_wardrobe.append({
            "id": item.get('id'),
            "name": item.get('name'),
            "type": ai_data.get('type'),
            "color": ai_data.get('color'),
            "styleTags": ai_data.get('styleTags'),
            "seasons": ai_data.get('seasons'),
            "occasions": ai_data.get('occasions')
        })
    
    wardrobe_json = json.dumps(simple_wardrobe, ensure_ascii=False, indent=2)
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)

    prompt = f"""
你是一位頂尖的時尚穿搭顧問。
請根據使用者的個人資料、今天的需求條件，以及她的衣櫃庫存，推薦一套最棒的 OOTD (Outfit of the Day)。

---
### 1. 使用者資料
```json
{profile_json}
```

### 2. 今天的情境條件
- 天氣狀況: {context.get('weather', '')}
- 出席場合: {context.get('occasion', '')}
- 今天心情/目標: {context.get('mood', '')}

### 3. 衣櫃庫存 (Wardrobe)
```json
{wardrobe_json}
```

---
### 4. 你的任務
請從衣櫃中挑選適合的單品組合成一套穿搭。
請考量：
1. 天氣是否合適。
2. 場合是否得體。
3. 是否符合使用者的身形修飾需求與今天的心情。

---
### 5. 回傳格式規定 (CRITICAL)
請 **只回傳一個 JSON 物件**，不要有其他廢話。
格式如下：

```json
{{
  "ok": true,
  "message": "給使用者的鼓勵",
  "outfits": [
    {{
      "title": "穿搭主題名稱",
      "reason": "為什麼這樣搭適合今天 (2-3句)",
      "itemIds": ["id1", "id2", ...],
      "notes": "穿搭小撇步 (例如: 捲起袖子, 搭配銀色耳環)"
    }}
  ]
}}
```
"""
    return prompt.strip()

def export_ootd_zip(outfit: Dict[str, Any], wardrobe_mgr: WardrobeManager, profile_mgr: UserProfileManager):
    """
    將 OOTD 結果匯出為 ZIP 檔
    包含:
    1. 全身照 (user_body.png)
    2. 單品圖片 (item_id.png)
    3. 穿搭資訊 (info.txt)
    """
    save_path = sg.popup_get_file('匯出 OOTD', save_as=True, file_types=(('ZIP Files', '*.zip'),), default_extension='.zip')
    if not save_path:
        return

    # 檢查是否有全身照
    body_photo_path = profile_mgr.data.get('body_photo_path')
    if not body_photo_path or not os.path.exists(body_photo_path):
        sg.popup_error('無法匯出：請先至「個人資料」分頁上傳全身照！\n這是生成試穿圖的必要條件。')
        return

    import tempfile
    import shutil
    import zipfile

    try:
        # 建立暫存資料夾
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 複製全身照
            body_photo_path = profile_mgr.data.get('body_photo_path')
            if body_photo_path and os.path.exists(body_photo_path):
                ext = os.path.splitext(body_photo_path)[1]
                shutil.copy2(body_photo_path, os.path.join(temp_dir, f"body{ext}"))

            # 2. 複製單品圖片
            item_ids = outfit.get('itemIds', [])
            item_names = []
            for i, iid in enumerate(item_ids):
                item = next((x for x in wardrobe_mgr.items if x['id'] == iid), None)
                if item:
                    item_names.append(f"{i+1}. {item['name']}")
                    if item.get('image_path') and os.path.exists(item['image_path']):
                        ext = os.path.splitext(item['image_path'])[1]
                        # 檔名: 1_單品名稱.png (避免檔名衝突與亂碼，可考慮用 ID)
                        safe_name = "".join([c for c in item['name'] if c.isalnum() or c in ('-', '_')])
                        shutil.copy2(item['image_path'], os.path.join(temp_dir, f"{i+1}_{safe_name}{ext}"))

            # 3. 建立資訊文字檔
            info_content = f"""
OOTD 穿搭建議
================================
標題: {outfit.get('title', '無標題')}
日期: {datetime.datetime.now().strftime('%Y-%m-%d')}

推薦理由:
{outfit.get('reason', '')}

穿搭筆記:
{outfit.get('notes', '')}

單品清單:
{chr(10).join(item_names)}
"""
            with open(os.path.join(temp_dir, 'ootd_info.txt'), 'w', encoding='utf-8') as f:
                f.write(info_content.strip())

            # 4. 建立 Virtual Try-On Prompt (prompt.txt)
            prompt_content = "Please generate a high-quality, realistic image of the person in 'body.png' wearing the following items:\n\n"
            
            for i, iid in enumerate(item_ids):
                item = next((x for x in wardrobe_mgr.items if x['id'] == iid), None)
                if item:
                    safe_name = "".join([c for c in item['name'] if c.isalnum() or c in ('-', '_')])
                    ext = os.path.splitext(item.get('image_path', ''))[1]
                    if not ext: ext = '.png'
                    filename = f"{i+1}_{safe_name}{ext}"
                    
                    ai_data = item.get('ai', {})
                    item_name = item.get('name', 'Unknown Item')
                    prompt_content += f"{i+1}. {item_name} (Type: {ai_data.get('type', 'Unknown')}, Color: {ai_data.get('color', 'Unknown')}) - Image: {filename}\n"
                else:
                    prompt_content += f"{i+1}. [Missing Item Data] (ID: {iid}) - Image: N/A\n"
            
            prompt_content += "\nTarget: A full-body shot of the person wearing these items. Maintain the person's original pose, body shape, and facial features.\n"
            prompt_content += "Important: Ensure the ENTIRE body is visible from HEAD to TOE. Do not crop the feet or shoes.\n"
            prompt_content += "Style: Photorealistic, High Definition."
            
            # Debug: Check item count
            print(f"Exporting OOTD: {len(item_ids)} items in list.")
            
            with open(os.path.join(temp_dir, 'prompt.txt'), 'w', encoding='utf-8') as f:
                f.write(prompt_content)

            # 5. 壓縮 (使用 zipfile 直接控制，避免 shutil 自動加副檔名問題)
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            sg.popup(f'匯出成功！\n檔案已儲存至: {save_path}\n包含 prompt.txt 供 AI 試穿使用。')

    except Exception as e:
        sg.popup_error(f'匯出失敗: {e}')

# =============================================================================
# GUI 介面
# =============================================================================

def make_profile_window(profile_mgr: UserProfileManager):
    """
    建立「編輯個人資料」視窗
    """
    p = profile_mgr.data
    m = p.get('measurements', {})
    # Helper to join list to string
    def list_to_str(l): return ", ".join(l) if isinstance(l, list) else str(l)

    # 準備全身照預覽
    body_photo_path = p.get('body_photo_path')
    body_img_data = None
    if body_photo_path and os.path.exists(body_photo_path):
        body_img_data = resize_image_to_bytes(body_photo_path, (200, 300))

    layout = [
        [sg.Text('基本資料', font=FONT_TITLE, pad=((0,0), (10, 20)))],
        
        [sg.Column([
            [sg.Frame(' 👤 個人資訊 ', [
                [sg.Text('暱稱:', size=(10,1), font=FONT_NORMAL), sg.Input(p.get('name', ''), key='name', font=FONT_NORMAL)],
                [sg.Text('身高 (cm):', size=(10,1), font=FONT_NORMAL), sg.Input(p.get('height_cm', ''), key='height_cm', size=(10,1), font=FONT_NORMAL),
                 sg.Text('體重 (kg):', size=(10,1), font=FONT_NORMAL), sg.Input(p.get('weight_kg', ''), key='weight_kg', size=(10,1), font=FONT_NORMAL)],
                [sg.Text('性別認同:', size=(10,1), font=FONT_NORMAL), sg.Combo(['cis_female', 'cis_male', 'trans_female', 'nonbinary', 'other'], default_value=p.get('gender_identity', ''), key='gender_identity', font=FONT_NORMAL)],
                [sg.Text('性別氣質:', size=(10,1), font=FONT_NORMAL), sg.Combo(['feminine', 'neutral', 'masculine', 'mixed'], default_value=p.get('gender_expression', ''), key='gender_expression', font=FONT_NORMAL)]
            ], font=FONT_HEADER, title_color='#E0E0E0', pad=((0,0), (0, 10)))],
            
            [sg.Frame(' 📏 身體圍度 (cm) ', [
                [sg.Text('肩寬:', size=(6,1), font=FONT_NORMAL), sg.Input(m.get('shoulder_width_cm', ''), key='m_shoulder', size=(6,1), font=FONT_NORMAL),
                 sg.Text('胸圍:', size=(6,1), font=FONT_NORMAL), sg.Input(m.get('bust_cm', ''), key='m_bust', size=(6,1), font=FONT_NORMAL),
                 sg.Text('下胸圍:', size=(6,1), font=FONT_NORMAL), sg.Input(m.get('underbust_cm', ''), key='m_underbust', size=(6,1), font=FONT_NORMAL)],
                [sg.Text('腰圍:', size=(6,1), font=FONT_NORMAL), sg.Input(m.get('waist_cm', ''), key='m_waist', size=(6,1), font=FONT_NORMAL),
                 sg.Text('腹圍:', size=(6,1), font=FONT_NORMAL), sg.Input(m.get('abdomen_cm', ''), key='m_abdomen', size=(6,1), font=FONT_NORMAL),
                 sg.Text('臀圍:', size=(6,1), font=FONT_NORMAL), sg.Input(m.get('hip_cm', ''), key='m_hip', size=(6,1), font=FONT_NORMAL)]
            ], font=FONT_HEADER, title_color='#E0E0E0', pad=((0,0), (0, 10)))],
            
            [sg.Frame(' 🎨 風格與偏好 ', [
                [sg.Text('身形特徵備註:', font=FONT_NORMAL)],
                [sg.Multiline(p.get('body_shape_notes', ''), key='body_shape_notes', size=(60, 3), font=FONT_NORMAL)],
                [sg.Text('喜歡的風格:', font=FONT_NORMAL)],
                [sg.Input(list_to_str(p.get('style_preferences', [])), key='style_preferences', size=(60,1), font=FONT_NORMAL)],
                [sg.Text('避免的風格:', font=FONT_NORMAL)],
                [sg.Input(list_to_str(p.get('style_avoid', [])), key='style_avoid', size=(60,1), font=FONT_NORMAL)]
            ], font=FONT_HEADER, title_color='#E0E0E0', pad=((0,0), (0, 20)))]
        ]), sg.Column([
            [sg.Frame(' 📸 全身照 ', [
                [sg.Image(data=body_img_data, key='-BODY-IMG-', size=(200, 300), background_color='#333333', visible=bool(body_img_data)),
                 sg.Text('尚未上傳全身照', size=(20, 10), justification='center', key='-BODY-TXT-', visible=not bool(body_img_data))],
                [sg.Button('上傳全身照', key='-UPLOAD-BODY-', font=FONT_NORMAL, size=(15,1), pad=((0,0), (10,0)))]
            ], font=FONT_HEADER, title_color='#E0E0E0', element_justification='center')]
        ], vertical_alignment='top', pad=((20,0), (0,0)))],
        
        [sg.Push(), sg.Button('儲存', key='-SAVE-', font=FONT_HEADER, size=(10,1), button_color=('white', '#00796B')), 
         sg.Button('取消', key='-CANCEL-', font=FONT_HEADER, size=(10,1)), sg.Push()]
    ]
    
    window = sg.Window('編輯個人資料', layout, modal=True)
    
    new_body_photo_path = body_photo_path # 暫存新上傳的路徑

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, '-CANCEL-'):
            break
        
        if event == '-UPLOAD-BODY-':
            file_path = sg.popup_get_file('選擇全身照', file_types=(('Images', '*.png;*.jpg;*.jpeg'),))
            if file_path:
                # 顯示預覽
                data = resize_image_to_bytes(file_path, (200, 300))
                if data:
                    window['-BODY-IMG-'].update(data=data, visible=True)
                    window['-BODY-TXT-'].update(visible=False)
                    new_body_photo_path = file_path # 標記待存
        
        if event == '-SAVE-':
            # 更新資料
            try:
                new_data = p.copy()
                new_data['name'] = values['name']
                new_data['height_cm'] = float(values['height_cm']) if values['height_cm'] else 0
                new_data['weight_kg'] = float(values['weight_kg']) if values['weight_kg'] else 0
                new_data['gender_identity'] = values['gender_identity']
                new_data['gender_expression'] = values['gender_expression']
                new_data['body_shape_notes'] = values['body_shape_notes']
                
                # 處理 List
                new_data['style_preferences'] = [x.strip() for x in values['style_preferences'].split(',') if x.strip()]
                new_data['style_avoid'] = [x.strip() for x in values['style_avoid'].split(',') if x.strip()]
                
                # 處理 Measurements
                new_m = new_data.get('measurements', {})
                new_m['shoulder_width_cm'] = float(values['m_shoulder']) if values['m_shoulder'] else 0
                new_m['bust_cm'] = float(values['m_bust']) if values['m_bust'] else 0
                new_m['underbust_cm'] = float(values['m_underbust']) if values['m_underbust'] else 0
                new_m['waist_cm'] = float(values['m_waist']) if values['m_waist'] else 0
                new_m['abdomen_cm'] = float(values['m_abdomen']) if values['m_abdomen'] else 0
                new_m['hip_cm'] = float(values['m_hip']) if values['m_hip'] else 0
                
                # 處理全身照存檔
                if new_body_photo_path and new_body_photo_path != body_photo_path:
                    try:
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        abs_image_dir = os.path.join(script_dir, IMAGE_DIR)
                        if not os.path.exists(abs_image_dir):
                            os.makedirs(abs_image_dir)
                            
                        ext = os.path.splitext(new_body_photo_path)[1]
                        if not ext: ext = '.png'
                        
                        target_path = os.path.join(abs_image_dir, f"user_body{ext}")
                        
                        import shutil
                        shutil.copy2(new_body_photo_path, target_path)
                        new_data['body_photo_path'] = target_path
                    except Exception as e:
                        sg.popup_error(f"全身照儲存失敗: {e}")
                
                if profile_mgr.save(new_data):
                    sg.popup('個人資料已更新！')
                    break
            except ValueError:
                sg.popup_error('請輸入正確的數字格式 (身高、體重、圍度)！')
    
    window.close()

def show_ootd_result_window(outfit: Dict[str, Any], wardrobe_mgr: WardrobeManager, profile_mgr: UserProfileManager = None):
    """
    顯示華麗的 OOTD 結果視窗，包含圖片與放大功能
    """
    # 準備單品資料與圖片
    item_ids = outfit.get('itemIds', [])
    items_ui = []
    
    for iid in item_ids:
        item = next((x for x in wardrobe_mgr.items if x['id'] == iid), None)
        if item:
            # 圖片處理
            img_data = None
            if HAS_PIL and item.get('image_path') and os.path.exists(item['image_path']):
                img_data = resize_image_to_bytes(item['image_path'], (200, 200)) # 加大縮圖
            
            # 單品卡片 Layout
            # 使用 Column 模擬卡片
            # 注意: sg.Image 的 enable_events=True 有時在 Column 內會被吃掉，改用 bind
            img_key = f'-IMG-{iid}-'
            img_elem = sg.Image(data=img_data, size=(200, 200), background_color='#2C2C2C', key=img_key, enable_events=True, tooltip='點擊放大') if img_data else sg.Text('無圖片', size=(20,10), justification='center', background_color='#2C2C2C')
            
            card_col = sg.Column([
                [img_elem],
                [sg.Text(item['name'], size=(20, 1), justification='center', font=('Segoe UI', 11, 'bold'), background_color='#1E1E1E', text_color='#D4AF37')],
                [sg.Text(item.get('ai', {}).get('type', ''), size=(20, 1), justification='center', font=FONT_SMALL, background_color='#1E1E1E', text_color='#9E9E9E')]
            ], background_color='#1E1E1E', pad=(10, 10), element_justification='center')
            
            items_ui.append(card_col)
    
    # 如果沒有單品 (或是 ID 對不上)，顯示提示
    if not items_ui:
        items_ui = [sg.Text('找不到對應的單品資料 (可能是建議購買的新品)', text_color='#E0E0E0', background_color='#1E1E1E', font=FONT_NORMAL)]
    
    # 版面配置: 標題區 + 單品展示區 (水平捲動) + 說明區
    # 使用 Scrollable Column 包覆整個內容，避免螢幕太小被切掉
    main_content = [
        [sg.Text('✨ 今日穿搭推薦 ✨', font=('Segoe UI', 28, 'bold'), text_color='#D4AF37', background_color='#121212', justification='center', expand_x=True, pad=((0,0), (20, 10)))],
        [sg.Text(outfit.get('title', '無標題'), font=('Segoe UI', 20, 'bold'), text_color='#FFFFFF', background_color='#121212', justification='center', expand_x=True, pad=((0,0), (0, 20)))],
        [sg.HorizontalSeparator(color='#D4AF37')],
        
        # 單品展示區 (用 Scrollable Column) - 加大高度
        [sg.Column([items_ui], scrollable=True, vertical_scroll_only=False, size=(900, 280), background_color='#121212', pad=((0,0), (20, 20)))],
        
        # 說明區 - 加大高度與字體
        [card_frame(' 💡 推薦理由 ', [[sg.Multiline(outfit.get('reason', ''), size=(90, 5), font=('Segoe UI', 12), disabled=True, background_color='#1E1E1E', text_color='#E0E0E0', border_width=0)]])],
        [card_frame(' 📝 穿搭筆記 ', [[sg.Multiline(outfit.get('notes', ''), size=(90, 4), font=('Segoe UI', 12), disabled=True, background_color='#1E1E1E', text_color='#E0E0E0', border_width=0)]])],
        
        [sg.Button('📦 匯出 ZIP', key='-EXPORT-ZIP-', font=FONT_HEADER, size=(15,1), button_color=('white', '#1565C0'), border_width=0, pad=((0,0), (20, 20))),
         sg.Button('關閉', key='-CLOSE-', font=FONT_HEADER, size=(15,1), button_color=('white', '#424242'), border_width=0, pad=((10,0), (20, 20)))]
    ]

    layout = [[sg.Column(main_content, scrollable=True, vertical_scroll_only=True, size=(980, 550), background_color='#121212')]]
    
    # 加大視窗預設大小，並允許調整
    # 改為 600 高度以適應較小螢幕
    win = sg.Window('OOTD Result', layout, modal=True, background_color='#121212', finalize=True, resizable=True, size=(1000, 600))
    
    # 強制綁定點擊事件 (Double check)
    for iid in item_ids:
        if win[f'-IMG-{iid}-']:
            win[f'-IMG-{iid}-'].bind('<Button-1>', '')

    while True:
        event, values = win.read()
        if event in (sg.WIN_CLOSED, '-CLOSE-'):
            break
            
        if event == '-EXPORT-ZIP-':
            if profile_mgr:
                export_ootd_zip(outfit, wardrobe_mgr, profile_mgr)
            else:
                sg.popup_error('無法匯出：缺少 Profile Manager 參照。') 
            
        # 處理圖片點擊放大
        # 檢查 event 是否包含 key (因為 bind 之後 event 可能會變)
        if isinstance(event, str) and '-IMG-' in event:
             # event format: -IMG-{iid}- or -IMG-{iid}-+CLICK+
            try:
                # 簡單 parsing
                parts = event.split('-')
                # parts: ['', 'IMG', 'id', ''] or similar
                if len(parts) >= 3:
                    iid = parts[2]
                    
                    # 找出圖片路徑
                    item = next((x for x in wardrobe_mgr.items if x['id'] == iid), None)
                    if item and item.get('image_path') and os.path.exists(item['image_path']):
                        large_bytes = resize_image_to_bytes(item['image_path'], (800, 800))
                        if large_bytes:
                            sg.Window(f"檢視單品: {item['name']}", 
                                      [[sg.Image(data=large_bytes)], [sg.Button('關閉')]], 
                                      modal=True, background_color='#121212').read(close=True)
            except:
                pass
    
    win.close()

def process_batch_import(folder_path, wardrobe_mgr, profile_mgr, progress_window, api_key):
    """
    批次匯入處理邏輯
    """
    valid_exts = ('.jpg', '.jpeg', '.png')
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_exts) and '_nobg' not in f]
    total = len(files)
    success_count = 0
    
    for i, filename in enumerate(files):
        if progress_window.was_closed():
            break
            
        img_path = os.path.join(folder_path, filename)
        progress_window['-PROG-BAR-'].update(current_count=i+1, max=total)
        progress_window['-PROG-TXT-'].update(f'正在處理 ({i+1}/{total}): {filename}')
        progress_window.refresh()
        
        # 1. 去背
        nobg_path = remove_bg_silent(img_path)
        final_img_path = nobg_path if nobg_path else img_path
        
        # 2. AI 分析
        # 為了省錢/省時，這裡可以簡化 prompt 或只傳圖片
        item_info = {'name': os.path.splitext(filename)[0], 'size': 'F', 'notes': 'Batch Import'}
        prompt = build_add_item_prompt(profile_mgr.data, item_info)
        
        # 呼叫 API (若無 key 則用 Mock)
        json_resp = call_ai_api(prompt, final_img_path, api_key)
        
        if json_resp:
            parsed = extract_json(json_resp)
            if parsed and 'data' in parsed:
                ai_data = parsed['data']
                new_id = wardrobe_mgr.generate_id(ai_data.get('type', 'unknown'))
                
                # 複製圖片到 images/
                try:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    abs_image_dir = os.path.join(script_dir, IMAGE_DIR)
                    ext = os.path.splitext(final_img_path)[1]
                    safe_id = "".join([c for c in new_id if c.isalnum() or c in ('-', '_')])
                    saved_img_path = os.path.join(abs_image_dir, f"{safe_id}{ext}")
                    
                    import shutil
                    shutil.copy2(final_img_path, saved_img_path)
                    
                    new_item = {
                        "id": new_id,
                        "name": item_info['name'],
                        "size": item_info['size'],
                        "price": 0,
                        "currency": "TWD",
                        "wear_count": 0,
                        "image_path": saved_img_path,
                        "user_notes": item_info['notes'],
                        "status": "available",
                        "purchase_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "ai": ai_data
                    }
                    wardrobe_mgr.add_item(new_item)
                    success_count += 1
                except Exception as e:
                    print(f"Save error: {e}")
                    
    return success_count

def build_batch_prompt(filenames: List[str], profile: Dict[str, Any]) -> str:
    """
    產生批次分析用的 Prompt。
    """
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    files_str = "\n".join([f"- {f}" for f in filenames])
    
    prompt = f"""
你是一位專業的個人造型師。
我將上傳 {len(filenames)} 張衣服的照片。請幫我一次分析這些衣服，並回傳一個 JSON Array。

---
### 1. 使用者資料
```json
{profile_json}
```

### 2. 待分析圖片清單
{files_str}

---
### 3. 回傳格式規定 (CRITICAL)
請 **只回傳一個 JSON Array**，不要有任何開場白。
每個物件必須包含 `filename` 欄位，且 **必須嚴格對應上述清單中的檔名**。

**重要：請務必確認圖片內容與檔名的對應關係，切勿張冠李戴！**

```json
[
  {{
    "filename": "圖片檔名 (必須與清單完全一致)",
    "data": {{
      "type": "衣服類型",
      "color": "主色系",
      "styleTags": ["標籤1", "標籤2"],
      "seasons": ["季節"],
      "occasions": ["場合"],
      "lengthDesc": "長度描述",
      "bodyEffect": "修飾效果",
      "notes": "搭配建議"
    }}
  }},
  ...
]
```
"""
    return prompt.strip()

def process_offline_batch(json_text: str, folder_path: str, wardrobe_mgr: WardrobeManager) -> int:
    """
    處理離線批次匯入的 JSON 回應。
    """
    try:
        # 嘗試解析 JSON
        # 有時候 GPT 會把 JSON 包在 markdown block 裡
        parsed = extract_json(json_text)
        
        # 如果 extract_json 回傳的是 dict (例如包在 {"items": [...]})，嘗試找 list
        items_data = []
        if isinstance(parsed, list):
            items_data = parsed
        elif isinstance(parsed, dict):
            # 嘗試找常見的 key
            for k in ['items', 'data', 'list']:
                if k in parsed and isinstance(parsed[k], list):
                    items_data = parsed[k]
                    break
        
        if not items_data:
            print("No list found in JSON")
            return 0
            
        success_count = 0
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_image_dir = os.path.join(script_dir, IMAGE_DIR)
        
        for item in items_data:
            filename = item.get('filename')
            ai_data = item.get('data')
            
            if not filename or not ai_data:
                continue
                
            # 尋找對應的圖片 (包含去背後的)
            # 優先找 _nobg 版本，如果沒有則找原檔
            # 但這裡假設 filename 是使用者上傳給 GPT 的檔名 (通常是去背後的)
            
            # 嘗試在 folder_path 找檔案
            source_path = os.path.join(folder_path, filename)
            
            # Robust File Matching Logic
            if not os.path.exists(source_path):
                # 1. 嘗試更換副檔名 (GPT 可能會把 .png 寫成 .jpg)
                base, ext = os.path.splitext(filename)
                alt_exts = ['.png', '.jpg', '.jpeg']
                found = False
                for alt in alt_exts:
                    if alt == ext: continue
                    alt_path = os.path.join(folder_path, base + alt)
                    if os.path.exists(alt_path):
                        source_path = alt_path
                        filename = base + alt # Update filename for later use
                        found = True
                        break
                
                if not found:
                    # 2. 嘗試拿掉或加上 _nobg
                    if '_nobg' in base:
                        # 嘗試拿掉 _nobg
                        clean_base = base.replace('_nobg', '')
                        for alt in alt_exts:
                            alt_path = os.path.join(folder_path, clean_base + alt)
                            if os.path.exists(alt_path):
                                source_path = alt_path
                                filename = clean_base + alt
                                found = True
                                break
                    else:
                        # 嘗試加上 _nobg
                        nobg_base = base + '_nobg'
                        for alt in alt_exts:
                            alt_path = os.path.join(folder_path, nobg_base + alt)
                            if os.path.exists(alt_path):
                                source_path = alt_path
                                filename = nobg_base + alt
                                found = True
                                break
                                
                if not found:
                    print(f"File not found: {source_path} (and alternatives)")
                    continue
                
            # 產生 ID 與存檔
            new_id = wardrobe_mgr.generate_id(ai_data.get('type', 'unknown'))
            ext = os.path.splitext(filename)[1]
            safe_id = "".join([c for c in new_id if c.isalnum() or c in ('-', '_')])
            saved_img_path = os.path.join(abs_image_dir, f"{safe_id}{ext}")
            
            try:
                import shutil
                shutil.copy2(source_path, saved_img_path)
                
                new_item = {
                    "id": new_id,
                    "name": os.path.splitext(filename)[0].replace('_nobg', ''),
                    "size": "F",
                    "price": 0,
                    "currency": "TWD",
                    "wear_count": 0,
                    "image_path": saved_img_path,
                    "user_notes": "Offline Batch Import",
                    "status": "available",
                    "purchase_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "ai": ai_data
                }
                wardrobe_mgr.add_item(new_item)
                success_count += 1
            except Exception as e:
                print(f"Save error for {filename}: {e}")
                
        return success_count
        
    except Exception as e:
        print(f"Process offline batch error: {e}")
        return 0

def main():
    # Register Custom Theme
    sg.LOOK_AND_FEEL_TABLE[THEME_NAME] = THEME_COLORS
    sg.theme(THEME_NAME)
    
    # 初始化 Managers
    profile_mgr = UserProfileManager(PROFILE_FILE)
    wardrobe_mgr = WardrobeManager(WARDROBE_FILE)
    ootd_mgr = OOTDLogManager(OOTD_LOG_FILE)
    currency_mgr = CurrencyManager()
    is_batch_mode = False # 批次管理模式狀態
    
    # 檢查匯率更新狀態
    # 由於 CurrencyManager 在 init 時會自動 update_rates
    # 我們可以檢查 rates 是否與預設值不同，或者簡單提示已嘗試更新
    # 這裡假設 update_rates 會 print 訊息，我們在 GUI 上也顯示一下
    # 為了更精確，我們可以修改 CurrencyManager 增加一個 last_updated 屬性，但這裡先簡單做
    pass # 佔位，稍後在 window 建立後更新 status bar
    
    # 檢查是否需要初始化 Profile
    if not os.path.exists(PROFILE_FILE):
        sg.popup('歡迎使用！初次使用請先設定個人資料。')
        make_profile_window(profile_mgr)

    # ==========================
    # Tab 1: 新增衣服 (Add Item)
    # ==========================

    tab1_layout = [
        [sg.Text('步驟 1: 輸入基本資料', font=FONT_HEADER, text_color='#80CBC4', background_color=THEME_COLORS['BACKGROUND'], pad=((0,0), (10, 5)))],
        [card_frame('', [
            [sg.Text('品名:', size=(8,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-ADD-NAME-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Text('價格:', size=(8,1), font=FONT_NORMAL, background_color='#1E1E1E'), 
             sg.Input(key='-ADD-PRICE-', size=(15,1), font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0),
             sg.Combo(['TWD', 'USD', 'CNY', 'EUR', 'JPY', 'KRW'], default_value='TWD', key='-ADD-CURRENCY-', size=(8,1), font=FONT_NORMAL, readonly=True, background_color='#2C2C2C', text_color='white')],
            [sg.Text('已穿次數:', size=(8,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(default_text='0', key='-ADD-WEAR-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Text('圖片:', size=(8,1), font=FONT_NORMAL, background_color='#1E1E1E'), 
             sg.Input(key='-ADD-IMG-PATH-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0, enable_events=True), 
             sg.FileBrowse('瀏覽...', font=FONT_NORMAL, file_types=(("Images", "*.jpg;*.png;*.jpeg"),), button_color=('#FFFFFF', '#424242')),
             sg.Checkbox('自動去背', default=True, key='-AUTO-REMBG-', font=FONT_NORMAL, text_color='#D4AF37', background_color='#1E1E1E', visible=HAS_REMBG),
             sg.Button('✨ 魔術去背', key='-REMOVE-BG-', font=FONT_NORMAL, button_color=('white', '#7B1FA2'), border_width=0, visible=HAS_REMBG)],
            [sg.Text('💡 提示: 安裝 rembg 套件 (pip install rembg) 即可啟用自動去背功能', font=FONT_SMALL, text_color='#757575', background_color='#1E1E1E', visible=not HAS_REMBG)],
            [sg.Text('尺寸:', size=(8,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-ADD-SIZE-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Text('備註:', size=(8,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-ADD-NOTES-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Push(background_color='#1E1E1E'), 
             sg.Button('✨ 產生分析 Prompt', key='-GEN-ADD-PROMPT-', font=FONT_HEADER, size=(20,1), button_color=('white', '#00897B'), border_width=0),
             sg.Button('📂 批次匯入 (Batch)', key='-BATCH-MENU-', font=FONT_HEADER, button_color=('white', '#1565C0'), size=(20,1), pad=((10,0), (0, 0))),
             sg.Push(background_color='#1E1E1E')]
        ])],
        
        [sg.Column([
            [sg.Text('給 GPT 的 Prompt:', font=FONT_NORMAL, background_color=THEME_COLORS['BACKGROUND'])],
            [sg.Multiline(size=(50, 6), key='-ADD-PROMPT-OUT-', disabled=True, font=FONT_SMALL, background_color='#2C2C2C', text_color='#B0BEC5', border_width=0)],
            [sg.Button('📋 複製 Prompt', key='-COPY-PROMPT-', font=FONT_NORMAL, size=(15,1), button_color=('white', '#424242'), border_width=0)]
        ], background_color=THEME_COLORS['BACKGROUND']), sg.Column([
            [sg.Text('GPT 回傳的 JSON:', font=FONT_NORMAL, background_color=THEME_COLORS['BACKGROUND'])],
            [sg.Multiline(size=(50, 6), key='-ADD-GPT-RESPONSE-', font=FONT_SMALL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Button('📥 解析並預覽', key='-PARSE-ADD-', font=FONT_NORMAL, size=(15,1), button_color=('white', '#424242'), border_width=0)]
        ], background_color=THEME_COLORS['BACKGROUND'])],
        
        [sg.Push(background_color=THEME_COLORS['BACKGROUND']), sg.Button('🗑️ 清空欄位', key='-CLEAR-ADD-', font=FONT_NORMAL, button_color=('white', '#D32F2F'), border_width=0), sg.Push(background_color=THEME_COLORS['BACKGROUND'])]
    ]

    tab2_layout = [
        [sg.Text('今天想穿什麼？', font=FONT_TITLE, pad=((0,0), (10, 10)), text_color='#D4AF37', background_color=THEME_COLORS['BACKGROUND'])],
        
        [card_frame('', [
            [sg.Text('天氣狀況:', size=(10,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-OOTD-WEATHER-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Text('出席場合:', size=(10,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-OOTD-OCCASION-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Text('心情/目標:', size=(10,1), font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-OOTD-MOOD-', font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Push(background_color='#1E1E1E'), sg.Button('👗 產生 OOTD Prompt', key='-GEN-OOTD-PROMPT-', font=FONT_HEADER, size=(25,1), button_color=('white', '#E64A19'), border_width=0), sg.Push(background_color='#1E1E1E')]
        ])],
        
        [sg.Text('步驟 1: 複製 Prompt', font=FONT_HEADER, text_color='#FFCC80', background_color=THEME_COLORS['BACKGROUND'], pad=((0,0), (20, 5)))],
        
        [sg.Column([
            [sg.Multiline(size=(50, 8), key='-OOTD-PROMPT-OUT-', disabled=True, font=FONT_SMALL, background_color='#2C2C2C', text_color='#B0BEC5', border_width=0)],
            [sg.Button('📋 複製 Prompt', key='-COPY-OOTD-', font=FONT_NORMAL, size=(15,1), button_color=('white', '#424242'), border_width=0)]
        ], background_color=THEME_COLORS['BACKGROUND']), sg.Column([
            [sg.Text('步驟 2: 貼上 GPT JSON', font=FONT_HEADER, text_color='#FFCC80', background_color=THEME_COLORS['BACKGROUND'])],
            [sg.Multiline(size=(50, 8), key='-OOTD-RESPONSE-', font=FONT_SMALL, background_color='#2C2C2C', text_color='white', border_width=0)],
            [sg.Button('✨ 解析並顯示穿搭', key='-PARSE-OOTD-', font=FONT_NORMAL, button_color=('white', '#E64A19'), border_width=0)]
        ], background_color=THEME_COLORS['BACKGROUND'])]
    ]

    # ==========================
    # Tab 3: 衣櫃清單 (簡易版)
    # ==========================
    # 準備表格資料
    # 準備表格資料
    # 定義狀態顯示文字
    STATUS_MAP = {
        'available': '✅ 在衣櫃',
        'laundry': '🧺 送洗中',
        'lent': '🤝 已借出',
        'repair': '🔧 維修中'
    }
    
    header_list = ['選取', 'ID', '狀態', '分類', '名稱', '類型', '顏色']
    data_list = []
    for item in wardrobe_mgr.items:
        status_key = item.get('status', 'available')
        status_text = STATUS_MAP.get(status_key, status_key)
        item_type = item.get('ai', {}).get('type', '')
        category = get_category(item_type)
        
        data_list.append([
            '☐', # 0: Checkbox
            item['id'], 
            status_text,
            category,
            item['name'], 
            item_type,
            item.get('ai', {}).get('color', '')
        ])
    
    # 用來追蹤目前表格顯示的資料 (因為會有篩選)
    current_table_data = data_list

    tab3_layout = [
        [card_frame(' 🔍 篩選條件 ', [
            [sg.Text('關鍵字:', font=FONT_NORMAL, background_color='#1E1E1E'), sg.Input(key='-FILTER-TXT-', size=(15,1), font=FONT_NORMAL, background_color='#2C2C2C', text_color='white', border_width=0),
             sg.Text('分類:', font=FONT_NORMAL, background_color='#1E1E1E'), sg.Combo(get_unique_categories(wardrobe_mgr.items), default_value='全部', key='-FILTER-CAT-', font=FONT_NORMAL, readonly=True, background_color='#2C2C2C', text_color='white'),
             sg.Button('🔍 搜尋', key='-APPLY-FILTER-', font=FONT_NORMAL, button_color=('white', '#00897B'), border_width=0),
             sg.Button('❌ 清除', key='-CLEAR-FILTER-', font=FONT_NORMAL, button_color=('white', '#424242'), border_width=0)]
        ])],
        
        [sg.Text(f'目前共有 {len(wardrobe_mgr.items)} 件衣服', key='-WARDROBE-COUNT-', font=FONT_NORMAL, text_color='#757575', background_color=THEME_COLORS['BACKGROUND'])],
        
        # Batch Toolbar (Initially Hidden)
        [sg.Column([
            [sg.Button('全選', key='-BATCH-ALL-', font=FONT_SMALL, size=(6,1)),
             sg.Button('全不選', key='-BATCH-NONE-', font=FONT_SMALL, size=(6,1)),
             sg.Text('將選取項目設為:', font=FONT_NORMAL, background_color='#1E1E1E'),
             sg.Combo(list(STATUS_MAP.values()), default_value='🧺 送洗中', key='-BATCH-STATUS-SEL-', font=FONT_NORMAL, readonly=True, size=(15, 1)),
             sg.Button('✅ 套用狀態', key='-APPLY-BATCH-', font=FONT_NORMAL, button_color=('white', '#00897B'))]
        ], key='-BATCH-TOOLBAR-', visible=False, background_color='#1E1E1E', pad=((0,0), (0, 10)))],

        [sg.Table(values=data_list, headings=header_list, 
                  auto_size_columns=False, col_widths=[5, 15, 15, 8, 15, 10, 10],
                  justification='left', num_rows=18, key='-WARDROBE-TABLE-',
                  background_color='#1E1E1E', text_color='#E0E0E0', 
                  header_background_color='#2C2C2C', header_text_color='#D4AF37',
                  alternating_row_color='#121212', enable_click_events=True)], # Enable click events for checkbox logic
        
        [sg.Button('✅ 批次管理', key='-TOGGLE-BATCH-', font=FONT_NORMAL, button_color=('white', '#424242'), border_width=0),
         sg.Button('👁️ 查看單品', key='-VIEW-ITEM-', font=FONT_NORMAL, button_color=('white', '#1565C0'), border_width=0),
         sg.Button('✏️ 編輯詳情', key='-EDIT-DETAILS-', font=FONT_NORMAL, button_color=('white', '#F57C00'), border_width=0),
         sg.Button('🗑️ 刪除選取', key='-DELETE-ITEM-', font=FONT_NORMAL, button_color=('white', '#D32F2F'), border_width=0)]
    ]

    # ==========================
    # Tab 4: 數據分析 (Analytics)
    # ==========================
    tab4_layout = [
        [sg.Text('📊 衣櫃數據分析', font=FONT_TITLE, text_color='#D4AF37', background_color=THEME_COLORS['BACKGROUND'], pad=((0,0), (10, 20))),
         sg.Push(background_color=THEME_COLORS['BACKGROUND']),
         sg.Text('顯示幣別:', font=FONT_NORMAL, background_color=THEME_COLORS['BACKGROUND']),
         sg.Combo(['TWD', 'USD', 'CNY', 'EUR', 'JPY', 'KRW'], default_value='TWD', key='-BASE-CURRENCY-', size=(6,1), font=FONT_NORMAL, readonly=True, enable_events=True)],
        
        [card_frame(' 💰 價值統計 ', [
            [sg.Text('衣櫃總價值:', font=FONT_HEADER, background_color='#1E1E1E'), sg.Text('$0', key='-TOTAL-VALUE-', font=FONT_TITLE, text_color='#81C784', background_color='#1E1E1E')],
            [sg.Text('平均單價:', font=FONT_NORMAL, background_color='#1E1E1E'), sg.Text('$0', key='-AVG-PRICE-', font=FONT_HEADER, background_color='#1E1E1E')],
            [sg.Text('總件數:', font=FONT_NORMAL, background_color='#1E1E1E'), sg.Text('0', key='-TOTAL-COUNT-', font=FONT_HEADER, background_color='#1E1E1E')]
        ])],
        
        [card_frame(' 🏆 CP 值冠軍 (穿最多次/最划算) ', [
            [sg.Table(values=[], headings=['名稱', '購入價', '穿著次數', '每次成本'], 
                      key='-CP-TABLE-', auto_size_columns=False, col_widths=[15, 8, 8, 8],
                      justification='right', num_rows=10,
                      background_color='#1E1E1E', text_color='#E0E0E0', 
                      header_background_color='#2C2C2C', header_text_color='#D4AF37',
                      alternating_row_color='#121212')]
        ])],
        
        [sg.Button('🔄 更新數據', key='-REFRESH-ANALYTICS-', font=FONT_NORMAL, size=(15,1), pad=((0,0), (10, 0)), button_color=('white', '#00897B'), border_width=0)]
    ]

    # ==========================
    # Tab 5: 穿搭日曆 (Calendar)
    # ==========================
    tab5_layout = [
        [sg.Text('📅 穿搭紀錄', font=FONT_TITLE, text_color='#90CAF9', background_color=THEME_COLORS['BACKGROUND'], pad=((0,0), (10, 20)))],
        [sg.Table(values=[], headings=['日期', '穿搭主題', '單品清單'], 
                  key='-CALENDAR-TABLE-', auto_size_columns=False, col_widths=[12, 20, 40],
                  justification='left', num_rows=15,
                  enable_events=True,
                  background_color='#1E1E1E', text_color='#E0E0E0', 
                  header_background_color='#2C2C2C', header_text_color='#D4AF37',
                  alternating_row_color='#121212')],
        [sg.Button('🔄 重新整理', key='-REFRESH-CALENDAR-', font=FONT_NORMAL, button_color=('white', '#424242'), border_width=0)]
    ]

    # 主視窗 Layout
    layout = [
        [sg.Text('✨ Wardrobe AI', font=('Segoe UI', 28, 'bold'), text_color='#D4AF37', background_color=THEME_COLORS['BACKGROUND'], pad=((20,0), (20, 10)))],
        [sg.Push(background_color=THEME_COLORS['BACKGROUND']), sg.Button('👤 編輯個人資料', key='-EDIT-PROFILE-', font=FONT_NORMAL, button_color=('#D4AF37', '#1E1E1E'), border_width=0), sg.Push(background_color=THEME_COLORS['BACKGROUND'])],
        [sg.TabGroup([
            [sg.Tab(' ➕ 新增衣物 ', tab1_layout, font=FONT_HEADER, background_color=THEME_COLORS['BACKGROUND'], key='-TAB1-'),
             sg.Tab(' 👗 OOTD 產生器 ', tab2_layout, font=FONT_HEADER, background_color=THEME_COLORS['BACKGROUND'], key='-TAB2-'),
             sg.Tab(' 🧥 衣櫃清單 ', tab3_layout, font=FONT_HEADER, background_color=THEME_COLORS['BACKGROUND'], key='-TAB3-'),
             sg.Tab(' 📊 數據分析 ', tab4_layout, font=FONT_HEADER, background_color=THEME_COLORS['BACKGROUND'], key='-TAB4-'),
             sg.Tab(' 📅 穿搭日曆 ', tab5_layout, font=FONT_HEADER, background_color=THEME_COLORS['BACKGROUND'], key='-TAB5-')]
        ], font=FONT_NORMAL, title_color='#757575', selected_title_color='#D4AF37', tab_background_color='#1E1E1E', selected_background_color='#121212', border_width=0, pad=((10,10), (0,0)), key='-MAIN-TABS-', enable_events=True)],
        [sg.Text('Ready', key='-STATUS-', size=(50,1), relief=sg.RELIEF_FLAT, font=FONT_SMALL, text_color='#757575', background_color=THEME_COLORS['BACKGROUND'], pad=((20,0), (5,10)))]
    ]

    # Register Custom Theme
    # sg.LOOK_AND_FEEL_TABLE[THEME_NAME] = THEME_COLORS # Moved to top of main
    # sg.theme(THEME_NAME) # Moved to top of main

    window = sg.Window('Wardrobe App Enterprise', layout, finalize=True, background_color=THEME_COLORS['BACKGROUND'], resizable=True)
    
    # Bind Double Click on Table
    window['-WARDROBE-TABLE-'].bind('<Double-Button-1>', '+DOUBLE_CLICK+')
    window['-CALENDAR-TABLE-'].bind('<Double-Button-1>', '+DOUBLE_CLICK+')

    # Startup Refresh
    window.write_event_value('-REFRESH-CALENDAR-', None)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
            
        # Tab Switch Event
        if event == '-MAIN-TABS-':
            if values['-MAIN-TABS-'] == '-TAB5-':
                window.write_event_value('-REFRESH-CALENDAR-', None)

        # --- 編輯個人資料 ---
        if event == '-EDIT-PROFILE-':
            make_profile_window(profile_mgr)
            window['-STATUS-'].update('個人資料已更新')

        # --- 新增衣服 Flow ---
        # 自動去背邏輯
        if event == '-ADD-IMG-PATH-' and values.get('-AUTO-REMBG-') and HAS_REMBG:
             # 觸發去背
             window.write_event_value('-REMOVE-BG-', None)

        if event == '-REMOVE-BG-':
            img_path = values['-ADD-IMG-PATH-']
            if not img_path or not os.path.exists(img_path):
                if values.get('-AUTO-REMBG-'): 
                    continue
                sg.popup_error('請先選擇圖片！')
                continue
            
            if '_nobg' in img_path:
                continue

            # 呼叫新的去背流程
            new_bg_path = perform_background_removal_flow(img_path)
            
            if new_bg_path:
                window['-ADD-IMG-PATH-'].update(new_bg_path)
                window['-STATUS-'].update(f'✨ 已套用去背圖片: {os.path.basename(new_bg_path)}')
            else:
                window['-STATUS-'].update('已保留原始圖片')


        if event == '-GEN-ADD-PROMPT-':
            item_info = {
                'name': values['-ADD-NAME-'],
                'size': values['-ADD-SIZE-'],
                'notes': values['-ADD-NOTES-']
            }
            
            # 檢查是否有圖片
            img_path = values['-ADD-IMG-PATH-']
            if not img_path:
                sg.popup_error('請先上傳圖片！\n為了讓 AI 能準確分析，請務必提供衣服的照片。')
                continue
            
            prompt = build_add_item_prompt(profile_mgr.data, item_info)
            window['-ADD-PROMPT-OUT-'].update(prompt)
            window['-ADD-GPT-RESPONSE-'].update('') # 清空舊的回應
            window['-STATUS-'].update('Prompt 已產生，請複製給 GPT。')


        if event == '-COPY-PROMPT-':
            sg.clipboard_set(values['-ADD-PROMPT-OUT-'])
            window['-STATUS-'].update('Prompt 已複製到剪貼簿！')

        if event == '-PARSE-ADD-':
            raw_response = values['-ADD-GPT-RESPONSE-']
            parsed_json = extract_json(raw_response)
            
            if not parsed_json or 'data' not in parsed_json:
                sg.popup_error('無法解析 JSON 或找不到 data 欄位。\n請確認 GPT 回傳格式是否正確。')
                continue
            
            # 預覽視窗
            preview_text = json.dumps(parsed_json['data'], ensure_ascii=False, indent=2)
            
            # 準備預覽圖片
            preview_img_path = values['-ADD-IMG-PATH-']
            img_data = None
            if preview_img_path and os.path.exists(preview_img_path):
                img_data = resize_image_to_bytes(preview_img_path, (300, 300))
            
            confirm_layout = [
                [sg.Text('解析成功！請確認以下資料是否正確', font=FONT_HEADER, text_color='#D4AF37')],
                [sg.Column([
                    [sg.Text('即將存入的圖片:', text_color='#9E9E9E')],
                    [sg.Image(data=img_data, background_color='#2C2C2C') if img_data else sg.Text('無圖片', size=(20,10), background_color='#2C2C2C')]
                ], element_justification='center'),
                 sg.Column([
                    [sg.Text('AI 分析資料:', text_color='#9E9E9E')],
                    [sg.Multiline(preview_text, size=(50, 15), font=FONT_SMALL, disabled=True, background_color='#1E1E1E', text_color='#E0E0E0')]
                ])],
                [sg.Button('✅ 確認存入', key='-CONFIRM-ADD-', font=FONT_HEADER, button_color=('white', '#00897B')),
                 sg.Button('❌ 取消', key='-CANCEL-ADD-', font=FONT_HEADER, button_color=('white', '#D32F2F'))]
            ]
            
            confirm_win = sg.Window('預覽確認', confirm_layout, modal=True, background_color='#121212')
            event_c, _ = confirm_win.read(close=True)
            
            if event_c == '-CONFIRM-ADD-':
                # 寫入資料庫
                ai_data = parsed_json['data']
                new_id = wardrobe_mgr.generate_id(ai_data.get('type', 'unknown'))
                
                # --- 處理圖片儲存 ---
                final_img_path = ""
                source_img_path = values['-ADD-IMG-PATH-']
                if source_img_path and os.path.exists(source_img_path):
                    try:
                        # 確保 IMAGE_DIR 是絕對路徑
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        abs_image_dir = os.path.join(script_dir, IMAGE_DIR)
                        if not os.path.exists(abs_image_dir):
                            os.makedirs(abs_image_dir)
                            
                        # 產生新檔名: id.png (保留原副檔名)
                        ext = os.path.splitext(source_img_path)[1]
                        if not ext: ext = '.png'
                        
                        # 移除檔名中的非法字元 (例如 / \ : * ? " < > |)
                        safe_id = "".join([c for c in new_id if c.isalnum() or c in ('-', '_')])
                        new_filename = f"{safe_id}{ext}"
                        final_img_path = os.path.join(abs_image_dir, new_filename)
                        
                        # 複製檔案 (使用 shutil 或讀寫)
                        import shutil
                        shutil.copy2(source_img_path, final_img_path)
                        print(f"Image saved to: {final_img_path}")
                    except Exception as e:
                        sg.popup_error(f"圖片儲存失敗: {e}")
                        final_img_path = source_img_path # Fallback to original
                
                new_item = {
                    "id": new_id,
                    "name": values['-ADD-NAME-'],
                    "size": values['-ADD-SIZE-'],
                    "price": int(values['-ADD-PRICE-']) if values['-ADD-PRICE-'].isdigit() else 0,
                    "currency": values['-ADD-CURRENCY-'],
                    "wear_count": int(values['-ADD-WEAR-']) if values['-ADD-WEAR-'].isdigit() else 0,
                    "image_path": final_img_path,
                    "user_notes": values['-ADD-NOTES-'],
                    "status": "available",
                    "purchase_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "ai": ai_data
                }
                
                wardrobe_mgr.add_item(new_item)
                sg.popup(f'新增成功！\nID: {new_id}')
                
                # 清空欄位
                window['-ADD-NAME-'].update('')
                window['-ADD-IMG-PATH-'].update('')
                window['-ADD-GPT-RESPONSE-'].update('')
                window['-ADD-PROMPT-OUT-'].update('')
                
                # 重新整理列表
                window.write_event_value('-REFRESH-TABLE-', None)
                window.write_event_value('-REFRESH-ANALYTICS-', None)

        # --- 編輯詳情 (完整編輯) ---
        if event == '-EDIT-DETAILS-':
            selected_rows = values['-WARDROBE-TABLE-']
            if not selected_rows:
                sg.popup_error('請先選擇衣服！')
                continue
            
            # 使用 current_table_data 確保拿到正確的 ID (即使有篩選)
            if not current_table_data:
                 current_table_data = data_list 
            
            row_idx = selected_rows[0]
            if row_idx < len(current_table_data):
                row_data = current_table_data[row_idx]
                item_id = row_data[1] # ID is now at index 1
                
                # 找出原始 item
                target_item = next((x for x in wardrobe_mgr.items if x['id'] == item_id), None)
                if target_item:
                    ai_data = target_item.get('ai', {})
                    
                    # Helper to join list
                    def list_to_str(l): return ", ".join(l) if isinstance(l, list) else str(l)
                    
                    # 編輯視窗 Layout
                    edit_layout = [
                        [sg.Text(f'編輯單品: {target_item["name"]}', font=FONT_HEADER, text_color='#D4AF37')],
                        [sg.HorizontalSeparator()],
                        
                        [sg.Frame(' 📦 基本資訊 ', [
                            [sg.Text('名稱:', size=(8,1)), sg.Input(target_item.get('name', ''), key='-ED-NAME-', size=(30,1))],
                            [sg.Text('分類:', size=(8,1)), sg.Input(ai_data.get('type', ''), key='-ED-TYPE-', size=(15,1)),
                             sg.Text('顏色:', size=(6,1)), sg.Input(ai_data.get('color', ''), key='-ED-COLOR-', size=(15,1))]
                        ], pad=((0,0), (0, 10)))],
                        
                        [sg.Frame(' 💰 購買資訊 ', [
                            [sg.Text('價格:', size=(8,1)), sg.Input(target_item.get('price', 0), key='-ED-PRICE-', size=(10,1)), 
                             sg.Combo(['TWD', 'USD', 'CNY', 'EUR', 'JPY', 'KRW'], default_value=target_item.get('currency', 'TWD'), key='-ED-CURRENCY-', size=(6,1), readonly=True)],
                            [sg.Text('購買日期:', size=(8,1)), sg.Input(target_item.get('purchase_date', ''), key='-ED-DATE-', size=(15,1)), sg.CalendarButton('📅', target='-ED-DATE-', format='%Y-%m-%d')],
                            [sg.Text('穿著次數:', size=(8,1)), sg.Input(target_item.get('wear_count', 0), key='-ED-WEAR-', size=(10,1))]
                        ], pad=((0,0), (0, 10)))],
                        
                        [sg.Frame(' 🏷️ 屬性與標籤 ', [
                            [sg.Text('風格標籤 (逗號分隔):')],
                            [sg.Multiline(list_to_str(ai_data.get('styleTags', [])), key='-ED-TAGS-', size=(50, 2))],
                            [sg.Text('適用季節 (逗號分隔):')],
                            [sg.Input(list_to_str(ai_data.get('seasons', [])), key='-ED-SEASONS-', size=(50, 1))],
                            [sg.Text('適用場合 (逗號分隔):')],
                            [sg.Input(list_to_str(ai_data.get('occasions', [])), key='-ED-OCCASIONS-', size=(50, 1))],
                            [sg.Text('尺寸:', size=(8,1)), sg.Input(target_item.get('size', ''), key='-ED-SIZE-', size=(15,1))]
                        ], pad=((0,0), (0, 10)))],
                        
                        [sg.Frame(' 📝 備註 ', [
                            [sg.Multiline(target_item.get('user_notes', ''), key='-ED-NOTES-', size=(50, 3))]
                        ])],
                        
                        [sg.Button('💾 儲存變更', key='-SAVE-EDIT-', font=FONT_HEADER, button_color=('white', '#00796B'), size=(15,1)), 
                         sg.Button('❌ 取消', key='-CANCEL-EDIT-', font=FONT_HEADER, button_color=('white', '#D32F2F'), size=(10,1))]
                    ]
                    
                    edit_win = sg.Window('編輯單品詳情', edit_layout, modal=True)
                    e2, v2 = edit_win.read(close=True)
                    
                    if e2 == '-SAVE-EDIT-':
                        try:
                            # 處理 List
                            tags = [x.strip() for x in v2['-ED-TAGS-'].split(',') if x.strip()]
                            seasons = [x.strip() for x in v2['-ED-SEASONS-'].split(',') if x.strip()]
                            occasions = [x.strip() for x in v2['-ED-OCCASIONS-'].split(',') if x.strip()]
                            
                            # 更新第一層
                            updates = {
                                'name': v2['-ED-NAME-'],
                                'size': v2['-ED-SIZE-'],
                                'price': int(v2['-ED-PRICE-']),
                                'currency': v2['-ED-CURRENCY-'],
                                'purchase_date': v2['-ED-DATE-'],
                                'wear_count': int(v2['-ED-WEAR-']),
                                'user_notes': v2['-ED-NOTES-']
                            }
                            
                            # 更新 AI Data (Nested)
                            # 先取得舊的 ai_data，更新後再寫回
                            new_ai_data = ai_data.copy()
                            new_ai_data.update({
                                'type': v2['-ED-TYPE-'],
                                'color': v2['-ED-COLOR-'],
                                'styleTags': tags,
                                'seasons': seasons,
                                'occasions': occasions
                            })
                            updates['ai'] = new_ai_data
                            
                            wardrobe_mgr.update_item(item_id, updates)
                            sg.popup('更新成功！')
                            
                            # 觸發更新
                            window.write_event_value('-REFRESH-TABLE-', None)
                            window.write_event_value('-REFRESH-ANALYTICS-', None)
                            
                        except ValueError:
                            sg.popup_error('價格和次數必須是數字！')
                        except Exception as ex:
                            sg.popup_error(f'更新失敗: {ex}')
                            
                    edit_win.close()

        # --- 批次管理邏輯 ---
        if event == '-TOGGLE-BATCH-':
            is_batch_mode = not is_batch_mode
            window['-BATCH-TOOLBAR-'].update(visible=is_batch_mode)
            window['-TOGGLE-BATCH-'].update(button_color=('white', '#00897B') if is_batch_mode else ('white', '#424242'))
            
            # 調整表格欄寬以顯示/隱藏 Checkbox
            # 注意: PySimpleGUI 的 Table 很難動態隱藏欄位，我們用更新資料的方式
            # 當 Batch Mode 開啟時，第一欄顯示 ☐/☑
            # 當 Batch Mode 關閉時，第一欄顯示空白，或者我們假設使用者不介意看到勾選框，只是不能操作
            # 為了直覺，我們在點擊事件做控制
            
            # 重新整理表格以確保顯示正確
            window.write_event_value('-REFRESH-TABLE-', None)
            
            # 嘗試動態調整欄寬 (Tkinter hack)
            try:
                # Column #1 is the first column (checkbox)
                # Note: Treeview columns are usually 1-indexed for data columns if show='headings'
                # But sometimes #0 is the tree column.
                # Let's try to force update.
                width = 40 if is_batch_mode else 0 
                window['-WARDROBE-TABLE-'].Widget.column('#1', width=width, stretch=False)
                
                # Also force update idletasks to ensure redraw
                window.refresh()
            except Exception as e:
                print(f"Resize failed: {e}")

        if event == '-BATCH-ALL-':
            for row in current_table_data:
                row[0] = '☑'
            window['-WARDROBE-TABLE-'].update(values=current_table_data)
            
        if event == '-BATCH-NONE-':
            for row in current_table_data:
                row[0] = '☐'
            window['-WARDROBE-TABLE-'].update(values=current_table_data)

        if event == '-APPLY-BATCH-':
            target_status_display = values['-BATCH-STATUS-SEL-']
            # 反向對照找出 key
            target_status = next((k for k, v in STATUS_MAP.items() if v == target_status_display), 'available')
            
            count = 0
            for row in current_table_data:
                if row[0] == '☑':
                    item_id = row[1] # ID 在第二欄 (index 1)
                    wardrobe_mgr.update_item(item_id, {'status': target_status})
                    count += 1
            
            if count > 0:
                sg.popup(f'已將 {count} 件衣服狀態更新為 {target_status_display}！')
                # 執行完後是否要退出批次模式？看使用者習慣，這裡先保留
                window.write_event_value('-REFRESH-TABLE-', None)
                window.write_event_value('-REFRESH-ANALYTICS-', None)
            else:
                sg.popup_error('請先勾選要修改的衣服！')

        # --- 表格點擊事件 (處理 Checkbox) ---
        if isinstance(event, tuple) and event[0] == '-WARDROBE-TABLE-':
            # event format: ('-WARDROBE-TABLE-', '+CLICKED+', (row, col))
            if event[2][0] == -1: # Header click
                pass
            else:
                row_idx = event[2][0]
                col_idx = event[2][1]
                
                # 如果是點擊第一欄 (Checkbox) 且在批次模式下
                if is_batch_mode and col_idx == 0:
                    if row_idx < len(current_table_data):
                        current_val = current_table_data[row_idx][0]
                        new_val = '☑' if current_val == '☐' else '☐'
                        current_table_data[row_idx][0] = new_val
                        window['-WARDROBE-TABLE-'].update(values=current_table_data)

        if event == '-BATCH-MENU-':
            # 選擇匯入模式
            mode_layout = [
                [sg.Text('請選擇批次匯入模式', font=FONT_HEADER, text_color='#D4AF37')],
                [sg.Text('選擇適合您的匯入方式：', font=FONT_NORMAL)],
                [sg.Button('🚀 自動匯入 (API Mode)', key='-MODE-API-', size=(30, 2), font=FONT_HEADER, button_color=('white', '#1565C0'))],
                [sg.Text('   需輸入 OpenAI API Key，全自動處理', font=FONT_SMALL, text_color='#90CAF9')],
                [sg.HorizontalSeparator()],
                [sg.Button('📋 手動匯入 (ChatGPT Mode)', key='-MODE-GPT-', size=(30, 2), font=FONT_HEADER, button_color=('white', '#E64A19'))],
                [sg.Text('   免 API Key，需手動複製 Prompt 與貼上 JSON', font=FONT_SMALL, text_color='#FFCC80')],
                [sg.Button('取消', key='-CANCEL-MODE-', size=(10,1), pad=((0,0), (20,0)))]
            ]
            mode_win = sg.Window('批次匯入模式選擇', mode_layout, modal=True, element_justification='center')
            mode_event, _ = mode_win.read(close=True)
            
            if mode_event == '-MODE-API-':
                # === API Mode Logic ===
                folder_path = sg.popup_get_folder('請選擇要匯入的照片資料夾')
                if folder_path:
                    api_key = sg.popup_get_text('請輸入 OpenAI API Key (若無則使用模擬模式):', password_char='*')
                    
                    prog_layout = [
                        [sg.Text('正在批次處理中...', font=FONT_HEADER)],
                        [sg.Text('準備開始...', key='-PROG-TXT-', size=(50,1))],
                        [sg.ProgressBar(100, orientation='h', size=(50, 20), key='-PROG-BAR-')],
                        [sg.Button('取消', key='-CANCEL-BATCH-')]
                    ]
                    prog_win = sg.Window('批次匯入進度', prog_layout, modal=True, finalize=True)
                    
                    try:
                        count = process_batch_import(folder_path, wardrobe_mgr, profile_mgr, prog_win, api_key)
                        prog_win.close()
                        sg.popup(f'批次匯入完成！\n成功匯入 {count} 件衣服。')
                        window.write_event_value('-REFRESH-TABLE-', None)
                        window.write_event_value('-REFRESH-ANALYTICS-', None)
                    except Exception as e:
                        prog_win.close()
                        sg.popup_error(f'批次匯入發生錯誤: {e}')

            elif mode_event == '-MODE-GPT-':
                # === GPT Mode Logic ===
                folder_path = sg.popup_get_folder('請選擇要處理的照片資料夾')
                if folder_path:
                    # 1. 預處理
                    sg.popup_quick_message('正在準備圖片與去背中...', background_color='#1E1E1E', text_color='#D4AF37')
                    valid_exts = ('.jpg', '.jpeg', '.png')
                    files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_exts) and '_nobg' not in f]
                    
                    processed_files = []
                    for f in files:
                        img_path = os.path.join(folder_path, f)
                        nobg_path = remove_bg_silent(img_path)
                        if nobg_path:
                            processed_files.append(os.path.basename(nobg_path))
                        else:
                            processed_files.append(f)
                    
                    if not processed_files:
                        sg.popup_error('資料夾內沒有圖片！')
                    else:
                        # 2. 產生 Prompt
                        prompt = build_batch_prompt(processed_files, profile_mgr.data)
                        
                        # 3. 顯示 Prompt 視窗
                        batch_layout = [
                            [sg.Text('步驟 1: 複製 Prompt 並貼給 ChatGPT', font=FONT_HEADER, text_color='#FFCC80')],
                            [sg.Multiline(prompt, size=(60, 10), key='-BATCH-PROMPT-OUT-', disabled=True, font=FONT_SMALL)],
                            [sg.Button('📋 複製 Prompt', key='-COPY-BATCH-PROMPT-', font=FONT_NORMAL)],
                            [sg.Text('步驟 2: 將圖片上傳給 ChatGPT (請上傳去背後的圖片)', font=FONT_NORMAL, text_color='#9E9E9E')],
                            [sg.Text(f'提示: 去背圖片已產生在原資料夾中 (檔名結尾 _nobg.png)', font=FONT_SMALL, text_color='#757575')],
                            [sg.HorizontalSeparator()],
                            [sg.Text('步驟 3: 貼上 ChatGPT 回傳的 JSON', font=FONT_HEADER, text_color='#81C784')],
                            [sg.Multiline(size=(60, 10), key='-BATCH-JSON-IN-', font=FONT_SMALL)],
                            [sg.Button('📥 解析並匯入', key='-PARSE-BATCH-', font=FONT_HEADER, button_color=('white', '#00897B')),
                             sg.Button('取消', key='-CANCEL-BATCH-PROMPT-')]
                        ]
                        
                        batch_win = sg.Window('離線批次匯入', batch_layout, modal=True)
                        
                        while True:
                            e_b, v_b = batch_win.read()
                            if e_b in (sg.WIN_CLOSED, '-CANCEL-BATCH-PROMPT-'):
                                break
                                
                            if e_b == '-COPY-BATCH-PROMPT-':
                                sg.clipboard_set(v_b['-BATCH-PROMPT-OUT-'])
                                sg.popup_quick_message('Prompt 已複製！')
                                
                            if e_b == '-PARSE-BATCH-':
                                json_text = v_b['-BATCH-JSON-IN-']
                                if not json_text.strip():
                                    sg.popup_error('請先貼上 JSON！')
                                    continue
                                    
                                count = process_offline_batch(json_text, folder_path, wardrobe_mgr)
                                if count > 0:
                                    sg.popup(f'成功匯入 {count} 件衣服！')
                                    window.write_event_value('-REFRESH-TABLE-', None)
                                    window.write_event_value('-REFRESH-ANALYTICS-', None)
                                    break
                                else:
                                    sg.popup_error('匯入失敗，請檢查 JSON 格式或檔名是否對應。')
                        
                        batch_win.close()

        # --- 刪除單品 (支援單選與批次) ---
        if event == '-DELETE-ITEM-':
            # 1. 檢查是否為批次模式且有勾選項目
            ids_to_delete = []
            names_to_delete = []
            
            # 檢查 Checkbox
            for row in current_table_data:
                if row[0] == '☑':
                    ids_to_delete.append(row[1])
                    names_to_delete.append(row[4])
            
            # 2. 如果沒有勾選，檢查是否有點擊選取 (Highlight)
            if not ids_to_delete:
                selected_rows = values['-WARDROBE-TABLE-']
                if selected_rows:
                    # 使用 current_table_data 確保拿到正確的 ID
                    if not current_table_data:
                         current_table_data = data_list
                    
                    row_idx = selected_rows[0]
                    if row_idx < len(current_table_data):
                        row_data = current_table_data[row_idx]
                        ids_to_delete.append(row_data[1])
                        names_to_delete.append(row_data[4])
            
            # 3. 執行刪除
            if not ids_to_delete:
                sg.popup_error('請先選擇或勾選要刪除的衣服！')
                continue
                
            confirm_msg = f"確定要刪除以下 {len(ids_to_delete)} 件衣服嗎？\n\n" + "\n".join(names_to_delete[:5])
            if len(names_to_delete) > 5:
                confirm_msg += f"\n...等共 {len(names_to_delete)} 件"
            confirm_msg += "\n\n此動作無法復原！"
            
            if sg.popup_yes_no(confirm_msg, title='確認刪除', icon='warning') == 'Yes':
                success_count = 0
                for item_id in ids_to_delete:
                    if wardrobe_mgr.delete_item(item_id):
                        success_count += 1
                
                if len(ids_to_delete) > 1:
                    sg.popup(f'已成功刪除 {success_count} 件衣服。')
                else:
                    sg.popup(f'已刪除 "{names_to_delete[0]}"')
                    
                # 觸發更新
                window.write_event_value('-REFRESH-TABLE-', None)
                window.write_event_value('-REFRESH-ANALYTICS-', None)

        # --- 重新整理列表 ---
        if event == '-REFRESH-TABLE-':
            # 重建 data_list
            data_list = []
            for item in wardrobe_mgr.items:
                status_key = item.get('status', 'available')
                status_text = STATUS_MAP.get(status_key, status_key)
                item_type = item.get('ai', {}).get('type', '')
                category = get_category(item_type)
                
                data_list.append([
                    '☐' if is_batch_mode else '', # Checkbox only if batch mode
                    item['id'], 
                    status_text,
                    category,
                    item['name'], 
                    item_type,
                    item.get('ai', {}).get('color', '')
                ])
            
            # 更新 Table
            window['-WARDROBE-TABLE-'].update(values=data_list)
            window['-WARDROBE-COUNT-'].update(f'目前共有 {len(wardrobe_mgr.items)} 件衣服')
            
            # 更新分類篩選選單 (Dynamic Category Filter)
            new_cats = get_unique_categories(wardrobe_mgr.items)
            current_cat = values['-FILTER-CAT-']
            # 如果原本選的分類還在新的清單中，就保留，否則重置為全部
            if current_cat not in new_cats:
                current_cat = '全部'
            
            window['-FILTER-CAT-'].update(value=current_cat, values=new_cats)
            
            # 重置 current_table_data (因為篩選被清除了，或者需要重新篩選)
            # 簡單起見，我們這裡先清空篩選欄位，顯示全部
            window['-FILTER-TXT-'].update('')
            # window['-FILTER-CAT-'].update('全部') # 已經在上面 update 過了
            current_table_data = data_list

        # --- OOTD Flow ---
        if event == '-GEN-OOTD-PROMPT-':
            weather = values['-OOTD-WEATHER-']
            occasion = values['-OOTD-OCCASION-']
            mood = values['-OOTD-MOOD-']
            
            # if not weather or not occasion:
            #     sg.popup_error('請至少輸入「天氣」與「場合」！')
            #     continue
                
            context = {
                "weather": weather if weather else "不限 (自由發揮)",
                "occasion": occasion if occasion else "不限 (自由發揮)",
                "mood": mood if mood else "不限 (自由發揮)"
            }
            
            prompt = build_ootd_prompt(profile_mgr.data, wardrobe_mgr.items, context)
            window['-OOTD-PROMPT-OUT-'].update(prompt)
            window['-OOTD-RESPONSE-'].update('') # 清空舊的回應
            window['-STATUS-'].update('OOTD Prompt 已產生，請複製給 GPT。')

        if event == '-COPY-OOTD-':
            sg.clipboard_set(values['-OOTD-PROMPT-OUT-'])
            window['-STATUS-'].update('Prompt 已複製到剪貼簿！')

        if event == '-PARSE-OOTD-':
            raw_response = values['-OOTD-RESPONSE-']
            parsed_json = extract_json(raw_response)
            
            if not parsed_json or 'outfits' not in parsed_json:
                sg.popup_error('無法解析 JSON 或找不到 outfits 欄位。')
                continue
            
            # 顯示結果
            outfits = parsed_json['outfits']
            if outfits:
                # 這裡只取第一套做示範，或顯示全部
                # 為了簡單，我們彈出一個視窗顯示建議
                outfit = outfits[0]
                
                # 記錄到 Log
                log_entry = {
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": outfit.get('title', '無標題'),
                    "reason": outfit.get('reason', ''),
                    "item_ids": outfit.get('itemIds', []),
                    "notes": outfit.get('notes', '')
                }
                ootd_mgr.add_log(log_entry)
                
                # 顯示
                # msg = f"✨ 推薦穿搭: {outfit.get('title')}\n\n"
                # msg += f"💡 理由: {outfit.get('reason')}\n\n"
                # msg += f"🧥 單品: {', '.join(outfit.get('itemIds', []))}\n\n"
                # msg += f"📝 筆記: {outfit.get('notes')}"
                # sg.popup_scrolled(msg, title='OOTD 建議', size=(50, 10))
                
                # show_ootd_result_window(outfit, wardrobe_mgr)
                show_ootd_result_window(outfit, wardrobe_mgr, profile_mgr)
                
                window['-STATUS-'].update('OOTD 解析成功並已記錄！')
                window.write_event_value('-REFRESH-CALENDAR-', None)



        # --- 數據分析更新 ---
        if event == '-REFRESH-ANALYTICS-' or event == '-BASE-CURRENCY-':
            base_curr = values.get('-BASE-CURRENCY-', 'TWD')
            total_value = 0
            total_count = len(wardrobe_mgr.items)
            cp_list = []
            
            for item in wardrobe_mgr.items:
                price = item.get('price', 0)
                currency = item.get('currency', 'TWD')
                wear_count = item.get('wear_count', 0)
                
                # 統一轉換為 Base Currency 計算
                price_in_base = currency_mgr.convert(price, currency, base_curr)
                
                total_value += price_in_base
                
                # 計算 CP 值 (每次成本)
                # 如果沒穿過，成本 = 原價
                cost_per_wear = price_in_base if wear_count == 0 else price_in_base / wear_count
                
                cp_list.append({
                    'name': item['name'],
                    'price_display': f"{currency} {price}",
                    'price_base': price_in_base,
                    'wear_count': wear_count,
                    'cp': cost_per_wear
                })
            
            avg_price = total_value / total_count if total_count > 0 else 0
            
            # 更新統計數字
            window['-TOTAL-VALUE-'].update(f'{base_curr} {int(total_value):,}')
            window['-AVG-PRICE-'].update(f'{base_curr} {int(avg_price):,}')
            window['-TOTAL-COUNT-'].update(str(total_count))
            
            # 更新 CP 值排行
            cp_list.sort(key=lambda x: x['cp'])
            
            table_data = [[x['name'], x['price_display'], x['wear_count'], f"{base_curr} {int(x['cp'])}"] for x in cp_list[:10]]
            window['-CP-TABLE-'].update(values=table_data)

        # --- 穿搭日曆更新 ---
        if event == '-REFRESH-CALENDAR-':
            calendar_data = []
            # 反向排序，最新的在上面
            for log in reversed(ootd_mgr.logs):
                # 組合單品名稱
                item_names = []
                for iid in log.get('item_ids', []):
                    found = next((x for x in wardrobe_mgr.items if x['id'] == iid), None)
                    if found:
                        item_names.append(found['name'])
                
                calendar_data.append([
                    log.get('date', ''),
                    log.get('title', ''),
                    ", ".join(item_names)
                ])
            window['-CALENDAR-TABLE-'].update(values=calendar_data)

        # --- 查看日曆詳情 ---
        if event == '-CALENDAR-TABLE-+DOUBLE_CLICK+':
            if not values['-CALENDAR-TABLE-']:
                continue
            
            row_idx = values['-CALENDAR-TABLE-'][0]
            # calendar_data 是反向排序的，所以要對應回 logs
            # logs: [old, ..., new]
            # calendar: [new, ..., old]
            # log_idx = len(logs) - 1 - row_idx
            
            if row_idx < len(ootd_mgr.logs):
                log_idx = len(ootd_mgr.logs) - 1 - row_idx
                log = ootd_mgr.logs[log_idx]
                
                # 重建 outfit 物件
                outfit = {
                    'title': log.get('title'),
                    'reason': log.get('reason'),
                    'itemIds': log.get('item_ids'),
                    'notes': log.get('notes')
                }
                
                show_ootd_result_window(outfit, wardrobe_mgr, profile_mgr)

        # --- 查看單品詳情 (View Item) ---
        if event == '-VIEW-ITEM-' or event == '-WARDROBE-TABLE-+DOUBLE_CLICK+':
            selected_rows = values['-WARDROBE-TABLE-']
            if not selected_rows:
                # 如果是按鈕觸發且沒選，提示錯誤。如果是雙擊，通常會有選取，但保險起見。
                if event == '-VIEW-ITEM-':
                    sg.popup_error('請先選擇一件衣服！')
                continue
            
            # 取得選取項目的 ID (Table 的第一欄)
            # 注意: values['-WARDROBE-TABLE-'] 回傳的是 row index list
            # 我們需要從 data_list 或是目前的 table values 中取得 ID
            # 由於有篩選功能，table 的顯示順序可能跟 wardrobe_mgr.items 不同
            # 最穩的方式是讀取 table 目前的 values
            
            # 使用 current_table_data 取代 window.get()
            # current_table_values = window['-WARDROBE-TABLE-'].get() 
            
            if not selected_rows:
                continue
                
            row_idx = selected_rows[0]
            if row_idx < len(current_table_data):
                row_data = current_table_data[row_idx]
                item_id = row_data[1] # ID 在第二欄 (index 1)
                
                target_item = next((x for x in wardrobe_mgr.items if x['id'] == item_id), None)
                if target_item:
                    # 顯示詳情視窗
                    ai_data = target_item.get('ai', {})
                    
                    # 圖片處理
                    img_elem = sg.Image(data=None, size=(300, 300), background_color='#1E1E1E')
                    if HAS_PIL and target_item.get('image_path') and os.path.exists(target_item['image_path']):
                        try:
                            pil_img = Image.open(target_item['image_path'])
                            pil_img.thumbnail((300, 300))
                            bio = io.BytesIO()
                            pil_img.save(bio, format="PNG")
                            img_elem = sg.Image(data=bio.getvalue(), background_color='#1E1E1E', enable_events=True, key='-VIEW-IMG-', tooltip='點擊放大')
                        except:
                            pass

                    detail_layout = [
                        [sg.Text(target_item.get('name', '未命名'), font=('Segoe UI', 18, 'bold'), text_color='#D4AF37', background_color='#1E1E1E')],
                        [sg.HorizontalSeparator()],
                        [sg.Column([[img_elem]], background_color='#1E1E1E'),
                         sg.Column([
                             [sg.Text(f"ID: {target_item.get('id')}", text_color='#757575', background_color='#1E1E1E')],
                             [sg.Text(f"分類: {ai_data.get('type', '未知')}", font=FONT_NORMAL, background_color='#1E1E1E')],
                             [sg.Text(f"顏色: {ai_data.get('color', '未知')}", font=FONT_NORMAL, background_color='#1E1E1E')],
                             [sg.Text(f"尺寸: {target_item.get('size', '')}", font=FONT_NORMAL, background_color='#1E1E1E')],
                             [sg.Text(f"價格: {target_item.get('currency', 'TWD')} {target_item.get('price', 0)}", font=FONT_NORMAL, text_color='#81C784', background_color='#1E1E1E')],
                             [sg.Text(f"穿著次數: {target_item.get('wear_count', 0)}", font=FONT_NORMAL, background_color='#1E1E1E')],
                             [sg.Text("風格標籤:", text_color='#D4AF37', background_color='#1E1E1E')],
                             [sg.Text(", ".join(ai_data.get('styleTags', [])), size=(30, 2), background_color='#1E1E1E')],
                             [sg.Text("備註:", text_color='#D4AF37', background_color='#1E1E1E')],
                             [sg.Multiline(target_item.get('user_notes', ''), size=(30, 3), disabled=True, background_color='#2C2C2C', text_color='white', border_width=0)]
                         ], vertical_alignment='top', background_color='#1E1E1E')]
                    ]
                    
                    view_window = sg.Window('單品詳情', [[card_frame('', detail_layout)]], 
                                          modal=True, background_color=THEME_COLORS['BACKGROUND'], finalize=True)
                    
                    while True:
                        e, v = view_window.read()
                        if e == sg.WIN_CLOSED:
                            break
                        
                        if e == '-VIEW-IMG-':
                            # 放大圖片
                            if target_item.get('image_path') and os.path.exists(target_item['image_path']):
                                large_bytes = resize_image_to_bytes(target_item['image_path'], (800, 800))
                                if large_bytes:
                                    sg.Window(f"檢視圖片: {target_item['name']}", 
                                              [[sg.Image(data=large_bytes)], [sg.Button('關閉')]], 
                                              modal=True).read(close=True)
                    
                    view_window.close()

        # --- 標記為可用 (歸還) ---
        if event == '-MARK-AVAILABLE-':
            selected_rows = values['-WARDROBE-TABLE-']
            if not selected_rows:
                sg.popup_error('請先選擇衣服！')
                continue
            
            # 使用 current_table_data 確保拿到正確的 ID
            if not current_table_data:
                 current_table_data = data_list
            
            row_idx = selected_rows[0]
            if row_idx < len(current_table_data):
                row_data = current_table_data[row_idx]
                item_id = row_data[0]
                
                wardrobe_mgr.set_status(item_id, 'available')
                sg.popup('已標記為「在衣櫃」！')
                window.write_event_value('-REFRESH-TABLE-', None)



    window.close()

if __name__ == '__main__':
    main()
