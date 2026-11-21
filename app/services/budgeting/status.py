# Ported from copilot/expenses/backend/app/services/budget/service.py `compute_status`
# (pre-existing code written by the project owner).
"""Month-end utilisation status: OPEN (no positive budget), UNDERUSED (< 85%), ON_TRACK (85% to 107%
inclusive), OVERRUN (strictly above 107%: the 7% tolerance). Integer arithmetic only."""

OVERRUN_BUFFER_PCT = 7
ON_TRACK_FLOOR = 85


def compute_status(adjusted_paise: int, actual_paise: int) -> str:
    if adjusted_paise <= 0:
        return "OPEN"
    if actual_paise * 100 > (100 + OVERRUN_BUFFER_PCT) * adjusted_paise:
        return "OVERRUN"  # only past the 7% tolerance
    if actual_paise * 100 >= ON_TRACK_FLOOR * adjusted_paise:
        return "ON_TRACK"
    return "UNDERUSED"
