"""Shared structlog setup (audit AUDIT-2.md M9).

structlog auto-configures itself with sane defaults on first use, but that
zero-config path ignores LOG_LEVEL -- only whichever process calls
configure_logging() first gets level filtering. Called from both main.py
(API) and celery_app.py (worker/beat) so every process respects LOG_LEVEL
consistently instead of only the API doing so.
"""

import logging

import structlog

from app.core.config import get_settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        )
    )
    _configured = True
