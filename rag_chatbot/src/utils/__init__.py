# Utils module - guardrails, language, helpers

# Lazy imports to avoid module errors when packages aren't installed
def _get_guardrails():
    from .guardrails import InputGuardrail, OutputGuardrail
    return InputGuardrail, OutputGuardrail

def _get_language_utils():
    from .language import detect_language, get_language_name, translate_text
    return detect_language, get_language_name, translate_text

# Export for direct imports
__all__ = [
    "InputGuardrail",
    "OutputGuardrail", 
    "detect_language",
    "get_language_name",
    "translate_text"
]
