from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple


def _parse_hhmm(s: str) -> Tuple[int, int]:
    hh, mm = s.split(":")
    return int(hh), int(mm)


def calculate_duration(sleep_time: str, wake_time: str) -> float:
    """Return sleep duration in hours between sleep_time and wake_time (HH:MM, may cross midnight)."""
    sh, sm = _parse_hhmm(sleep_time)
    wh, wm = _parse_hhmm(wake_time)
    today = datetime(2000, 1, 1, sh, sm)
    wake = datetime(2000, 1, 1, wh, wm)
    if wake <= today:
        wake += timedelta(days=1)
    dur = wake - today
    return round(dur.total_seconds() / 3600.0, 2)


def _time_to_minutes(s: str) -> int:
    h, m = _parse_hhmm(s)
    return h * 60 + m


def evaluate_sleep(sleep_time: str, wake_time: str) -> str:
    """Return evaluation key: under_6 | 6_7 | 7_8_late_wake | 7_8_late_sleep | 7_8_correct | 8_10 | over_10."""
    duration = calculate_duration(sleep_time, wake_time)
    
    if duration < 6:
        return "under_6"
    elif 6 <= duration < 7:
        return "6_7"
    elif 7 <= duration <= 8:
        # Check if within ideal window 23:00–06:00 ±30 min
        s_min = _time_to_minutes(sleep_time)
        e_min = _time_to_minutes(wake_time)
        if e_min <= s_min:
            e_min += 24 * 60
        
        # within [22:30, 06:30]
        if (22 * 60 + 30) <= s_min <= (23 * 60 + 59) and (6 * 60) <= (e_min % (24 * 60)) <= (6 * 60 + 30):
            return "7_8_correct"
        else:
            # Distinguish between late sleep vs late wake
            if s_min > (23 * 60 + 30):  # Sleep after 23:30
                return "7_8_late_sleep"
            else:  # Wake after 06:30
                return "7_8_late_wake"
    elif 8 < duration <= 10:
        return "8_10"
    else:  # > 10 hours
        return "over_10"


def calculate_next_targets(sleep_time: str, wake_time: str) -> tuple[str, str]:
    """Calculate next bedtime and wake time targets, moving toward 23:00–06:00 window."""
    s_min = _time_to_minutes(sleep_time)
    w_min = _time_to_minutes(wake_time)
    
    # Target wake time: max(06:00, current - 10min)
    target_wake_min = max(6 * 60, w_min - 10)
    
    # Calculate if we need to adjust bedtime to maintain ≥7h sleep
    current_duration = calculate_duration(sleep_time, wake_time)
    if current_duration < 7:
        # Need to extend sleep, so move bedtime earlier
        target_sleep_min = max(23 * 60, s_min - 10)
    else:
        # Can maintain current bedtime if wake time adjustment doesn't reduce sleep below 7h
        new_duration = calculate_duration(sleep_time, f"{target_wake_min // 60:02d}:{target_wake_min % 60:02d}")
        if new_duration >= 7:
            target_sleep_min = s_min
        else:
            target_sleep_min = max(23 * 60, s_min - 10)
    
    # Convert back to HH:MM format
    next_sleep = f"{target_sleep_min // 60:02d}:{target_sleep_min % 60:02d}"
    next_wake = f"{target_wake_min // 60:02d}:{target_wake_min % 60:02d}"
    
    return next_sleep, next_wake


def suggest_improvement(last_sleep_time: str, target: str = "23:00") -> str:
    """Suggest shifting bedtime gradually by 10 minutes toward target time."""
    lh, lm = _parse_hhmm(last_sleep_time)
    th, tm = _parse_hhmm(target)
    last_minutes = lh * 60 + lm
    target_minutes = th * 60 + tm
    if last_minutes <= target_minutes:
        return "Maintain current schedule and keep steady!"
    new_minutes = max(target_minutes, last_minutes - 10)
    nh, nm = divmod(new_minutes, 60)
    return f"Try going to bed at {nh:02d}:{nm:02d} tonight (10 minutes earlier)."


def get_reminder_time(sleep_time: str) -> str:
    """Calculate reminder time (1 hour before sleep time)."""
    sh, sm = _parse_hhmm(sleep_time)
    reminder_minutes = (sh * 60 + sm - 60) % (24 * 60)
    rh, rm = divmod(reminder_minutes, 60)
    return f"{rh:02d}:{rm:02d}"




