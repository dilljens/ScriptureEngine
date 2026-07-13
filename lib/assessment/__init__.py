from .engine import AssessmentEngine
from .items import DeepQuestionGenerator, build_deep_questions
from .models import BLIM, KnowledgeState

__all__ = ['AssessmentEngine', 'DeepQuestionGenerator', 'build_deep_questions', 'BLIM', 'KnowledgeState']

# Self-test
if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    from lib.db import get_db
    conn = get_db()

    # Test engine instantiation
    engine = AssessmentEngine(conn)
    state = KnowledgeState(user_id="test")

    logger.info("Engine created. Initial mastery: %.3f", state.overall_mastery())

    # Test item selection
    item_id = engine.select_item(state, n_candidates=10)
    logger.info("Selected item: %s", item_id)

    if item_id:
        # Test response
        engine.assess_response(state, item_id, correct=True)
        logger.info("After correct: mastery=%.3f", state.get_mastery(item_id))

        engine.assess_response(state, item_id, correct=False)
        logger.info("After wrong: mastery=%.3f", state.get_mastery(item_id))

    # Test termination
    should_stop, reason = engine.should_terminate(state)
    logger.info("Termination: %s", reason)

    # Test BLIM
    blim = BLIM()
    for ability in [0.0, 0.25, 0.5, 0.75, 1.0]:
        p = blim.p_correct(ability)
        info = blim.information(ability)
        logger.info("  θ=%.2f: P(correct)=%.3f, info=%.3f", ability, p, info)

    conn.close()
