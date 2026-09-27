# Object Detection

`app/cv/detector.py` defines the `ObjectDetector` interface with two
implementations, selected automatically by `build_default_detector()`:

## YoloDetector (primary)
Wraps Ultralytics YOLO (default weights: `yolov8n.pt`, configurable via
`YOLO_MODEL`). Returns real bounding boxes, class IDs/names, and confidence
scores exactly as predicted by the model — nothing is post-processed into a
different label.

**Supported classes**: whatever the loaded weights file was trained on. The
default COCO-pretrained YOLOv8n recognizes 80 classes including
`person, car, bus, truck, motorcycle, bicycle, backpack, handbag, suitcase,
cell phone, laptop` (the classes spec section 12 calls out by name) plus 69
others. **The system never claims to identify every possible object** — see
`docs/limitations.md`.

## FallbackMotionDetector (used only when YOLO/weights are unavailable)
OpenCV `MOG2` background subtraction + contour bounding boxes. Every
detection from this backend is tagged `class_name="moving_object"` and
`detector_backend="motion_fallback"` — it never invents a real class label
it didn't actually predict. Confidence is a bounded heuristic proportional
to the relative size of the moving region, explicitly documented as not
comparable to a trained model's probability output.

## Which one ran?

`Analysis.detector_backend` records exactly which backend processed that
run (`yolo` or `motion_fallback`), surfaced in the UI's Overview tab and in
section H of the PDF report — an analyst reviewing results always knows
whether they're looking at real object classification or the reduced-
capability fallback.
