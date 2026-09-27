# Installation

## Requirements

- Python 3.11+ (3.12 also verified)
- Node.js 20+ and npm
- ~2 GB free disk for model weights + a sample video's worth of evidence frames
- No GPU required. YOLO and MediaPipe both run on CPU (slower, but fully
  functional); CUDA is auto-detected and used by `ultralytics`/`torch` if
  present — nothing in the app hardcodes a GPU requirement.

## 1. Clone and enter the project

```bash
git clone <your-fork-url> tracevision
cd tracevision
```

## 2. Backend setup

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env       # edit if you need non-default paths/ports
python scripts/setup.py            # creates data dirs + runs migrations
python scripts/download_models.py  # downloads YOLO + face landmark models (needs network)
python scripts/health_check.py
cd backend && uvicorn app.main:app --reload
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy .env.example backend\.env
python scripts\setup.py
python scripts\download_models.py
python scripts\health_check.py
cd backend
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The UI is now at `http://localhost:5173` and proxies `/api` and `/media` to
the backend (see `frontend/vite.config.ts`).

## 4. Optional: GPU / CUDA

If you have an NVIDIA GPU and want faster YOLO inference, install a CUDA
build of PyTorch before installing `ultralytics` (see
https://pytorch.org/get-started/locally/ for the exact command for your CUDA
version), then `pip install -r backend/requirements.txt` as normal.
`ultralytics` and MediaPipe both auto-detect and use the GPU when available;
nothing else in the codebase needs to change.

## 5. Docker (alternative to steps 2-3)

```bash
docker compose up --build
```

This builds and runs the backend (port 8000, running migrations on startup)
and a dev-mode frontend (port 5173). See `docker-compose.yml`. Docker is
optional — native installation above is equally supported and is what was
actually exercised during development of this project (see
`PROJECT_COMPLETION_REPORT.md` for exactly what was and wasn't verified in
which environment).

## Troubleshooting

See `docs/troubleshooting.md`.
