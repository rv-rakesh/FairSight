import os
import numpy as np
import cv2
import pytest
from modules.face_utils import FaceMeshDetector, draw_face_annotations

def test_detector_initialization_and_keys():
    try:
        detector = FaceMeshDetector()
    except OSError as e:
        if "4551" in str(e) or "Application Control" in str(e):
            pytest.skip(f"Windows Smart App Control blocked libmediapipe.dll: {e}")
        raise
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    res = detector.process(blank)

    assert 'face_count' in res
    assert 'person_count' in res
    assert 'mesh_face_count' in res
    assert 'landmarks_list' in res
    assert 'auxiliary_persons' in res
    assert res['face_count'] == 0
    assert res['person_count'] == 0
    assert len(res['landmarks_list']) == 0
    assert len(res['auxiliary_persons']) == 0
    detector.close()

def test_draw_annotations_with_auxiliary_persons():
    h, w = 300, 400
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    aux_persons = [
        {
            'bbox': (250, 100, 350, 220),
            'type': 'face',
            'confidence': 0.85,
            'label': 'Unauthorized Person (Corner/Profile)',
        }
    ]
    annotated = draw_face_annotations(frame, landmarks_list=[], auxiliary_persons=aux_persons)
    assert annotated.shape == (h, w, 3)
    assert np.any(annotated > 0)

def test_multi_person_on_test_frame_if_available():
    # Dynamically check for local test frames in scratch or user directories
    test_paths = [
        os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "scratch", "top_left.png"),
        os.path.join(os.path.dirname(__file__), "..", "scratch", "top_left.png"),
    ]
    for path in test_paths:
        if os.path.exists(path):
            img = cv2.imread(path)
            detector = FaceMeshDetector()
            res = detector.process(img)
            assert res['person_count'] >= 2
            assert res['face_count'] >= 2
            detector.close()
            break

def test_duplicate_mesh_face_suppression_on_single_candidate():
    temp_video = os.path.join(os.environ.get("TEMP", ""), "tmph9hvh2yd.mp4")
    if os.path.exists(temp_video):
        cap = cv2.VideoCapture(temp_video)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        # Frame at 39.0s was previously triggering 2 duplicate mesh faces
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(39.0 * fps))
        ret, frame = cap.read()
        cap.release()
        if ret:
            detector = FaceMeshDetector()
            res = detector.process(frame, timestamp_ms=39000)
            detector.close()
            assert res['mesh_face_count'] == 1, f"Expected 1 mesh face at 39s, got {res['mesh_face_count']}"
            assert res['face_count'] == 1, f"Expected 1 total person at 39s, got {res['face_count']}"


def test_candidate_hand_and_chest_proposal_suppression():
    """Verifies that candidate hands/arms/chest are not flagged as auxiliary unauthorized persons."""
    from modules.face_utils import _is_candidate_body_or_hand
    cand_mesh = (120, 20, 175, 70)
    mesh_boxes = [cand_mesh]
    frame_h, frame_w = 170, 300

    # Hand proposal in chest/desk typing area (as raised by user in live proctoring)
    hand_box = (160, 65, 220, 125)
    assert _is_candidate_body_or_hand(hand_box, 0.55, cand_mesh, mesh_boxes, frame_h, frame_w, is_face_proposal=True) is True

    # Real secondary person face to the side (should NOT be suppressed)
    side_face = (235, 20, 280, 65)
    assert _is_candidate_body_or_hand(side_face, 0.85, cand_mesh, mesh_boxes, frame_h, frame_w, is_face_proposal=True) is False

    # Real secondary person face behind candidate (should NOT be suppressed)
    behind_face = (130, 0, 175, 25)
    assert _is_candidate_body_or_hand(behind_face, 0.85, cand_mesh, mesh_boxes, frame_h, frame_w, is_face_proposal=True) is False


def test_intruder_hand_vs_self_hand():
    """Verifies that an intruder reaching hand is flagged as multi-person, while self hand is not."""
    test_video = os.path.join(os.environ.get("TEMP", ""), "tmphya0mdab.mp4")
    if os.path.exists(test_video):
        cap = cv2.VideoCapture(test_video)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        # At 23.7s, another person's hand reaches into frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(23.7 * fps))
        ret, frame_intruder = cap.read()

        # At 5.8s, candidate touches own face/glasses
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(5.8 * fps))
        ret_self, frame_self = cap.read()
        cap.release()

        detector = FaceMeshDetector()
        if ret_self:
            res_self = detector.process(frame_self, timestamp_ms=5800)
            assert res_self['face_count'] == 1, f"Expected 1 person during self hand, got {res_self['face_count']}"

        if ret_intruder:
            res_intruder = detector.process(frame_intruder, timestamp_ms=23700)
            assert res_intruder['face_count'] >= 2, f"Expected >=2 persons during intruder hand, got {res_intruder['face_count']}"
        detector.close()



