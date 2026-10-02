import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. "
        "Please add it to your .env file."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY
)

PRIMARY_MODEL = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-flash-latest"]


def call_gemini_with_retry(prompt: str, response_format=None, max_retries: int = 3, delay: int = 3):
    """
    Wrapper for Gemini API calls with exponential backoff retry for HTTP 429 rate limit errors,
    HTTP 503 high demand/service unavailable errors, and transient network errors (e.g. getaddrinfo failed).
    Includes automatic fallback models.
    """
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS

    for model_index, model_name in enumerate(models_to_try):
        current_delay = delay
        for attempt in range(1, max_retries + 1):
            try:
                kwargs = {
                    "model": model_name,
                    "input": prompt
                }
                if response_format:
                    kwargs["response_format"] = response_format

                interaction = client.interactions.create(**kwargs)
                return interaction.output_text

            except Exception as error:
                error_str = str(error).lower()
                is_rate_limit = "429" in error_str or "too_many_requests" in error_str or "quota" in error_str
                is_service_unavailable = any(code in error_str for code in ["503", "service_unavailable", "high demand", "overloaded", "temporarily unavailable", "500", "502", "504"])
                is_network_error = any(net_err in error_str for net_err in ["getaddrinfo", "gaierror", "connection", "connecterror", "socket", "timeout", "reset by peer", "winerror 10060", "winerror 10061"])

                if is_rate_limit or is_service_unavailable or is_network_error:
                    if is_network_error:
                        reason = "Network connection error"
                    elif is_service_unavailable:
                        reason = "503 High Demand / Service Busy"
                    else:
                        reason = "429 Rate Limit"

                    if attempt < max_retries:
                        print(f"Gemini {reason} ({model_name}). Retrying in {current_delay}s (Attempt {attempt}/{max_retries})...")
                        time.sleep(current_delay)
                        current_delay *= 2
                        continue
                    elif model_index < len(models_to_try) - 1:
                        next_model = models_to_try[model_index + 1]
                        print(f"Gemini model {model_name} unavailable after {max_retries} retries ({reason}). Switching to fallback model {next_model}...")
                        break
                    else:
                        if is_network_error:
                            raise RuntimeError(
                                f"Network Connection Error ({error}). Please check your internet connection or DNS and try again."
                            )
                        else:
                            raise RuntimeError(
                                "Gemini API is currently experiencing high demand or rate limits. "
                                "Please wait 30-60 seconds and try again."
                            )
                elif "403" in error_str or "permission_denied" in error_str or "denied access" in error_str:
                    raise RuntimeError(
                        "Gemini API Key Permission Denied (403). Your project or API key has been denied access by Google. "
                        "Please update GEMINI_API_KEY in your .env file with a valid key from Google AI Studio (https://aistudio.google.com/)."
                    )
                else:
                    raise error


def ask_gemini(prompt: str) -> str:
    """
    Send a prompt to Gemini using the Interactions API with retry mechanism.
    """
    return call_gemini_with_retry(prompt)