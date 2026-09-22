from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os

from app.rule_engine import recommend, find_commodity, COMMODITIES, MATERIALS
from app.shelf_life import predict_shelf_life
from app.extras import get_map_gas, generate_qr_base64
from app.ai_analyzer import analyze_food_item, analyze_food_image, DEFAULT_GEMINI_API_KEY

app = FastAPI(title="AI Packaging Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve material assets statically
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


class FoodAnalysisRequest(BaseModel):
    product_name: str
    api_key: Optional[str] = None


class FoodImageAnalysisRequest(BaseModel):
    image_base64: str
    mime_type: Optional[str] = "image/jpeg"
    api_key: Optional[str] = None


class RecommendationRequest(BaseModel):
    commodity_name: Optional[str] = None
    moisture_content: float = 0
    oil_content: float = 0
    ph: Optional[float] = None
    respiration_rate: Optional[float] = 0
    desired_shelf_life_days: float = 7
    storage_temp_c: float = 25
    rh_pct: Optional[float] = 60
    storage_type: str = "ambient"  # ambient | chilled | frozen


@app.get("/commodities")
def list_commodities():
    return [c["name"] for c in COMMODITIES]


@app.get("/materials")
def list_materials():
    return MATERIALS


@app.post("/analyze-food")
def analyze_food(req: FoodAnalysisRequest):
    """
    Analyzes any food item with Gemini (or Food Science Engine) and calculates
    moisture %, oil %, pH, respiration rate, storage temp, and recommended RH %.
    """
    result = analyze_food_item(req.product_name, api_key=req.api_key)
    return result


@app.post("/analyze-food-image")
def analyze_image_food(req: FoodImageAnalysisRequest):
    """
    Multimodal Vision Analysis using Gemini 2.5 Flash:
    Accepts base64 encoded photo from camera or phone gallery and identifies the food item,
    visual state/freshness, moisture %, oil %, pH, respiration rate, storage temp, and RH %.
    """
    import base64
    img_bytes = base64.b64decode(req.image_base64)
    result = analyze_food_image(img_bytes, mime_type=req.mime_type or "image/jpeg", api_key=req.api_key)
    return result


@app.post("/recommend")
def get_recommendation(req: RecommendationRequest):
    commodity = find_commodity(req.commodity_name) if req.commodity_name else None

    inputs = req.dict()
    if commodity and not req.respiration_rate:
        inputs["respiration_rate"] = sum(commodity["typical_respiration_mgCO2_kg_hr"]) / 2

    top_materials, required_barrier = recommend(inputs, top_n=3)

    # shelf life prediction using the #1 recommended material
    shelf_life_estimate = None
    if commodity and top_materials:
        best = top_materials[0]
        avg_wvtr = sum(best["spec"]["wvtr_g_m2_day"]) / 2
        shelf_life_estimate = predict_shelf_life(
            ref_shelf_life_days=commodity["ref_shelf_life_days_at_ref_temp"],
            ref_temp_c=commodity["ref_temp_c"],
            storage_temp_c=req.storage_temp_c,
            material_wvtr_avg=avg_wvtr,
            required_wvtr_max=required_barrier["wvtr_required"][1],
        )

    map_gas = get_map_gas(commodity) if commodity else None

    qr_payload = {
        "commodity": req.commodity_name,
        "top_material": top_materials[0]["material"] if top_materials else None,
        "shelf_life_days": shelf_life_estimate,
    }
    qr_base64 = generate_qr_base64(qr_payload)

    return {
        "required_barrier": {
            "wvtr_g_m2_day": required_barrier["wvtr_required"],
            "otr_cc_m2_day": required_barrier["otr_required"],
        },
        "recommendations": top_materials,
        "shelf_life_prediction_days": shelf_life_estimate,
        "map_gas_composition": map_gas,
        "qr_traceability_png_base64": qr_base64,
    }
