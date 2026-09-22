"""
AI Food Science Analyzer (Powered by Google Gemini):
Automatically calculates food moisture %, oil/fat %, pH, respiration rate,
recommended storage temperature, relative humidity (RH %), storage category,
and shelf-life using Google Gemini 2.5 Flash, with an intelligent built-in
Food Science Knowledge Engine fallback for offline reliability.
"""

import os
import json
import re
import requests
from io import BytesIO
from PIL import Image

# Default Gemini API key (read from environment variable)
DEFAULT_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Comprehensive Food Science Reference Database for Fallback / Offline Estimation
FOOD_SCIENCE_DB = [
    {
        "keywords": ["strawberry", "strawberries", "berry", "berries", "raspberry", "blueberry", "blackberry"],
        "category": "Fresh Soft Fruit / Perishable Berries",
        "moisture_content": 91.0,
        "oil_content": 0.3,
        "ph": 3.5,
        "respiration_rate": 35.0,
        "storage_temp_c": 1.0,
        "rh_pct": 92.0,
        "storage_type": "chilled",
        "desired_shelf_life_days": 8,
        "scientific_rationale": "Berries have very high moisture (>90%) and rapid respiration with fragile cellular structure. They require near-freezing chill (0-2°C) and high relative humidity (90-95%) with breathable or anti-fog micro-perforated film to stop desiccation while venting excess moisture to prevent fungal Botrytis mold."
    },
    {
        "keywords": ["mushroom", "mushrooms", "button mushroom", "shiitake", "oyster mushroom"],
        "category": "Fresh Fungi / High Respiration Produce",
        "moisture_content": 92.0,
        "oil_content": 0.3,
        "ph": 6.5,
        "respiration_rate": 80.0,
        "storage_temp_c": 4.0,
        "rh_pct": 95.0,
        "storage_type": "chilled",
        "desired_shelf_life_days": 6,
        "scientific_rationale": "Mushrooms exhibit exceptionally high respiration (80+ mg CO2/kg/hr) and lack a protective cuticle skin. They need breathable micro-perforated film or high OTR permeable membranes to prevent anaerobic conditions that induce cap browning and toxic spoilage, along with 90-95% RH to avoid weight loss."
    },
    {
        "keywords": ["spinach", "lettuce", "kale", "herb", "herbs", "coriander", "mint", "greens", "cabbage", "salad"],
        "category": "Fresh Leafy Vegetables",
        "moisture_content": 94.0,
        "oil_content": 0.3,
        "ph": 6.2,
        "respiration_rate": 55.0,
        "storage_temp_c": 2.0,
        "rh_pct": 95.0,
        "storage_type": "chilled",
        "desired_shelf_life_days": 10,
        "scientific_rationale": "Leafy greens possess a high surface-area-to-volume ratio, making them acutely vulnerable to wilting and transpiration. They require near-saturation humidity (95% RH), 1-4°C chill, and tailored OTR film to prevent anaerobic fermentation while curbing ethylene sensitivity."
    },
    {
        "keywords": ["banana", "mango", "papaya", "avocado", "climacteric", "apple", "guava"],
        "category": "Climacteric Fresh Fruits",
        "moisture_content": 78.0,
        "oil_content": 1.2,
        "ph": 4.8,
        "respiration_rate": 25.0,
        "storage_temp_c": 13.0,
        "rh_pct": 88.0,
        "storage_type": "ambient",
        "desired_shelf_life_days": 14,
        "scientific_rationale": "Climacteric fruits undergo ethylene-mediated post-harvest ripening bursts. Storing them below 12°C causes chill injury (flesh darkening). They thrive at controlled ambient (12-15°C) with moderate gas-permeable films to modulate O2 and CO2 levels."
    },
    {
        "keywords": ["paneer", "cottage cheese", "cheese", "dairy", "tofu"],
        "category": "Fresh Dairy & Protein Curd",
        "moisture_content": 54.0,
        "oil_content": 22.0,
        "ph": 5.9,
        "respiration_rate": 0.0,
        "storage_temp_c": 4.0,
        "rh_pct": 85.0,
        "storage_type": "chilled",
        "desired_shelf_life_days": 15,
        "scientific_rationale": "Fresh paneer and cheeses are non-respiring, high-moisture, high-fat products susceptible to mold growth, whey separation (syneresis), and lipid oxidation. They require chilled storage (2-4°C) with vacuum or high-barrier nitrogen MAP packaging and near-zero WVTR."
    },
    {
        "keywords": ["meat", "chicken", "poultry", "beef", "pork", "mutton", "fish", "salmon", "prawn", "seafood"],
        "category": "Fresh Raw Meat & Poultry / Seafood",
        "moisture_content": 72.0,
        "oil_content": 14.0,
        "ph": 5.8,
        "respiration_rate": 0.0,
        "storage_temp_c": 1.0,
        "rh_pct": 85.0,
        "storage_type": "chilled",
        "desired_shelf_life_days": 7,
        "scientific_rationale": "Raw muscle foods are highly perishable due to microbial proliferation and myoglobin oxidation. Strict chill (0-2°C) combined with high-barrier vacuum skin or MAP packaging (high CO2 for microbial inhibition, high O2 for red meat bloom) is essential."
    },
    {
        "keywords": ["chip", "chips", "crisp", "crisps", "namkeen", "fry", "fried", "snack", "snacks", "popcorn", "kurkure"],
        "category": "Fried / Oily Savory Snacks",
        "moisture_content": 2.5,
        "oil_content": 32.0,
        "ph": 6.0,
        "respiration_rate": 0.0,
        "storage_temp_c": 25.0,
        "rh_pct": 45.0,
        "storage_type": "ambient",
        "desired_shelf_life_days": 120,
        "scientific_rationale": "Fried snacks feature low water activity (<0.3 aw) and elevated fat content (>30%). Contact with atmospheric oxygen triggers rancidity (lipid peroxidation), and ambient moisture causes loss of crispness. High-barrier metalized films (MET-PET/BOPP) flushed with 100% Nitrogen gas are strictly required."
    },
    {
        "keywords": ["bread", "cake", "pastry", "bakery", "muffin", "bun", "croissant"],
        "category": "Bakery Products",
        "moisture_content": 38.0,
        "oil_content": 8.0,
        "ph": 5.5,
        "respiration_rate": 0.0,
        "storage_temp_c": 22.0,
        "rh_pct": 60.0,
        "storage_type": "ambient",
        "desired_shelf_life_days": 7,
        "scientific_rationale": "Bakery goods suffer from starch retrogradation (staling) and mold growth. Refrigeration accelerates staling; thus ambient storage with moderate moisture retention barrier (BOPP/PET) or anti-mold CO2 flushed packaging is recommended."
    },
    {
        "keywords": ["biscuit", "cookie", "cookies", "crackers", "wafers"],
        "category": "Dry Baked Confectionery",
        "moisture_content": 3.0,
        "oil_content": 18.0,
        "ph": 6.8,
        "respiration_rate": 0.0,
        "storage_temp_c": 24.0,
        "rh_pct": 50.0,
        "storage_type": "ambient",
        "desired_shelf_life_days": 180,
        "scientific_rationale": "Dry cookies must be kept crisp and protected against moisture ingress and light-induced fat oxidation. BOPP and metalized barrier pouches provide the critical moisture and oxygen barrier needed for multi-month shelf life."
    },
    {
        "keywords": ["nut", "nuts", "almond", "cashew", "walnut", "peanut", "pistachio"],
        "category": "Oilseeds & Tree Nuts",
        "moisture_content": 4.5,
        "oil_content": 52.0,
        "ph": 6.4,
        "respiration_rate": 0.0,
        "storage_temp_c": 20.0,
        "rh_pct": 55.0,
        "storage_type": "ambient",
        "desired_shelf_life_days": 180,
        "scientific_rationale": "Tree nuts contain up to 50-60% polyunsaturated fats. Light, heat, and oxygen rapidly induce rancid hexanal off-odors. Ultra-low OTR metalized pouches or vacuum packaging with desiccant maintain freshness."
    },
    {
        "keywords": ["spice", "spices", "powder", "curry powder", "chili powder", "tea", "coffee"],
        "category": "Spices, Aromatics & Beverages",
        "moisture_content": 8.0,
        "oil_content": 10.0,
        "ph": 5.2,
        "respiration_rate": 0.0,
        "storage_temp_c": 22.0,
        "rh_pct": 50.0,
        "storage_type": "ambient",
        "desired_shelf_life_days": 365,
        "scientific_rationale": "Spices and coffee contain volatile essential oils and aroma compounds that escape standard plastics. Aluminum foil laminates or MET-PET laminates with zero aroma permeability are required to retain pungent flavors."
    },
    {
        "keywords": ["cooked", "curry", "biryani", "rice", "meal", "ready to eat", "dal", "gravy"],
        "category": "Cooked Ready-to-Eat (RTE) Meals",
        "moisture_content": 68.0,
        "oil_content": 12.0,
        "ph": 5.5,
        "respiration_rate": 0.0,
        "storage_temp_c": 3.0,
        "rh_pct": 80.0,
        "storage_type": "chilled",
        "desired_shelf_life_days": 5,
        "scientific_rationale": "Cooked food contains readily available water and nutrients prone to spoilage microflora. Immediate chilling (<4°C) with hermetic seal barrier trays/pouches or retort pouches is critical."
    },
    {
        "keywords": ["frozen", "ice cream", "frozen vegetables", "frozen fries"],
        "category": "Frozen Foods",
        "moisture_content": 65.0,
        "oil_content": 6.0,
        "ph": 6.2,
        "respiration_rate": 0.0,
        "storage_temp_c": -18.0,
        "rh_pct": 85.0,
        "storage_type": "frozen",
        "desired_shelf_life_days": 270,
        "scientific_rationale": "Sub-zero temperatures stop microbial growth, but water sublimation causes freezer burn. Tough low-temperature impact films like LDPE with low WVTR are essential."
    }
]


