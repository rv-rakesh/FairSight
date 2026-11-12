"""
head_pose.py
Estimates head orientation (yaw / pitch / roll) using OpenCV's solvePnP,
matching 2D facial landmarks to a generic 3D face model.
This is the same technique used in the academic proctoring papers
(e.g. the "Attentive System" and browser-exam cheating-detection papers).
"""

import numpy as np
import cv2
from modules.face_utils import HEAD_POSE_LANDMARKS
from scoring_config import (
    YAW_THRESHOLD,
    PITCH_DOWN_THRESHOLD,
    PITCH_UP_THRESHOLD,
)

# Generic 3D face model points (arbitrary units, approximate human face geometry)
MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),          # nose tip
    (0.0, -330.0, -65.0),     # chin
    (-225.0, 170.0, -135.0),  # left eye left corner
    (225.0, 170.0, -135.0),   # right eye right corner
    (-150.0, -150.0, -125.0), # mouth left
    (150.0, -150.0, -125.0),  # mouth right
], dtype=np.float64)


def estimate_head_pose(landmarks, frame_shape):
    """
    landmarks: list of (x_px, y_px, z) for ONE face.
    frame_shape: (h, w) of the frame.
    Returns dict: { "yaw", "pitch", "roll", "flag" }
    flag is True if yaw/pitch suggest the person is looking away.
    """
    h, w = frame_shape
    image_points = np.array([
        landmarks[HEAD_POSE_LANDMARKS["nose_tip"]][:2],
        landmarks[HEAD_POSE_LANDMARKS["chin"]][:2],
        landmarks[HEAD_POSE_LANDMARKS["left_eye_left_corner"]][:2],
        landmarks[HEAD_POSE_LANDMARKS["right_eye_right_corner"]][:2],
        landmarks[HEAD_POSE_LANDMARKS["mouth_left"]][:2],
        landmarks[HEAD_POSE_LANDMARKS["mouth_right"]][:2],
    ], dtype=np.float64)

    # 1. 2D Facial Landmark Symmetry Guard (physical ground truth)
    # Computes horizontal distance from nose tip to each outer eye corner.
    # In a neutral frontal pose, d_left ~= d_right. As the head turns sideways,
    # the nose moves towards one eye corner; at extreme turns the nose physically
    # crosses the outer eye margin. This metric is immune to 3D solver flips.
    nose = landmarks[HEAD_POSE_LANDMARKS["nose_tip"]]
    l_eye = landmarks[HEAD_POSE_LANDMARKS["left_eye_left_corner"]]
    r_eye = landmarks[HEAD_POSE_LANDMARKS["right_eye_right_corner"]]
    d_left = nose[0] - l_eye[0]
    d_right = r_eye[0] - nose[0]
    sym_denom = max(1e-5, (d_right + d_left))
    # sym_index > 0 when nose is closer to right eye (candidate turned right, yaw < 0)
    # sym_index < 0 when nose is closer to left eye (candidate turned left, yaw > 0)
    sym_index = (d_right - d_left) / sym_denom
    landmark_yaw = sym_index * 55.0

    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))  # assume no lens distortion

    # Use cv2.SOLVEPNP_SQPNP for robust global minimum convergence without
    # Necker-cube / planar ambiguity flips. Fallback to ITERATIVE if needed.
    success = False
    rotation_vec = None
    try:
        success, rotation_vec, _ = cv2.solvePnP(
            MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_SQPNP
        )
    except Exception:
        success = False

    if not success or rotation_vec is None:
        success, rotation_vec, _ = cv2.solvePnP(
            MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

    if not success:
        return {"yaw": None, "pitch": None, "roll": None, "flag": False}

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pose_mat = cv2.hconcat((rotation_mat, np.zeros((3, 1))))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)

    pitch, yaw, roll = [float(a) for a in euler_angles.flatten()]

    # Correction: decomposeProjectionMatrix returns pitch wrapped around
    # 180 degrees for a face looking straight at the camera, not around 0.
    if pitch >= 0:
        pitch = 180 - pitch
    else:
        pitch = -180 - pitch

    # Safeguards against solver singularities:
    # 1. If solver flips pitch into steep degenerate angle while yaw collapses near 0
    if abs(pitch) > 60.0 and abs(yaw) < 20.0:
        yaw = landmark_yaw
        pitch = 0.0

    # 2. Landmark symmetry confirmation: if physical landmarks show unmistakable turn (>28°)
    # but 3D solver under-reported yaw
    if abs(landmark_yaw) > 28.0 and abs(yaw) < 18.0:
        yaw = landmark_yaw

    flag = (
        abs(yaw) > YAW_THRESHOLD
        or pitch > PITCH_DOWN_THRESHOLD
        or pitch < -PITCH_UP_THRESHOLD
        or abs(landmark_yaw) > YAW_THRESHOLD
    )

    return {
        "yaw": round(yaw, 2),
        "pitch": round(pitch, 2),
        "roll": round(roll, 2),
        "flag": flag,
    }
