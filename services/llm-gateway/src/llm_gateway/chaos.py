"""Fault injection state, same contract as the Retail Store /chaos/* API."""

from dataclasses import dataclass

MIN_ERROR_STATUS = 400
MAX_ERROR_STATUS = 599


class InvalidFaultError(ValueError):
    pass


@dataclass
class ChaosState:
    status_code: int | None = None
    latency_ms: int = 0

    def inject_status(self, status_code: int) -> None:
        if not MIN_ERROR_STATUS <= status_code <= MAX_ERROR_STATUS:
            raise InvalidFaultError(
                f"status code must be between {MIN_ERROR_STATUS} and {MAX_ERROR_STATUS}"
            )
        self.status_code = status_code

    def clear_status(self) -> None:
        self.status_code = None

    def inject_latency(self, latency_ms: int) -> None:
        if latency_ms <= 0:
            raise InvalidFaultError("latency must be a positive number of milliseconds")
        self.latency_ms = latency_ms

    def clear_latency(self) -> None:
        self.latency_ms = 0
