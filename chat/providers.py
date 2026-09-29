import os
from dataclasses import dataclass

from chat.models import Provider


@dataclass(frozen=True)
class ModelOption:
    provider_id: str
    provider_label: str
    model_id: str
    model_label: str
    key_environment_variable: str


MODEL_OPTIONS = (
    ModelOption(
        provider_id=Provider.OPENAI,
        provider_label="OpenAI API",
        model_id="gpt-5.6-luna",
        model_label="gpt-5.6-luna",
        key_environment_variable="BUILD_OPENAI_KEY",
    ),
    ModelOption(
        provider_id=Provider.ANTHROPIC,
        provider_label="Anthropic API",
        model_id="claude-haiku-4-5-20251001",
        model_label="claude-haiku-4-5-20251001",
        key_environment_variable="BUILD_ANTHROPIC_KEY",
    ),
    ModelOption(
        provider_id=Provider.GOOGLE,
        provider_label="Google Gemini API",
        model_id="gemini-3.8-flash",
        model_label="gemini-3.8-flash",
        key_environment_variable="BUILD_GOOGLE_KEY",
    ),
)


def list_model_options():
    return [
        {
            "provider_id": option.provider_id,
            "provider_label": option.provider_label,
            "model_id": option.model_id,
            "model_label": option.model_label,
            "configured": bool(os.environ.get(option.key_environment_variable)),
        }
        for option in MODEL_OPTIONS
    ]


def get_model_option(provider_id, model_id):
    for option in MODEL_OPTIONS:
        if option.provider_id == provider_id and option.model_id == model_id:
            return option
    return None
