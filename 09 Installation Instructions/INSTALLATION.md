# Installation instructions

## Release prerequisites and supported systems

Observed baseline: Windows 11 with a Python 3.14.6 web runtime and a separate Python 3.11/TensorFlow 2.15.1 audit runtime. The final supported OS/Python combination is [[SUPPORTED_OS]] / [[RELEASE_RUNTIME]]. Linux/macOS clean installation is not verified. Provide at least the SRS hardware baseline: Core i5/i7-class CPU, 8/16 GB RAM and adequate storage. A browser, Git, Python and internet access for dependency/OCR downloads are needed. GPU use is optional and must be documented if required.

The repository snapshot is under 02 Source Repository. Do not copy an old .venv between computers: interpreter paths are machine-specific. Do not load another person's live SQLite database or uploads into a public evaluator instance.

## Create an isolated environment

From the source repository root, use the release Python version chosen by the team:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH='src;.'
```

The supplied requirements/pyproject are preserved source artifacts. Their complete clean installation and TensorFlow compatibility are not certified; replace them only with the team's tested release lock and record [[CLEAN_INSTALL_LOG]]. Do not interpret successful web-only installation as dual-model readiness. POSIX equivalents are python3 -m venv .venv, source .venv/bin/activate and export PYTHONPATH=src:.

## Database configuration and initialization

The current database path resolves to database/assurex.db beneath the application source root. The baseline has no documented DATABASE_URL environment override. Use a writable directory, back up existing data before migrations and initialize a fresh evaluator instance:

```powershell
python -c "from assurex_claim_engine.db.database import init_db; init_db()"
```

On an empty user table this creates four synthetic accounts: admin@assurex.com/admin123, reviewer@assurex.com/reviewer123, service@assurex.com/service123 and customer@assurex.com/customer123. It does not reset an existing user's password. Replace or disable public demonstration credentials when deploying a non-demo instance.

## Model and policy placement

Place Python artifacts in model/v2/: best_python_model.joblib, preprocessor.joblib and label_encoder.joblib. Place the actual exported GTM keras_model.h5 and labels.txt in GTM Models/. Keep labels in exported order. The loader expects the three SRS classes. policies/ contains category JSON files; config/settings.yaml contains comparison and alert thresholds. The package supplies data/train.csv, val.csv, test.csv and matching data/summary_cards. Reconcile original versus v2 training provenance before retraining or release.

## TensorFlow audit environment

The following separately reproduced environment loads the supplied H5 artifact; it is not a validated unified web environment:

```powershell
py -3.11 -m venv .venv-gtm
.\.venv-gtm\Scripts\python.exe -m pip install tensorflow-cpu==2.15.1 pillow h5py
```

Do not append TensorFlow 2.15.1 to Python 3.14 and assume compatibility. The team must supply [[RELEASE_RUNTIME]] and the tested dependency lock for genuine live dual-model inference. Record /health showing both python_ready and vision_ready true, then test a real claim. A process being alive is not sufficient.

## OCR installation and configuration

The source uses PyMuPDF for embedded PDF text and EasyOCR for scanned images/PDF fallback. Install the application's matching EasyOCR/Torch dependencies; initial OCR use may need a model download. Ensure the OCR cache is writable and test a synthetic image receipt and scanned PDF before an offline demonstration. This implementation does not invoke Tesseract as its primary parser. pdf_render_dpi in config/settings.yaml controls rasterization. Record [[OCR_SETUP_EVIDENCE]] including the cache/model availability and sample extraction.

## Environment and folders

Set SECRET_KEY to a strong locally generated value and keep it outside Git. Set OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and OMP_NUM_THREADS to 1 for the observed CPU configuration. The source also sets these limits. Keep database/ and uploads/ writable. static/, templates/, config/, policies/ and model artifacts must be present. Do not expose uploads through an unauthenticated static file server.

## Start and test

```powershell
python -m uvicorn src.assurex_claim_engine.web.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and inspect /health. Run tests only in an isolated source copy with a fresh database:

```powershell
python -m pytest tests -q
```

Do not use reload mode as a production deployment recipe. Record clean installation, model readiness, OCR, claim submission and test output in [[CLEAN_INSTALL_LOG]].

## Troubleshooting

Interpreter/trampoline not found: recreate the virtual environment on this computer. Missing modules or version conflicts: use the tested release lock, not copied site-packages. H5 load error: confirm runtime, model/label pair and preprocessing; never substitute made-up probabilities. Models_ready false: check python_ready/vision_ready separately and actual model logs. Database locked: inspect concurrent writers and migration state. OCR empty: inspect document quality, model download/cache and embedded text. Unsupported upload: check extension, size and final content validation. Port occupied: identify the owning app and choose another port; do not terminate unknown processes. Missing data/v2: restore the correct versioned corpus instead of relabeling original data to fit a saved model.
