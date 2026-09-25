"""Classify failures so we know what is worth retrying."""


class TransientLLMError(Exception):
    """Temporary: timeout, rate limit (429), server error (5xx). SAFE to retry."""


class PermanentLLMError(Exception):
    """Won't fix itself: bad API key, invalid request. DO NOT retry."""
