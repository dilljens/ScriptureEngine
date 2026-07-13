"""Statistical analysis for connection quality.

Provides:
- Monte Carlo p-value estimation
- Bonferroni correction for multiple comparisons
- False discovery rate (FDR) control
- Effect size computation
"""



def monte_carlo_p_value(observed, null_distribution, tail="two-sided"):
    """Compute p-value using a Monte Carlo null distribution.

    Args:
        observed: the number of patterns found in real text
        null_distribution: list of counts from null text (shuffled or random)
        tail: 'one-sided' (more patterns than expected) or 'two-sided'

    Returns:
        p_value: probability of observing ≥ observed patterns by chance
        z_score: how many standard deviations from null mean
    """
    if not null_distribution:
        return 1.0, 0.0

    mean = sum(null_distribution) / len(null_distribution)
    std = (sum((x - mean) ** 2 for x in null_distribution) / len(null_distribution)) ** 0.5

    if std == 0:
        return 0.5, 0.0

    z_score = (observed - mean) / std

    if tail == "one-sided":
        # Proportion of null runs with ≥ observed
        extreme = sum(1 for x in null_distribution if x >= observed)
        p_value = extreme / len(null_distribution)
    else:
        # Two-sided: proportion of null runs with ≥ |observed| from mean
        extreme = sum(1 for x in null_distribution if abs(x - mean) >= abs(observed - mean))
        p_value = extreme / len(null_distribution)

    return p_value, z_score


def bonferroni_correction(p_values, alpha=0.05):
    """Apply Bonferroni correction for multiple comparisons.

    Args:
        p_values: list of (method_name, p_value) tuples
        alpha: desired family-wise error rate (default 0.05)

    Returns:
        list of (method_name, original_p, corrected_p, significant) tuples
    """
    n = len(p_values)
    results = []
    for name, p in p_values:
        corrected = min(p * n, 1.0)  # Bonferroni: multiply by number of tests
        results.append((name, p, corrected, corrected < alpha))
    return results


def false_discovery_rate(p_values, alpha=0.05):
    """Apply Benjamini-Hochberg FDR control.

    Args:
        p_values: list of (method_name, p_value) tuples
        alpha: desired FDR (default 0.05)

    Returns:
        list of (method_name, original_p, rejected) tuples
    """
    sorted_p = sorted(p_values, key=lambda x: x[1])
    n = len(sorted_p)
    max_idx = -1

    for i, (_name, p) in enumerate(sorted_p):
        bh_threshold = (i + 1) / n * alpha
        if p <= bh_threshold:
            max_idx = i

    results = []
    for i, (name, p) in enumerate(sorted_p):
        results.append((name, p, i <= max_idx))

    return results


def compute_effect_size(observed, null_mean, null_std):
    """Compute Cohen's d effect size.

    Standard interpretation:
        0.2 = small effect
        0.5 = medium effect
        0.8 = large effect

    Args:
        observed: pattern count in real text
        null_mean: mean pattern count in null text
        null_std: std dev of pattern count in null text

    Returns:
        d: Cohen's d effect size
    """
    if null_std == 0:
        return 0.0 if observed == null_mean else 10.0  # Infinite for perfect detection
    return (observed - null_mean) / null_std


def weighted_confidence(p_value, effect_size, preregistered, cross_validated, base=0.5):
    """Compute a weighted confidence score from multiple factors.

    Args:
        p_value: statistical significance
        effect_size: Cohen's d
        preregistered: 1 if method was pre-registered, 0 otherwise
        cross_validated: 1 if independently confirmed, 0 otherwise
        base: base confidence (default 0.5)

    Returns:
        confidence: 0.0 to 1.0
    """
    # p-value component: p < 0.05 → +0.2, p < 0.01 → +0.3, p < 0.001 → +0.35
    p_component = 0.0
    if p_value < 0.001:
        p_component = 0.35
    elif p_value < 0.01:
        p_component = 0.30
    elif p_value < 0.05:
        p_component = 0.20
    elif p_value < 0.10:
        p_component = 0.10

    # Effect size component
    es_component = min(effect_size / 3.0, 0.3)

    # Pre-registration bonus
    reg_bonus = 0.1 if preregistered else 0.0

    # Cross-validation bonus
    cv_bonus = 0.15 if cross_validated else 0.0

    # Penalty for post-hoc discovery
    posthoc_penalty = 0.1 if not preregistered else 0.0

    confidence = base + p_component + es_component + reg_bonus + cv_bonus - posthoc_penalty
    return max(0.0, min(1.0, confidence))
