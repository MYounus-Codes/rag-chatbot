"""
Language utilities for detection, translation, and formatting.
"""

from typing import Optional
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

from ..core.constants import LANGUAGE_MAP, SUPPORTED_LANGUAGES


def detect_language(text: str) -> str:
    """
    Detect the language of the input text.
    Returns ISO 639-1 code (en, fr, de, it, es, da).
    Defaults to English if detection fails.
    """
    if not text or len(text.strip()) < 3:
        return "en"
    
    try:
        detected = detect(text)
        # Map detected language to supported languages
        if detected in SUPPORTED_LANGUAGES:
            return detected
        return "en"
    except LangDetectException:
        return "en"
    except Exception:
        return "en"


def get_language_name(lang_code: str) -> str:
    """Get full language name from ISO code."""
    return LANGUAGE_MAP.get(lang_code, "English")


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Translate text to the target language.
    Returns original text if translation fails.
    """
    if not text:
        return text
    
    if target_lang == source_lang:
        return text
    
    if target_lang == "en" and source_lang == "en":
        return text
    
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def translate_to_english(text: str) -> str:
    """Translate text to English."""
    return translate_text(text, target_lang="en", source_lang="auto")


def get_localized_greeting(lang_code: str, username: str = "there") -> str:
    """Get a localized greeting message."""
    greetings = {
        "en": f"Hello {username}! How can I help you today?",
        "fr": f"Bonjour {username}! Comment puis-je vous aider aujourd'hui?",
        "de": f"Hallo {username}! Wie kann ich Ihnen heute helfen?",
        "it": f"Ciao {username}! Come posso aiutarti oggi?",
        "es": f"¡Hola {username}! ¿Cómo puedo ayudarte hoy?",
        "da": f"Hej {username}! Hvordan kan jeg hjælpe dig i dag?"
    }
    return greetings.get(lang_code, greetings["en"])


def get_localized_error(lang_code: str, error_type: str = "general") -> str:
    """Get a localized error message."""
    errors = {
        "general": {
            "en": "I apologize, but I encountered an error. Please try again.",
            "fr": "Je m'excuse, mais j'ai rencontré une erreur. Veuillez réessayer.",
            "de": "Entschuldigung, es ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
            "it": "Mi scuso, ma ho riscontrato un errore. Riprova.",
            "es": "Lo siento, pero encontré un error. Por favor, inténtalo de nuevo.",
            "da": "Beklager, men jeg stødte på en fejl. Prøv igen."
        },
        "not_found": {
            "en": "I couldn't find information about that. Could you please rephrase your question?",
            "fr": "Je n'ai pas trouvé d'informations à ce sujet. Pouvez-vous reformuler votre question?",
            "de": "Ich konnte dazu keine Informationen finden. Können Sie Ihre Frage umformulieren?",
            "it": "Non ho trovato informazioni al riguardo. Puoi riformulare la tua domanda?",
            "es": "No pude encontrar información sobre eso. ¿Podrías reformular tu pregunta?",
            "da": "Jeg kunne ikke finde oplysninger om det. Kan du omformulere dit spørgsmål?"
        }
    }
    
    error_messages = errors.get(error_type, errors["general"])
    return error_messages.get(lang_code, error_messages["en"])
