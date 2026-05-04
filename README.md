# Attention Monitor

Attention Monitor is a Chrome extension plus local Flask service for real-time student engagement tracking in Google Meet. It combines computer vision, NLP, and a confidence-weighted fusion layer to generate per-student attention labels and scores.

## Features

- Real-time analysis of Google Meet video tiles
- Vision pipeline with XGBoost and Random Forest models
- DistilBERT-based NLP fallback for student text input
- Late fusion for a final engagement label and score
- Live dashboard inside the extension popup
- Overlay badges on Meet tiles
- Session export from the dashboard

## How it works

```
chrome_extension/content.js
        |
        |  POST /predict and /predict_text
        v
flask_server/app.py
        |
        +-- feature_extractor.py  -> facial feature extraction
        +-- vision_model.py       -> vision inference helpers
        +-- fusion.py             -> final label fusion
        +-- distilbert_nlp_final/  -> local NLP model
```

The extension uses a Manifest V3 service worker in `chrome_extension/background.js` to inject content scripts and relay popup messages to the active Meet tab.

## Requirements

Python dependencies are listed in the top-level `requirements.txt` and include:

- Flask and flask-cors
- OpenCV and OpenCV contrib
- NumPy, pandas, Pillow, SciPy
- xgboost and scikit-learn
- torch, transformers, and tokenizers

No npm install is required for the extension; it is plain JavaScript and HTML.

## Installation

1. Clone the repository and open it in VS Code.
2. Install the Python dependencies:

```bash
pip install -r requirements.txt
```

3. Make sure the model files exist under `flask_server/models/`.

The repo currently includes these model artifacts:

```text
flask_server/models/
├── distilbert_nlp_final/
├── feature_cols_BEST.json
├── label_encoder_BEST_final.pkl
├── lbfmodel.yaml
├── le_nlp_final.pkl
├── rf_BEST_final.pkl
├── xgboost_BEST_final.json
└── xgboost_BEST_final.pkl
```

On Windows, `flask_server/app.py` will automatically re-launch under `venv/Scripts/python.exe` when that bundled environment exists.

## Running the server

From the repository root:

```bash
python flask_server/app.py
```

The server listens on `http://localhost:5000`.

## Load the extension

1. Open Chrome and go to `chrome://extensions`.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select the `chrome_extension/` folder.

The extension assets in that folder are:

- `manifest.json`
- `background.js`
- `content.js`
- `dashboard.html`
- `dashboard.js`
- `icon16.png`
- `icon48.png`
- `icon128.png`

## Usage

1. Join a Google Meet call.
2. Wait for the content script to start monitoring tiles.
3. Open the extension popup to view the dashboard.
4. Use Pause/Resume, Export, and the text input overlay as needed.

## Project structure

```text
attention-monitor/
├── chrome_extension/
│   ├── background.js
│   ├── content.js
│   ├── dashboard.html
│   ├── dashboard.js
│   ├── icon16.png
│   ├── icon48.png
│   ├── icon128.png
│   ├── make_icons.py
│   └── manifest.json
├── flask_server/
│   ├── app.py
│   ├── feature_extractor.py
│   ├── fusion.py
│   ├── vision_model.py
│   └── models/
├── Model Training/
│   ├── AI_Attention_Monitor.ipynb
│   ├── Fusion_Layer!.ipynb
│   └── NLP_Attention_Model.ipynb
├── requirements.txt
└── README.md
```

## Notes

- All processing is local to your machine.
- The Flask server only needs to be reachable on `localhost:5000`.
- If you are on Windows, prefer the repository venv for running the Flask app when available.
