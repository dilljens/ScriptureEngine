// FIRe — Fractional Implicit Repetition.
//
// Adapted from plcourse (MIT): https://github.com/moaaz-ae/plcourse
// And Skycak's "The Math Academy Way" (Chapter 29).
//
// FIRe generalizes spaced repetition to connected knowledge:
//   1. CREDIT flows downward — reviewing an advanced topic gives
//      implicit repetition credit to simpler connected topics.
//   2. PENALTIES flow upward — failing a foundational topic
//      penalizes the topics that depend on it.
//   3. EARLY DISCOUNT — implicit credit is discounted when the
//      review was too early (retrievability still high).
//
// The Engine is graph-agnostic — it works with any KnowledgeGraph:
//   - Verse connections (memorization mode)
//   - Hebrew concept prerequisites (language learning mode)
//   - Story/thematic relationships (knowledge mode)

package fire

// Engine computes FIRe boosts and penalties using DFS.
type Engine struct{}

// Boost represents implicit repetition credit for a connected node.
type Boost struct {
	NodeID string  `json:"node_id"`
	CardID int64   `json:"card_id"`
	Boost  float64 `json:"boost"`
}

// New creates a FIRe engine.
func New() *Engine {
	return &Engine{}
}

// ConnectionWeight returns the encompassing weight for a connection type.
func ConnectionWeight(connType string) float64 {
	switch connType {
	case "direct_quotation", "direct_prerequisite":
		return 0.8
	case "modified_quotation", "key_prerequisite":
		return 0.7
	case "type_antitype", "encompassing":
		return 0.6
	case "chiastic":
		return 0.6
	case "parallel_synonymous", "parallel":
		return 0.5
	case "parallel_antithetic":
		return 0.5
	case "parallel_synthetic":
		return 0.5
	case "parallel_step":
		return 0.5
	case "same_lemma", "related_concept":
		return 0.4
	case "keyword_linking":
		return 0.4
	case "merismus":
		return 0.4
	case "emblematic_parallelism":
		return 0.4
	case "allusion", "story_echo":
		return 0.3
	case "echo":
		return 0.2
	case "shared_symbol":
		return 0.3
	default:
		return 0.2
	}
}

// RatingMultiplier — Good=0.5, Easy=1.0.
func RatingMultiplier(rating int) float64 {
	switch rating {
	case 4:
		return 1.0
	case 3:
		return 0.5
	default:
		return 0.0
	}
}

// PenaltyMultiplier — Again=1.0, Hard=0.3.
func PenaltyMultiplier(rating int) float64 {
	switch rating {
	case 1:
		return 1.0
	case 2:
		return 0.3
	default:
		return 0.0
	}
}

// EarlyDiscount reduces FIRe credit when review was too early.
func EarlyDiscount(boost, retrievability float64) float64 {
	if retrievability <= 0 {
		return boost
	}
	if retrievability >= 1 {
		return 0
	}
	return boost * (1.0 - retrievability*retrievability)
}

// KnowledgeGraph is a graph-agnostic interface for FIRe.
// Use with verse connections, language concepts, stories, etc.
type KnowledgeGraph struct {
	GetConnections func(nodeID string) ([]Edge, error)
	HasCard        func(nodeID string) (cardID int64, exists bool)
}

// Edge represents a directed relationship in a knowledge graph.
type Edge struct {
	SourceNode string `json:"source_node"`
	TargetNode string `json:"target_node"`
	Type       string `json:"type"`
}

// ComputeCredits computes both credits and penalties for any KnowledgeGraph.
func (e *Engine) ComputeCredits(
	sourceNodeID string,
	rating int,
	graph KnowledgeGraph,
) (credits, penalties []Boost, err error) {
	credits, err = computeCredit(sourceNodeID, RatingMultiplier(rating), graph)
	if err != nil {
		return nil, nil, err
	}
	penalties, err = computeCredit(sourceNodeID, PenaltyMultiplier(rating), graph)
	if err != nil {
		return nil, nil, err
	}
	return
}

func computeCredit(
	sourceNodeID string,
	multiplier float64,
	graph KnowledgeGraph,
) ([]Boost, error) {
	if multiplier <= 0 {
		return nil, nil
	}

	best := make(map[string]float64)
	bestCardID := make(map[string]int64)
	visited := make(map[string]bool)

	type node struct {
		id          string
		chainWeight float64
	}
	stack := []node{{id: sourceNodeID, chainWeight: 1.0}}

	for len(stack) > 0 {
		cur := stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		if cur.chainWeight < 0.001 || visited[cur.id] {
			continue
		}
		visited[cur.id] = true

		edges, err := graph.GetConnections(cur.id)
		if err != nil {
			return nil, err
		}

		for _, e := range edges {
			w := ConnectionWeight(e.Type)
			if w <= 0 {
				continue
			}
			cw := cur.chainWeight * w
			if cw < 0.001 || cw <= best[e.TargetNode] || e.TargetNode == sourceNodeID {
				continue
			}
			if cardID, ok := graph.HasCard(e.TargetNode); ok {
				best[e.TargetNode] = cw
				bestCardID[e.TargetNode] = cardID
			}
			stack = append(stack, node{id: e.TargetNode, chainWeight: cw})
		}
	}

	var res []Boost
	for id, cw := range best {
		res = append(res, Boost{NodeID: id, CardID: bestCardID[id], Boost: cw * multiplier})
	}
	return res, nil
}

// ── Legacy verse API (backward compat) ──

func (e *Engine) ComputeBoosts(
	sourceVerseID string, rating int,
	getConnections func(string) ([]Connection, error),
	hasCard func(string) (int64, bool),
) ([]Boost, error) {
	return computeCredit(sourceVerseID, RatingMultiplier(rating), toGraph(getConnections, hasCard))
}

func (e *Engine) ComputePenalties(
	sourceVerseID string, rating int,
	getConnections func(string) ([]Connection, error),
	hasCard func(string) (int64, bool),
) ([]Boost, error) {
	return computeCredit(sourceVerseID, PenaltyMultiplier(rating), toGraph(getConnections, hasCard))
}

func toGraph(
	getConnections func(string) ([]Connection, error),
	hasCard func(string) (int64, bool),
) KnowledgeGraph {
	return KnowledgeGraph{
		GetConnections: func(id string) ([]Edge, error) {
			cs, err := getConnections(id)
			if err != nil {
				return nil, err
			}
			es := make([]Edge, len(cs))
			for i, c := range cs {
				es[i] = Edge{SourceNode: c.SourceVerse, TargetNode: c.TargetVerse, Type: c.Type}
			}
			return es, nil
		},
		HasCard: hasCard,
	}
}

// Connection is a legacy verse-to-verse edge.
type Connection struct {
	SourceVerse string `json:"source_verse"`
	TargetVerse string `json:"target_verse"`
	Type        string `json:"type"`
}
