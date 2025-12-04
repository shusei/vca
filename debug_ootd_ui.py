import FreeSimpleGUI as sg
import os

# Mock dependencies
FONT_TITLE = ('Segoe UI', 24, 'bold')
FONT_HEADER = ('Segoe UI', 14, 'bold')
FONT_NORMAL = ('Segoe UI', 11)
FONT_SMALL = ('Segoe UI', 9)
HAS_PIL = False

def card_frame(title, layout, font=FONT_HEADER):
    return sg.Frame(title, layout, font=font, title_color='#E0E0E0', pad=((0,0), (0, 10)), border_width=0, background_color='#1E1E1E')

def resize_image_to_bytes(image_path, size):
    return None

def export_ootd_zip(outfit, wardrobe_mgr, profile_mgr):
    sg.popup('Export triggered!')

class MockManager:
    def __init__(self):
        self.items = []
        self.data = {'body_photo_path': 'test.png'}

def show_ootd_result_window(outfit, wardrobe_mgr, profile_mgr=None):
    # Copy of the function from wardrobe_app.py
    item_ids = outfit.get('itemIds', [])
    items_ui = []
    
    for iid in item_ids:
        # Mock item
        item = {'name': 'Test Item', 'ai': {'type': 'Top'}}
        
        img_data = None
        
        img_key = f'-IMG-{iid}-'
        img_elem = sg.Text('無圖片', size=(20,10), justification='center', background_color='#2C2C2C')
        
        card_col = sg.Column([
            [img_elem],
            [sg.Text(item['name'], size=(20, 1), justification='center', font=('Segoe UI', 11, 'bold'), background_color='#1E1E1E', text_color='#D4AF37')],
            [sg.Text(item.get('ai', {}).get('type', ''), size=(20, 1), justification='center', font=FONT_SMALL, background_color='#1E1E1E', text_color='#9E9E9E')]
        ], background_color='#1E1E1E', pad=(10, 10), element_justification='center')
        
        items_ui.append(card_col)
    
    if not items_ui:
        items_ui = [sg.Text('找不到對應的單品資料', text_color='#E0E0E0', background_color='#1E1E1E', font=FONT_NORMAL)]
    
    layout = [
        [sg.Text('✨ 今日穿搭推薦 ✨', font=('Segoe UI', 28, 'bold'), text_color='#D4AF37', background_color='#121212', justification='center', expand_x=True, pad=((0,0), (20, 10)))],
        [sg.Text(outfit.get('title', '無標題'), font=('Segoe UI', 20, 'bold'), text_color='#FFFFFF', background_color='#121212', justification='center', expand_x=True, pad=((0,0), (0, 20)))],
        [sg.HorizontalSeparator(color='#D4AF37')],
        
        [sg.Column([items_ui], scrollable=True, vertical_scroll_only=False, size=(900, 280), background_color='#121212', pad=((0,0), (20, 20)))],
        
        [card_frame(' 💡 推薦理由 ', [[sg.Multiline(outfit.get('reason', ''), size=(90, 5), font=('Segoe UI', 12), disabled=True, background_color='#1E1E1E', text_color='#E0E0E0', border_width=0)]])],
        [card_frame(' 📝 穿搭筆記 ', [[sg.Multiline(outfit.get('notes', ''), size=(90, 4), font=('Segoe UI', 12), disabled=True, background_color='#1E1E1E', text_color='#E0E0E0', border_width=0)]])],
        
        [sg.Button('📦 匯出 ZIP', key='-EXPORT-ZIP-', font=FONT_HEADER, size=(15,1), button_color=('white', '#1565C0'), border_width=0, pad=((0,0), (20, 20))),
         sg.Button('關閉', key='-CLOSE-', font=FONT_HEADER, size=(15,1), button_color=('white', '#424242'), border_width=0, pad=((10,0), (20, 20)))]
    ]
    
    win = sg.Window('OOTD Result', layout, modal=True, background_color='#121212', finalize=True, resizable=True, size=(1000, 800))
    
    while True:
        event, values = win.read()
        if event in (sg.WIN_CLOSED, '-CLOSE-'):
            break
        if event == '-EXPORT-ZIP-':
            export_ootd_zip(None, None, None)
            
    win.close()

if __name__ == '__main__':
    dummy_outfit = {
        'title': 'Test Outfit',
        'reason': 'Testing UI',
        'notes': 'Check for button',
        'itemIds': ['1', '2']
    }
    show_ootd_result_window(dummy_outfit, MockManager(), MockManager())
