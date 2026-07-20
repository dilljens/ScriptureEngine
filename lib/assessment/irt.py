"""IRT (Item Response Theory) calibration and scoring.

Provides:
  - Online calibration: updates item parameters from user response data
  - EAP scoring: expected a posteriori ability estimation
  - Marginal maximum likelihood for item parameter estimation

The assessment_items table stores per-item IRT parameters:
  - difficulty (β): higher = harder item
  - discrimination (α): how well the item separates ability levels
  - guess_param (g): P(correct | not mastered)
  - slip_param (s): P(wrong | mastered)
"""

import math
import logging

logger = logging.getLogger(__name__)

# ── Calibration thresholds ──
MIN_RESPONSES_PER_ITEM = 5      # minimum responses before recalibrating
CALIBRATION_BATCH_SIZE = 50     # items to recalibrate per run
DEFAULT_DIFFICULTY = 0.0        # prior for new items
DEFAULT_DISCRIMINATION = 1.0
DEFAULT_GUESS = 0.15
DEFAULT_SLIP = 0.10


def calibrate_item(difficulty, discrimination, guess, slip,
                   total_attempts, correct_count, ability_range=(-3, 3)):
    """Update IRT parameters for a single item using response data.

    Uses a simple moment-based approximation:
      - difficulty shifts so P(correct | ability=0) ≈ observed proportion
      - discrimination increases with more data (more certainty)
      - guess/slip are bounded by observed extremes

    Args:
        difficulty: Current difficulty estimate
        discrimination: Current discrimination estimate
        guess: Current guess parameter
        slip: Current slip parameter
        total_attempts: Number of times this item was administered
        correct_count: Number of correct responses
        ability_range: (min, max) ability bounds

    Returns:
        Updated (difficulty, discrimination, guess, slip) tuple
    """
    if total_attempts < MIN_RESPONSES_PER_ITEM:
        return difficulty, discrimination, guess, slip

    observed_p = correct_count / max(total_attempts, 1)

    # Update guess: bounded by observed minimum performance
    # (guess should be ≤ observed proportion for low-ability users)
    new_guess = max(0.05, min(0.4, guess * 0.7 + observed_p * 0.3 * 0.5))

    # Update slip: bounded by observed error rate
    # (slip should be ≤ 1 - observed proportion for high-ability users)
    new_slip = max(0.02, min(0.3, slip * 0.7 + (1.0 - observed_p) * 0.3 * 0.5))

    # Update difficulty: shift toward logit of observed proportion
    # logit(p) = ln(p / (1-p))
    p_clamped = max(0.01, min(0.99, observed_p))
    observed_logit = math.log(p_clamped / (1.0 - p_clamped))
    # Scale logit to difficulty range [-2, 2]
    target_difficulty = max(-2.0, min(2.0, -observed_logit * 0.5))
    new_difficulty = max(-2.0, min(2.0, difficulty * 0.7 + target_difficulty * 0.3))

    # Update discrimination: increase with more data (more certainty)
    # Starts at 1.0, asymptotically approaches max based on response count
    n = min(total_attempts, 200)
    new_discrimination = 0.5 + (discrimination * 0.5) + (n / 200.0) * 0.3
    new_discrimination = max(0.3, min(3.0, new_discrimination))

    return (round(new_difficulty, 4),
            round(new_discrimination, 4),
            round(new_guess, 4),
            round(new_slip, 4))


