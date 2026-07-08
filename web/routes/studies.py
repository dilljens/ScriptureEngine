"""Study guide routes — thematic + user + published."""
import json, os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent


def get_db():
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()

# Study API functions — imported at module level so route functions can use them
from lib.api.study import (
    create_guide, get_guide, list_guides, update_guide as study_update,
    add_step as study_add_step, remove_step as study_remove_step,
    reorder_steps as study_reorder, bulk_update_steps as study_bulk_update,
    export_json as study_export_json,
    export_html as study_export_html, import_json as study_import_json,
    publish_study as study_publish, get_published as study_get_published,
    list_published as study_list_published, fork_published as study_fork,
)


# ─── Thematic Study Guides ───

THEMATIC_GUIDES = {
    "covenant": {
        "title": "Covenant Thread",
        "description": "God's covenant relationship with His people from Noah through the New Covenant",
        "connections": [
            ("gen.9.9", "Noahic Covenant — God promises never to flood the earth again"),
            ("gen.15.18", "Abrahamic Covenant — land and seed promised"),
            ("gen.17.10", "Circumcision as the sign of the covenant"),
            ("exo.19.5", "Sinai Covenant — Israel as a kingdom of priests"),
            ("exo.24.8", "Blood of the covenant ratifies the relationship"),
            ("deu.29.1", "Covenant renewal in Moab"),
            ("2sam.7.12", "Davidic Covenant — an eternal throne"),
            ("jer.31.31", "New Covenant promised — law written on the heart"),
            ("ezek.36.26", "A new heart and a new spirit"),
            ("luke.22.20", "New Covenant in Christ's blood"),
            ("heb.8.8", "The New Covenant makes the first obsolete"),
        ],
    },
    "exodus": {
        "title": "Exodus Pattern",
        "description": "The Exodus as the template for God's deliverance — repeated throughout scripture",
        "connections": [
            ("gen.12.1", "Abraham's call begins the journey pattern"),
            ("exo.3.1", "Moses called at the burning bush"),
            ("exo.12.1", "Passover — the lamb's blood delivers from death"),
            ("exo.14.21", "Red Sea crossing — deliverance through waters"),
            ("exo.16.4", "Manna — bread from heaven"),
            ("exo.17.6", "Water from the rock"),
            ("isa.43.16", "A new exodus promised"),
            ("hos.11.1", "Out of Egypt I called my son"),
            ("matt.2.15", "Jesus recapitulates the Exodus"),
            ("john.6.31", "Jesus as the true bread from heaven"),
            ("1ne.17.26", "Lehi's exodus to the promised land"),
        ],
    },
    "temple": {
        "title": "Temple / Presence of God",
        "description": "The dwelling of God with humanity — from Eden to the New Jerusalem",
        "connections": [
            ("gen.2.8", "Eden as God's garden-temple"),
            ("gen.28.17", "Bethel — the gate of heaven"),
            ("exo.25.8", "The Tabernacle — God dwells among His people"),
            ("exo.40.34", "The glory of the LORD fills the Tabernacle"),
            ("1kgs.8.10", "The glory fills Solomon's Temple"),
            ("isa.6.1", "Isaiah's vision of the LORD in the Temple"),
            ("ezek.47.1", "Water flows from the Temple"),
            ("1cor.3.16", "Believers as the temple of God"),
            ("rev.21.22", "The Lord God Almighty is the Temple"),
        ],
    },
    "temple_symbolism": {
        "title": "Temple Symbolism Deep Dive",
        "description": "Every element of the Tabernacle/Temple as a symbol of Christ, creation, and the covenant path",
        "connections": [
            ("exo.25.10", "Ark of the Covenant — the throne of God (Christ as King)"),
            ("exo.25.17", "Mercy Seat (kapporet) — the place of atonement (Christ as High Priest)"),
            ("exo.25.18", "Cherubim — guardians of God's throne (heavenly attendants)"),
            ("exo.25.23", "Table of Showbread — bread of God's presence (Christ as Bread of Life)"),
            ("exo.25.31", "Golden Lampstand (menorah) — light of God's presence (Christ as Light)"),
            ("exo.26.1", "Tabernacle curtains — the heavens stretched out (cosmic symbolism)"),
            ("exo.26.31", "The Veil — separation between God and humanity (rent in Christ)"),
            ("exo.27.1", "Bronze Altar — judgment and sacrifice (the cross)"),
            ("exo.30.1", "Altar of Incense — prayers ascending to God"),
            ("exo.30.17", "Laver — cleansing and baptism"),
            ("exo.28.15", "High Priest's breastplate — bearing the tribes before God"),
            ("lev.16.15", "Day of Atonement — the scapegoat and the sin offering"),
            ("heb.9.11", "Christ as the High Priest entering the heavenly Holy of Holies"),
            ("rev.21.22", "No temple — God's presence is everywhere"),
        ],
    },
    "shepherd": {
        "title": "Shepherd / Flock",
        "description": "The shepherd metaphor — God as Shepherd, Israel as flock, Christ as Good Shepherd",
        "connections": [
            ("psa.23.1", "The LORD is my Shepherd"),
            ("psa.80.1", "Shepherd of Israel"),
            ("isa.40.11", "He shall feed His flock like a shepherd"),
            ("jer.23.1", "Woe to the shepherds who scatter the flock"),
            ("ezek.34.11", "I myself will search for my sheep"),
            ("zech.13.7", "Smite the Shepherd"),
            ("john.10.11", "I am the good Shepherd"),
            ("1pet.5.4", "Chief Shepherd shall appear"),
        ],
    },
    "creation_new_creation": {
        "title": "Creation & New Creation",
        "description": "The biblical arc from creation to new creation",
        "connections": [
            ("gen.1.1", "In the beginning God created"),
            ("gen.1.26", "Man created in God's image"),
            ("gen.2.7", "Man formed from the dust"),
            ("gen.3.17", "The ground cursed because of sin"),
            ("isa.65.17", "New heavens and a new earth"),
            ("2cor.5.17", "If any man be in Christ, new creature"),
            ("rev.21.1", "New heaven and new earth"),
            ("rev.22.1", "River of life — Eden restored and surpassed"),
        ],
    },
}

