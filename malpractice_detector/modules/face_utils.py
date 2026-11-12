"""
face_utils.py
Core face + landmark detection using MediaPipe's FaceLandmarker (Tasks API).

IMPORTANT - MediaPipe API version note:
Many older tutorials/GitHub repos use `mp.solutions.face_mesh`. That legacy
API is NOT available in current mediapipe releases (0.10.x) - only the newer
Tasks API (`mp.tasks.vision.FaceLandmarker`) is. This module uses the current
API, which requires a downloaded model file (face_landmarker.task).
Run `python download_model.py` once (with internet access) before first use.
"""

import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "face_landmarker.task")
BLAZE_FACE_PATH = os.path.join(MODEL_DIR, "blaze_face_short_range.tflite")
OBJECT_DETECTOR_PATH = os.path.join(MODEL_DIR, "efficientdet_lite0.tflite")
HAND_LANDMARKER_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")

MODEL_URLS = {
    MODEL_PATH: (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/face_landmarker.task"
    ),
    BLAZE_FACE_PATH: (
        "https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
    ),
    OBJECT_DETECTOR_PATH: (
        "https://storage.googleapis.com/mediapipe-models/object_detector/"
        "efficientdet_lite0/float16/1/efficientdet_lite0.tflite"
    ),
    HAND_LANDMARKER_PATH: (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task"
    ),
}


