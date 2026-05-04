# app.py — Main Flask Server  (fixed)
import os, sys, warnings, subprocess


def _ensure_project_venv():
    """Re-launch under the repo's bundled venv when available."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_python = os.path.join(repo_root, 'venv', 'Scripts', 'python.exe')

    if not os.path.exists(venv_python):
        return

    current_python = os.path.normcase(os.path.abspath(sys.executable))
    target_python = os.path.normcase(os.path.abspath(venv_python))
    if current_python == target_python:
        return

    script_path = os.path.abspath(__file__)
    print(f"⚠️  Re-launching with project venv: {venv_python}")
    subprocess.Popen([venv_python, script_path] + sys.argv[1:], cwd=repo_root)
    raise SystemExit(0)


_ensure_project_venv()

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2, numpy as np, pickle, json, base64, torch, io
import os, sys, warnings
from importlib.metadata import version as pkg_version, PackageNotFoundError
import pandas as pd
from PIL import Image
from transformers import AutoTokenizer, DistilBertForSequenceClassification
from feature_extractor import extract_features
from fusion import fuse

app = Flask(__name__)
CORS(app)

# ── version helper ──────────────────────────────────────────
def _safe_pkg_version(name):
    try:    return pkg_version(name)
    except: return 'unknown'

# ── startup banner ──────────────────────────────────────────
print("Loading models...")
print(f"Python      : {sys.version.split()[0]}")
print(f"xgboost     : {_safe_pkg_version('xgboost')}")
print(f"scikit-learn: {_safe_pkg_version('scikit-learn')}")
print(f"torch       : {_safe_pkg_version('torch')}")

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

# ══════════════════════════════════════════════════════════════
#  XGBoost loader  — tries 4 strategies in order
# ══════════════════════════════════════════════════════════════
def _load_xgboost():
    pkl_path  = os.path.join(MODELS_DIR, 'xgboost_BEST_final.pkl')
    json_path = os.path.join(MODELS_DIR, 'xgboost_BEST_final.json')
    ubj_path  = os.path.join(MODELS_DIR, 'xgboost_BEST_final.ubj')

    import xgboost as xgb_lib

    # Strategy 1: JSON  (version-independent — best)
    if os.path.exists(json_path):
        try:
            clf = xgb_lib.XGBClassifier()
            clf.load_model(json_path)
            print(f"✅ XGBoost loaded via JSON: {json_path}")
            return clf
        except Exception as e:
            print(f"   JSON load failed: {e}")

    # Strategy 2: UBJ binary
    if os.path.exists(ubj_path):
        try:
            clf = xgb_lib.XGBClassifier()
            clf.load_model(ubj_path)
            print(f"✅ XGBoost loaded via UBJ: {ubj_path}")
            return clf
        except Exception as e:
            print(f"   UBJ load failed: {e}")

    # Strategy 3: plain pickle
    if os.path.exists(pkl_path):
        try:
            with open(pkl_path, 'rb') as f:
                model = pickle.load(f)
            print(f"✅ XGBoost loaded via pickle: {pkl_path}")
            return model
        except Exception as e:
            print(f"   pickle load failed: {e}")

        # Strategy 4: native Booster (pkl treated as booster binary)
        try:
            booster = xgb_lib.Booster()
            booster.load_model(pkl_path)
            print(f"✅ XGBoost loaded via Booster.load_model: {pkl_path}")
            return _BoosterWrapper(booster)
        except Exception as e:
            print(f"   Booster load failed: {e}")

    print("❌ XGBoost could not be loaded by any strategy.")
    return None


# ── Wrapper so a raw Booster behaves like XGBClassifier ──────
class _BoosterWrapper:
    def __init__(self, booster):
        self._b = booster

    def predict_proba(self, X):
        import xgboost as xgb_lib
        dm   = xgb_lib.DMatrix(X)
        pred = self._b.predict(dm)
        pred = np.asarray(pred)
        if pred.ndim == 1:
            pred = np.column_stack([1.0 - pred, pred])
        return pred


# ── Random Forest loader ──────────────────────────────────────
def _load_rf():
    path = os.path.join(MODELS_DIR, 'rf_BEST_final.pkl')
    if not os.path.exists(path):
        print("❌ RF model file not found.")
        return None
    try:
        with open(path, 'rb') as f:
            model = pickle.load(f)
        print(f"✅ RandomForest loaded: {path}")
        return model
    except Exception as e:
        print(f"   RF pickle failed: {e}")
    try:
        import joblib
        model = joblib.load(path)
        print(f"✅ RandomForest loaded via joblib: {path}")
        return model
    except Exception as e:
        print(f"❌ RF joblib failed: {e}")
    return None


# ══════════════════════════════════════════════════════════════
#  Load all models
# ══════════════════════════════════════════════════════════════
xgb = _load_xgboost()
rf  = _load_rf()

VISION_OK = (xgb is not None) or (rf is not None)
if not VISION_OK:
    warnings.warn("⚠️  No vision model loaded — NLP-only mode.")

# label encoder, feature columns, NLP label encoder
with open(os.path.join(MODELS_DIR, 'label_encoder_BEST_final.pkl'), 'rb') as f:
    le_v = pickle.load(f)
with open(os.path.join(MODELS_DIR, 'feature_cols_BEST.json'), 'r') as f:
    feat_cols = json.load(f)
with open(os.path.join(MODELS_DIR, 'le_nlp_final.pkl'), 'rb') as f:
    le_n = pickle.load(f)

N_VISION_CLASSES = len(le_v.classes_)

# NLP model
device  = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
NLP_DIR = os.path.join(MODELS_DIR, 'distilbert_nlp_final')
try:
    tokenizer = AutoTokenizer.from_pretrained(NLP_DIR, local_files_only=True)
    nlp_model = DistilBertForSequenceClassification.from_pretrained(
                    NLP_DIR, local_files_only=True)
except Exception as e:
    raise RuntimeError(f"Failed to load NLP model from {NLP_DIR}: {e}")

nlp_model.to(device).eval()
print(f"✅ Server ready | device={device} | vision={'ON' if VISION_OK else 'OFF (NLP-only)'}")


# ══════════════════════════════════════════════════════════════
#  Vision prediction — handles any proba shape safely
# ══════════════════════════════════════════════════════════════
def _align_proba(p):
    """Ensure proba array is shape (1, N_VISION_CLASSES)."""
    if p is None:
        return None
    p = np.asarray(p, dtype=float)
    if p.ndim == 1:
        p = p.reshape(1, -1)
    n_cols = p.shape[1]
    if n_cols == N_VISION_CLASSES:
        return p
    # Pad missing columns with 0 and renormalise
    out = np.zeros((p.shape[0], N_VISION_CLASSES), dtype=float)
    out[:, :n_cols] = p
    row_sum = out.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    return out / row_sum


def predict_vision(features_dict):
    if not VISION_OK:
        raise RuntimeError("Vision models unavailable.")

    X  = pd.DataFrame([features_dict])[feat_cols]
    xp = _align_proba(xgb.predict_proba(X) if xgb is not None else None)
    rp = _align_proba(rf.predict_proba(X)  if rf  is not None else None)

    if xp is not None and rp is not None:
        ep = 0.6 * xp + 0.4 * rp
    elif xp is not None:
        ep = xp
    else:
        ep = rp

    pid = int(np.argmax(ep[0]))
    return {
        'label'     : le_v.classes_[pid],
        'confidence': float(ep[0][pid]),
        'proba'     : {le_v.classes_[i]: float(ep[0][i])
                       for i in range(N_VISION_CLASSES)},
    }


# ══════════════════════════════════════════════════════════════
#  NLP prediction
# ══════════════════════════════════════════════════════════════
def predict_nlp(text):
    enc = tokenizer(text, max_length=128, padding='max_length',
                    truncation=True, return_tensors='pt')
    with torch.no_grad():
        out   = nlp_model(input_ids      = enc['input_ids'].to(device),
                          attention_mask = enc['attention_mask'].to(device))
        proba = torch.softmax(out.logits, dim=1).cpu().numpy()[0]
    pid = int(np.argmax(proba))
    n   = len(le_n.classes_)
    return {
        'label'     : le_n.classes_[pid],
        'confidence': float(proba[pid]),
        'proba'     : {le_n.classes_[i]: float(proba[i]) for i in range(n)},
    }


# ══════════════════════════════════════════════════════════════
#  Frame decoder
# ══════════════════════════════════════════════════════════════
def decode_frames(frames_b64):
    frames = []
    for b64 in frames_b64:
        try:
            data  = base64.b64decode(b64.split(',')[-1])
            img   = Image.open(io.BytesIO(data)).convert('RGB')
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            frames.append(frame)
        except Exception as e:
            print(f"  Frame decode error (skipped): {e}")
    return frames


# ══════════════════════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════════════════════
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status'                 : 'ok',
        'message'                : 'Attention Monitor Server Running!',
        'vision_models_available': VISION_OK,
    })


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data       = request.json or {}
        frames_b64 = data.get('frames', [])
        text       = data.get('text', '')
        student_id = data.get('student_id', 'unknown')

        # ── Vision branch ──────────────────────────────────────
        if VISION_OK:
            if not frames_b64:
                return jsonify({'error': 'No frames provided'}), 400

            frames   = decode_frames(frames_b64)
            features = extract_features(frames)

            if features is None:
                print(f"[{student_id}] Camera Away")
                return jsonify({
                    'student_id'             : student_id,
                    'final_label'            : 'Camera Away',
                    'attention_score'        : 0,
                    'vision'                 : {'label': 'Camera Away', 'confidence': 0},
                    'nlp'                    : {'label': 'Camera Away', 'confidence': 0},
                    'camera_away'            : True,
                    'vision_models_available': True,
                }), 200

            vision_result = predict_vision(features)
            nlp_result    = predict_nlp(text) if text.strip() else {
                'label'     : vision_result['label'],
                'confidence': vision_result['confidence'],
                'proba'     : vision_result['proba'],
            }

        # ── NLP-only fallback ──────────────────────────────────
        else:
            if not text.strip():
                return jsonify({
                    'error': 'Vision unavailable — provide text for NLP prediction.'
                }), 503
            nlp_result    = predict_nlp(text)
            vision_result = {
                'label'     : nlp_result['label'],
                'confidence': nlp_result['confidence'],
                'proba'     : nlp_result['proba'],
            }

        # ── Fusion ─────────────────────────────────────────────
        result = fuse(vision_result, nlp_result, text)
        result['student_id']              = student_id
        result['vision_models_available'] = VISION_OK

        print(f"[{student_id}] → {result['final_label']} ({result['attention_score']}/100)")
        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/predict_text', methods=['POST'])
def predict_text_only():
    try:
        text   = (request.json or {}).get('text', '')
        result = predict_nlp(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Attention Monitor Server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)