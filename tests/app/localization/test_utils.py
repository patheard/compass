"""Unit tests for localization utilities."""

from unittest.mock import MagicMock, patch

from babel.support import Translations
from jinja2 import Environment

from app.localization.utils import (
    DEFAULT_LANGUAGE,
    configure_jinja_i18n,
    get_locale_path,
    get_translation_function,
    get_user_preferred_language,
    load_translations,
    parse_accept_language,
)


class TestGetLocalePath:
    """Tests for get_locale_path function."""

    def test_get_locale_path_returns_string(self) -> None:
        """Test that get_locale_path returns a string."""
        path = get_locale_path()
        assert isinstance(path, str)

    def test_get_locale_path_contains_locales(self) -> None:
        """Test that returned path contains 'locales' directory."""
        path = get_locale_path()
        assert "locales" in path

    def test_get_locale_path_is_absolute(self) -> None:
        """Test that returned path is absolute."""
        path = get_locale_path()
        assert path.startswith("/") or ":" in path


class TestParseAcceptLanguage:
    """Tests for parse_accept_language function."""

    def test_parse_empty_header(self) -> None:
        """Test parsing empty Accept-Language header."""
        result = parse_accept_language(None)
        assert result == []

    def test_parse_single_language(self) -> None:
        """Test parsing single language without quality."""
        result = parse_accept_language("en")
        assert result == [("en", 1.0)]

    def test_parse_single_language_with_quality(self) -> None:
        """Test parsing single language with quality value."""
        result = parse_accept_language("fr;q=0.8")
        assert result == [("fr", 0.8)]

    def test_parse_multiple_languages(self) -> None:
        """Test parsing multiple languages."""
        result = parse_accept_language("en,fr")
        assert len(result) == 2
        assert ("en", 1.0) in result
        assert ("fr", 1.0) in result

    def test_parse_multiple_languages_with_quality(self) -> None:
        """Test parsing multiple languages with quality values."""
        result = parse_accept_language("en;q=0.9,fr;q=0.8")
        assert result == [("en", 0.9), ("fr", 0.8)]

    def test_parse_languages_sorted_by_quality(self) -> None:
        """Test that languages are sorted by quality score."""
        result = parse_accept_language("fr;q=0.8,en;q=1.0")
        assert result[0] == ("en", 1.0)
        assert result[1] == ("fr", 0.8)

    def test_parse_language_with_country_code(self) -> None:
        """Test parsing language with country code extracts base language."""
        result = parse_accept_language("en-US")
        assert result == [("en", 1.0)]

    def test_parse_complex_accept_language(self) -> None:
        """Test parsing complex Accept-Language header."""
        result = parse_accept_language("en-US,en;q=0.9,fr;q=0.8,de;q=0.7")
        assert result[0][0] == "en"
        assert result[1][0] == "en"
        assert result[2][0] == "fr"

    def test_parse_invalid_language_filtered(self) -> None:
        """Test that invalid languages are filtered out."""
        result = parse_accept_language("es,en")
        assert len(result) == 1
        assert result[0] == ("en", 1.0)

    def test_parse_invalid_quality_defaults_to_one(self) -> None:
        """Test that invalid quality value defaults to 1.0."""
        result = parse_accept_language("en;q=invalid")
        assert result == [("en", 1.0)]

    def test_parse_whitespace_handling(self) -> None:
        """Test that whitespace is properly handled."""
        result = parse_accept_language(" en , fr ;q=0.8 ")
        assert len(result) == 2
        assert ("en", 1.0) in result
        assert ("fr", 0.8) in result


class TestGetUserPreferredLanguage:
    """Tests for get_user_preferred_language function."""

    def test_default_language_when_no_preferences(self) -> None:
        """Test that default language is returned when no preferences provided."""
        result = get_user_preferred_language()
        assert result == DEFAULT_LANGUAGE

    def test_session_preference_takes_priority(self) -> None:
        """Test that session preference takes priority over Accept-Language."""
        result = get_user_preferred_language(
            accept_language="en", session_preference="fr"
        )
        assert result == "fr"

    def test_accept_language_used_when_no_session(self) -> None:
        """Test that Accept-Language is used when no session preference."""
        result = get_user_preferred_language(accept_language="fr")
        assert result == "fr"

    def test_invalid_session_preference_ignored(self) -> None:
        """Test that invalid session preference is ignored."""
        result = get_user_preferred_language(
            accept_language="en", session_preference="es"
        )
        assert result == "en"

    def test_highest_quality_language_selected(self) -> None:
        """Test that highest quality language is selected from Accept-Language."""
        result = get_user_preferred_language(accept_language="fr;q=0.9,en;q=0.8")
        assert result == "fr"

    def test_fallback_to_default_on_invalid_accept_language(self) -> None:
        """Test fallback to default when Accept-Language has no valid languages."""
        result = get_user_preferred_language(accept_language="es,de")
        assert result == DEFAULT_LANGUAGE

    def test_session_preference_must_be_valid(self) -> None:
        """Test that session preference must be in LANGUAGES list."""
        result = get_user_preferred_language(session_preference="invalid")
        assert result == DEFAULT_LANGUAGE


