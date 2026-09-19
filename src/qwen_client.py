"""TCET Centre of Excellence Qwen AI Gateway Client.

Provides configuration, initialization, and health checks for the official
TCET CoE AI Gateway (Qwen3.6-35B-A3B) using the OpenAI-compatible protocol.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
    for env_file in ("ai.env", ".env.local", ".env"):
        if os.path.exists(env_file):
            load_dotenv(env_file, override=False)
except ImportError:
    pass

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
)

DEFAULT_BASE_URL = "https://ai.tcetcercd.in/v1"
DEFAULT_MODEL = "qwen3.6"
DEFAULT_TIMEOUT = 30.0


@dataclass(slots=True)
class QwenConfig:
    """Configuration for TCET CoE Qwen AI Gateway."""

    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = DEFAULT_TIMEOUT
    enable_thinking: bool = False
    reasoning_effort: str = "medium"

    @classmethod
    def from_env(cls, custom_key: str | None = None) -> QwenConfig:
        """Create configuration from environment variables or explicitly passed key."""
        api_key = (
            custom_key
            or os.environ.get("AI_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or None
        )
        base_url = os.environ.get("QWEN_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
        model = os.environ.get("QWEN_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

        return cls(
            api_key=api_key.strip() if api_key else None,
            base_url=base_url,
            model=model,
        )


def get_qwen_client(config: QwenConfig | None = None) -> OpenAI:
    """Initialize and return an OpenAI-compatible client for TCET CoE Qwen Gateway."""
    cfg = config or QwenConfig.from_env()
    api_key = cfg.api_key or "missing_key"

    return OpenAI(
        base_url=cfg.base_url,
        api_key=api_key,
        timeout=cfg.timeout,
    )


def check_qwen_health(config: QwenConfig | None = None) -> tuple[bool, str, str]:
    """Perform a lightweight health check on the TCET CoE AI Gateway.

    Returns:
        tuple of (is_connected, status_badge_text, detail_message)
    """
    cfg = config or QwenConfig.from_env()

    if not cfg.api_key:
        return (
            False,
            "🟡 Not Configured",
            "TCET CoE AI_KEY is not set. Provide AI_KEY in your .env file or sidebar to enable Qwen reasoning.",
        )

    try:
        client = get_qwen_client(cfg)
        # Use models.list() as the official lightweight health check endpoint
        client.models.list(timeout=8.0)
        return (
            True,
            "🟢 Connected",
            f"TCET CoE Qwen Gateway is online (Endpoint: {cfg.base_url}, Model: {cfg.model})",
        )
    except AuthenticationError:
        return (
            False,
            "🔴 Authentication Failed",
            "Invalid AI_KEY provided. Please check your TCET CoE API key.",
        )
    except (APIConnectionError, InternalServerError):
        return (
            False,
            "🔴 Gateway Offline",
            f"Unable to reach TCET CoE Gateway at {cfg.base_url}. Model server may be busy or offline.",
        )
    except APITimeoutError:
        return (
            False,
            "🔴 Connection Timeout",
            "Gateway health check timed out. Campus AI server is currently experiencing high load.",
        )
    except (BadRequestError, APIError) as exc:
        return (
            False,
            "🔴 Gateway Error",
            f"TCET CoE Gateway returned an error ({exc.message if hasattr(exc, 'message') else exc}).",
        )
    except Exception as exc:
        return (
            False,
            "🔴 Unavailable",
            f"Gateway check failed ({type(exc).__name__}: {exc}).",
        )