@router.get("/api/v1/studies/thematic/{guide_id:path}")
def get_thematic_study(guide_id: str):
    """Get a thematic study guide — ordered progression of verses on a theme."""
    gid = guide_id.strip("/").lower()
    guide = THEMATIC_GUIDES.get(gid)
    if not guide:
        return {"ok": False, "error": f"Guide not found. Available: {list(THEMATIC_GUIDES.keys())}"}

    conn = get_db()
    enriched = []
    for verse_ref, explanation in guide["connections"]:
        row = conn.execute("""
            SELECT text_english, text_hebrew, text_greek
            FROM verses WHERE id = ?
        """, (verse_ref,)).fetchone()
        entry = {"reference": verse_ref, "explanation": explanation}
        if row:
            entry["text"] = row["text_english"]
            entry["has_hebrew"] = bool(row["text_hebrew"])
        enriched.append(entry)
    conn.close()

    return {"ok": True, "data": {
        "id": gid,
        "title": guide["title"],
        "description": guide["description"],
        "connections": enriched,
        "total": len(enriched),
    }}

@router.get("/api/v1/studies/thematic")
def list_thematic_studies():
    """List all available thematic study guides."""
    return {"ok": True, "data": {
        "studies": [
            {"id": k, "title": v["title"], "description": v["description"], "count": len(v["connections"])}
            for k, v in THEMATIC_GUIDES.items()
        ],
        "total": len(THEMATIC_GUIDES),
    }}


# ─── User Study Guides (JSON-first, with graph paths) ───


class CreateStudyRequest(BaseModel):
    title: str
    description: str = ""
    theme: str = ""
    seed_verse: str = ""
    created_by: str = "anonymous"
    steps: list = []

class ImportStudyRequest(BaseModel):
    json_str: str
    created_by: str = "user"

class PublishStudyRequest(BaseModel):
    author_name: str = "anonymous"
    author_id: str = ""
    forked_from: str = ""


@router.get("/api/v1/studies")
def list_study_guides(theme: str = "", limit: int = 20):
    """List all study guides."""
    conn = get_db()
    result = list_guides(conn, theme=theme or None, limit=limit)
    conn.close()
    return {"ok": True, "data": result}


@router.post("/api/v1/studies")
def create_study_guide(req: CreateStudyRequest):
    """Create a new study guide with optional initial steps."""
    conn = get_db()
    steps_data = [dict(s) for s in req.steps] if req.steps else None
    result = create_guide(conn, req.title, req.description, req.theme,
                          req.seed_verse, req.created_by, steps=steps_data)
    conn.close()
    return {"ok": True, "data": result}


# ─── Published Studies (public, immutable, shareable) — defined BEFORE {guide_id} routes ───


@router.get("/api/v1/studies/published")
def list_published_studies(limit: int = 20, offset: int = 0):
    """List all published studies, most recent first."""
    conn = get_db()
    result = study_list_published(conn, limit=limit, offset=offset)
    conn.close()
    return {"ok": True, "data": result}


@router.post("/api/v1/studies/import")
def import_study(req: ImportStudyRequest):
    """Import a study from a JSON string."""
    conn = get_db()
    try:
        result = study_import_json(conn, req.json_str, created_by=req.created_by)
        conn.close()
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}



@router.post("/api/v1/studies/published/{slug}/fork")
def fork_published_study(slug: str, created_by: str = "user"):
    """Fork a published study into a new mutable study guide."""
    conn = get_db()
    result = study_fork(conn, slug, created_by=created_by)
    conn.close()
    return {"ok": True, "data": result}


