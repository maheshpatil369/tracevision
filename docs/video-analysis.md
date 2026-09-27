# Video Analysis Pipeline

Implemented in `app/services/analysis_orchestrator.py`, driven by
`app/cv/video_io.py` for I/O. See `docs/architecture.md` for the full
stage diagram.

## Frame extraction

`iter_frames()` reads the video with OpenCV and yields every Nth frame
(`frame_interval`, default 5) as a generator — the whole video is never
loaded into memory at once. Frames are optionally downscaled to
`MAX_PROCESSING_DIMENSION` (default 960px on the long edge) before running
detection/face models, trading a small accuracy cost for significantly
faster CPU inference; this is documented so an analyst can raise it back to
the source resolution for a slower, more thorough pass if needed.

## Timestamps

Timestamp = `frame_index / fps`, using the FPS OpenCV reports for the file
(with a conservative fallback of 25fps if a container misreports 0fps).
This means timestamps are always derived from the actual frame position,
never estimated separately from playback.

## Configurable settings (per analysis, stored on the `Analysis` row)

| Setting | Default | Effect |
|---|---|---|
| `detection_confidence` | 0.4 | Minimum detector confidence to keep a box |
| `iou_threshold` | 0.5 | NMS IoU threshold passed to the detector |
| `frame_interval` | 5 | Process every Nth frame |
| `tracker` | `auto` | `auto` prefers ByteTrack, falls back to the built-in IoU tracker |

## Performance trade-offs

- Larger `frame_interval` = faster processing, coarser timestamps and a
  higher chance of missing a very brief event.
- Smaller `MAX_PROCESSING_DIMENSION` = faster inference, lower detection
  accuracy for small/distant objects.
- CPU-only inference is fully supported (this project was developed and
  verified without a GPU) but is meaningfully slower than a CUDA-enabled
  setup for long videos — see `docs/deployment.md`.
