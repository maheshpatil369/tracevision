"""
Facial geometric feature extraction.

Implements the geometry primitives required by the TRACEVISION spec:
  - Euclidean distances between landmark pairs
  - Geodesic distances (shortest path across the facial mesh graph)
  - Landmark ratios (normalized distance ratios, e.g. eye-width / face-width)
  - Deterministic feature vectors for ML classification

This module is pure numpy/scipy and has NO dependency on FastAPI/SQLAlchemy,
so it can be executed and unit-tested standalone (see backend/tests/test_geometry.py).

Determinism: given the same 468x3 landmark array and the same FEATURE_SET_VERSION,
`build_feature_vector` always returns the same vector. No randomness is used.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

FEATURE_SET_VERSION = "geom-v1"

# A landmark "edge set" describing which of MediaPipe's 468 points are directly
# adjacent on the face mesh surface. This is a curated subset of MediaPipe's
# FACEMESH_TESSELATION restricted to stable, well-known anatomical landmarks,
# used to build the graph over which geodesic (surface) distance is computed.
# Full 468-point tessellation edges are loaded at runtime from mediapipe when
# available (see `_load_full_mesh_edges`); this constant is the fallback used
# whenever mediapipe's connection set cannot be imported.
_FALLBACK_EDGES: List[Tuple[int, int]] = [
    (33, 133), (133, 362), (362, 263),           # eye corners across nose bridge
    (61, 291), (61, 0), (291, 17), (0, 17),       # mouth corners <-> nose tip/chin
    (10, 152), (10, 234), (10, 454),              # forehead to jaw/cheeks
    (234, 454), (127, 356), (162, 389),
    (70, 63), (63, 105), (105, 66), (66, 107),    # left brow chain
    (336, 296), (296, 334), (334, 293), (293, 300),  # right brow chain
    (168, 6), (6, 197), (197, 195), (195, 5),     # nose bridge -> tip
    (5, 4), (4, 1), (1, 19), (19, 94),
    (78, 191), (191, 80), (80, 81), (81, 82),     # inner lip
    (13, 14), (14, 87), (87, 178), (178, 88),
]

# Named landmark indices used for ratio computations (MediaPipe FaceMesh convention).
LM = {
    "left_eye_outer": 33, "left_eye_inner": 133,
    "right_eye_inner": 362, "right_eye_outer": 263,
    "left_eye_top": 159, "left_eye_bottom": 145,
    "right_eye_top": 386, "right_eye_bottom": 374,
    "nose_tip": 1, "nose_bottom": 2,
    "mouth_left": 61, "mouth_right": 291,
    "mouth_top": 13, "mouth_bottom": 14,
    "chin": 152, "forehead": 10,
    "jaw_left": 234, "jaw_right": 454,
    "brow_left": 105, "brow_right": 334,
}


def _load_full_mesh_edges() -> List[Tuple[int, int]]:
    """Loads the real 468-point face-mesh tessellation edge list bundled with
    the installed mediapipe package. This works with both the legacy
    `mp.solutions.face_mesh` API (mediapipe < 0.10) and the current Tasks API
    (`mediapipe.tasks.python.vision.FaceLandmarksConnections`, mediapipe >=
    0.10.9) — no model file or network access needed, since these are static
    topology constants, not a downloaded model. Falls back to the curated
    anatomical edge set only if neither API is present."""
    try:
        from mediapipe.tasks.python import vision
        conns = vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION
        return [(int(c.start), int(c.end)) for c in conns]
    except Exception:
        pass
    try:
        import mediapipe as mp
        conns = mp.solutions.face_mesh.FACEMESH_TESSELATION
        return [(int(a), int(b)) for a, b in conns]
    except Exception:
        return _FALLBACK_EDGES


@dataclass
class GeometricFeatures:
    euclidean: Dict[str, float] = field(default_factory=dict)
    geodesic: Dict[str, float] = field(default_factory=dict)
    ratios: Dict[str, float] = field(default_factory=dict)
    vector: List[float] = field(default_factory=list)
    vector_names: List[str] = field(default_factory=list)
    version: str = FEATURE_SET_VERSION

    def to_dict(self) -> dict:
        return {
            "euclidean": self.euclidean,
            "geodesic": self.geodesic,
            "ratios": self.ratios,
            "vector": self.vector,
            "vector_names": self.vector_names,
            "version": self.version,
        }


class FaceGeometryEngine:
    """Computes Euclidean distance, geodesic distance, ratios and a deterministic
    feature vector from a set of 3D facial landmarks (normalized coordinates)."""

    # Fixed pairs used for the standard distance/ratio report. Order matters —
    # changing this list changes FEATURE_SET_VERSION-relevant output and must
    # bump the version string above.
    DISTANCE_PAIRS: List[Tuple[str, str]] = [
        ("left_eye_outer", "right_eye_outer"),   # bi-ocular width
        ("left_eye_inner", "right_eye_inner"),    # inter-canthal width
        ("mouth_left", "mouth_right"),            # mouth width
        ("nose_tip", "chin"),                     # nose-to-chin
        ("forehead", "chin"),                     # face height
        ("jaw_left", "jaw_right"),                # jaw width
        ("left_eye_top", "left_eye_bottom"),      # left eye opening
        ("right_eye_top", "right_eye_bottom"),    # right eye opening
        ("mouth_top", "mouth_bottom"),             # mouth opening
        ("brow_left", "brow_right"),               # inter-brow width
    ]

    RATIO_TRIPLETS: List[Tuple[str, str, str]] = [
        # (numerator_pair_a, numerator_pair_b, denominator_pair) encoded as keys
        # into DISTANCE_PAIRS names, defined explicitly below in compute_ratios.
    ]

    def __init__(self):
        self._edges = _load_full_mesh_edges()

    # ---------------------------------------------------------- distances --
    @staticmethod
    def _dist(p: np.ndarray, q: np.ndarray) -> float:
        return float(np.linalg.norm(p - q))

    def compute_euclidean(self, landmarks: np.ndarray) -> Dict[str, float]:
        """landmarks: (468, 3) array of (x, y, z) normalized coordinates."""
        out = {}
        for a, b in self.DISTANCE_PAIRS:
            ia, ib = LM[a], LM[b]
            out[f"{a}__{b}"] = round(self._dist(landmarks[ia], landmarks[ib]), 6)
        return out

    # ----------------------------------------------------------- geodesic --
    def _build_graph(self, landmarks: np.ndarray) -> csr_matrix:
        n = landmarks.shape[0]
        rows, cols, weights = [], [], []
        for a, b in self._edges:
            if a >= n or b >= n:
                continue
            w = self._dist(landmarks[a], landmarks[b])
            rows += [a, b]
            cols += [b, a]
            weights += [w, w]
        return csr_matrix((weights, (rows, cols)), shape=(n, n))

    def compute_geodesic(self, landmarks: np.ndarray) -> Dict[str, float]:
        """Shortest-path (surface) distance across the mesh graph between the
        same named landmark pairs used for Euclidean distance. Uses Dijkstra
        via scipy.sparse.csgraph, computed only for the source nodes actually
        needed (not a full all-pairs solve)."""
        graph = self._build_graph(landmarks)
        sources = sorted({LM[a] for a, _ in self.DISTANCE_PAIRS} | {LM[b] for _, b in self.DISTANCE_PAIRS})
        dist_matrix = shortest_path(graph, method="D", directed=False, indices=sources)
        index_of = {node: i for i, node in enumerate(sources)}
        out = {}
        for a, b in self.DISTANCE_PAIRS:
            ia, ib = LM[a], LM[b]
            d = dist_matrix[index_of[ia], ib]
            out[f"{a}__{b}"] = None if not np.isfinite(d) else round(float(d), 6)
        return out

    # -------------------------------------------------------------- ratios --
    def compute_ratios(self, euclidean: Dict[str, float]) -> Dict[str, float]:
        def g(a, b):
            v = euclidean.get(f"{a}__{b}")
            return v if v not in (None, 0) else None

        face_h = g("forehead", "chin")
        jaw_w = g("jaw_left", "jaw_right")
        bi_ocular = g("left_eye_outer", "right_eye_outer")
        ratios = {}
        pairs = [
            ("eye_opening_L_over_bi_ocular", g("left_eye_top", "left_eye_bottom"), bi_ocular),
            ("eye_opening_R_over_bi_ocular", g("right_eye_top", "right_eye_bottom"), bi_ocular),
            ("mouth_width_over_bi_ocular", g("mouth_left", "mouth_right"), bi_ocular),
            ("mouth_opening_over_face_height", g("mouth_top", "mouth_bottom"), face_h),
            ("jaw_width_over_face_height", jaw_w, face_h),
            ("nose_to_chin_over_face_height", g("nose_tip", "chin"), face_h),
            ("inter_brow_over_bi_ocular", g("brow_left", "brow_right"), bi_ocular),
            ("face_height_over_jaw_width", face_h, jaw_w),
        ]
        for name, num, den in pairs:
            ratios[name] = round(num / den, 6) if (num is not None and den) else None
        return ratios

    # ---------------------------------------------------------- feature vec --
    def build_feature_vector(self, landmarks: np.ndarray) -> GeometricFeatures:
        euclidean = self.compute_euclidean(landmarks)
        geodesic = self.compute_geodesic(landmarks)
        ratios = self.compute_ratios(euclidean)

        names: List[str] = []
        values: List[float] = []
        for k in sorted(euclidean):
            names.append(f"euclid.{k}")
            values.append(euclidean[k] if euclidean[k] is not None else 0.0)
        for k in sorted(geodesic):
            names.append(f"geodesic.{k}")
            values.append(geodesic[k] if geodesic[k] is not None else 0.0)
        for k in sorted(ratios):
            names.append(f"ratio.{k}")
            values.append(ratios[k] if ratios[k] is not None else 0.0)

        return GeometricFeatures(
            euclidean=euclidean, geodesic=geodesic, ratios=ratios,
            vector=values, vector_names=names, version=FEATURE_SET_VERSION,
        )


def feature_vector_hash(vector: Sequence[float]) -> str:
    """Stable hash of a feature vector, used to detect duplicate/near-duplicate
    faces and for provenance logging (not for security)."""
    payload = json.dumps([round(float(v), 6) for v in vector], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
