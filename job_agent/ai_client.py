#!/usr/bin/python3
"""
    AI Client — Single entry point for all AgentRouter API calls.
    Every AI agent in this system imports call_ai from here.
    One place to update the key, model, base URL, or retry logic.
    Author: Fortune Nwohiri
"""
import os
import time
import random
import requests
import json
from logging_config.logger import get_logger
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

logger = get_logger("AIClient")

# ── CONFIG ────────────────────────────────────────────────────────────────────
AGENTROUTER_BASE_URL = os.environ.get("AGENTROUTER_BASE_URL", "https://agentrouter.org/v1")
AGENTROUTER_API_KEY = os.environ.get("AGENTROUTER_API_KEY", "")
AGENTROUTER_MODEL = os.environ.get("AGENTROUTER_MODEL", "gpt-5.6-sol")

# Retry config
MAX_RETRIES = 5
RETRY_DELAY_MIN = 3
RETRY_DELAY_MAX = 8

# Token limits per agent type — kept tight to conserve balance
TOKEN_LIMITS = {
    "classifier": 300,
    "scorer": 800,
    "extractor": 600,
    "cv_builder": 1500,
    "cover_letter": 500,
    "custom_question": 300,
    "email_body": 400,
    "salary": 50,
    "default": 500,
}


def _get_api_key() -> str:
    key = AGENTROUTER_API_KEY

    if not key:
        try:
            with open("./config/agent_profile.json", "r") as f:
                profile = json.load(f)
                key = profile.get("agentrouter_api_key", "")
        except Exception:
            pass

    if not key:
        logger.error(
            "AgentRouter API key not found. "
            "Set AGENTROUTER_API_KEY in your .env file."
        )

    return key


def _get_model() -> str:
    return AGENTROUTER_MODEL or "gpt-5.6-sol"


