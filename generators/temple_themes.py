"""Temple-theme connections — Hebrew/Greek priority, English fallback.

Populates 5 empty sod connection types:
  - living_water        — Temple as source of living water (Ezek 47, Zech 14, Rev 22)
  - temple_throne        — Temple as divine throne room (Isa 6, Jer 17, throne-ark link)
  - temple_veil          — Veil as boundary between realms (poreketh, katapetasma)
  - primordial_creation  — Creation as first temple / Genesis temple themes
  - sacred_center        — Temple as navel of the world / axis mundi

Priority: Hebrew lemma (OT) → Greek lemma (NT) → English keyword (BoM/D&C).
"""

import json
from ._heb_grk import (
    get_ot_by_lemmas, get_ot_by_lemma, get_nt_by_greek,
    get_cross_canon, add_connections_for_group,
)

META = json.dumps({
    "generator": "temple_themes",
    "tag": "temple_themes",
    "note": "Algorithmic keyword-based temple theme connections",
}, ensure_ascii=False)


def _get_ot_like(conn, lemma):
    """Like get_ot_by_lemma but uses LIKE for lemmas with prefixes/suffixes."""
    rows = conn.execute(
        "SELECT DISTINCT verse_id FROM gematria WHERE lemma LIKE ?",
        (f'%{lemma}%',)
    ).fetchall()
    return [r["verse_id"] for r in rows]


def _add_pair(conn, src, tgt, type_name, subtype, strength, confidence):
    """Add a single hub pair connection if it doesn't exist."""
    existing = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE source_verse=? AND target_verse=? AND type=?",
        (src, tgt, type_name)
    ).fetchone()[0]
    if existing == 0:
        try:
            from lib.db import add_connection
            add_connection(conn, src, tgt, layer="sod",
                           type_name=type_name, subtype=subtype,
                           strength=strength, confidence=confidence,
                           discovered_by="algorithm", metadata=META)
            return 1
        except Exception:
            pass
    return 0


