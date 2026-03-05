# feature_extractor.py — Extracts 28 features from video frames
import cv2
import numpy as np

# ── Landmark indices (68-point LBF model) ──
L_EYE_IDX  = [42, 43, 44, 45, 46, 47]
R_EYE_IDX  = [36, 37, 38, 39, 40, 41]
MOUTH_IDX  = [48, 54, 50, 56, 52, 58, 60, 64]
L_BROW_IDX = [17, 18, 19, 20, 21]
R_BROW_IDX = [22, 23, 24, 25, 26]
POSE_IDX   = [30, 8, 45, 36, 54, 48]

FACE_3D = np.array([
    [0.0,    0.0,    0.0  ],
    [0.0,   -330.0, -65.0 ],
    [-225.0, 170.0, -135.0],
    [225.0,  170.0, -135.0],
    [-150.0,-150.0, -125.0],
    [150.0, -150.0, -125.0]
], dtype=np.float64)

# ── Load detectors once ──
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
landmark_det = cv2.face.createFacemarkLBF()
landmark_det.loadModel('models/lbfmodel.yaml')

print("✅ Face detector loaded!")
print("✅ Landmark detector loaded!")


def get_ear(lm, idx):
    pts = lm[idx]
    v1  = np.linalg.norm(pts[1] - pts[5])
    v2  = np.linalg.norm(pts[2] - pts[4])
    hor = np.linalg.norm(pts[0] - pts[3])
    return (v1 + v2) / (2.0 * hor) if hor > 0 else 0.3

def get_mar(lm):
    m   = lm[MOUTH_IDX]
    v1  = np.linalg.norm(m[2] - m[6])
    v2  = np.linalg.norm(m[3] - m[5])
    hor = np.linalg.norm(m[0] - m[1])
    return (v1 + v2) / (2.0 * hor) if hor > 0 else 0.3

def get_brow(lm, brow_idx, eye_idx, h):
    return abs(np.mean(lm[brow_idx, 1]) - np.mean(lm[eye_idx, 1])) / h


def detect_faces_robust(gray):
    """
    Multi-strategy face detection that handles both:
      - Square frames  (640x640) → Deep's tile
      - Landscape frames (1280x720 → 640x360) → Gauri's tile
    """
    h, w = gray.shape

    if h < 60 or w < 60:
        return []

    # Safe maxSize cap — prevents OpenCV 4.13 cascade assertion errors
    max_dim  = min(h, w) - 10
    max_size = (max_dim, max_dim) if max_dim >= 30 else None

    # Landscape frames (w/h > 1.5) have smaller faces — go relaxed immediately
    is_landscape = (w / h) > 1.5

    # Strategy 1: strict (good for close-up square frames)
    strict_params = [
        dict(scaleFactor=1.05, minNeighbors=3, minSize=(30, 30)),
        dict(scaleFactor=1.1,  minNeighbors=3, minSize=(30, 30)),
        dict(scaleFactor=1.2,  minNeighbors=3, minSize=(30, 30)),
    ]

    # Strategy 2: relaxed (essential for landscape/wide frames)
    relaxed_params = [
        dict(scaleFactor=1.05, minNeighbors=1, minSize=(20, 20)),
        dict(scaleFactor=1.1,  minNeighbors=1, minSize=(20, 20)),
        dict(scaleFactor=1.2,  minNeighbors=1, minSize=(20, 20)),
        dict(scaleFactor=1.3,  minNeighbors=1, minSize=(20, 20)),
    ]

    strategies = relaxed_params if is_landscape else (strict_params + relaxed_params)

    for params in strategies:
        # First try with maxSize (prevents OpenCV crash)
        try:
            kwargs = dict(**params)
            if max_size:
                kwargs['maxSize'] = max_size
            faces = face_cascade.detectMultiScale(gray, **kwargs)
            if len(faces) > 0:
                return faces
        except cv2.error:
            pass

        # Fallback: try without maxSize
        try:
            faces = face_cascade.detectMultiScale(gray, **params)
            if len(faces) > 0:
                return faces
        except cv2.error:
            continue
        except Exception as e:
            print(f"  Unexpected detection error: {e}")
            continue

    return []


def preprocess_frame(frame):
    """
    Resize so the LONGEST side = 640px.
    - Square 640x640 stays 640x640
    - Landscape 1280x720 becomes 640x360  (was previously 640x480 — wrong!)
    This keeps face proportions correct for the cascade.
    """
    h, w  = frame.shape[:2]
    scale = 640 / max(h, w)
    return cv2.resize(frame, (int(w * scale), int(h * scale)))


