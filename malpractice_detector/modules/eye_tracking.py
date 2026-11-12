"""
eye_tracking.py
Estimates gaze direction (center / left / right / up / down) from
MediaPipe iris + eye-corner landmarks.

Approach: for each eye, find the iris center's relative horizontal
position between the eye corners (0 = fully left corner, 1 = fully
right corner). A ratio near 0.5 means looking straight ahead.
Same idea vertically using eyelid landmarks for up/down.
"""

from modules.face_utils import LEFT_IRIS, RIGHT_IRIS, LEFT_EYE_CORNERS, RIGHT_EYE_CORNERS
from scoring_config import (
    HORIZONTAL_CENTER_RANGE,
    VERTICAL_DOWN_THRESHOLD,
    VERTICAL_UP_THRESHOLD,
)

# Eyelid top/bottom landmarks (for vertical gaze ratio)
# BUGFIX: swapped to match the corrected LEFT_EYE_CORNERS/RIGHT_EYE_CORNERS
# pairing in face_utils.py — see that file's comment for the full explanation.
LEFT_EYE_TOP_BOTTOM = [386, 374]
RIGHT_EYE_TOP_BOTTOM = [159, 145]


def _horizontal_ratio(landmarks, iris_idxs, corner_idxs):
    iris_x = sum(landmarks[i][0] for i in iris_idxs) / len(iris_idxs)
    left_corner_x = landmarks[corner_idxs[0]][0]
    right_corner_x = landmarks[corner_idxs[1]][0]
    eye_width = abs(right_corner_x - left_corner_x)
    if eye_width == 0:
        return 0.5
    ratio = (iris_x - left_corner_x) / eye_width
    return max(0.0, min(1.0, ratio))


def _vertical_ratio(landmarks, iris_idxs, top_bottom_idxs):
    iris_y = sum(landmarks[i][1] for i in iris_idxs) / len(iris_idxs)
    top_y = landmarks[top_bottom_idxs[0]][1]
    bottom_y = landmarks[top_bottom_idxs[1]][1]
    eye_height = abs(bottom_y - top_y)
    if eye_height == 0:
        return 0.5
    ratio = (iris_y - top_y) / eye_height
    return max(0.0, min(1.0, ratio))


def estimate_gaze(landmarks):
    """
    landmarks: list of (x_px, y_px, z) for ONE face, from FaceMeshDetector.
    Returns dict: { "horizontal_ratio", "vertical_ratio", "direction" }
    direction is one of: "center", "left", "right", "up", "down"
    Prioritizes horizontal looking away (left/right) so that eyelid narrowing
    during sideways glances does not misclassify as vertical flutter.
    """
    h_left = _horizontal_ratio(landmarks, LEFT_IRIS, LEFT_EYE_CORNERS)
    h_right = _horizontal_ratio(landmarks, RIGHT_IRIS, RIGHT_EYE_CORNERS)
    h_ratio = (h_left + h_right) / 2

    v_left = _vertical_ratio(landmarks, LEFT_IRIS, LEFT_EYE_TOP_BOTTOM)
    v_right = _vertical_ratio(landmarks, RIGHT_IRIS, RIGHT_EYE_TOP_BOTTOM)
    v_ratio = (v_left + v_right) / 2

    if h_ratio < HORIZONTAL_CENTER_RANGE[0]:
        direction = "left"
    elif h_ratio > HORIZONTAL_CENTER_RANGE[1]:
        direction = "right"
    elif v_ratio > VERTICAL_DOWN_THRESHOLD:
        direction = "down"
    elif v_ratio < VERTICAL_UP_THRESHOLD:
        direction = "up"
    else:
        direction = "center"

    return {
        "horizontal_ratio": round(h_ratio, 3),
        "vertical_ratio": round(v_ratio, 3),
        "direction": direction,
    }
