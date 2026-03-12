# 🎓 Attention Monitor — Real-Time Student Engagement Detection

A multimodal AI system that monitors student attention during Google Meet sessions using **computer vision** + **NLP fusion**, deployed as a Chrome Extension.

---

## 📋 Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Model Accuracy](#model-accuracy)

---

## ✨ Features
- 🎥 Real-time face detection from Google Meet video tiles
- 🧠 Vision model: XGBoost + Random Forest (92.18% accuracy)
- 💬 NLP model: DistilBERT fine-tuned on student text (75.39% accuracy)
- 🔀 Confidence-weighted late fusion (88.82% accuracy)
- 📊 Live dashboard with per-student engagement scores
- 🏷️ Overlay badges on each student tile (Attentive / Bored / Confused / Frustrated)
- 📤 Export session data

---

## 🏗️ Architecture

```
Chrome Extension (content.js)
        │
        │  POST /predict (frames + text)
        ▼
Flask Server (app.py)
        │
        ├── feature_extractor.py  →  28 facial features
        │        └── OpenCV Haar Cascade + LBF Landmarks
        │
        ├── Vision Model          →  XGBoost + Random Forest ensemble
        │
        ├── NLP Model             →  DistilBERT fine-tuned
        │
        └── fusion.py             →  Confidence-weighted late fusion
                                        α = 0.8 (NLP) if confidence > 0.6
                                        α = 0.2 (Vision) otherwise
```

---

## 📦 Requirements

### Python (Flask Server)
| Library | Version | Purpose |
|---|---|---|
| flask | 2.3.3 | Web server |
| flask-cors | 4.0.0 | Cross-origin requests from extension |
| opencv-python | 4.8.1.78 | Frame processing & face detection |
| opencv-contrib-python | 4.8.1.78 | LBF facial landmark model |
| Pillow | 10.1.0 | Image decoding from base64 |
| numpy | 1.24.4 | Numerical operations |
| xgboost | 2.0.3 | Vision ensemble classifier |
| scikit-learn | 1.3.2 | Random Forest classifier |
| pandas | 2.0.3 | Feature DataFrame construction |
| torch | 2.1.0 | DistilBERT inference |
| transformers | 4.35.2 | DistilBERT model & tokenizer |
| tokenizers | 0.15.0 | Fast tokenization |
| scipy | 1.11.4 | Statistical utilities |

### Chrome Extension
No npm install needed — pure vanilla JavaScript.

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/attention-monitor.git
cd attention-monitor
```

### 2. Install Python dependencies
```bash
cd flask_server
pip install -r requirements.txt
```

### 3. Add model files
Download models from Google Drive and place them in `flask_server/models/`:
```
flask_server/
└── models/
    ├── xgboost_BEST_final.json        ← XGBoost (use .json not .pkl)
    ├── rf_BEST_final.pkl
    ├── label_encoder_BEST_final.pkl
    ├── feature_cols_BEST.json
    ├── le_nlp_final.pkl
    ├── lbfmodel.yaml
    └── distilbert_nlp_final/
        ├── config.json
        ├── pytorch_model.bin
        └── tokenizer files...
```

> ⚠️ Model files are not included in the repo due to size. Download from the shared Google Drive link.

### 4. Start the Flask server
```bash
cd flask_server
python app.py
```
Server runs at `http://localhost:5000`

### 5. Load the Chrome Extension
1. Open Chrome → go to `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select the `chrome_extension/` folder
5. The extension icon will appear in your toolbar

### 6. Use in Google Meet
1. Join a Google Meet call
2. The extension auto-starts monitoring
3. Open the extension popup to see the dashboard

---

## 🚀 Usage

| Action | How |
|---|---|
| View scores | Click the extension icon |
| Pause monitoring | Click **Pause** in dashboard |
| Export session | Click **Export** in dashboard |
| Student text input | Use the floating input box (bottom right of Meet) |

---

## 📁 Project Structure

```
attention-monitor/
│
├── flask_server/
│   ├── app.py                  # Main Flask server & API routes
│   ├── feature_extractor.py    # 28-feature facial landmark pipeline
│   ├── fusion.py               # Confidence-weighted late fusion
│   ├── requirements.txt        # Python dependencies
│   └── models/                 # (not in repo — download separately)
│
├── chrome_extension/
│   ├── manifest.json           # Extension manifest (MV3)
│   ├── content.js              # Injected into Google Meet
│   ├── popup.html              # Dashboard UI
│   ├── popup.js                # Dashboard logic
│   └── icons/                  # Extension icons
│
└── README.md
```

---

## 📊 Model Accuracy

| Component | Accuracy | Details |
|---|---|---|
| Vision (XGBoost+RF) | **92.18%** | 28 features, DAiSEE dataset |
| NLP (DistilBERT) | **75.39%** | 71,582 samples |
| Fusion V9 (final) | **88.82%** | Confidence-weighted late fusion |

---

## 🔒 Privacy Note
All processing is done **locally on your machine**. No video or audio data is sent to any external server. The Flask server runs on `localhost:5000` only.

---



"# Attention-Monitor" 