def _ensure_models():
    """Ensures required models exist locally, downloading if necessary."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    for path, url in MODEL_URLS.items():
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            try:
                urllib.request.urlretrieve(url, path)
            except Exception:
                pass


def _compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    areaB = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    denom = areaA + areaB - inter
    return inter / denom if denom > 0 else 0.0


def _is_duplicate_box(boxA, boxB):
    """Checks if two detected person/body boxes represent the same person."""
    iou = _compute_iou(boxA, boxB)
    if iou > 0.25:
        return True
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    areaB = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    min_area = min(areaA, areaB)
    if min_area > 0 and (inter / min_area > 0.65):
        ratio = max(areaA, areaB) / min_area
        if ratio < 4.0:
            return True
    return False


def _is_candidate_body_or_hand(b_box, score, cand_mesh, mesh_boxes, frame_h, frame_w, is_face_proposal=False):
    """
    Distinguishes the candidate's own body parts (hands, fingers, arms, shoulders, torso,
    typing on keyboard, resting on desk) from an unauthorized secondary person.
    Handles both ObjectDetector body proposals and BlazeFace false positives on hands/knuckles.
    """
    if cand_mesh is None:
        return False

    bx1, by1, bx2, by2 = b_box
    bw = max(1, bx2 - bx1)
    bh = max(1, by2 - by1)
    aspect_ratio = bw / bh
    cx1, cy1, cx2, cy2 = cand_mesh
    cw = max(1, cx2 - cx1)
    ch = max(1, cy2 - cy1)
    cmx = (cx1 + cx2) / 2
    cmy = (cy1 + cy2) / 2
    bmx = (bx1 + bx2) / 2
    bmy = (by1 + by2) / 2

    # Candidate workspace lateral boundaries
    cand_workspace_x1 = max(0, cmx - 2.5 * cw)
    cand_workspace_x2 = min(frame_w, cmx + 2.5 * cw)
    in_cand_workspace = (bx1 >= cand_workspace_x1 - 25) and (bx2 <= cand_workspace_x2 + 25)
    near_cand_center = abs(bmx - cmx) < 2.0 * cw

    # 1. Check if ANY tracked face mesh is inside this detection box
    has_face_inside = any(
        (bx1 - 10 <= (mb[0] + mb[2]) / 2 <= bx2 + 10) and (by1 - 10 <= (mb[1] + mb[3]) / 2 <= by2 + 10)
        for mb in mesh_boxes
    )
    if has_face_inside:
        body_area = bw * bh
        c_area = cw * ch
        if (bx1 <= cmx <= bx2) and (by1 <= cmy <= by2 + 50) and (body_area >= c_area * 0.7):
            return True
        if _compute_iou(b_box, cand_mesh) > 0.15:
            return True
        return False

    # 2. Candidate hands / knuckles / chest detected as a false face proposal (BlazeFace false positive)
    if is_face_proposal:
        # Hands or fingers in front of camera are located in candidate's chest/desk area
        # They must start at or below candidate nose level and extend well below chin into chest/lap
        in_chest_or_desk = (by1 >= cy1 + 0.35 * ch) and (by2 > cy2 + 0.3 * ch)
        in_lower_foreground = (by1 >= cy1) and (by2 >= frame_h * 0.65)

        if near_cand_center and (in_chest_or_desk or in_lower_foreground):
            return True
        if score < 0.62 and in_cand_workspace and (by1 >= cy2 - 10) and (by2 >= cy2 + 20):
            return True
        return False

    # 3. ObjectDetector body proposals (headless proposals)
    # If the proposal is tall (bh >= frame_h * 0.45) and does NOT contain candidate face:
    # It is another person standing or moving in the room (e.g. standing to the side or reaching in)!
    if bh >= frame_h * 0.45:
        return False

    # Candidate hand/wrist/partial arm in candidate's typing workspace:
    # Must be within candidate lateral typing span (|bmx - cmx| < 1.4 * cw) and partial height
    cand_typing_span = abs(bmx - cmx) < 1.4 * cw
    if bh < frame_h * 0.40 and cand_typing_span and (by2 >= cy1 or by1 >= cy1 - 20):
        if aspect_ratio >= 1.10:  # flat / horizontal hand/arm across keyboard
            return True
        if by2 >= frame_h * 0.65:  # lower foreground desk/keyboard
            return True

    # Direct physical attachment to candidate face/chin (resting chin on hand)
    dist_to_face_x = max(0, max(cx1 - bx2, bx1 - cx2))
    dist_to_face_y = max(0, max(cy1 - by2, by1 - cy2))
    if dist_to_face_x < cw * 0.5 and dist_to_face_y < ch * 0.5:
        return True

    return False


# Landmark indices we care about (MediaPipe 468-point face mesh)
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]
LEFT_EYE_CORNERS = [362, 263]    # correctly pairs with LEFT_IRIS (474-477)
RIGHT_EYE_CORNERS = [33, 133]    # correctly pairs with RIGHT_IRIS (469-472)

# 6 points used for solvePnP head pose (nose tip, chin, eye corners, mouth corners)
HEAD_POSE_LANDMARKS = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_left_corner": 33,
    "right_eye_right_corner": 263,
    "mouth_left": 61,
    "mouth_right": 291,
}


class FaceMeshDetector:
    """
    Multi-stage detector combining MediaPipe FaceLandmarker (478-mesh telemetry),
    BlazeFace detector (periphery/corner/profile faces), and ObjectDetector (unauthorized persons/bodies).
    """

    def __init__(self, model_path=MODEL_PATH, max_num_faces=10, min_detection_confidence=0.35):
        _ensure_models()
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        self.options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
        )
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(self.options)
        self._timestamp_ms = 0

        # Auxiliary BlazeFace detector for partial/profile faces missed by dense mesh
        self.face_detector = None
        if os.path.exists(BLAZE_FACE_PATH):
            try:
                fd_opts = mp_vision.FaceDetectorOptions(
                    base_options=mp_python.BaseOptions(model_asset_path=BLAZE_FACE_PATH),
                    min_detection_confidence=0.55,
                )
                self.face_detector = mp_vision.FaceDetector.create_from_options(fd_opts)
            except Exception:
                self.face_detector = None

        # Auxiliary Object detector for persons/bodies/heads/shoulders in frame
        self.obj_detector = None
        if os.path.exists(OBJECT_DETECTOR_PATH):
            try:
                od_opts = mp_vision.ObjectDetectorOptions(
                    base_options=mp_python.BaseOptions(model_asset_path=OBJECT_DETECTOR_PATH),
                    category_allowlist=["person"],
                    score_threshold=0.18,
                )
                self.obj_detector = mp_vision.ObjectDetector.create_from_options(od_opts)
            except Exception:
                self.obj_detector = None

        # Auxiliary HandLandmarker for detecting intruder hands / reaching arms
        self.hand_detector = None
        if os.path.exists(HAND_LANDMARKER_PATH):
            try:
                hd_opts = mp_vision.HandLandmarkerOptions(
                    base_options=mp_python.BaseOptions(model_asset_path=HAND_LANDMARKER_PATH),
                    running_mode=mp_vision.RunningMode.IMAGE,
                    num_hands=4,
                    min_hand_detection_confidence=0.35,
                )
                self.hand_detector = mp_vision.HandLandmarker.create_from_options(hd_opts)
            except Exception:
                self.hand_detector = None

    def reset(self):
        """Resets the underlying landmarker C++ instance so timestamps can start from 0 again."""
        try:
            self.landmarker.close()
        except Exception:
            pass
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(self.options)
        self._timestamp_ms = 0

    def process(self, frame_bgr, timestamp_ms=None):
        """
        Runs full multi-stage detection on frame:
        1. MediaPipe FaceLandmarker for primary 478 3D landmarks (candidate & frontal faces).
        2. BlazeFace & ObjectDetector for peripheral, profile, corner, background, or occluded persons.

        Returns a dict:
          {
            "face_count": int (total persons detected across all models),
            "person_count": int,
            "mesh_face_count": int,
            "landmarks_list": [ [ (x_px, y_px, z), ... ] per mesh face ],
            "auxiliary_persons": [ {"bbox": (x1,y1,x2,y2), "type": str, "confidence": float, "label": str} ],
            "frame_shape": (h, w)
          }
        """
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        if timestamp_ms is not None and timestamp_ms <= self._timestamp_ms:
            self.reset()

        if timestamp_ms is None:
            self._timestamp_ms += 33
            curr_ts = self._timestamp_ms
        else:
            self._timestamp_ms = timestamp_ms
            curr_ts = timestamp_ms

        try:
            result = self.landmarker.detect_for_video(mp_image, curr_ts)
        except ValueError as e:
            if "monotonically increasing" in str(e):
                self.reset()
                curr_ts = max(33, curr_ts)
                self._timestamp_ms = curr_ts
                result = self.landmarker.detect_for_video(mp_image, curr_ts)
            else:
                raise

        landmarks_list = []
        mesh_boxes = []
        if result.face_landmarks:
            for face_landmarks in result.face_landmarks:
                pts = [(lm.x * w, lm.y * h, lm.z) for lm in face_landmarks]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                cur_box = (min(xs), min(ys), max(xs), max(ys))

                # Deduplicate: Ignore duplicate/ghost proposals on the exact same face
                is_duplicate = False
                for existing_box in mesh_boxes:
                    if _compute_iou(cur_box, existing_box) > 0.30:
                        is_duplicate = True
                        break
                    cx1, cy1 = (cur_box[0] + cur_box[2]) / 2, (cur_box[1] + cur_box[3]) / 2
                    cx2, cy2 = (existing_box[0] + existing_box[2]) / 2, (existing_box[1] + existing_box[3]) / 2
                    dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
                    min_dim = min(cur_box[2] - cur_box[0], cur_box[3] - cur_box[1],
                                  existing_box[2] - existing_box[0], existing_box[3] - existing_box[1])
                    if dist < 0.45 * min_dim:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    landmarks_list.append(pts)
                    mesh_boxes.append(cur_box)

        # Identify primary candidate face (largest & most central face in foreground)
        candidate_mesh_box = None
        if mesh_boxes:
            def _score_face(box):
                area = (box[2] - box[0]) * (box[3] - box[1])
                fcx, fcy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                dist_center = abs(fcx - w / 2) + abs(fcy - h / 2)
                return area - dist_center * 5.0
            candidate_mesh_box = max(mesh_boxes, key=_score_face)

        # Run auxiliary detectors to catch corner/profile/background/partial persons
        raw_aux_persons = []

        # 1. BlazeFace check (catches partial/edge faces)
        if self.face_detector is not None:
            try:
                fd_res = self.face_detector.detect(mp_image)
                for d in fd_res.detections:
                    bb = d.bounding_box
                    score = d.categories[0].score if d.categories else 0.5
                    bx1, by1, bx2, by2 = bb.origin_x, bb.origin_y, bb.origin_x + bb.width, bb.origin_y + bb.height
                    cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
                    # Discard if it overlaps any already-tracked mesh face
                    matched = any(
                        _compute_iou((bx1, by1, bx2, by2), mbox) > 0.15 or
                        (abs(cx - (mbox[0] + mbox[2]) / 2) < 40 and abs(cy - (mbox[1] + mbox[3]) / 2) < 40)
                        for mbox in mesh_boxes
                    )
                    if not matched:
                        b_box = (bx1, by1, bx2, by2)
                        # Suppress false face proposals on candidate's hands, arms, and chest
                        if _is_candidate_body_or_hand(b_box, score, candidate_mesh_box, mesh_boxes, h, w, is_face_proposal=True):
                            continue

                        raw_aux_persons.append({
                            "bbox": (int(bx1), int(by1), int(bx2), int(by2)),
                            "type": "face",
                            "confidence": float(score),
                            "label": "Unauthorized Person (Face / Head Detected)",
                        })
            except Exception:
                pass

        # 2. ObjectDetector person check (catches bodies, background students, partial torsos/heads)
        if self.obj_detector is not None:
            try:
                od_res = self.obj_detector.detect(mp_image)
                for d in od_res.detections:
                    bb = d.bounding_box
                    score = d.categories[0].score if d.categories else 0.5
                    bx1, by1, bx2, by2 = bb.origin_x, bb.origin_y, bb.origin_x + bb.width, bb.origin_y + bb.height
                    bw, bh = bx2 - bx1, by2 - by1

                    # Filter out sub-pixel noise (allow distant background persons down to 14px)
                    if bw < 14 or bh < 14:
                        continue

                    body_area = bw * bh
                    b_box = (bx1, by1, bx2, by2)

                    # Suppress candidate's own body, arms, hands, and keyboard interactions from triggering false auxiliary alert
                    if _is_candidate_body_or_hand(b_box, score, candidate_mesh_box, mesh_boxes, h, w):
                        continue

                    # Suppress body if another tracked mesh face is inside it
                    belongs_to_other_mesh = False
                    for mbox in mesh_boxes:
                        if mbox == candidate_mesh_box:
                            continue
                        mx = (mbox[0] + mbox[2]) / 2
                        my = (mbox[1] + mbox[3]) / 2
                        if (bx1 <= mx <= bx2) and (by1 <= my <= by2 + 40):
                            belongs_to_other_mesh = True
                            break

                    if belongs_to_other_mesh:
                        continue

                    raw_aux_persons.append({
                        "bbox": (int(bx1), int(by1), int(bx2), int(by2)),
                        "type": "body",
                        "confidence": float(score),
                        "label": "Unauthorized Person (Body / Motion Detected)",
                    })
            except Exception:
                pass

        # 3. HandLandmarker check (catches unauthorized reaching hands, arms, body parts)
        if self.hand_detector is not None:
            try:
                hd_res = self.hand_detector.detect(mp_image)
                if hd_res.hand_landmarks:
                    for lms in hd_res.hand_landmarks:
                        xs = [lm.x * w for lm in lms]
                        ys = [lm.y * h for lm in lms]
                        bx1, by1, bx2, by2 = min(xs), min(ys), max(xs), max(ys)
                        hw = bx2 - bx1
                        hh = by2 - by1
                        bmx = (bx1 + bx2) / 2

                        is_intruder = False
                        if candidate_mesh_box is None:
                            is_intruder = True
                        else:
                            cx1, cy1, cx2, cy2 = candidate_mesh_box
                            cw = max(1, cx2 - cx1)
                            cmx = (cx1 + cx2) / 2

                            # Reaching arm/hand extending across candidate body
                            if hw >= 2.0 * cw:
                                is_intruder = True
                            # Peripheral hand outside candidate workspace
                            elif abs(bmx - cmx) >= 2.2 * cw:
                                is_intruder = True

                        if is_intruder:
                            raw_aux_persons.append({
                                "bbox": (int(bx1), int(by1), int(bx2), int(by2)),
                                "type": "hand",
                                "confidence": 0.85,
                                "label": "Unauthorized Person (Hand / Body Part Detected)",
                            })
            except Exception:
                pass

        # Deduplicate overlapping detections among auxiliary persons
        auxiliary_persons = []
        for cand in sorted(raw_aux_persons, key=lambda x: x["confidence"], reverse=True):
            if not any(_is_duplicate_box(cand["bbox"], a["bbox"]) for a in auxiliary_persons):
                auxiliary_persons.append(cand)

        mesh_count = len(landmarks_list)
        total_persons = mesh_count + len(auxiliary_persons)

        return {
            "face_count": total_persons,
            "person_count": total_persons,
            "mesh_face_count": mesh_count,
            "landmarks_list": landmarks_list,
            "auxiliary_persons": auxiliary_persons,
            "frame_shape": (h, w),
        }

    def close(self):
        try:
            self.landmarker.close()
        except Exception:
            pass
        if self.face_detector:
            try:
                self.face_detector.close()
            except Exception:
                pass
        if self.obj_detector:
            try:
                self.obj_detector.close()
            except Exception:
                pass
        if self.hand_detector:
            try:
                self.hand_detector.close()
            except Exception:
                pass


def draw_face_annotations(frame_bgr, landmarks_list, gaze_info=None, pose_info=None, auxiliary_persons=None):
    """
    Renders comprehensive proctoring visual feedback on candidate frame:
    - Primary candidate mesh landmarks (iris centers, eye corners, nose tip, chin)
    - Auxiliary detected persons / profile faces with high-visibility warning bounding boxes
    - Dynamic multi-person alert HUD banner
    """
    annotated = frame_bgr.copy()
    h, w = annotated.shape[:2]
    aux_list = auxiliary_persons or []
    total_persons = len(landmarks_list) + len(aux_list)

    # 1. Draw Primary Face Mesh landmarks
    for pts in landmarks_list:
        for idx in LEFT_IRIS + RIGHT_IRIS:
            pt = pts[idx]
            cv2.circle(annotated, (int(pt[0]), int(pt[1])), 2, (0, 255, 255), -1)

        for idx in LEFT_EYE_CORNERS + RIGHT_EYE_CORNERS:
            pt = pts[idx]
            cv2.circle(annotated, (int(pt[0]), int(pt[1])), 3, (255, 128, 0), -1)

        nose = pts[HEAD_POSE_LANDMARKS["nose_tip"]]
        chin = pts[HEAD_POSE_LANDMARKS["chin"]]
        cv2.circle(annotated, (int(nose[0]), int(nose[1])), 4, (0, 200, 0), -1)
        cv2.circle(annotated, (int(chin[0]), int(chin[1])), 4, (0, 200, 0), -1)

    # 2. Draw Auxiliary Detected Persons / Bodies with bold RED LINE and clean compact non-overlapping tags
    hud_h = 46
    for i, aux in enumerate(aux_list, len(landmarks_list) + 1):
        bx1, by1, bx2, by2 = aux["bbox"]
        bx1, by1 = max(0, bx1), max(0, by1)
        bx2, by2 = min(w - 1, bx2), min(h - 1, by2)

        # Bold Red Line bounding box (per user request: "mark them with red line")
        cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (0, 0, 245), 2)

        # Clean compact badge: "#i" (per user request: "no overiding of text like unauthorizedperson so many")
        tag_text = f"#{i}"
        (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        pad = 3
        tag_w = tw + pad * 2
        tag_h = th + pad * 2

        # If box top is near or under the HUD banner, place tag inside box to prevent collision
        if by1 - tag_h - 2 < hud_h:
            ty1 = max(hud_h + 2, by1 + 2)
            ty2 = ty1 + tag_h
            text_y = ty1 + th + pad
        else:
            ty1 = by1 - tag_h - 1
            ty2 = by1
            text_y = by1 - pad - 1

        cv2.rectangle(annotated, (bx1, ty1), (bx1 + tag_w, ty2), (0, 0, 220), -1)
        cv2.putText(annotated, tag_text, (bx1 + pad, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Two-Tier Telemetry HUD Banner (No text collisions)
    hud_bg = (20, 24, 38)
    cv2.rectangle(annotated, (0, 0), (w, hud_h), hud_bg, -1)

    if total_persons > 1:
        # Crimson Malpractice Alert Banner Line
        cv2.line(annotated, (0, hud_h), (w, hud_h), (0, 0, 245), 2)
        # Line 1: Alert Status
        hud_txt = f"WARNING: {total_persons} PERSONS DETECTED (UNAUTHORIZED PRESENCE)"
        cv2.putText(annotated, hud_txt, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)
        # Line 2: Breakdown
        sub_txt = f"Candidate: 1 Verified | Unauthorized: {total_persons - 1} (Red Boxes #{len(landmarks_list) + 1}-#{total_persons})"
        cv2.putText(annotated, sub_txt, (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 200, 255), 1, cv2.LINE_AA)
    elif total_persons == 1:
        # Emerald Verified Banner Line
        cv2.line(annotated, (0, hud_h), (w, hud_h), (0, 255, 128), 2)
        # Line 1: Verified Status
        status_txt = "Candidate Verified (1 Person in Frame)"
        cv2.putText(annotated, status_txt, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 255, 128), 1, cv2.LINE_AA)
        # Line 2: Telemetry
        gaze_dir = gaze_info.get("direction", "center").upper() if gaze_info else "CENTER"
        yaw_val = f"{pose_info['yaw']:+.1f}" if (pose_info and pose_info.get("yaw") is not None) else "+0.0"
        pitch_val = f"{pose_info['pitch']:+.1f}" if (pose_info and pose_info.get("pitch") is not None) else "+0.0"
        telemetry_txt = f"Gaze: {gaze_dir}  |  Yaw: {yaw_val} deg  |  Pitch: {pitch_val} deg"
        cv2.putText(annotated, telemetry_txt, (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)
    else:
        # Amber Candidate Absent Banner Line
        cv2.line(annotated, (0, hud_h), (w, hud_h), (0, 200, 255), 2)
        cv2.putText(annotated, "WARNING: Candidate Absent (0 Persons in Frame)", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 200, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated, "No face or body detected in camera frame", (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1, cv2.LINE_AA)

    return annotated

