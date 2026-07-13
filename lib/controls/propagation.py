"""Confidence propagation through the connection graph.

When verse A connects to verse B with confidence C1, and verse B connects
to verse C with confidence C2, the inferred path A→B→C has some propagated
confidence. This module computes that.

The propagation considers:
  1. Product of edge confidences along the path
  2. Path length penalty (longer paths are weaker)
  3. Layer compatibility (some layers chain naturally)
"""

# Layer compatibility matrix
# Values 0.0-1.0: how naturally two layers chain together
# 0.8+ = natural pipeline (linguistic→sod, intertextual→interpretive)
# 0.5 = neutral
# 0.0 = incompatible (should not chain)

LAYER_COMPATIBILITY = {
    # ── Natural pipelines ──
    ("linguistic", "sod"): 0.8,          # Words → hidden meaning
    ("linguistic", "symbolic"): 0.7,     # Words → symbols
    ("linguistic", "numerical"): 0.6,    # Words → gematria
    ("intertextual", "interpretive"): 0.7,  # Quotes → meaning
    ("intertextual", "sod"): 0.6,        # Quotes → hidden meaning
    ("structural", "symbolic"): 0.6,     # Patterns → symbols
    ("numerical", "sod"): 0.6,           # Numbers → hidden
    ("frequency", "structural"): 0.6,    # Word counts → patterns
    ("chronological", "interpretive"): 0.5,  # Timeline → meaning
    ("geographic", "chronological"): 0.5,    # Places → time
    ("textual", "linguistic"): 0.6,      # Variants → words

    # ── Moderate connections ──
    ("symbolic", "interpretive"): 0.5,
    ("sod", "interpretive"): 0.5,
    ("linguistic", "intertextual"): 0.5,
    ("chronological", "geographic"): 0.5,

    # ── Weak connections ──
    ("geographic", "linguistic"): 0.3,
    ("frequency", "sod"): 0.3,
    ("numerical", "interpretive"): 0.3,
    ("structural", "textual"): 0.2,
    ("frequency", "chronological"): 0.3,
}


DEFAULT_LAYER_COMPATIBILITY = 0.2


def layer_compatibility(layer_a, layer_b):
    """Get compatibility score between two layers."""
    if layer_a == layer_b:
        return 1.0
    pair = (layer_a, layer_b) if layer_a <= layer_b else (layer_b, layer_a)
    # Try exact match
    pair_rev = (layer_a, layer_b) if layer_a > layer_b else (layer_b, layer_a)
    return LAYER_COMPATIBILITY.get(pair, LAYER_COMPATIBILITY.get(pair_rev, DEFAULT_LAYER_COMPATIBILITY))


def path_confidence(path, fallback_confidence=0.5):
    """Compute propagated confidence along a path of connections.
    
    Args:
        path: list of dicts, each with at least 'confidence' and 'layer' keys
              OR list of (confidence, layer) tuples
        fallback_confidence: default confidence if a hop has none
    
    Returns:
        Propagated confidence value (0.0-1.0).
    """
    if not path:
        return 0.0
    if len(path) == 1:
        return path[0].get("confidence", fallback_confidence) if isinstance(path[0], dict) else path[0][0]
    
    # Extract confidence and layer from each hop
    hops = []
    for hop in path:
        if isinstance(hop, dict):
            hops.append({
                "confidence": float(hop.get("confidence", fallback_confidence) or fallback_confidence),
                "layer": hop.get("layer", ""),
                "type": hop.get("type", ""),
            })
        elif isinstance(hop, (list, tuple)):
            # Tuple (confidence, layer) or (confidence, layer, type)
            c = float(hop[0] or fallback_confidence) if hop[0] is not None else float(fallback_confidence)
            l = str(hop[1]) if len(hop) > 1 else ""
            hops.append({"confidence": c, "layer": l, "type": str(hop[2]) if len(hop) > 2 else ""})
        else:
            hops.append({"confidence": float(fallback_confidence), "layer": "", "type": ""})
    
    # Product of confidences
    conf_product = 1.0
    for h in hops:
        conf_product *= h["confidence"]
    
    # Path length penalty
    length_penalty = 1.0 / (len(hops) ** 0.5)
    
    # Layer compatibility product
    compat_product = 1.0
    for i in range(len(hops) - 1):
        compat_product *= layer_compatibility(hops[i]["layer"], hops[i + 1]["layer"])
    
    propagated = conf_product * length_penalty * compat_product
    return round(min(propagated, 1.0), 4)


def propagate_to_reachable(reachable_verses, source_verse, connection_graph):
    """Add propagated confidence to reachable verses from a source.
    
    Args:
        reachable_verses: list of {verse, path, ...} from graph traversal
        source_verse: the starting verse
        connection_graph: function that returns connections for a verse
    
    Returns:
        The same list with 'propagated_confidence' added to each entry.
    """
    for entry in reachable_verses:
        path = entry.get("path", [])
        if path:
            # Build path with confidence and layer
            full_path = []
            # Start with source→first
            if source_verse:
                conns = connection_graph(source_verse)
                first_target = path[0] if isinstance(path[0], str) else path[0].get("verse", "")
                for c in conns:
                    if c.get("target_verse") == first_target or c.get("source_verse") == first_target:
                        full_path.append(c)
                        break
            entry["propagated_confidence"] = path_confidence(full_path)
        else:
            entry["propagated_confidence"] = 0.0
    
    return reachable_verses