def call_ai(
    messages: list,
    max_tokens: int = 500,
    json_response: bool = False,
    agent_type: str = "default",
    temperature: float = 0.3,
) -> str:
    """
    Single AI call function used by every job agent module.
    Uses AgentRouter /v1/responses endpoint (required for gpt-5.6-sol).

    Args:
        messages: list of message dicts with role and content keys
        max_tokens: maximum tokens in the response
        json_response: if True enforces JSON output via format parameter
        agent_type: classifier, scorer, extractor, cv_builder,
                    cover_letter, custom_question, email_body, salary, default
        temperature: 0.0 to 1.0

    Returns:
        str: the response text from the model

    Raises:
        RuntimeError if all retries fail
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("No AgentRouter API key available")

    model = _get_model()

    if max_tokens == 500 and agent_type in TOKEN_LIMITS:
        max_tokens = TOKEN_LIMITS[agent_type]

    # /v1/responses uses input + max_output_tokens
    payload = {
        "model": model,
        "input": messages,
        "max_output_tokens": max_tokens,
    }

    if json_response:
        payload["text"] = {"format": {"type": "json_object"}}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Originator": "codex_cli_rs",
        "User-Agent": "codex_cli_rs/0.114.0 (Windows 10.0.26100; x86_64)",
    }

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                delay = random.uniform(RETRY_DELAY_MIN, RETRY_DELAY_MAX)
                logger.info(f"AI call retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s")
                time.sleep(delay)

            logger.debug(
                f"AI call: model={model} agent={agent_type} "
                f"max_output_tokens={max_tokens} json={json_response} "
                f"messages={len(messages)}"
            )

            response = requests.post(
                f"{AGENTROUTER_BASE_URL}/responses",
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code >= 400:
                logger.warning(f"AgentRouter error body: {response.text}")

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 30))
                logger.warning(f"Rate limited. Waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            if response.status_code == 401:
                logger.error(
                    "AgentRouter authentication failed. "
                    "Check your API key in .env"
                )
                raise RuntimeError("AgentRouter authentication failed")

            if response.status_code >= 500:
                logger.warning(
                    f"AgentRouter server error {response.status_code} "
                    f"on attempt {attempt + 1}"
                )
                last_error = f"Server error {response.status_code}"
                continue

            response.raise_for_status()
            data = response.json()

            # /v1/responses response structure
            output = data.get("output", [])
            if not output:
                logger.warning("Empty output in AgentRouter response")
                last_error = "Empty output"
                continue

            content = ""
            for block in output:
                if block.get("type") == "message":
                    for part in block.get("content", []):
                        if part.get("type") == "output_text":
                            content += part.get("text", "")

            if not content:
                logger.warning("Empty content in AgentRouter response")
                if attempt >= 1:
                    logger.debug(f"Raw AgentRouter response on empty: {data}")
                last_error = "Empty content"
                continue

            content = content.strip()

            usage = data.get("usage", {})
            if usage:
                logger.debug(
                    f"Tokens: input={usage.get('input_tokens', 0)} "
                    f"output={usage.get('output_tokens', 0)} "
                    f"total={usage.get('total_tokens', 0)}"
                )

            return content

        except RuntimeError:
            raise

        except requests.exceptions.Timeout:
            logger.warning(f"AI call timed out on attempt {attempt + 1}")
            last_error = "Request timeout"
            continue

        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error on attempt {attempt + 1}")
            last_error = "Connection error"
            continue

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error on attempt {attempt + 1}: {e}")
            last_error = str(e)
            continue

        except Exception as e:
            logger.error(f"Unexpected AI client error: {e}", exc_info=True)
            last_error = str(e)
            continue

    raise RuntimeError(
        f"AI call failed after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


def call_ai_safe(
    messages: list,
    max_tokens: int = 500,
    json_response: bool = False,
    agent_type: str = "default",
    temperature: float = 0.3,
    fallback: str = "",
) -> str:
    """
    Safe wrapper around call_ai that never raises.
    Returns the fallback string if the call fails.
    """
    try:
        return call_ai(
            messages=messages,
            max_tokens=max_tokens,
            json_response=json_response,
            agent_type=agent_type,
            temperature=temperature,
        )
    except Exception as e:
        logger.error(f"call_ai_safe caught error: {e}")
        return fallback


def test_connection() -> bool:
    """
    Usage:
        python -c "from job_agent.ai_client import test_connection; test_connection()"
    """
    logger.info("Testing AgentRouter connection")

    try:
        response = call_ai(
            messages=[
                {"role": "user", "content": "Reply with the single word: connected"}
            ],
            max_tokens=16,
            agent_type="default",
        )

        if response:
            logger.info(f"AgentRouter connection OK. Response: '{response}'")
            print(f"AgentRouter connection OK. Response: '{response}'")
            return True
        else:
            logger.error("AgentRouter returned empty response")
            return False

    except Exception as e:
        logger.error(f"AgentRouter connection failed: {e}")
        print(f"AgentRouter connection failed: {e}")
        return False

def test_system_role() -> bool:
    """
    Tests whether AgentRouter /v1/responses accepts a system role
    as a separate message entry in the input array.

    Usage:
        python -c "from job_agent.ai_client import test_system_role; test_system_role()"
    """
    logger.info("Testing AgentRouter system role support")

    try:
        response = call_ai(
            messages=[
                {"role": "system", "content": "You are a test assistant. Reply only with the single word: confirmed"},
                {"role": "user", "content": "Respond now."}
            ],
            max_tokens=16,
            agent_type="default",
        )

        if response:
            logger.info(f"System role test OK. Response: '{response}'")
            print(f"System role test OK. Response: '{response}'")
            return True
        else:
            logger.error("System role test returned empty response")
            print("System role test returned empty response")
            return False

    except Exception as e:
        logger.error(f"System role test failed: {e}")
        print(f"System role test failed: {e}")
        return False

def get_available_models() -> list:
    """
    Usage:
        python -c "from job_agent.ai_client import get_available_models; print(get_available_models())"
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    try:
        response = requests.get(
            f"{AGENTROUTER_BASE_URL}/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Originator": "codex_cli_rs",
                "User-Agent": "codex_cli_rs/0.114.0 (Windows 10.0.26100; x86_64)",
            },
            timeout=15,
        )
        if response.status_code >= 400:
            logger.warning(f"Models fetch error body: {response.text}")
        response.raise_for_status()
        data = response.json()
        models = [m.get("id", "") for m in data.get("data", [])]
        logger.info(f"Available models: {models}")
        return models

    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return []