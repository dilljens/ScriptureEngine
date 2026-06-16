"""Connection generator registry.

Each generator module exports a `run(conn, book_ids=None) -> int` function.
The registry discovers all generators and provides a unified runner.
"""

import importlib
import pkgutil
from pathlib import Path

# Generator registry — populated at import time
REGISTRY = {}

# Generator metadata — each entry has:
#   name: display name
#   module: the Python module
#   layers: list of layer names this generator populates
#   automatic: True if can run without AI review
#   requires: data dependencies

GENERATOR_DEFS = [
    {
        "name": "Linguistic — Same Lemma",
        "module_path": ".linguistic",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses sharing rare Hebrew lemmas (Strong's numbers)",
    },
    {
        "name": "Structural — Chiastic Pairs",
        "module_path": ".structural",
        "layers": ["structural"],
        "automatic": True,
        "requires": "known_chiasms table + chiastic detector",
        "description": "Connects A↔A', B↔B' pairs from known and detected chiasms",
    },
    {
        "name": "Intertextual — Quotation Detection",
        "module_path": ".intertextual",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through shared rare-word clusters indicating quotations/allusions",
    },
    {
        "name": "Frequency — Distribution",
        "module_path": ".frequency",
        "layers": ["frequency"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses with shared word frequency patterns",
    },
    {
        "name": "Geographic — Location",
        "module_path": ".geographic",
        "layers": ["geographic"],
        "automatic": False,
        "requires": "place name gazetteer (simple seed included)",
        "description": "Connects verses mentioning the same biblical location",
    },
    {
        "name": "Numerical — Full Gematria",
        "module_path": ".numerical_full",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Expands gematria connections beyond divine names to all sacred numbers and value matches",
    },
]

# Import all generator modules
def _import_all():
    for gen_def in GENERATOR_DEFS:
        module_path = gen_def["module_path"]
        try:
            module = importlib.import_module(module_path, package="generators")
            gen_def["module"] = module
            gen_def["loaded"] = True
        except Exception as e:
            gen_def["module"] = None
            gen_def["loaded"] = False
            gen_def["load_error"] = str(e)


def run_generator(conn, name, book_ids=None):
    """Run a single generator by name."""
    for gen in GENERATOR_DEFS:
        if gen["name"] == name:
            if not gen.get("loaded"):
                return {"error": f"Generator '{name}' not loaded: {gen.get('load_error', 'unknown')}"}
            try:
                count = gen["module"].run(conn, book_ids)
                conn.commit()
                return {"generator": name, "connections": count, "layers": gen["layers"]}
            except Exception as e:
                conn.rollback()
                return {"error": f"Generator '{name}' failed: {e}"}
    return {"error": f"Generator '{name}' not found"}


def run_all(conn, book_ids=None, automatic_only=True):
    """Run all loaded generators and return stats."""
    results = []
    for gen in GENERATOR_DEFS:
        if automatic_only and not gen["automatic"]:
            continue
        if not gen.get("loaded"):
            results.append({"generator": gen["name"], "status": "skipped", "error": gen.get("load_error", "not loaded")})
            continue
        try:
            count = gen["module"].run(conn, book_ids)
            conn.commit()
            results.append({"generator": gen["name"], "connections": count, "layers": gen["layers"], "status": "ok"})
        except Exception as e:
            conn.rollback()
            results.append({"generator": gen["name"], "status": "error", "error": str(e)})
    return results


def list_generators():
    """List all registered generators and their status."""
    return [
        {
            "name": g["name"],
            "layers": g["layers"],
            "automatic": g["automatic"],
            "requires": g["requires"],
            "description": g["description"],
            "loaded": g.get("loaded", False),
        }
        for g in GENERATOR_DEFS
    ]


# Import all at module load
_import_all()
