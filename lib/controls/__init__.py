"""Statistical controls for the scripture connection graph.

Anti-hallucination and anti-backfitting system.
Ensures connections are statistically meaningful, not coincidental patterns.
"""

from .calibration import (
    QUALITY_LEVELS,
    calibrate_connection,
    get_quality_color,
    get_quality_emoji,
)
from .stats import (
    monte_carlo_p_value,
    bonferroni_correction,
    false_discovery_rate,
    compute_effect_size,
)
from .preregistration import (
    register_method,
    is_method_registered,
    list_methods,
)
