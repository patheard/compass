"""Localization utilities for the Compass application."""

import os
from babel import Locale
from babel.support import Translations
from typing import Optional
from jinja2 import Environment

# Available languages
LANGUAGES = ['en', 'fr']
DEFAULT_LANGUAGE = 'en'

# Store loaded translations
_translations: dict[str, Translations] = {}

def get_locale_path() -> str:
    """Get the path to the locales directory."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locales')

def load_translations(language: str) -> Optional[Translations]:
    """Load translations for a specific language."""
    if language in _translations:
        return _translations[language]
    
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    locale_path = get_locale_path()
    translations = Translations.load(locale_path, [language], domain='messages')
    
    if translations:
        _translations[language] = translations
        return translations
    
    return None

def get_translation_function(language: str):
    """Get a translation function for a specific language."""
    translations = load_translations(language)
    
    if translations and hasattr(translations, 'gettext'):
        return translations.gettext
    
    # Fallback to identity function if no translations found
    return lambda x: x

def configure_jinja_i18n(env: Environment, language: str = DEFAULT_LANGUAGE) -> None:
    """Configure Jinja2 environment with internationalization support."""
    # Add custom template functions
    env.globals['_'] = get_translation_function(language)
    env.globals['get_locale'] = lambda: language

def parse_accept_language(accept_language: Optional[str] = None) -> list[tuple[str, float]]:
    """Parse Accept-Language header and return ordered list of (language, quality) pairs."""
    if not accept_language:
        return []
    
    languages = []
    for lang_range in accept_language.split(','):
        lang_range = lang_range.strip()
        if ';q=' in lang_range:
            lang, quality = lang_range.split(';q=', 1)
            try:
                quality = float(quality)
            except ValueError:
                quality = 1.0
        else:
            lang = lang_range
            quality = 1.0
        
        # Extract just the language part (ignore country codes for now)
        lang_code = lang.strip().split('-')[0].lower()
        if lang_code in LANGUAGES:
            languages.append((lang_code, quality))
    
    # Sort by quality score (highest first)
    return sorted(languages, key=lambda x: x[1], reverse=True)

def get_user_preferred_language(
    accept_language: Optional[str] = None,
    session_preference: Optional[str] = None
) -> str:
    """Determine user's preferred language from multiple sources."""
    # Priority order: session preference > Accept-Language > default
    
    # 1. Session preference (for users who have set a preference)
    if session_preference and session_preference in LANGUAGES:
        return session_preference
    
    # 2. Accept-Language header
    if accept_language:
        parsed_languages = parse_accept_language(accept_language)
        if parsed_languages:
            return parsed_languages[0][0]  # Return the highest quality language
    
    # 3. Default language
    return DEFAULT_LANGUAGE