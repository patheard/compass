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
    return os.path.join(os.path.dirname(__file__), 'locales')

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

def get_user_preferred_language(accept_language: Optional[str] = None) -> str:
    """Determine user's preferred language from Accept-Language header."""
    if not accept_language:
        return DEFAULT_LANGUAGE
    
    # Simple language detection - check if French is preferred
    if 'fr' in accept_language.lower():
        return 'fr'
    
    return DEFAULT_LANGUAGE