# These use path() suffix to avoid conflicting with "published" path component
@router.api_route("/api/v1/studies/published/{slug}.json", methods=["GET"])
def download_published_study_json(slug: str):
    """Download a published study as JSON. Slug must not have .json extension."""
    conn = get_db()
    result = study_get_published(conn, slug)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Published study '{slug}' not found"}
    from fastapi.responses import Response
    import json
    return Response(content=json.dumps(result, indent=2, ensure_ascii=False),
                    media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{slug}.json"'})


@router.api_route("/api/v1/studies/published/{slug}.html", methods=["GET"])
def download_published_study_html(slug: str):
    """Download a published study as self-contained HTML. Slug must not have .html extension."""
    conn = get_db()
    result = study_get_published(conn, slug)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Published study '{slug}' not found"}
    from lib.api.study import _render_html
    html = _render_html(result)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.get("/api/v1/studies/published/{slug}")
def get_published_study(slug: str):
    """Get a published study by its slug."""
    conn = get_db()
    result = study_get_published(conn, slug)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Published study '{slug}' not found"}
    return {"ok": True, "data": result}


# ─── Parameterized study guide routes (keep after static routes) ───


@router.get("/api/v1/studies/{guide_id}")
def get_study_guide(guide_id: int):
    """Get a study guide with enriched steps and graph paths."""
    conn = get_db()
    result = get_guide(conn, guide_id)
    conn.close()
    if not result:
        return {"ok": False, "error": f"Study guide {guide_id} not found"}
    return {"ok": True, "data": result}


@router.get("/api/v1/studies/{guide_id}/export.json")
def export_study_json(guide_id: int):
    """Export a study guide as JSON with full graph paths."""
    conn = get_db()
    js = study_export_json(conn, guide_id)
    conn.close()
    if not js:
        return {"ok": False, "error": f"Study guide {guide_id} not found"}
    from fastapi.responses import Response
    return Response(content=js, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="study-{guide_id}.json"'})


@router.get("/api/v1/studies/{guide_id}/export.html")
def export_study_html(guide_id: int):
    """Export a study guide as a self-contained HTML page."""
    conn = get_db()
    html = study_export_html(conn, guide_id)
    conn.close()
    if not html:
        return {"ok": False, "error": f"Study guide {guide_id} not found"}
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.post("/api/v1/studies/{guide_id}/publish")
def publish_study_guide(guide_id: int, req: PublishStudyRequest = None):
    """Publish a study as an immutable snapshot with a shareable URL."""
    conn = get_db()
    kw = {"author_name": req.author_name, "author_id": req.author_id} if req else {}
    if req and req.forked_from:
        kw["forked_from"] = req.forked_from
    result = study_publish(conn, guide_id, **kw)
    conn.close()
    return {"ok": True, "data": result}


class UpdateStudyRequest(BaseModel):
    title: str = ""
    description: str = ""
    theme: str = ""
    seed_verse: str = ""

class AddStepRequest(BaseModel):
    step_number: int
    verse_id: str
    title: str = ""
    explanation: str = ""
    connection_from: str = ""
    connection_type: str = ""
    connection_layer: str = ""

class BulkStepsRequest(BaseModel):
    steps: list


@router.patch("/api/v1/studies/{guide_id}")
def update_study_metadata(guide_id: int, req: UpdateStudyRequest):
    """Update study guide metadata."""
    conn = get_db()
    kw = {k: v for k, v in req.dict().items() if v}
    result = study_update(conn, guide_id, **kw)
    conn.close()
    return {"ok": True, "data": result}


@router.post("/api/v1/studies/{guide_id}/steps")
def add_study_step(guide_id: int, req: AddStepRequest):
    """Add a step to a study guide."""
    conn = get_db()
    result = study_add_step(conn, guide_id, req.step_number, req.verse_id,
                            title=req.title, explanation=req.explanation,
                            connection_from=req.connection_from,
                            connection_type=req.connection_type,
                            connection_layer=req.connection_layer)
    conn.close()
    return {"ok": True, "data": result}


@router.delete("/api/v1/studies/{guide_id}/steps/{step_number}")
def delete_study_step(guide_id: int, step_number: int):
    """Remove a step from a study guide and re-number remaining steps."""
    conn = get_db()
    result = study_remove_step(conn, guide_id, step_number)
    conn.close()
    return {"ok": True, "data": result}


@router.put("/api/v1/studies/{guide_id}/steps")
def bulk_update_study_steps(guide_id: int, req: BulkStepsRequest):
    """Replace all steps of a study guide (deletes existing, inserts new)."""
    conn = get_db()
    result = study_bulk_update(conn, guide_id, req.steps)
    conn.close()
    return {"ok": True, "data": result}