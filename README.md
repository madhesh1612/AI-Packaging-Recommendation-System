# 📦 AI Packaging Recommendation System

An intelligent, AI-powered food packaging recommendation platform that provides tailored packaging material suggestions, shelf-life estimations, Modified Atmosphere Packaging (MAP) gas flush ratios, sustainability ratings, and dynamic QR labels.

---

## ✨ Features

- **🤖 AI Product & Image Analysis**: Identify food properties, shelf stability, and packaging requirements via AI analysis (powered by Google Gemini).
- **📊 Smart Rule Engine**: Recommends optimal packaging materials (PET, HDPE, LDPE, BOPP, Aluminum Foil, Biodegradable Films, etc.) based on moisture, oxygen, light barrier, and temperature requirements.
- **⏳ Shelf Life Prediction**: Dynamic calculation of predicted shelf-life across ambient, refrigerated, and frozen storage conditions.
- **💨 MAP Gas Mixture Suggestions**: Gas composition guidelines ($O_2$, $CO_2$, $N_2$) for extending perishable freshness.
- **🌱 Sustainability & Cost Comparison**: Compares carbon footprint, recyclability, and cost metrics across suggested materials.
- **📱 Smart QR Code Generator**: Generates verifiable packaging QR codes containing food metadata and packaging specs.
- **🖥️ Dual Interface**: Includes both a **FastAPI backend** and a modern **Streamlit web dashboard**.

---

## 🏗️ Project Architecture

```
packaging-recommender/
│
├── app/
│   ├── ai_analyzer.py      # AI analysis for food text & image inputs
│   ├── extras.py           # MAP gas composition & QR code generation
│   ├── main.py             # FastAPI REST endpoints
│   ├── rule_engine.py      # Multi-criteria packaging recommendation logic
│   └── shelf_life.py       # Shelf life estimation model
│
├── assets/
│   └── materials/          # Packaging material imagery
│
├── data/
│   ├── commodities.json    # Food commodity profiles & storage properties
│   └── materials.json      # Packaging material specs (barrier, cost, eco-score)
│
├── streamlit_app.py        # Interactive Streamlit Frontend
├── requirements.txt        # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+ installed
- Git installed

### 2. Clone the Repository
```bash
git clone https://github.com/madhesh1612/AI-Packaging-Recommendation-System.git
cd AI-Packaging-Recommendation-System
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Running the Application

#### Option A: Streamlit UI
```bash
streamlit run streamlit_app.py
```
Open your browser and navigate to `http://localhost:8501`.

#### Option B: FastAPI Backend
```bash
uvicorn app.main:app --reload --port 8000
```
Access interactive API docs at `http://localhost:8000/docs`.

---

## ⚙️ Environment Variables / API Key (Optional)

To enable Gemini AI Vision and text analysis features, you can provide your Google Gemini API Key:
- In the Streamlit sidebar settings, or
- As an environment variable:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

---

## 📜 License
This project is open-source and available under the [MIT License](LICENSE).
