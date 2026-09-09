"""The provider keys this process is holding, for as long as it is running.

Memory only, and deliberately (D17, D41). The key is encrypted on disk by
Electron's `safeStorage`, decrypted in the main process, and sent here over
the authenticated loopback API once per launch. Nothing in the sidecar writes
one down, so a crash, a log or a copied database directory cannot leak it.
"""

from __future__ import annotations

import threading

from sidecar.domain.providers import ProviderId


class ProviderKeys:
    """Keys by provider. Every read and write is safe from any request thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._keys: dict[ProviderId, str] = {}

    def remember(self, provider: ProviderId, key: str) -> None:
        """Hold this key for `provider`. An empty or blank key forgets instead.

        Blank counts as forgetting because that is what an emptied settings
        field means, and storing it would leave the app authenticating with
        nothing and blaming the provider for the 401.
        """
        with self._lock:
            if key.strip():
                self._keys[provider] = key.strip()
            else:
                self._keys.pop(provider, None)

    def forget(self, provider: ProviderId) -> None:
        with self._lock:
            self._keys.pop(provider, None)

    def key_for(self, provider: ProviderId) -> str | None:
        with self._lock:
            return self._keys.get(provider)

    def known(self) -> set[ProviderId]:
        """Which providers have a key. Never the keys themselves: this answer reaches the UI."""
        with self._lock:
            return set(self._keys)
