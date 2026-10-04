"""The Anthropic API key, read from a file mounted from a Kubernetes Secret.

The file is read on every request: when the Secret changes, the kubelet updates the file
(within about a minute) and the gateway uses the new key without a restart.
"""

from pathlib import Path

# Every Anthropic API key starts with this. The mock LLM rejects keys without it, like the real API would.
API_KEY_PREFIX = "sk-ant-"


class ApiKeyFile:
    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> str:
        """The current key, or "" when no Secret is mounted (mock mode needs none)."""
        try:
            return self._path.read_text(encoding="utf-8").strip()  # tolerate a trailing newline from --from-file
        except FileNotFoundError:
            return ""


def is_rejected_by_mock(api_key: str) -> bool:
    """The mock LLM accepts no key (the free default) or a well-formed one."""
    return bool(api_key) and not api_key.startswith(API_KEY_PREFIX)