def estimate_food_properties_offline(product_name: str) -> dict:
    """
    Intelligent heuristic & food science model fallback that derives
    moisture %, oil %, pH, respiration rate, storage temp, and humidity
    for any food product query when offline.
    """
    cleaned = product_name.lower().strip()
    words = set(re.findall(r"\w+", cleaned))

    best_match = None
    max_overlap = 0

    for item in FOOD_SCIENCE_DB:
        overlap = sum(1 for kw in item["keywords"] if kw in cleaned or kw in words)
        if overlap > max_overlap:
            max_overlap = overlap
            best_match = item

    if best_match and max_overlap > 0:
        res = dict(best_match)
        res.pop("keywords", None)
        res["product_name"] = product_name
        res["source"] = "Food Science Knowledge Engine (Offline Fallback)"
        res["status"] = "calculated"
        return res

    if any(k in cleaned for k in ["juice", "water", "soup", "drink", "beverage"]):
        moisture, oil, ph, resp, temp, rh, st_type, days = 92.0, 0.0, 3.8, 0.0, 4.0, 75.0, "chilled", 30
        cat = "Beverage / Liquid Food"
    elif any(k in cleaned for k in ["dry", "flour", "grain", "seed", "lentil", "pasta"]):
        moisture, oil, ph, resp, temp, rh, st_type, days = 10.0, 2.0, 6.2, 0.0, 24.0, 50.0, "ambient", 180
        cat = "Dry Cereals & Grains"
    elif any(k in cleaned for k in ["vegetable", "veggie", "root", "carrot", "potato"]):
        moisture, oil, ph, resp, temp, rh, st_type, days = 85.0, 0.2, 6.0, 20.0, 7.0, 90.0, "chilled", 21
        cat = "Fresh Vegetables"
    elif any(k in cleaned for k in ["sweet", "chocolate", "candy", "sugar"]):
        moisture, oil, ph, resp, temp, rh, st_type, days = 5.0, 25.0, 6.0, 0.0, 18.0, 50.0, "ambient", 180
        cat = "Confectionery / Sweets"
    else:
        moisture, oil, ph, resp, temp, rh, st_type, days = 60.0, 5.0, 6.0, 0.0, 4.0, 80.0, "chilled", 14
        cat = "General Food Product"

    return {
        "product_name": product_name,
        "category": cat,
        "moisture_content": moisture,
        "oil_content": oil,
        "ph": ph,
        "respiration_rate": resp,
        "storage_temp_c": temp,
        "rh_pct": rh,
        "storage_type": st_type,
        "desired_shelf_life_days": days,
        "scientific_rationale": f"Food science properties derived for {product_name} based on its estimated water activity, fat fraction, and perishability profile.",
        "source": "Food Science Knowledge Engine (Offline Fallback)",
        "status": "calculated"
    }


