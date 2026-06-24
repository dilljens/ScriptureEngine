from .engine import AssessmentEngine
from .items import ItemGenerator
from .models import BLIM, KnowledgeState

__all__ = ['AssessmentEngine', 'ItemGenerator', 'BLIM', 'KnowledgeState']

# Self-test
if __name__ == "__main__":
    from lib.db import get_db
    conn = get_db()

    # Test engine instantiation
    engine = AssessmentEngine(conn)
    state = KnowledgeState(user_id="test")

    print(f"Engine created. Initial mastery: {state.overall_mastery():.3f}")

    # Test item selection
    item_id = engine.select_item(state, n_candidates=10)
    print(f"Selected item: {item_id}")

    if item_id:
        # Test response
        engine.assess_response(state, item_id, correct=True)
        print(f"After correct: mastery={state.get_mastery(item_id):.3f}")

        engine.assess_response(state, item_id, correct=False)
        print(f"After wrong: mastery={state.get_mastery(item_id):.3f}")

    # Test termination
    should_stop, reason = engine.should_terminate(state)
    print(f"Termination: {reason}")

    # Test BLIM
    blim = BLIM()
    for ability in [0.0, 0.25, 0.5, 0.75, 1.0]:
        p = blim.p_correct(ability)
        info = blim.information(ability)
        print(f"  θ={ability:.2f}: P(correct)={p:.3f}, info={info:.3f}")

    conn.close()
