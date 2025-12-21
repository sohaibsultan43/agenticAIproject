import logging
import os
import warnings


def setup_logging(app_name: str = "ScholarSync") -> None:
    """
    Keep logs readable by default:
    - concise format
    - reduce noisy third-party loggers
    - optionally suppress common deprecation/resource warnings
    """
    level = os.getenv("SCHOLARSYNC_LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=f"{app_name} | %(levelname)s | %(message)s",
    )

    # Silence common noisy loggers (can be overridden by SCHOLARSYNC_LOG_LEVEL per-logger if needed)
    noisy = [
        "httpx",
        "httpcore",
        "urllib3",
        "weaviate",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "llama_index",
        "llama_parse",
    ]
    for name in noisy:
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        # Avoid duplicated or overly chatty propagation from server loggers
        if name.startswith("uvicorn"):
            lg.propagate = False

    # Fully suppress uvicorn access logs by default (they tend to be pure noise in dev)
    if os.getenv("SCHOLARSYNC_SUPPRESS_UVICORN_ACCESS", "1") == "1":
        logging.getLogger("uvicorn.access").disabled = True

    # Cut down known noisy warnings in dev output
    if os.getenv("SCHOLARSYNC_SUPPRESS_WARNINGS", "1") == "1":
        # LlamaParse deprecation noise + general resource warnings from asyncio transports
        warnings.filterwarnings("ignore", message=".*deprecated.*parsing_instruction.*", category=Warning)
        warnings.filterwarnings("ignore", message=".*parsing_instruction is deprecated.*", category=Warning)
        warnings.filterwarnings("ignore", category=ResourceWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)


