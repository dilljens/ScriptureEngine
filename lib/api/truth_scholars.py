"""
Scholar credibility database for truth evaluation.
Each scholar gets a credibility weight based on credentials, peer review,
field expertise, and controversy level.
"""

SCHOLAR_CREDIBILITY = {
    "Margaret Barker": {
        "credentials": "Independent scholar, former Methodist preacher, Fellow of the Society of Antiquaries",
        "peer_reviewed": True,
        "field": "temple theology, Old Testament, Christian origins",
        "controversy_level": "high",  # Her First Temple thesis is debated
        "weight": 0.55,
        "notes": "Controversial but influential. Her work on temple theology is cited widely even by those who disagree.",
    },
    "G.K. Beale": {
        "credentials": "Professor of NT, Westminster Theological Seminary; PhD, Cambridge",
        "peer_reviewed": True,
        "field": "NT, temple theology, biblical theology",
        "controversy_level": "low",
        "weight": 0.90,
        "notes": "Highly respected in evangelical scholarship.",
    },
    "Michael S. Heiser": {
        "credentials": "PhD in Hebrew Bible, University of Wisconsin-Madison; Scholar-in-Residence, Logos Bible Software",
        "peer_reviewed": True,
        "field": "OT, divine council, Hebrew Bible",
        "controversy_level": "medium",
        "weight": 0.75,
        "notes": "Well-regarded dissertation on divine council, but his popular work (Unseen Realm) is less rigorous.",
    },
    "John H. Walton": {
        "credentials": "Professor of OT, Wheaton College; PhD, Hebrew Union College",
        "peer_reviewed": True,
        "field": "OT, ANE background, Genesis, temple",
        "controversy_level": "medium",
        "weight": 0.85,
        "notes": "His 'cosmic temple' thesis is respected but debated.",
    },
    "Richard Bauckham": {
        "credentials": "Professor of NT, University of St Andrews; PhD, Cambridge",
        "peer_reviewed": True,
        "field": "NT, early Christology, divine identity",
        "controversy_level": "low",
        "weight": 0.95,
        "notes": "Highly respected. His 'God Crucified' is a landmark work.",
    },
    "Alan Segal": {
        "credentials": "Professor of Religion, Barnard College/Columbia University; PhD, Hebrew University",
        "peer_reviewed": True,
        "field": "Second Temple Judaism, two powers, rabbinics",
        "controversy_level": "low",
        "weight": 0.85,
        "notes": "His 'Two Powers in Heaven' is the standard work on the subject.",
    },
    "Daniel Boyarin": {
        "credentials": "Professor of Talmudic Culture, UC Berkeley; PhD, Jewish Theological Seminary",
        "peer_reviewed": True,
        "field": "Talmud, Jewish Christianity, Logos theology",
        "controversy_level": "medium",
        "weight": 0.80,
        "notes": "Controversial but influential. Sometimes pushes beyond evidence.",
    },
    "Larry W. Hurtado": {
        "credentials": "Professor of NT Language and Literature, University of Edinburgh; PhD, Case Western",
        "peer_reviewed": True,
        "field": "NT, early Christian worship, Christology",
        "controversy_level": "low",
        "weight": 0.90,
        "notes": "His 'Lord Jesus Christ' is a standard reference.",
    },
    "Mark S. Smith": {
        "credentials": "Professor of OT, Princeton Theological Seminary; PhD, Yale",
        "peer_reviewed": True,
        "field": "OT, Ugaritic, Canaanite religion, early Israel",
        "controversy_level": "low",
        "weight": 0.85,
        "notes": "His 'Early History of God' is the standard work on Canaanite influence on Israel.",
    },
    "William G. Dever": {
        "credentials": "Professor of Near Eastern Archaeology, University of Arizona; PhD, Harvard",
        "peer_reviewed": True,
        "field": "ANE archaeology, Israelite religion, Asherah",
        "controversy_level": "medium",
        "weight": 0.80,
        "notes": "Leading Syro-Palestinian archaeologist. Controversial on minimalist-maximalist debates.",
    },
    "Raphael Patai": {
        "credentials": "Anthropologist, ethnographer; PhD, University of Budapest",
        "peer_reviewed": True,
        "field": "Hebrew myth, goddess worship, Jewish folklore",
        "controversy_level": "high",
        "weight": 0.50,
        "notes": "Pioneering but dated. His 'Hebrew Goddess' opened the field but is not current scholarship.",
    },
    "Susan Ackerman": {
        "credentials": "Professor of Religion, Dartmouth; PhD, Harvard",
        "peer_reviewed": True,
        "field": "Israelite religion, gender, goddess worship",
        "controversy_level": "low",
        "weight": 0.80,
        "notes": "Solid scholar on Asherah/Astarte distinctions.",
    },
    "Frank Moore Cross": {
        "credentials": "Professor of Hebrew, Harvard; PhD, Johns Hopkins",
        "peer_reviewed": True,
        "field": "OT, Ugaritic, Israelite religion, Deuteronomy",
        "controversy_level": "low",
        "weight": 0.90,
        "notes": "One of the most influential OT scholars of the 20th century.",
    },
    "Dave Butler": {
        "credentials": "Independent scholar (lawyer by trade), self-published",
        "peer_reviewed": False,
        "field": "LDS temple studies",
        "controversy_level": "medium",
        "weight": 0.20,
        "notes": "No academic credentials or peer review. Builds on Barker/Welch/Nibley but without scholarly apparatus.",
    },
    "Scholarly Consensus": {
        "credentials": "General consensus among relevant scholars",
        "peer_reviewed": True,
        "field": "varies",
        "controversy_level": "low",
        "weight": 0.85,
        "notes": "Used for claims that represent mainstream scholarly agreement.",
    },
}


def get_scholar_weight(name: str) -> float:
    """Get the credibility weight for a scholar by name (fuzzy match)."""
    # Direct match first
    if name in SCHOLAR_CREDIBILITY:
        return SCHOLAR_CREDIBILITY[name]["weight"]

    # Try matching on last name
    name_lower = name.lower()
    for key, info in SCHOLAR_CREDIBILITY.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return info["weight"]
    
    # Check if it's a compound name (e.g., "Margaret Barker / William Dever")
    parts = name.split("/")
    weights = []
    for part in parts:
        part = part.strip()
        for key, info in SCHOLAR_CREDIBILITY.items():
            if key.lower() in part.lower():
                weights.append(info["weight"])
                break
    
    if weights:
        return sum(weights) / len(weights)  # Average weight for compound scholars
    
    # Default: moderate credibility for unknown scholars
    return 0.50


def list_scholars():
    """List all scholars with their weights and credentials."""
    result = []
    for name, info in sorted(SCHOLAR_CREDIBILITY.items()):
        result.append({
            "name": name,
            "weight": info["weight"],
            "credentials": info["credentials"],
            "peer_reviewed": info["peer_reviewed"],
            "field": info["field"],
            "controversy_level": info["controversy_level"],
        })
    return result


def add_scholar(name: str, credentials: str = "", peer_reviewed: bool = False,
                 field: str = "", controversy_level: str = "medium",
                 weight: float = 0.5, notes: str = ""):
    """Add or update a scholar in the database (in-memory)."""
    SCHOLAR_CREDIBILITY[name] = {
        "credentials": credentials,
        "peer_reviewed": peer_reviewed,
        "field": field,
        "controversy_level": controversy_level,
        "weight": weight,
        "notes": notes,
    }
    return SCHOLAR_CREDIBILITY[name]