def run(conn, book_ids=None):
    count = 0

    # ── 1. living_water — Temple as source of living water ──
    # Hebrew: chay (2416) + mayim (4325) co-occurring = "living water"
    # Use LIKE because lemmas in DB have suffixes (e.g., "2416 a", "c/4325")
    chay_verses = _get_ot_like(conn, '2416')
    mayim_verses = _get_ot_like(conn, '4325')
    living_water_ot = list(set(chay_verses) & set(mayim_verses))

    # English fallback
    lw_english = []
    for pat in ['living water', 'water of life', 'river of water of life',
                'living waters', 'river of life']:
        rows = conn.execute(
            "SELECT id FROM verses WHERE text_english LIKE ? LIMIT 30",
            (f'%{pat}%',)
        ).fetchall()
        for r in rows:
            if r["id"] not in lw_english:
                lw_english.append(r["id"])

    # Greek: hydor (water) in NT
    lw_greek = get_nt_by_greek(conn, 'ὕδωρ')

    all_lw = list(set(living_water_ot + lw_greek + lw_english))
    c = add_connections_for_group(conn, all_lw, "sod", "living_water",
                                   "temple_water", 0.5, 0.35, "algorithm", META)
    count += c

    # Key hub connections — temple river passages
    for src, tgt in [
        ("ezek.47.1", "rev.22.1"),
        ("ezek.47.12", "rev.22.2"),
        ("psa.46.4", "rev.22.1"),
        ("john.7.38", "rev.22.1"),
        ("zec.14.8", "ezek.47.1"),
    ]:
        count += _add_pair(conn, src, tgt, "living_water", "temple_river", 0.55, 0.4)

    # ── 2. temple_throne — Temple as divine throne room ──
    # Hebrew: kisse (3678) + ark (7272) or sanctuary (4720) or tabernacle (4908)
    # Use get_ot_by_lemmas for exact match co-occurrence; fall back to LIKE on kisse
    kisse = _get_ot_like(conn, '3678')
    ark = _get_ot_like(conn, '7272')
    sanctuary = _get_ot_like(conn, '4720')
    tabernacle = _get_ot_like(conn, '4908')

    throne_ark = list(set(kisse) & set(ark))
    throne_sanct = list(set(kisse) & set(sanctuary))
    throne_tab = list(set(kisse) & set(tabernacle))
    all_throne_temple = list(set(throne_ark + throne_sanct + throne_tab))

    # NT: throne + temple/naos co-occurrence
    naos_throne = []
    thronos_rows = conn.execute(
        "SELECT DISTINCT verse_id FROM gematria_greek WHERE lemma LIKE '%θρόνο%' LIMIT 50"
    ).fetchall()
    for r in thronos_rows:
        vid = r["verse_id"]
        check = conn.execute(
            "SELECT COUNT(*) FROM gematria_greek WHERE verse_id=? AND (lemma LIKE '%ναό%' OR lemma LIKE '%ἱερό%')",
            (vid,)
        ).fetchone()[0]
        if check > 0:
            naos_throne.append(vid)

    cc_throne_temple = get_cross_canon(conn, 'throne of God')
    all_tt = list(set(all_throne_temple + naos_throne + cc_throne_temple))
    c = add_connections_for_group(conn, all_tt, "sod", "temple_throne",
                                   "throne_temple", 0.5, 0.35, "algorithm", META)
    count += c

    # Hub connections — key throne-temple passages
    for src, tgt in [
        ("isa.6.1", "rev.4.2"),
        ("jer.17.12", "psa.11.4"),
        ("psa.11.4", "hab.2.20"),
        ("rev.4.2", "rev.7.15"),
    ]:
        count += _add_pair(conn, src, tgt, "temple_throne", "throne_temple", 0.55, 0.4)

    # ── 3. temple_veil — Veil as boundary between realms ──
    # Hebrew: poreketh (6532), yeri'ah (3407 curtain), masak (4539 screen)
    veil_ot = _get_ot_like(conn, '6532')
    curtain_ot = _get_ot_like(conn, '3407')
    masak = _get_ot_like(conn, '4539')

    # NT: katapetasma (veil of the temple)
    gk_rows = conn.execute(
        "SELECT DISTINCT verse_id FROM gematria_greek WHERE lemma LIKE '%καταπέτασμα%' LIMIT 20"
    ).fetchall()
    veil_nt = [r["verse_id"] for r in gk_rows]

    cc_veil = get_cross_canon(conn, 'veil')
    all_veil = list(set(veil_ot + curtain_ot + masak + veil_nt + cc_veil))
    c = add_connections_for_group(conn, all_veil, "sod", "temple_veil",
                                   "veil_boundary", 0.5, 0.35, "algorithm", META)
    count += c

    # Hub connections — veil torn, veil of temple
    for src, tgt in [
        ("exo.26.31", "exo.26.33"),
        ("exo.26.31", "matt.27.51"),
        ("matt.27.51", "heb.6.19"),
        ("heb.6.19", "heb.10.20"),
        ("exo.26.33", "lev.16.2"),
    ]:
        count += _add_pair(conn, src, tgt, "temple_veil", "veil_boundary", 0.6, 0.45)

    # ── 4. primordial_creation — Creation as first temple ──
    # Hebrew: bara (1254/create) — use LIKE because DB stores "1254 a", "c/1254 a" etc.
    bara = _get_ot_like(conn, '1254')
    # yasad (3245/founded) — temple foundation language
    yasad = _get_ot_like(conn, '3245')

    # Cross-connect creation hub verses with temple foundation verses
    hub_creation = ['gen.1.1', 'gen.1.2', 'gen.1.3', 'gen.2.1', 'gen.2.2', 'gen.2.3']
    hub_temple = [r["id"] for r in conn.execute(
        "SELECT id FROM verses WHERE (book_id='1kgs' AND chapter=8) "
        "OR (book_id='psa' AND text_english LIKE '%founded%earth%') "
        "OR (book_id='psa' AND text_english LIKE '%laid%foundation%') LIMIT 20"
    ).fetchall()]

    for c_v in hub_creation:
        for t_v in hub_temple:
            count += _add_pair(conn, c_v, t_v, "primordial_creation",
                                "cosmos_temple", 0.45, 0.3)

    # Group connect bara + yasad verses (cap at 30 each to avoid explosion)
    bara_30 = bara[:30]
    yasad_30 = yasad[:30]
    c = add_connections_for_group(conn, list(set(bara_30 + yasad_30)),
                                   "sod", "primordial_creation",
                                   "creation_foundation", 0.4, 0.3, "algorithm", META)
    count += c

    # ── 5. sacred_center — Temple as navel of the world / axis mundi ──
    # Hebrew: tabbur (5369/navel), tavek (8432/midst)
    tabbur = _get_ot_like(conn, '5369')
    tavek = _get_ot_like(conn, '8432')
    # English cross-canon
    english_center = get_cross_canon(conn, 'midst')
    cc_center = get_cross_canon(conn, 'center')
    all_center_eng = list(set(english_center + cc_center))

    # Mountain-of-God passages: har (2022) + elohim (430)
    har = _get_ot_like(conn, '2022')
    elohim = _get_ot_like(conn, '430')
    mountain_god = list(set(har) & set(elohim))

    # Zion as sacred center
    zion_center = [r["id"] for r in conn.execute(
        "SELECT id FROM verses WHERE text_english LIKE '%Zion%' "
        "AND (text_english LIKE '%mountain%' OR text_english LIKE '%hill%') LIMIT 30"
    ).fetchall()]

    all_sc = list(set(tabbur + tavek + mountain_god + zion_center + all_center_eng))
    c = add_connections_for_group(conn, all_sc, "sod", "sacred_center",
                                   "axis_mundi", 0.45, 0.3, "algorithm", META)
    count += c

    # Key hub connections — sacred center passages
    for src, tgt in [
        ("ezek.38.12", "psa.74.12"),
        ("ezek.38.12", "isa.2.2"),
        ("psa.74.12", "isa.2.2"),
        ("psa.48.2", "isa.2.2"),
    ]:
        count += _add_pair(conn, src, tgt, "sacred_center", "axis_mundi", 0.5, 0.35)

    conn.commit()
    return count