class TestLoadTranslations:
    """Tests for load_translations function."""

    @patch("app.localization.utils.Translations.load")
    def test_load_translations_for_english(self, mock_load: MagicMock) -> None:
        """Test loading translations for English."""
        mock_translations = MagicMock(spec=Translations)
        mock_load.return_value = mock_translations

        with patch.dict("app.localization.utils._translations", {}, clear=True):
            result = load_translations("en")
            assert result == mock_translations
            mock_load.assert_called_once()

    @patch("app.localization.utils.Translations.load")
    def test_load_translations_for_french(self, mock_load: MagicMock) -> None:
        """Test loading translations for French."""
        mock_translations = MagicMock(spec=Translations)
        mock_load.return_value = mock_translations

        with patch.dict("app.localization.utils._translations", {}, clear=True):
            result = load_translations("fr")
            assert result == mock_translations
            mock_load.assert_called_once()

    @patch("app.localization.utils.Translations.load")
    def test_load_translations_caching(self, mock_load: MagicMock) -> None:
        """Test that translations are cached after first load."""
        mock_translations = MagicMock(spec=Translations)
        mock_load.return_value = mock_translations

        with patch.dict("app.localization.utils._translations", {}, clear=True):
            result1 = load_translations("en")
            result2 = load_translations("en")

            assert result1 == result2
            mock_load.assert_called_once()

    @patch("app.localization.utils.Translations.load")
    def test_load_translations_invalid_language_fallback(
        self, mock_load: MagicMock
    ) -> None:
        """Test that invalid language falls back to default."""
        mock_translations = MagicMock(spec=Translations)
        mock_load.return_value = mock_translations

        with patch.dict("app.localization.utils._translations", {}, clear=True):
            result = load_translations("invalid")
            assert result == mock_translations
            args = mock_load.call_args[0]
            assert DEFAULT_LANGUAGE in args[1]

    @patch("app.localization.utils.Translations.load")
    def test_load_translations_returns_none_on_failure(
        self, mock_load: MagicMock
    ) -> None:
        """Test that None is returned when translations cannot be loaded."""
        mock_load.return_value = None

        with patch.dict("app.localization.utils._translations", {}, clear=True):
            result = load_translations("en")
            assert result is None


class TestGetTranslationFunction:
    """Tests for get_translation_function function."""

    @patch("app.localization.utils.load_translations")
    def test_get_translation_function_with_translations(
        self, mock_load: MagicMock
    ) -> None:
        """Test getting translation function when translations exist."""
        mock_translations = MagicMock(spec=Translations)
        mock_translations.gettext = lambda x: f"translated_{x}"
        mock_load.return_value = mock_translations

        func = get_translation_function("en")
        assert callable(func)
        assert func == mock_translations.gettext

    @patch("app.localization.utils.load_translations")
    def test_get_translation_function_fallback(self, mock_load: MagicMock) -> None:
        """Test that fallback identity function is returned when no translations."""
        mock_load.return_value = None

        func = get_translation_function("en")
        assert callable(func)
        assert func("test") == "test"

    @patch("app.localization.utils.load_translations")
    def test_get_translation_function_without_gettext(
        self, mock_load: MagicMock
    ) -> None:
        """Test fallback when translations object lacks gettext method."""
        mock_translations = MagicMock(spec=Translations)
        delattr(mock_translations, "gettext")
        mock_load.return_value = mock_translations

        func = get_translation_function("en")
        assert callable(func)
        assert func("test") == "test"


class TestConfigureJinjaI18n:
    """Tests for configure_jinja_i18n function."""

    @patch("app.localization.utils.get_translation_function")
    def test_configure_jinja_i18n_adds_translation_function(
        self, mock_get_translation: MagicMock
    ) -> None:
        """Test that translation function is added to Jinja environment."""

        def mock_func(x: str) -> str:
            return f"translated_{x}"

        mock_get_translation.return_value = mock_func

        env = Environment()
        configure_jinja_i18n(env, "en")

        assert "_" in env.globals
        assert env.globals["_"] == mock_func

    @patch("app.localization.utils.get_translation_function")
    def test_configure_jinja_i18n_adds_get_locale(
        self, mock_get_translation: MagicMock
    ) -> None:
        """Test that get_locale function is added to Jinja environment."""
        mock_get_translation.return_value = lambda x: x

        env = Environment()
        configure_jinja_i18n(env, "fr")

        assert "get_locale" in env.globals
        assert callable(env.globals["get_locale"])
        assert env.globals["get_locale"]() == "fr"

    @patch("app.localization.utils.get_translation_function")
    def test_configure_jinja_i18n_default_language(
        self, mock_get_translation: MagicMock
    ) -> None:
        """Test configure_jinja_i18n with default language."""
        mock_get_translation.return_value = lambda x: x

        env = Environment()
        configure_jinja_i18n(env)

        assert env.globals["get_locale"]() == DEFAULT_LANGUAGE
        mock_get_translation.assert_called_once_with(DEFAULT_LANGUAGE)

    @patch("app.localization.utils.get_translation_function")
    def test_configure_jinja_i18n_custom_language(
        self, mock_get_translation: MagicMock
    ) -> None:
        """Test configure_jinja_i18n with custom language."""
        mock_get_translation.return_value = lambda x: x

        env = Environment()
        configure_jinja_i18n(env, "fr")

        assert env.globals["get_locale"]() == "fr"
        mock_get_translation.assert_called_once_with("fr")
