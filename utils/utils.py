import json

# Load locale files
with open("locales/en.json", "r", encoding="utf-8") as f:
    en = json.load(f)
with open("locales/ko.json", "r", encoding="utf-8") as f:
    ko = json.load(f)
with open("locales/ja.json", "r", encoding="utf-8") as f:
    ja = json.load(f)
with open("locales/zh.json", "r", encoding="utf-8") as f:
    zh = json.load(f)

# Dictionary to map locale to translations
translations = {"en": en, "ko": ko, "ja": ja, "zh": zh}

def get_translation(key, locale="en", **kwargs):
    """
    Get the translation for the given key and locale.
    If the key does not exist, return the key itself.
    """
    locale_translations = translations.get(locale, en)  # Default to English
    translation = locale_translations.get(key, key)
    return translation.format(**kwargs)

def ellipsis(text, max_length=40):
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text
