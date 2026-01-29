import os
import json
import re
import datetime

WARDROBE_FILE = 'wardrobe.json'
IMAGE_DIR = 'images'

def recover_data():
    if not os.path.exists(IMAGE_DIR):
        print(f"Error: Image directory '{IMAGE_DIR}' not found.")
        return

    recovered_items = []
    
    # Regex to parse filename: Name_Date_Index.ext
    # Example: 寬版長褲_20251203_001.png
    # Some might be just Name.png or have different formats, we'll try to be flexible
    
    print(f"Scanning {IMAGE_DIR}...")
    
    for filename in os.listdir(IMAGE_DIR):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            continue
            
        if filename == 'user_body.png':
            continue

        name_part = os.path.splitext(filename)[0]
        
        # Try to extract ID parts
        # Assuming format: Name_YYYYMMDD_NNN
        # If we can't parse it perfectly, we'll just use the filename as ID and Name
        
        item_id = name_part
        item_name = name_part
        purchase_date = datetime.date.today().strftime('%Y-%m-%d')
        
        # Simple heuristic parsing
        parts = name_part.split('_')
        if len(parts) >= 3 and len(parts[-2]) == 8 and parts[-2].isdigit():
            # Likely Name_Date_Index
            item_name = "_".join(parts[:-2])
            date_str = parts[-2]
            try:
                purchase_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            except:
                pass
        
        item = {
            "id": item_id,
            "name": item_name,
            "image": os.path.join(IMAGE_DIR, filename),
            "type": "Unknown", # We don't know the type from filename usually, unless we use AI to classify again.
            "category": "Unknown",
            "purchase_date": purchase_date,
            "price": 0,
            "currency": "TWD",
            "brand": "",
            "material": "",
            "season": "四季",
            "occasion": "日常",
            "color": "Unknown",
            "status": "available",
            "notes": "Recovered from image file"
        }
        
        recovered_items.append(item)
        print(f"Recovered: {item_name} (ID: {item_id})")

    print(f"Total items recovered: {len(recovered_items)}")
    
    if recovered_items:
        # Backup existing if it has content (unlikely based on previous check, but good practice)
        if os.path.exists(WARDROBE_FILE) and os.path.getsize(WARDROBE_FILE) > 2:
            backup_name = f"{WARDROBE_FILE}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            os.rename(WARDROBE_FILE, backup_name)
            print(f"Backed up existing wardrobe.json to {backup_name}")
            
        with open(WARDROBE_FILE, 'w', encoding='utf-8') as f:
            json.dump(recovered_items, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote to {WARDROBE_FILE}")
    else:
        print("No items found to recover.")

if __name__ == "__main__":
    recover_data()
