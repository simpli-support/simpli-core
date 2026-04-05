"""Supabase client for persistent storage across Simpli services."""

from __future__ import annotations

import functools
from typing import Any

from supabase import Client, create_client


@functools.lru_cache(maxsize=1)
def get_supabase_client(url: str, key: str) -> Client:
    """Return a cached Supabase client singleton.

    Parameters
    ----------
    url:
        Supabase project URL (``SUPABASE_URL``).
    key:
        Supabase service-role key (``SUPABASE_SERVICE_ROLE_KEY``).
    """
    return create_client(url, key)


def supabase_from_settings(settings: Any) -> Client:
    """Create a Supabase client from a SimpliSettings instance.

    Expects ``supabase_url`` and ``supabase_key`` fields on the settings
    object.  Raises ``ValueError`` if either is missing.
    """
    url: str = getattr(settings, "supabase_url", "")
    key: str = getattr(settings, "supabase_key", "")
    if not url or not key:
        msg = (
            "supabase_url and supabase_key must be set in settings or "
            "environment (SUPABASE_URL, SUPABASE_KEY)"
        )
        raise ValueError(msg)
    return get_supabase_client(url, key)
