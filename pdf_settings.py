import json
import os
from pathlib import Path

SETTINGS_FILE = "pdf_settings.json"

DEFAULT_SETTINGS = {
    "templates": {
        "mcq_bg": "",
        "notes_bg": "",
        "use_templates": True
    },
    "layout": {
        "margin_top": 20,
        "margin_bottom": 25,
        "margin_left": 20,
        "margin_right": 20,
        "font_family": "Helvetica",
        "title_size": 18,
        "question_size": 10,
        "option_size": 9.5,
        "explanation_size": 9,
        "explanation_bg_color": "#eff6ff",
        "explanation_text_color": "#1e293b",
        "explanation_padding": 6
    },
    "header": {
        "enabled": True,
        "text": "",
        "url": "",
        "color": "#1a1a2e",
        "font_size": 8,
        "show_line": True
    },
    "footer": {
        "enabled": True,
        "text": "— {page_num} —",
        "url": "",
        "color": "#2d3748",
        "font_size": 7.5,
        "show_line": True
    },
    "first_page": {
        "enabled": False,
        "content_text": "Welcome to our Premium Material!",
        "bg_image": ""
    },
    "last_page": {
        "enabled": False,
        "content_text": "Thank you for studying with us!",
        "bg_image": ""
    }
}

class PDFSettingsManager:
    def __init__(self, config_path=SETTINGS_FILE):
        self.config_path = config_path
        self.settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.config_path):
            return DEFAULT_SETTINGS.copy()
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged = DEFAULT_SETTINGS.copy()
                for section in merged:
                    if section in data:
                        merged[section].update(data[section])
                return merged
        except Exception as e:
            print(f"Error loading PDF settings: {e}")
            return DEFAULT_SETTINGS.copy()

    def save_settings(self, new_settings):
        self.settings = new_settings
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving PDF settings: {e}")
            return False

    def get(self, section, key=None):
        if section not in self.settings:
            return None
        if key:
            return self.settings[section].get(key)
        return self.settings[section]
