import numpy as np

from app.cv.face_mesh import FaceLandmarker, ModelAssetMissingError, build_3d_representation, NUM_LANDMARKS


def test_missing_model_asset_raises_clear_error_instead_of_faking_landmarks(tmp_path):
    """No face_landmarker.task model file is present (and none is fabricated
    here) -> the wrapper must refuse to run rather than invent 468 fake
    points. This is the honest behavior required by spec section 68."""
    empty_model_dir = str(tmp_path / "no_models_here")
    try:
        FaceLandmarker(model_dir=empty_model_dir)
        raised = False
    except ModelAssetMissingError:
        raised = True
    assert raised is True


def test_build_3d_representation_from_explicit_landmarks_is_derived_not_faked():
    rng = np.random.default_rng(7)
    landmarks = rng.normal(0.5, 0.1, size=(NUM_LANDMARKS, 3))
    rep = build_3d_representation(landmarks)
    assert rep["point_count"] == NUM_LANDMARKS
    assert len(rep["points"]) == NUM_LANDMARKS
    # centered representation should have ~zero mean
    pts = np.array(rep["points"])
    assert np.allclose(pts.mean(axis=0), 0, atol=1e-6)


def test_build_3d_representation_handles_missing_landmarks():
    rep = build_3d_representation(None)
    assert rep["points"] == []
    assert rep["centroid"] is None
