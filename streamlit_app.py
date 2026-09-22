import streamlit as st
import base64
import sys
import os
import io
from PIL import Image

sys.path.append(os.path.dirname(__file__))
from app.rule_engine import recommend, find_commodity, COMMODITIES, MATERIALS
from app.shelf_life import predict_shelf_life
from app.extras import get_map_gas, generate_qr_base64
from app.ai_analyzer import analyze_food_item, analyze_food_image, DEFAULT_GEMINI_API_KEY

st.set_page_config(
    page_title="AI Packaging Recommender & Food Vision Scanner",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1e3a8a, #0284c7, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #475569;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .vision-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 50%, #eff6ff 100%);
        border: 1px solid #86efac;
        border-radius: 14px;
        padding: 20px 24px;
        margin-top: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.08);
    }
    .vision-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        background: linear-gradient(90deg, #059669, #0284c7);
        color: white;
        margin-bottom: 10px;
    }
    .identified-food-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 6px;
    }
    .observation-box {
        background: rgba(255, 255, 255, 0.75);
        border-left: 4px solid #059669;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 10px 0;
        font-size: 0.95rem;
        color: #334155;
    }
    .material-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .material-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .tag {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 6px;
        margin-top: 4px;
    }
    .tag-green {
        background: #dcfce7;
        color: #15803d;
    }
    .tag-blue {
        background: #e0e7ff;
        color: #4338ca;
    }
    .metric-pill {
        display: inline-block;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        padding: 6px 12px;
        border-radius: 8px;
        margin: 4px 6px 4px 0;
        font-size: 0.85rem;
        font-weight: 600;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/package.png", width=64)
    st.title("Settings & AI Config")
    
    st.markdown("### 🔎 Search Engine Settings")
    gemini_key_input = st.text_input(
        "Search Engine Key",
        value=DEFAULT_GEMINI_API_KEY,
        type="password",
        help="Search engine key used to analyze food photos and food properties automatically."
    )
    
    if gemini_key_input:
        st.success("Search Engine Connected (Vision + NLP)", icon="✨")
    else:
        st.warning("No Search Engine key entered. Using built-in Food Science Knowledge Engine.")
        
    st.markdown("---")
    st.markdown("### 💡 Quick Food Presets")
    preset_col1, preset_col2 = st.columns(2)
    quick_presets = [
        "Fresh Strawberries", "Mushrooms", 
        "Raw Paneer", "Potato Chips", 
        "Fresh Bread", "Cooked Biryani",
        "Roasted Almonds", "Raw Salmon"
    ]
    
    selected_preset = None
    for i, p in enumerate(quick_presets):
        col = preset_col1 if i % 2 == 0 else preset_col2
        if col.button(p, use_container_width=True, key=f"btn_preset_{i}"):
            selected_preset = p

    st.markdown("---")
    st.caption("AI Packaging Recommender • Powered by Search Engine Vision")


# ----------------- SESSION STATE INIT -----------------
if "food_name" not in st.session_state:
    st.session_state.food_name = "Fresh Strawberries"
if "moisture" not in st.session_state:
    st.session_state.moisture = 91.0
if "oil" not in st.session_state:
    st.session_state.oil = 0.3
if "ph" not in st.session_state:
    st.session_state.ph = 3.5
if "respiration" not in st.session_state:
    st.session_state.respiration = 35.0
if "storage_temp" not in st.session_state:
    st.session_state.storage_temp = 1.0
if "rh" not in st.session_state:
    st.session_state.rh = 92.0
if "storage_type" not in st.session_state:
    st.session_state.storage_type = "chilled"
if "shelf_life" not in st.session_state:
    st.session_state.shelf_life = 8
if "ai_analysis" not in st.session_state:
    st.session_state.ai_analysis = None
if "scanned_image_bytes" not in st.session_state:
    st.session_state.scanned_image_bytes = None


def apply_analysis_to_state(analysis: dict, img_bytes: bytes = None):
    """Updates session state variables with analysis results."""
    st.session_state.ai_analysis = analysis
    if img_bytes:
        st.session_state.scanned_image_bytes = img_bytes
    if "product_name" in analysis and analysis["product_name"]:
        st.session_state.food_name = analysis["product_name"]
    st.session_state.moisture = float(analysis.get("moisture_content", 60.0))
    st.session_state.oil = float(analysis.get("oil_content", 5.0))
    st.session_state.ph = float(analysis.get("ph", 6.0))
    st.session_state.respiration = float(analysis.get("respiration_rate", 0.0))
    st.session_state.storage_temp = float(analysis.get("storage_temp_c", 4.0))
    st.session_state.rh = float(analysis.get("rh_pct", 85.0))
    st.session_state.storage_type = analysis.get("storage_type", "chilled")
    st.session_state.shelf_life = int(analysis.get("desired_shelf_life_days", 14))


# If a sidebar preset was clicked, update the food_name and trigger calculation
if selected_preset:
    st.session_state.food_name = selected_preset
    st.session_state.scanned_image_bytes = None
    with st.spinner(f"Analyzing {selected_preset} with Search Engine AI..."):
        analysis = analyze_food_item(selected_preset, api_key=gemini_key_input)
        apply_analysis_to_state(analysis)


# ----------------- MAIN HEADER -----------------
st.markdown('<div class="main-header">📦 AI Packaging Recommender & Visual Food Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Take a camera photo or upload from phone gallery — Search Engine Vision automatically detects the food, observes freshness, computes preservation properties, and matches the ideal packaging.</div>', unsafe_allow_html=True)


# ----------------- INPUT MODULE: CAMERA, GALLERY & TEXT -----------------
st.markdown("#### 🔍 1. Capture, Upload or Search Food Product")

tab_cam, tab_gallery, tab_text = st.tabs([
    "📸 Live Camera Photo", 
    "🖼️ Phone Gallery / File Upload", 
    "⌨️ Search / Manual Input"
])

with tab_cam:
    st.caption("Point your phone or laptop camera at any fruit, vegetable, cooked meal, dairy, meat, or snack item:")
    st.info("On Android, camera access requires opening the app over HTTPS. If this network link uses HTTP, use the Phone Gallery tab or deploy Streamlit with SSL enabled.")
    camera_file = st.camera_input("Take a photo of any food item")
    if camera_file is not None:
        img_bytes = camera_file.getvalue()
        cam_col1, cam_col2 = st.columns([1, 2])
        with cam_col1:
            st.image(img_bytes, caption="Captured Food Photo", use_column_width=True)
        with cam_col2:
            st.info("Photo captured successfully! Click below to identify this food with Search Engine Vision.")
            if st.button("✨ Scan & Identify Food with Search Engine Vision", type="primary", key="btn_scan_camera", use_container_width=True):
                with st.spinner("🧠 Search Engine Vision scanning photo: identifying food item, analyzing visual freshness, and calculating properties..."):
                    mime = camera_file.type or "image/jpeg"
                    analysis = analyze_food_image(img_bytes, mime_type=mime, api_key=gemini_key_input)
                    apply_analysis_to_state(analysis, img_bytes)
                    st.rerun()

with tab_gallery:
    st.caption("Select and upload any food photo from your phone photo gallery or computer files:")
    uploaded_file = st.file_uploader("Upload food image from device gallery", type=["jpg", "jpeg", "png", "webp"], key="gallery_uploader")
    if uploaded_file is not None:
        img_bytes = uploaded_file.getvalue()
        up_col1, up_col2 = st.columns([1, 2])
        with up_col1:
            st.image(img_bytes, caption=f"Gallery Image: {uploaded_file.name}", use_column_width=True)
        with up_col2:
            st.info("Image loaded! Ready for AI visual recognition & packaging analysis.")
            if st.button("✨ Scan & Identify Uploaded Image with Search Engine Vision", type="primary", key="btn_scan_gallery", use_container_width=True):
                with st.spinner("🧠 Search Engine Vision scanning uploaded image: identifying food item and computing properties..."):
                    mime = uploaded_file.type or "image/jpeg"
                    analysis = analyze_food_image(img_bytes, mime_type=mime, api_key=gemini_key_input)
                    apply_analysis_to_state(analysis, img_bytes)
                    st.rerun()

with tab_text:
    st.caption("Or type any food name directly to calculate properties via Search Engine AI:")
    c1, c2 = st.columns([3, 1])
    with c1:
        food_input = st.text_input(
            "Food commodity or dish name",
            value=st.session_state.food_name,
            placeholder="e.g. Fresh Strawberries, Paneer, Dark Chocolate Truffles, Cooked Biryani, Raw Salmon...",
            help="Type ANY raw or processed food item. Search Engine AI will calculate its moisture %, oil %, pH, respiration rate, and optimal humidity level automatically."
        )
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        calc_btn = st.button("✨ Auto-Calculate with Search Engine", type="primary", use_container_width=True)

    if calc_btn and food_input.strip():
        st.session_state.scanned_image_bytes = None
        with st.spinner(f"Search Engine AI analyzing contents and humidity for '{food_input}'..."):
            st.session_state.food_name = food_input.strip()
            analysis = analyze_food_item(food_input.strip(), api_key=gemini_key_input)
            apply_analysis_to_state(analysis)
            st.rerun()


# ----------------- DISPLAY AI ANALYSIS CARD -----------------
if st.session_state.ai_analysis:
    ana = st.session_state.ai_analysis
    
    st.markdown('<div class="vision-card">', unsafe_allow_html=True)
    
    # If a camera/gallery photo was analyzed, show photo side-by-side with analysis
    if st.session_state.scanned_image_bytes:
        vcol1, vcol2 = st.columns([1, 2])
        with vcol1:
            st.image(st.session_state.scanned_image_bytes, caption="📸 Analyzed Food Sample", use_column_width=True)
        with vcol2:
            st.markdown(f'<span class="vision-badge">✨ {ana.get("source", "Search Engine Vision")}</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="identified-food-title">🎯 Identified: {ana.get("product_name", st.session_state.food_name)}</div>', unsafe_allow_html=True)
            st.markdown(f'**Category:** `{ana.get("category", "Food Product")}`')
            
            if ana.get("visual_observations"):
                st.markdown(f"""
                <div class="observation-box">
                    👁️ <b>Visual Observations & Freshness:</b><br>{ana.get('visual_observations')}
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"""
            <div>
                <span class="metric-pill">💧 Moisture: {ana.get('moisture_content', st.session_state.moisture)}%</span>
                <span class="metric-pill">🧈 Fat/Oil: {ana.get('oil_content', st.session_state.oil)}%</span>
                <span class="metric-pill">🧪 pH: {ana.get('ph', st.session_state.ph)}</span>
                <span class="metric-pill">🌬️ Respiration: {ana.get('respiration_rate', st.session_state.respiration)} mg CO₂/kg/hr</span>
                <span class="metric-pill">🌡️ Storage: {ana.get('storage_temp_c', st.session_state.storage_temp)}°C ({ana.get('storage_type', 'chilled')})</span>
                <span class="metric-pill">🌫️ Target RH: {ana.get('rh_pct', st.session_state.rh)}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<p style='color: #1e293b; font-size: 0.95rem; margin-top: 10px; line-height: 1.5;'><b>💡 Packaging Rationale:</b> {ana.get('scientific_rationale', '')}</p>", unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="vision-badge">✨ {ana.get("source", "Search Engine")} • {ana.get("category", "Analyzed Food")}</span>', unsafe_allow_html=True)
        st.markdown(f'<div class="identified-food-title">🎯 Food Profile: {ana.get("product_name", st.session_state.food_name)}</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div>
            <span class="metric-pill">💧 Moisture: {ana.get('moisture_content', st.session_state.moisture)}%</span>
            <span class="metric-pill">🧈 Fat/Oil: {ana.get('oil_content', st.session_state.oil)}%</span>
            <span class="metric-pill">🧪 pH: {ana.get('ph', st.session_state.ph)}</span>
            <span class="metric-pill">🌬️ Respiration: {ana.get('respiration_rate', st.session_state.respiration)} mg CO₂/kg/hr</span>
            <span class="metric-pill">🌡️ Storage: {ana.get('storage_temp_c', st.session_state.storage_temp)}°C ({ana.get('storage_type', 'chilled')})</span>
            <span class="metric-pill">🌫️ Target RH: {ana.get('rh_pct', st.session_state.rh)}%</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<p style='color: #1e293b; font-size: 0.95rem; margin-top: 10px; line-height: 1.5;'><b>💡 Packaging Rationale:</b> {ana.get('scientific_rationale', '')}</p>", unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)


# ----------------- PARAMETER SLIDERS & TUNING -----------------
st.markdown("#### ⚙️ 2. Storage & Food Property Parameters")
st.caption("Values are auto-calculated by Search Engine AI. You can fine-tune any parameter below before generating packaging recommendations.")

col_prop1, col_prop2 = st.columns(2)
with col_prop1:
    moisture = st.slider(
        "💧 Moisture content (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.moisture),
        step=0.5,
        help="Affects water vapor transmission requirements (WVTR)."
    )
    oil = st.slider(
        "🧈 Oil / Fat content (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.oil),
        step=0.5,
        help="High oil requires low oxygen transmission (OTR) to prevent oxidative rancidity."
    )
    ph = st.slider(
        "🧪 pH level",
        min_value=1.0,
        max_value=14.0,
        value=float(st.session_state.ph),
        step=0.1
    )
    respiration = st.number_input(
        "🌬️ Respiration rate (mg CO₂/kg/hr, 0 if non-respiring)",
        min_value=0.0,
        max_value=200.0,
        value=float(st.session_state.respiration),
        step=1.0,
        help="Fresh produce breathes and requires permeable or micro-perforated film."
    )

with col_prop2:
    rh = st.slider(
        "🌫️ Optimal Relative Humidity (RH %)",
        min_value=10.0,
        max_value=100.0,
        value=float(st.session_state.rh),
        step=1.0,
        help="Target humidity level calculated by Search Engine AI for quality retention."
    )
    storage_temp = st.slider(
        "🌡️ Storage temperature (°C)",
        min_value=-25.0,
        max_value=45.0,
        value=float(st.session_state.storage_temp),
        step=1.0
    )
    storage_options = ["ambient", "chilled", "frozen"]
    default_idx = storage_options.index(st.session_state.storage_type) if st.session_state.storage_type in storage_options else 0
    storage_type = st.selectbox(
        "❄️ Storage Environment",
        storage_options,
        index=default_idx
    )
    shelf_life = st.number_input(
        "⏳ Desired target shelf life (days)",
        min_value=1,
        max_value=730,
        value=int(st.session_state.shelf_life),
        step=1
    )

st.markdown("<br>", unsafe_allow_html=True)
recommend_btn = st.button("🚀 Recommend Packaging Materials", type="primary", use_container_width=True)


# ----------------- RECOMMENDATION RESULTS -----------------
if recommend_btn or st.session_state.ai_analysis is not None:
    inputs = {
        "moisture_content": moisture,
        "oil_content": oil,
        "ph": ph,
        "respiration_rate": respiration,
        "desired_shelf_life_days": shelf_life,
        "storage_temp_c": storage_temp,
        "rh_pct": rh,
        "storage_type": storage_type,
    }

    top_materials, required_barrier = recommend(inputs, top_n=3)

    st.markdown("---")
    st.markdown("### 📦 Top Recommended Packaging Materials")

    # Display Top 3 Recommended Materials with Images
    for i, m in enumerate(top_materials, 1):
        with st.container():
            st.markdown(f"#### #{i} {m['material']} — Match Score: `{m['score'] * 100:.1f}%`")
            card_col1, card_col2 = st.columns([1, 2])
            
            with card_col1:
                img_path = m.get("image_path", "")
                if img_path and os.path.exists(img_path):
                    st.image(img_path, caption=f"Sample: {m['material']}", use_column_width=True)
                else:
                    st.info("Visual sample loading...")
                    
            with card_col2:
                # Key Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("OTR Range", f"{m['spec']['otr_cc_m2_day']} cc/m²/day")
                m2.metric("WVTR Range", f"{m['spec']['wvtr_g_m2_day']} g/m²/day")
                m3.metric("Cost", f"₹{m['cost_inr_per_sqm']}/m²")
                
                # Tags & Badges
                tag_html = f'<span class="tag tag-blue">{m["type"].replace("_", " ").title()}</span>'
                if m["sustainability_score"] > 0.5:
                    tag_html += '<span class="tag tag-green">🌱 High Sustainability</span>'
                if m.get("spec", {}).get("sealability_score", 0) >= 4:
                    tag_html += '<span class="tag">🔒 Hermetic Seal</span>'
                st.markdown(tag_html, unsafe_allow_html=True)
                
                st.markdown(f"""
                - **Thickness:** {m['spec']['thickness_micron']} µm
                - **Sealability Rating:** {m['spec']['sealability_score']} / 5
                - **Mechanical Strength:** {m['spec']['mechanical_strength_score']} / 5
                - **Typical Commercial Applications:** {", ".join(m.get("typical_uses", []))}
                """)
            st.divider()

    # Derived Barrier Requirements & Shelf Life
    st.markdown("### 🧪 Engineering Barrier Window & Shelf Life")
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.markdown("##### Required Barrier Windows")
        st.info(f"""
        - **Target WVTR Window:** `{required_barrier['wvtr_required'][0]} - {required_barrier['wvtr_required'][1]}` g/m²/day
        - **Target OTR Window:** `{required_barrier['otr_required'][0]} - {required_barrier['otr_required'][1]}` cc/m²/day
        - **Optimal Ambient RH:** `{rh}%`
        """)
        
    with res_col2:
        st.markdown("##### Kinetic Shelf-Life Prediction (Q₁₀ Model)")
        commodity_match = find_commodity(st.session_state.food_name)
        ref_days = commodity_match["ref_shelf_life_days_at_ref_temp"] if commodity_match else shelf_life
        ref_temp = commodity_match["ref_temp_c"] if commodity_match else (4.0 if storage_type == "chilled" else 22.0)
        
        if top_materials:
            best = top_materials[0]
            avg_wvtr = sum(best["spec"]["wvtr_g_m2_day"]) / 2
            sl = predict_shelf_life(
                ref_shelf_life_days=ref_days,
                ref_temp_c=ref_temp,
                storage_temp_c=storage_temp,
                material_wvtr_avg=avg_wvtr,
                required_wvtr_max=required_barrier["wvtr_required"][1],
            )
            st.success(f"Estimated Shelf Life with #{1} **{best['material']}**: **{sl} days** at {storage_temp}°C")
        
        map_gas = get_map_gas(commodity_match) if commodity_match else None
        if map_gas:
            st.markdown("##### 🌬️ Recommended MAP Gas Flush")
            g1, g2, g3 = st.columns(3)
            g1.metric("O₂ Gas", f"{map_gas['o2_pct']}%")
            g2.metric("CO₂ Gas", f"{map_gas['co2_pct']}%")
            g3.metric("N₂ Gas", f"{map_gas['n2_pct']}%")

    # QR Traceability Tag
    st.markdown("### 🔗 Digital QR Traceability Tag")
    qr_payload = {
        "commodity": st.session_state.food_name,
        "moisture_pct": moisture,
        "oil_pct": oil,
        "rh_pct": rh,
        "top_packaging": top_materials[0]["material"] if top_materials else None,
        "shelf_life_days": sl if 'sl' in locals() else shelf_life,
    }
    qr_b64 = generate_qr_base64(qr_payload)
    qr_img_data = base64.b64decode(qr_b64)
    
    qr_col1, qr_col2 = st.columns([1, 3])
    with qr_col1:
        st.image(qr_img_data, width=160, caption="Scan for Pack Spec")
    with qr_col2:
        st.write("This QR code encodes packaging barrier compliance data, commodity profile, and shelf-life tracking parameters for farm-to-shelf traceability.")
        st.download_button(
            label="📥 Download Traceability QR Tag",
            data=qr_img_data,
            file_name=f"{st.session_state.food_name.lower().replace(' ', '_')}_qr_tag.png",
            mime="image/png"
        )


# ----------------- ALL MATERIALS CATALOG GALLERY -----------------
with st.expander(f"🔍 Browse All {len(MATERIALS)} Packaging Materials Catalog & Visuals", expanded=False):
    st.markdown("Explore the complete material library with technical barrier ranges and sample images:")
    gallery_cols = st.columns(4)
    for idx, mat in enumerate(MATERIALS):
        col = gallery_cols[idx % 4]
        with col:
            img_p = mat.get("image_path", "")
            if img_p and os.path.exists(img_p):
                st.image(img_p, caption=mat["name"], use_column_width=True)
            st.markdown(f"**{mat['name']}**")
            st.caption(f"Cost: ₹{mat['cost_inr_per_sqm']}/m² | WVTR: {mat['wvtr_g_m2_day']} | OTR: {mat['otr_cc_m2_day']}")
            st.markdown("---")