def extract_features(frames):
    print(f"  Received {len(frames)} frames")
    if frames:
        h, w = frames[0].shape[:2]
        print(f"  First frame size: {w}x{h}")

    ears, pitches, yaws = [], [], []
    mars, brows         = [], []
    gaze_xs, gaze_ys    = [], []
    blink_count         = 0
    prev_closed         = False
    EAR_THRESH          = 0.20
    faces_found         = 0

    for frame in frames:
        # ✅ Scale by longest side — correct for both square and landscape tiles
        frame = preprocess_frame(frame)
        h, w  = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = detect_faces_robust(gray)

        if len(faces) == 0:
            continue

        faces_found += 1
        face = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]

        fx, fy, fw, fh = face
        if fw < 20 or fh < 20:
            continue

        try:
            ok, lms = landmark_det.fit(gray, np.array([face]))
        except Exception as e:
            print(f"  Landmark error: {e}")
            continue

        if not ok:
            continue

        lm  = lms[0][0]
        ear = (get_ear(lm, L_EYE_IDX) + get_ear(lm, R_EYE_IDX)) / 2
        ears.append(ear)

        if ear < EAR_THRESH and not prev_closed:
            blink_count += 1
            prev_closed  = True
        elif ear >= EAR_THRESH:
            prev_closed  = False

        try:
            face_2d = np.array([lm[i] for i in POSE_IDX], dtype=np.float64)
            cam_mat = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]], dtype=np.float64)
            _, rvec, _ = cv2.solvePnP(FACE_3D, face_2d, cam_mat,
                                       np.zeros((4, 1)),
                                       flags=cv2.SOLVEPNP_ITERATIVE)
            rmat, _   = cv2.Rodrigues(rvec)
            angles, _ = cv2.RQDecomp3x3(rmat)
            pitches.append(angles[0] * 360)
            yaws.append(angles[1] * 360)
        except Exception:
            pitches.append(0.0)
            yaws.append(0.0)

        mars.append(get_mar(lm))

        lb = get_brow(lm, L_BROW_IDX, L_EYE_IDX, h)
        rb = get_brow(lm, R_BROW_IDX, R_EYE_IDX, h)
        brows.append((lb + rb) / 2)

        l_cx = np.mean(lm[L_EYE_IDX, 0])
        r_cx = np.mean(lm[R_EYE_IDX, 0])
        f_cx = face[0] + face[2] / 2
        gaze_xs.append((l_cx + r_cx) / 2 - f_cx)
        gaze_ys.append(np.mean(lm[L_EYE_IDX, 1]))

    print(f"  Faces found in {faces_found}/{len(frames)} frames")
    print(f"  Valid EAR readings: {len(ears)}")

    if len(ears) < 3:
        print(f"  ❌ Not enough readings — returning None")
        return None

    ears    = np.array(ears)
    pitches = np.array(pitches)
    yaws    = np.array(yaws)
    mars    = np.array(mars)
    brows   = np.array(brows)
    gaze_xs = np.array(gaze_xs)
    gaze_ys = np.array(gaze_ys)
    dur     = max(len(frames) / 10.0, 0.1)

    print(f"  ✅ Features extracted! avg_ear={np.mean(ears):.3f}")

    return {
        'avg_ear'     : float(np.mean(ears)),
        'std_ear'     : float(np.std(ears)),
        'min_ear'     : float(np.min(ears)),
        'max_ear'     : float(np.max(ears)),
        'median_ear'  : float(np.median(ears)),
        'ear_range'   : float(np.ptp(ears)),
        'ear_q25'     : float(np.percentile(ears, 25)),
        'ear_q75'     : float(np.percentile(ears, 75)),
        'perclos'     : float(np.mean(ears < EAR_THRESH)),
        'blink_count' : float(blink_count),
        'blink_rate'  : float(blink_count / dur),
        'avg_pitch'   : float(np.mean(pitches)),
        'std_pitch'   : float(np.std(pitches)),
        'avg_yaw'     : float(np.mean(yaws)),
        'std_yaw'     : float(np.std(yaws)),
        'pitch_range' : float(np.ptp(pitches)),
        'yaw_range'   : float(np.ptp(yaws)),
        'avg_mar'     : float(np.mean(mars)),
        'std_mar'     : float(np.std(mars)),
        'max_mar'     : float(np.max(mars)),
        'avg_brow'    : float(np.mean(brows)),
        'std_brow'    : float(np.std(brows)),
        'avg_gaze_x'  : float(np.mean(gaze_xs)),
        'std_gaze_x'  : float(np.std(gaze_xs)),
        'avg_gaze_y'  : float(np.mean(gaze_ys)),
        'std_gaze_y'  : float(np.std(gaze_ys)),
        'gaze_x_range': float(np.ptp(gaze_xs)),
        'gaze_y_range': float(np.ptp(gaze_ys)),
    }