def _clean_and_parse_json(raw_text: str) -> dict:
    """Safely extracts and parses JSON from Gemini responses even with Markdown fences."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def normalize_image_for_vision(image_bytes: bytes) -> tuple[bytes, str]:
    """Convert browser camera uploads to a broadly supported JPEG payload."""
    with Image.open(BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=92, optimize=True)
    return output.getvalue(), "image/jpeg"


def analyze_food_item(product_name: str, api_key: str = None) -> dict:
    """
    Main entry point: Calls Google Gemini 2.5 Flash API with user's Gemini API key.
    Calculates moisture %, oil %, pH, respiration rate, storage temp, optimal RH%,
    and scientific packaging rationale. Falls back to offline Food Science Engine if needed.
    """
    key = api_key.strip() if api_key and api_key.strip() else DEFAULT_GEMINI_API_KEY

    prompt = f"""
You are an expert food scientist and food packaging engineer.
Analyze the following food commodity / product: "{product_name}"
Return a strictly valid JSON object with the following numerical parameters and scientific packaging guidance:
{{
    "product_name": "{product_name}",
    "category": "Appropriate category name (e.g. Fresh Soft Fruit, High-Fat Savory Snack, Raw Poultry, Fresh Cheese)",
    "moisture_content": <float between 0 and 100, typical moisture percentage>,
    "oil_content": <float between 0 and 100, typical oil/fat percentage>,
    "ph": <float between 1.0 and 14.0, typical pH>,
    "respiration_rate": <float >= 0, mg CO2/kg/hr. Use 0 for non-respiring, cooked, processed or dairy/meat items>,
    "storage_temp_c": <float, recommended commercial storage temperature in Celsius, e.g. 1-4 for chilled, 20-25 for ambient, -18 for frozen>,
    "rh_pct": <float between 30 and 100, recommended relative humidity % for optimal quality retention>,
    "storage_type": "<one of 'ambient', 'chilled', or 'frozen'>",
    "desired_shelf_life_days": <integer >= 1, typical target commercial shelf life in days>,
    "scientific_rationale": "<2-3 sentence scientific explanation detailing water activity, oxidation sensitivity, respiration requirements, and recommended packaging barrier properties>"
}}
"""

    if key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _clean_and_parse_json(raw_text)
                
                # Normalize storage_type to ambient | chilled | frozen
                st_type = str(parsed.get("storage_type", "chilled")).lower()
                if "refrig" in st_type or "chill" in st_type or "cool" in st_type:
                    parsed["storage_type"] = "chilled"
                elif "froz" in st_type:
                    parsed["storage_type"] = "frozen"
                else:
                    parsed["storage_type"] = "ambient"

                parsed["source"] = "Search Engine AI"
                parsed["status"] = "calculated"
                parsed["api_status"] = "online"
                return parsed
            else:
                err_data = {}
                try:
                    err_data = resp.json()
                except Exception:
                    pass
                err_msg = err_data.get("error", {}).get("message", resp.text)
                fallback = estimate_food_properties_offline(product_name)
                fallback["api_status"] = "error"
                fallback["api_message"] = err_msg
                return fallback

        except Exception as e:
            fallback = estimate_food_properties_offline(product_name)
            fallback["api_status"] = "network_error"
            fallback["api_message"] = str(e)
            return fallback

    # No key provided
    fallback = estimate_food_properties_offline(product_name)
    fallback["api_status"] = "no_key"
    return fallback


def analyze_food_image(image_bytes: bytes, mime_type: str = "image/jpeg", api_key: str = None) -> dict:
    """
    Multimodal Vision Analysis using Google Gemini 2.5 Flash:
    Captures or receives a food photo (from camera or gallery), visually identifies the specific food/dish,
    assesses its physical freshness, texture, and visual condition, and calculates:
    moisture %, oil %, pH, respiration rate, storage temp, optimal RH%, storage type,
    shelf life, and scientific packaging requirements.
    """
    import base64
    try:
        image_bytes, mime_type = normalize_image_for_vision(image_bytes)
    except (OSError, ValueError):
        pass
    key = api_key.strip() if api_key and api_key.strip() else DEFAULT_GEMINI_API_KEY
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
You are an expert food scientist and computer vision food analyst.
Carefully examine this photograph of food:
1. Identify specifically what food commodity, dish, ingredient, or snack is shown in the image (e.g. Fresh Red Strawberries, Sliced Cheddar Cheese, Raw Atlantic Salmon, Crispy Fried Potato Chips, Sliced White Bread, Cooked Chicken Biryani, Roasted Salted Cashews, Fresh Button Mushrooms, etc.).
2. Observe its visual appearance (freshness, surface moisture, cut vs whole, raw vs cooked, color, crispness, physical state).
3. Compute its scientific food preservation parameters:
   - product_name: Specific name of the identified food
   - category: Category name (e.g. Fresh Soft Fruit, High-Fat Savory Snack, Raw Poultry/Seafood, Fresh Dairy, Bakery)
   - visual_observations: Brief 1-2 sentence visual assessment of what you see (color, condition, freshness, cut/raw/cooked state)
   - moisture_content: float (% between 0 and 100)
   - oil_content: float (% between 0 and 100)
   - ph: float (between 1.0 and 14.0)
   - respiration_rate: float (mg CO2/kg/hr, 0 for non-respiring, cooked, processed, or meat/dairy items)
   - storage_temp_c: float (recommended commercial storage temperature in Celsius)
   - rh_pct: float (optimal relative humidity % to maintain freshness and prevent spoilage)
   - storage_type: "ambient", "chilled", or "frozen"
   - desired_shelf_life_days: int (target commercial shelf life in days)
   - scientific_rationale: 2-3 sentences explaining the required packaging barrier protection (WVTR, OTR, light, modified atmosphere)

Return strictly valid JSON with this schema:
{
    "product_name": "<identified food name>",
    "category": "<category name>",
    "visual_observations": "<visual freshness & condition assessment>",
    "moisture_content": <float>,
    "oil_content": <float>,
    "ph": <float>,
    "respiration_rate": <float>,
    "storage_temp_c": <float>,
    "rh_pct": <float>,
    "storage_type": "<'ambient'|'chilled'|'frozen'>",
    "desired_shelf_life_days": <int>,
    "scientific_rationale": "<scientific packaging barrier rationale>"
}
"""

    if key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": mime_type if "/" in mime_type else "image/jpeg",
                                    "data": b64_image
                                }
                            },
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _clean_and_parse_json(raw_text)

                st_type = str(parsed.get("storage_type", "chilled")).lower()
                if "refrig" in st_type or "chill" in st_type or "cool" in st_type:
                    parsed["storage_type"] = "chilled"
                elif "froz" in st_type:
                    parsed["storage_type"] = "frozen"
                else:
                    parsed["storage_type"] = "ambient"

                parsed["source"] = "Search Engine Vision"
                parsed["status"] = "calculated"
                parsed["api_status"] = "online"
                return parsed
            else:
                err_msg = resp.text
                return {
                    "product_name": "Unidentified Food Sample",
                    "category": "General Food Product",
                    "visual_observations": "Unable to complete visual identification due to API response error.",
                    "moisture_content": 65.0,
                    "oil_content": 5.0,
                    "ph": 6.0,
                    "respiration_rate": 0.0,
                    "storage_temp_c": 4.0,
                    "rh_pct": 85.0,
                    "storage_type": "chilled",
                    "desired_shelf_life_days": 7,
                    "scientific_rationale": "Standard food preservation barrier profile applied.",
                    "source": "Offline Fallback Estimator",
                    "status": "fallback",
                    "api_status": "error",
                    "api_message": err_msg
                }
        except Exception as e:
            return {
                "product_name": "Unidentified Food Sample",
                "category": "General Food Product",
                "visual_observations": f"Network error during image processing: {str(e)}",
                "moisture_content": 65.0,
                "oil_content": 5.0,
                "ph": 6.0,
                "respiration_rate": 0.0,
                "storage_temp_c": 4.0,
                "rh_pct": 85.0,
                "storage_type": "chilled",
                "desired_shelf_life_days": 7,
                "scientific_rationale": "Standard food preservation barrier profile applied.",
                "source": "Offline Fallback Estimator",
                "status": "fallback",
                "api_status": "network_error",
                "api_message": str(e)
            }

    fallback = estimate_food_properties_offline("food sample")
    fallback["visual_observations"] = "Visual scan unavailable (offline mode). Default food profile loaded."
    return fallback

