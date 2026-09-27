import numpy as np
import pytest

from app.cv.geometry import FaceGeometryEngine, feature_vector_hash, FEATURE_SET_VERSION


def _synthetic_face(n=468, seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pts = rng.normal(loc=0.5, scale=0.15, size=(n, 3))
    pts[:, 2] *= 0.1  # z is typically much smaller than x,y in MediaPipe output
    return pts


def test_euclidean_distances_are_nonnegative_and_symmetric_pairs():
    engine = FaceGeometryEngine()
    pts = _synthetic_face()
    eu = engine.compute_euclidean(pts)
    assert len(eu) == len(engine.DISTANCE_PAIRS)
    assert all(v >= 0 for v in eu.values())


def test_geodesic_distances_are_greater_or_equal_to_euclidean():
    engine = FaceGeometryEngine()
    pts = _synthetic_face()
    eu = engine.compute_euclidean(pts)
    geo = engine.compute_geodesic(pts)
    for key in eu:
        if geo[key] is not None:
            # Shortest path over a graph is never shorter than the straight-line distance.
            assert geo[key] + 1e-6 >= eu[key]


def test_ratios_are_none_when_denominator_missing_and_finite_otherwise():
    engine = FaceGeometryEngine()
    pts = _synthetic_face()
    eu = engine.compute_euclidean(pts)
    ratios = engine.compute_ratios(eu)
    assert "jaw_width_over_face_height" in ratios
    for v in ratios.values():
        assert v is None or np.isfinite(v)


def test_feature_vector_is_deterministic():
    engine = FaceGeometryEngine()
    pts = _synthetic_face(seed=42)
    f1 = engine.build_feature_vector(pts)
    f2 = engine.build_feature_vector(pts)
    assert f1.vector == f2.vector
    assert f1.vector_names == f2.vector_names
    assert f1.version == FEATURE_SET_VERSION
    assert feature_vector_hash(f1.vector) == feature_vector_hash(f2.vector)


def test_feature_vector_differs_for_different_faces():
    engine = FaceGeometryEngine()
    f1 = engine.build_feature_vector(_synthetic_face(seed=1))
    f2 = engine.build_feature_vector(_synthetic_face(seed=2))
    assert f1.vector != f2.vector
