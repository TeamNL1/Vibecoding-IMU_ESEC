from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class JumpEvent:
    takeoff_time: float
    landing_time: float
    flight_duration: float
    takeoff_peak: float
    landing_peak: float
    rest_level: float


class JumpDetector:
    def __init__(
        self,
        takeoff_multiplier=1.28,
        flight_multiplier=0.70,
        landing_multiplier=1.18,
        takeoff_window_seconds=0.55,
        min_flight_seconds=0.10,
        cooldown_seconds=0.60,
        rest_update_alpha=0.015,
    ):
        self.takeoff_multiplier = float(takeoff_multiplier)
        self.flight_multiplier = float(flight_multiplier)
        self.landing_multiplier = float(landing_multiplier)
        self.takeoff_window_seconds = float(takeoff_window_seconds)
        self.min_flight_seconds = float(min_flight_seconds)
        self.cooldown_seconds = float(cooldown_seconds)
        self.rest_update_alpha = float(rest_update_alpha)
        self.reset()

    def reset(self):
        self.state = "idle"
        self.rest_level = None
        self._prejump_started_at = None
        self._prejump_peak = None
        self._flight_low_since = None
        self._takeoff_time = None
        self._landing_peak = None
        self._cooldown_until = None
        self.last_event = None

    def thresholds(self):
        rest = self.rest_level or 1.0
        return {
            "takeoff": rest * self.takeoff_multiplier,
            "flight": rest * self.flight_multiplier,
            "landing": rest * self.landing_multiplier,
        }

    def _update_rest_level(self, norm):
        if self.rest_level is None:
            self.rest_level = max(float(norm), 1e-6)
            return

        if self.state != "idle":
            return

        lower = self.rest_level * 0.85
        upper = self.rest_level * 1.15
        if lower <= norm <= upper:
            alpha = self.rest_update_alpha
            self.rest_level = (1.0 - alpha) * self.rest_level + alpha * norm

    def update(self, sensor_time, ax, ay, az):
        norm = sqrt(ax * ax + ay * ay + az * az)
        self._update_rest_level(norm)

        if self.rest_level is None:
            return None

        thresholds = self.thresholds()

        if self.state == "cooldown":
            if self._cooldown_until is not None and sensor_time >= self._cooldown_until:
                self.state = "idle"
                self._cooldown_until = None
            return None

        if self.state == "idle":
            if norm >= thresholds["takeoff"]:
                self.state = "prejump"
                self._prejump_started_at = sensor_time
                self._prejump_peak = norm
                self._flight_low_since = None
            return None

        if self.state == "prejump":
            if self._prejump_peak is None or norm > self._prejump_peak:
                self._prejump_peak = norm

            if self._prejump_started_at is not None:
                if sensor_time - self._prejump_started_at > self.takeoff_window_seconds:
                    self.state = "idle"
                    self._prejump_started_at = None
                    self._prejump_peak = None
                    self._flight_low_since = None
                    return None

            if norm <= thresholds["flight"]:
                if self._flight_low_since is None:
                    self._flight_low_since = sensor_time
                elif sensor_time - self._flight_low_since >= self.min_flight_seconds:
                    self.state = "flight"
                    self._takeoff_time = self._flight_low_since
                    self._landing_peak = norm
            else:
                self._flight_low_since = None
            return None

        if self.state == "flight":
            if self._landing_peak is None or norm > self._landing_peak:
                self._landing_peak = norm

            if self._takeoff_time is None:
                return None

            if sensor_time - self._takeoff_time >= self.min_flight_seconds and norm >= thresholds["landing"]:
                event = JumpEvent(
                    takeoff_time=self._takeoff_time,
                    landing_time=sensor_time,
                    flight_duration=sensor_time - self._takeoff_time,
                    takeoff_peak=self._prejump_peak or norm,
                    landing_peak=self._landing_peak or norm,
                    rest_level=self.rest_level,
                )
                self.last_event = event
                self.state = "cooldown"
                self._cooldown_until = sensor_time + self.cooldown_seconds
                self._prejump_started_at = None
                self._prejump_peak = None
                self._flight_low_since = None
                self._takeoff_time = None
                self._landing_peak = None
                return event

        return None
