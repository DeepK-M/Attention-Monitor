# app.py — Main Flask Server
from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2, numpy as np, pickle, json, base64, torch, io
import pandas as pd
from PIL import Image
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from feature_extractor import extract_features
from fusion import fuse

app = Flask(__name__)
CORS(app)

# ── Load all models at startup ──
print("Loading models...")

with open('models/xgboost_BEST_final.pkl', 'rb') as f: xgb      = pickle.load(f)
with open('models/rf_BEST_final.pkl',      'rb') as f: rf       = pickle.load(f)
with open('models/label_encoder_BEST_final.pkl', 'rb') as f: le_v = pickle.load(f)
with open('models/feature_cols_BEST.json', 'r')  as f: feat_cols = json.load(f)
with open('models/le_nlp_final.pkl',       'rb') as f: le_n     = pickle.load(f)

device    = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
tokenizer = DistilBertTokenizer.from_pretrained('models/distilbert_nlp_final')
nlp_model = DistilBertForSequenceClassification.from_pretrained(
                'models/distilbert_nlp_final')
nlp_model.to(device)
nlp_model.eval()

print(f"✅ All models loaded! Device: {device}")


# ── Helper functions ──
def predict_vision(features_dict):
    X   = pd.DataFrame([features_dict])[feat_cols]
    xp  = xgb.predict_proba(X)
    rp  = rf.predict_proba(X)
    ep  = 0.6 * xp + 0.4 * rp
    pid = int(np.argmax(ep[0]))
    return {
        'label'     : le_v.classes_[pid],
        'confidence': float(ep[0][pid]),
        'proba'     : {le_v.classes_[i]: float(ep[0][i]) for i in range(4)}
    }

def predict_nlp(text):
    enc = tokenizer(text, max_length=128, padding='max_length',
                    truncation=True, return_tensors='pt')
    with torch.no_grad():
        out   = nlp_model(
                    input_ids=enc['input_ids'].to(device),
                    attention_mask=enc['attention_mask'].to(device))
        proba = torch.softmax(out.logits, dim=1).cpu().numpy()[0]
    pid = int(np.argmax(proba))
    return {
        'label'     : le_n.classes_[pid],
        'confidence': float(proba[pid]),
        'proba'     : {le_n.classes_[i]: float(proba[i]) for i in range(4)}
    }

def decode_frames(frames_b64):
    frames = []
    for b64 in frames_b64:
        data  = base64.b64decode(b64.split(',')[-1])
        img   = Image.open(io.BytesIO(data))
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        frames.append(frame)
    return frames


# ── Routes ──
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Attention Monitor Server Running!'})


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data       = request.json
        frames_b64 = data.get('frames', [])
        text       = data.get('text', '')
        student_id = data.get('student_id', 'unknown')

        if not frames_b64:
            return jsonify({'error': 'No frames provided'}), 400

        # ✅ FIX: Decode base64 frames to OpenCV images before using them
        frames = decode_frames(frames_b64)

        # Extract features (face detection)
        features = extract_features(frames)
        if features is None:
            print(f"[{student_id}] → Camera Away (no face detected)")
            return jsonify({
                'student_id'     : student_id,
                'final_label'    : 'Camera Away',
                'attention_score': 0,
                'vision'         : {'label': 'Camera Away', 'confidence': 0},
                'nlp'            : {'label': 'Camera Away', 'confidence': 0},
                'camera_away'    : True
            }), 200

        # Vision prediction
        vision_result = predict_vision(features)

        # NLP prediction
        if text.strip():
            nlp_result = predict_nlp(text)
        else:
            nlp_result = {
                'label'     : vision_result['label'],
                'confidence': vision_result['confidence'],
                'proba'     : vision_result['proba']
            }

        # Fusion
        result               = fuse(vision_result, nlp_result, text)
        result['student_id'] = student_id

        print(f"[{student_id}] → {result['final_label']} "
              f"({result['attention_score']}/100)")
        return jsonify(result)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/predict_text', methods=['POST'])
def predict_text_only():
    try:
        text   = request.json.get('text', '')
        result = predict_nlp(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Attention Monitor Server...")
    print("   URL  : http://localhost:5000")
    print("   Health: http://localhost:5000/health")
    app.run(host='0.0.0.0', port=5000, debug=False)