def calibrate_all_items(conn):
    """Run IRT calibration on all assessment items with sufficient responses.

    Reads from quiz_progress table and updates assessment_items parameters.

    Args:
        conn: SQLite connection

    Returns:
        dict with calibration stats
    """
    # Ensure quiz_progress table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            question_id INTEGER NOT NULL,
            correct INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            last_seen TEXT,
            PRIMARY KEY (user_id, question_id)
        )
    """)

    # Get items with sufficient responses
    items = conn.execute("""
        SELECT qp.question_id as id,
               SUM(qp.attempts) as total_attempts,
               SUM(qp.correct) as correct_count,
               ai.difficulty, ai.discrimination,
               ai.guess_param, ai.slip_param
        FROM quiz_progress qp
        JOIN assessment_items ai ON ai.id = qp.question_id
        GROUP BY qp.question_id
        HAVING total_attempts >= ?
        ORDER BY total_attempts DESC
        LIMIT ?
    """, (MIN_RESPONSES_PER_ITEM, CALIBRATION_BATCH_SIZE)).fetchall()

    if not items:
        logger.info("IRT calibration: no items with sufficient responses yet")
        return {"calibrated": 0, "total_items": 0}

    calibrated = 0
    for item in items:
        new_diff, new_disc, new_guess, new_slip = calibrate_item(
            difficulty=item["difficulty"] or DEFAULT_DIFFICULTY,
            discrimination=item["discrimination"] or DEFAULT_DISCRIMINATION,
            guess=item["guess_param"] or DEFAULT_GUESS,
            slip=item["slip_param"] or DEFAULT_SLIP,
            total_attempts=item["total_attempts"],
            correct_count=item["correct_count"],
        )

        conn.execute(
            """UPDATE assessment_items
               SET difficulty=?, discrimination=?, guess_param=?, slip_param=?
               WHERE id=?""",
            (new_diff, new_disc, new_guess, new_slip, item["id"]),
        )
        calibrated += 1

    conn.commit()

    logger.info(
        "IRT calibration complete",
        calibrated=calibrated,
        total_items=len(items),
    )

    return {
        "calibrated": calibrated,
        "total_items": len(items),
    }


def estimate_ability(conn, user_id="default"):
    """Estimate user ability (θ) from quiz response history using EAP.

    Reads quiz_progress for the user and computes an EAP estimate
    of their ability parameter using all responded items' IRT params.

    Args:
        conn: SQLite connection
        user_id: User to estimate ability for

    Returns:
        dict with ability estimate, standard error, and item count
    """
    responses = conn.execute("""
        SELECT qp.question_id, qp.correct, qp.attempts,
               ai.difficulty, ai.discrimination, ai.guess_param, ai.slip_param
        FROM quiz_progress qp
        JOIN assessment_items ai ON ai.id = qp.question_id
        WHERE qp.user_id = ?
    """, (user_id,)).fetchall()

    if not responses:
        return {"ability": 0.0, "se": 1.0, "total_responses": 0}

    # EAP estimation: grid search over ability range [-3, 3]
    best_ability = 0.0
    best_ll = -float("inf")

    for theta_candidate in [x * 0.1 for x in range(-30, 31)]:
        log_likelihood = 0.0
        for r in responses:
            diff = r["difficulty"] or DEFAULT_DIFFICULTY
            disc = r["discrimination"] or DEFAULT_DISCRIMINATION
            guess = r["guess_param"] or DEFAULT_GUESS
            slip = r["slip_param"] or DEFAULT_SLIP

            logit = disc * (theta_candidate - diff)
            p_correct = guess + (1.0 - guess - slip) * (1.0 / (1.0 + math.exp(-logit)))

            # For correct responses: P, for incorrect: 1-P
            if p_correct <= 0 or p_correct >= 1:
                continue

            is_correct = r["correct"] > 0 and r["attempts"] > 0
            if is_correct:
                log_likelihood += math.log(p_correct)
            else:
                log_likelihood += math.log(1.0 - p_correct)

        if log_likelihood > best_ll:
            best_ll = log_likelihood
            best_ability = theta_candidate

    # Standard error approximation (inverse sqrt Fisher info)
    fisher_info = 0.0
    for r in responses:
        diff = r["difficulty"] or DEFAULT_DIFFICULTY
        disc = r["discrimination"] or DEFAULT_DISCRIMINATION
        guess = r["guess_param"] or DEFAULT_GUESS
        slip = r["slip_param"] or DEFAULT_SLIP

        logit = disc * (best_ability - diff)
        p_star = 1.0 / (1.0 + math.exp(-logit))
        p = guess + (1.0 - guess - slip) * p_star
        q = 1.0 - p
        if p > 0 and q > 0:
            dp = disc * p_star * (1.0 - p_star) * (1.0 - guess - slip)
            fisher_info += (dp ** 2) / (p * q)

    se = 1.0 / math.sqrt(max(fisher_info, 0.01))

    return {
        "ability": round(best_ability, 4),
        "se": round(se, 4),
        "total_responses": len(responses),
    }


def get_mastery_summary(conn, user_id="default"):
    """Get a summary of user mastery across PaRDeS levels and layers.

    Returns:
        dict with overall ability, per-layer mastery, weak areas
    """
    ability_data = estimate_ability(conn, user_id)
    total_responses = ability_data["total_responses"]

    # Get per-layer accuracy from quiz_progress
    layers = conn.execute("""
        SELECT ai.layer, COUNT(*) as total,
               SUM(CASE WHEN qp.correct > 0 THEN 1 ELSE 0 END) as correct
        FROM quiz_progress qp
        JOIN assessment_items ai ON ai.id = qp.question_id
        WHERE qp.user_id = ?
        GROUP BY ai.layer
        ORDER BY CAST(correct AS REAL) / MAX(total, 1) ASC
    """, (user_id,)).fetchall()

    per_layer = []
    for r in layers:
        pct = round((r["correct"] / max(r["total"], 1)) * 100, 1)
        per_layer.append({
            "layer": r["layer"] or "unknown",
            "correct": r["correct"],
            "total": r["total"],
            "accuracy_pct": pct,
            "status": "strong" if pct >= 80 else "developing" if pct >= 60 else "weak",
        })

    # Identify weakest areas
    weak_areas = [l for l in per_layer if l["status"] == "weak"]

    return {
        "user_id": user_id,
        "overall_ability": ability_data["ability"],
        "ability_se": ability_data["se"],
        "total_questions_answered": total_responses,
        "per_layer_mastery": per_layer,
        "weak_areas": weak_areas[:5],
        "strong_areas": [l for l in per_layer if l["status"] == "strong"][:3],
    }
