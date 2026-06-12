# Multilingual Support

The Streamlit UI uses `translations.py` for all visible labels, buttons, alerts, page headings, table headers, and report export headers.

## Current Languages

- English: `en`
- Hindi: `hi`
- Telugu: `te`

The selected language is stored in `st.session_state.language`, so it remains active while users navigate between pages and after logout.

## How to Add Another Indian Language

1. Open `translations.py`.
2. Add the display name and language code to `LANGUAGE_OPTIONS`.

```python
LANGUAGE_OPTIONS = {
    "English": "en",
    "हिन्दी": "hi",
    "తెలుగు": "te",
    "தமிழ்": "ta",
}
```

3. Copy the English dictionary inside `translations`.
4. Paste it as a new entry using the new language code.
5. Translate every value, but keep the keys exactly the same.

```python
translations = {
    "en": {...},
    "hi": {...},
    "te": {...},
    "ta": {
        "app_title": "வருகைப் பதிவேடு",
        "dashboard": "டாஷ்போர்டு",
        ...
    },
}
```

6. Restart Streamlit.

## Important Notes

- Do not translate database values such as `Present`, `Absent`, `Excused`, `Admin`, `Teacher`, `Active`, and `Archived`. The app translates them only for display.
- CSV reports include a UTF-8 BOM so Hindi, Telugu, and other Indian-language text opens correctly in spreadsheet tools.
- If a new UI label is added in `app.py`, add a matching key to every language in `translations.py` and display it with `t("your_key")`.
