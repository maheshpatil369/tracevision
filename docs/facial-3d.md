# 3D Facial Representation

`app/cv/face_mesh.py:build_3d_representation()` derives a 3D point cloud
directly from the actual detected landmarks — no synthetic points are added
and no generic face template is blended in:

1. Center: subtract the centroid of all 468 points.
2. Scale-normalize: divide by the mean distance of points from the
   (now-zero) centroid, so faces at different distances from the camera
   become comparable.
3. Store: the centered/normalized points, the original centroid, and the
   scale factor (`Face.representation_3d`), so the transform is fully
   reversible/auditable.

This is intentionally a lightweight, transparent transform rather than a
3D Morphable Model (3DMM) fit — spec section 19 requires the representation
be "derived from actual facial landmarks," not that it match a specific
academic 3D face model. `docs/limitations.md` notes this explicitly.

## Frontend

The Faces tab currently shows the 2D face crop and quality metadata; an
interactive 3D point-cloud viewer (e.g. via `three.js`) is a natural next
addition and is flagged as not-yet-built in
`docs/implementation-checklist.md` rather than silently omitted.
