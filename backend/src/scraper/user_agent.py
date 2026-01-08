"""
User agent management and rotation for scraper.
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.core.constants import DEFAULT_HEADERS, USER_AGENTS


@dataclass
class UserAgentState:
    """Tracks user agent usage per domain."""

    current_index: int = 0
    failures: dict[int, int] = field(default_factory=dict)  # UA index -> failure count
    last_success_index: int | None = None


class UserAgentManager:
    """
    Manages user agent rotation and headers for scraping.

    Supports:
    - Round-robin rotation
    - Per-domain tracking
    - Failure-based rotation
    """

    def __init__(self, user_agents: list[str] | None = None):
        """
        Initialize user agent manager.

        Args:
            user_agents: List of user agent strings (defaults to constants)
        """
        self.user_agents = user_agents or USER_AGENTS.copy()
        self._domain_state: dict[str, UserAgentState] = defaultdict(UserAgentState)

    def get_user_agent(self, domain: str | None = None) -> str:
        """
        Get next user agent for a domain.

        Args:
            domain: Optional domain for per-domain tracking

        Returns:
            User agent string
        """
        if not domain:
            return random.choice(self.user_agents)

        state = self._domain_state[domain]
        return self.user_agents[state.current_index % len(self.user_agents)]

    def get_headers(self, domain: str | None = None) -> dict[str, str]:
        """
        Get complete headers with user agent for a domain.

        Args:
            domain: Optional domain for per-domain tracking

        Returns:
            Headers dict
        """
        headers = DEFAULT_HEADERS.copy()
        headers["User-Agent"] = self.get_user_agent(domain)
        return headers

    def rotate(self, domain: str) -> str:
        """
        Rotate to next user agent for a domain.

        Args:
            domain: Domain to rotate

        Returns:
            New user agent string
        """
        state = self._domain_state[domain]
        state.current_index = (state.current_index + 1) % len(self.user_agents)
        return self.user_agents[state.current_index]

    def report_success(self, domain: str) -> None:
        """
        Report successful request for a domain.

        Args:
            domain: Domain of successful request
        """
        state = self._domain_state[domain]
        state.last_success_index = state.current_index
        # Clear failures for this UA
        if state.current_index in state.failures:
            state.failures[state.current_index] = 0

    def report_failure(self, domain: str) -> str | None:
        """
        Report failed request for a domain.
        Rotates user agent if failures exceed threshold.

        Args:
            domain: Domain of failed request

        Returns:
            New user agent if rotated, None otherwise
        """
        state = self._domain_state[domain]

        # Track failure
        current_failures = state.failures.get(state.current_index, 0) + 1
        state.failures[state.current_index] = current_failures

        # Rotate if 3 failures with same UA
        if current_failures >= 3:
            # Find UA with least failures
            failures_per_ua = [
                (i, state.failures.get(i, 0)) for i in range(len(self.user_agents))
            ]
            failures_per_ua.sort(key=lambda x: x[1])
            best_ua_index = failures_per_ua[0][0]

            state.current_index = best_ua_index
            return self.user_agents[best_ua_index]

        return None

    def reset(self, domain: str | None = None) -> None:
        """
        Reset tracking for a domain or all domains.

        Args:
            domain: Specific domain or None for all
        """
        if domain:
            if domain in self._domain_state:
                del self._domain_state[domain]
        else:
            self._domain_state.clear()

    def get_stats(self, domain: str | None = None) -> dict[str, Any]:
        """
        Get statistics for user agent usage.

        Args:
            domain: Specific domain or None for all

        Returns:
            Stats dict
        """
        if domain:
            state = self._domain_state.get(domain)
            if not state:
                return {}
            return {
                "current_ua": self.user_agents[state.current_index],
                "failures": dict(state.failures),
                "last_success_index": state.last_success_index,
            }

        return {
            domain: {
                "current_ua": self.user_agents[state.current_index],
                "total_failures": sum(state.failures.values()),
            }
            for domain, state in self._domain_state.items()
        }


# ===========================================
# Browser Fingerprint Helpers
# ===========================================


def get_browser_headers(browser: str = "chrome") -> dict[str, str]:
    """
    Get headers that match a specific browser.

    Args:
        browser: Browser type (chrome, firefox, safari)

    Returns:
        Headers dict matching browser fingerprint
    """
    if browser == "firefox":
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    elif browser == "safari":
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    else:  # chrome (default)
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }


# ===========================================
# Global Instance
# ===========================================

_ua_manager: UserAgentManager | None = None


def get_user_agent_manager() -> UserAgentManager:
    """Get the global user agent manager instance."""
    global _ua_manager
    if _ua_manager is None:
        _ua_manager = UserAgentManager()
    return _ua_manager
