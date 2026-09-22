"""
Rule-based multi-criteria recommendation engine.

Logic:
1. Derive a REQUIRED range for OTR and WVTR from the input food/storage
   parameters (this is the "AI knowledge" layer — encodes packaging science).
2. Score every material in the DB against those required ranges plus
   temperature compatibility, cost, and sustainability.
3. Return the ranked top-N materials with reasoning.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

with open(os.path.join(DATA_DIR, "materials.json")) as f:
    MATERIALS = json.load(f)

with open(os.path.join(DATA_DIR, "commodities.json")) as f:
    COMMODITIES = json.load(f)


def derive_required_barrier(inputs: dict) -> dict:
    """
    Turns raw food/storage parameters into required OTR/WVTR windows.
    inputs keys: moisture_content(%), oil_content(%), pH, respiration_rate
    (mgCO2/kg/hr or None), storage_type ('ambient'|'chilled'|'frozen'),
    desired_shelf_life_days, storage_temp_c, rh_pct
    """
    moisture = inputs.get("moisture_content", 0)
    oil = inputs.get("oil_content", 0)
    respiration = inputs.get("respiration_rate", 0) or 0
    shelf_life = inputs.get("desired_shelf_life_days", 7)
    storage_type = inputs.get("storage_type", "ambient")

    # --- WVTR requirement ---
    # High moisture + long shelf life + dry/ambient storage => need LOW WVTR
    # (stop moisture escaping/entering). Fresh produce needs some breathability.
    if respiration > 0:
        # fresh produce: allow moderate-high WVTR (needs to breathe)
        wvtr_max = 40
        wvtr_min = 10
    elif moisture > 50:
        # high moisture product (dairy, meat) -> must retain moisture, low WVTR
        wvtr_max = 5
        wvtr_min = 0
    elif moisture > 15:
        wvtr_max = 10
        wvtr_min = 0
    else:
        # dry product (snacks) -> must keep moisture OUT, low WVTR, longer = stricter
        wvtr_max = max(1, 8 - shelf_life / 30)
        wvtr_min = 0

    if storage_type == "frozen":
        wvtr_max = min(wvtr_max, 2)  # frost/freezer burn protection

    # --- OTR requirement ---
    if oil > 10:
        # oxidation-prone (fats/oils) -> need LOW OTR, stricter with longer shelf life
        otr_max = max(0.5, 10 - shelf_life / 10)
        otr_min = 0
    elif respiration > 0:
        # fresh produce needs OTR roughly proportional to respiration rate
        # (simplified steady-state MAP approximation)
        otr_min = respiration * 20
        otr_max = respiration * 80
    else:
        otr_max = 50
        otr_min = 0

    return {
        "wvtr_required": (wvtr_min, wvtr_max),
        "otr_required": (otr_min, otr_max),
    }


def _range_overlap_score(required, material_range):
    """
    0-1 score for how well a material fits the required window.
    Scored as the fraction of the MATERIAL's own range that falls inside the
    requirement — so a tight, precise barrier film that sits fully inside the
    required window scores 1.0 (not penalized just for being narrow), while a
    material only partially overlapping the requirement is scored down.
    """
    req_lo, req_hi = required
    mat_lo, mat_hi = material_range
    overlap_lo = max(req_lo, mat_lo)
    overlap_hi = min(req_hi, mat_hi)
    if overlap_hi <= overlap_lo:
        return 0.0
    overlap = overlap_hi - overlap_lo
    mat_span = max(mat_hi - mat_lo, 1e-6)
    return min(1.0, overlap / mat_span)


def recommend(inputs: dict, top_n: int = 3, sustainability_weight: float = 0.15,
              cost_weight: float = 0.15) -> list:
    req = derive_required_barrier(inputs)
    storage_temp = inputs.get("storage_temp_c", 25)

    scored = []
    for m in MATERIALS:
        wvtr_score = _range_overlap_score(req["wvtr_required"], tuple(m["wvtr_g_m2_day"]))
        otr_score = _range_overlap_score(req["otr_required"], tuple(m["otr_cc_m2_day"]))

        temp_ok = m["min_temp_c"] <= storage_temp <= m["max_temp_c"]
        temp_score = 1.0 if temp_ok else 0.0

        sustainability_score = (0.6 if m["recyclable"] else 0) + (0.4 if m["biodegradable"] else 0)
        cost_score = 1 - min(1.0, m["cost_inr_per_sqm"] / 30)  # cheaper = higher score

        barrier_score = 0.5 * wvtr_score + 0.5 * otr_score
        total = (
            barrier_score * (1 - sustainability_weight - cost_weight)
            + sustainability_score * sustainability_weight
            + cost_score * cost_weight
        ) * temp_score  # hard filter: unusable if temp range doesn't fit

        scored.append({
            "material": m["name"],
            "type": m["type"],
            "score": round(total, 3),
            "barrier_fit": round(barrier_score, 2),
            "temp_compatible": temp_ok,
            "sustainability_score": round(sustainability_score, 2),
            "cost_inr_per_sqm": m["cost_inr_per_sqm"],
            "image_path": m.get("image_path", ""),
            "typical_uses": m.get("typical_uses", []),
            "spec": {
                "otr_cc_m2_day": m["otr_cc_m2_day"],
                "wvtr_g_m2_day": m["wvtr_g_m2_day"],
                "thickness_micron": m["thickness_micron"],
                "sealability_score": m["sealability_score"],
                "mechanical_strength_score": m["mechanical_strength_score"],
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n], req


def find_commodity(name_query: str):
    name_query = name_query.lower()
    for c in COMMODITIES:
        if name_query in c["name"].lower():
            return c
    return None
