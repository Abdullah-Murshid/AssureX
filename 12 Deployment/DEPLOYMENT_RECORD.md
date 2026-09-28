# AssureX Claim Engine - Deployment & Evaluator Guide

> **Release Version:** 2.0.0 Enterprise Release  
> **Team Name:** SFC Karachi Coders  
> **Official Git Repository:** [https://github.com/Musab-Al-Mustafa/Techwiz.git](https://github.com/Musab-Al-Mustafa/Techwiz.git)  
> **Live Technical Blog:** [https://assurexclaimengine.blogspot.com/2026/09/building-assurex-claim-engine.html](https://assurexclaimengine.blogspot.com/2026/09/building-assurex-claim-engine.html)  
> **Demonstration Video:** `13 Demonstration Video/demo_video.mp4` (203.3 MB)

---

## 🚀 Quick Start for Teachers & Evaluators

The application is pre-configured and ready to run out of the box with an already populated SQLite database (`database/assurex.db`) containing seeded products, test warranties, claims, and audit logs.

### Option A: One-Click Execution (Windows)
1. Double-click **`run_app.bat`** located in the root submission directory or inside `02 Source Repository`.
2. The batch script will automatically:
   - Configure thread-safety environment variables (`OMP_NUM_THREADS=1`, `TF_ENABLE_ONEDNN_OPTS=0`).
   - Free port `8000` if occupied.
   - Start the FastAPI / Uvicorn server on `http://127.0.0.1:8000`.
   - Automatically open your default web browser directly to the AssureX Claim Engine portal.

### Option B: Command Line Execution (Any OS)
```bash
# Navigate to the Source Repository directory
cd "02 Source Repository"

# Install requirements (if using a new clean environment)
pip install -r requirements.txt

# Run the launcher (handles port cleanup & launches browser)
python launch.py

# Alternatively, run via uvicorn directly:
python -m uvicorn src.assurex_claim_engine.web.app:app --host 127.0.0.1 --port 8000
```

---

## 🔑 Evaluator Test Accounts & Credentials

The system includes pre-seeded accounts corresponding to the four primary roles required by Aptech SRS v1.0:

| Role | Email / Username | Password | Purpose & Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@assurex.com` | `admin123` | Full administrative analytics dashboard, system audit logs, exportable CSV reports, model metrics. |
| **Claim Reviewer** | `reviewer@assurex.com` | `reviewer123` | Manual Review Queue adjudication, decision override with required reason logging, dossier view. |
| **Service Center** | `service@assurex.com` | `service123` | Authorized repair center claim intake, batch receipt OCR extraction, warranty status check. |
| **Customer** | `customer@assurex.com` | `customer123` | End-user warranty claim filing, product registration, real-time claim status tracking. |

---

## 🌐 Cloud / Production Deployment Architecture

For deployment onto cloud PaaS/IaaS providers (e.g. Render, Railway, AWS EC2, or Azure App Service):

### 1. Docker Deployment
A containerized deployment configuration:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY "02 Source Repository/requirements.txt" .
RUN pip install --no-cache-dir -r requirements.txt

COPY "02 Source Repository" .
EXPOSE 8000

CMD ["uvicorn", "src.assurex_claim_engine.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Environment Variables & Production Hardening
- `PORT`: Port to bind (default `8000`).
- `ASSUREX_ENV`: `production` or `development`.
- `SESSION_SECRET`: Set a cryptographically secure random string in production.
- `SQLITE_DB_PATH`: Path to persistent volume SQLite database or configure PostgreSQL connection URL.
- `ENABLE_HTTPS`: Enforce HTTPS redirect behind reverse proxy (Nginx / Cloudflare).

### 3. Health Check Endpoint
- Health Endpoint: `GET http://127.0.0.1:8000/health`
- Response: `{"status": "healthy", "service": "AssureX Claim Engine", "version": "2.0.0"}`

---

## 📦 Deliverables Mapping for Evaluation

| Deliverable Folder | Contents |
| :--- | :--- |
| **`01 Project Report`** | Complete Word document (`AssureX_Project_Report.docx`), Markdown report, diagrams, database dictionary. |
| **`02 Source Repository`** | Complete runnable FastAPI source code, templates, database, ML models, and `run_app.bat`. |
| **`03 Common Dataset`** | 1,500 balanced claims CSV, 2,550 visual Claim Summary Cards, data dictionary, audit report. |
| **`04 Python Model Evidence`** | Trained XGBoost model (`best_python_model.joblib`), evaluation metrics (91.56% accuracy), test predictions. |
| **`05 Teachable Machine Evidence`** | Google Teachable Machine Keras model (`keras_model.h5`), labels, test predictions, metrics. |
| **`06 Model Comparison`** | 30-claim side-by-side comparison table (`comparison_table.csv`), evaluation runs, confusion analysis. |
| **`07 Warranty Policies`** | Category JSON policies (appliances, electronics, automotive), field matrix, policy documentation. |
| **`08 Test Cases and Results`** | Automated pytest results (11 mandatory SRS scenarios passing), smoke test logs. |
| **`09 Installation Instructions`** | Step-by-step setup guide for virtual environments, dependencies, OCR engine, and database. |
| **`10 Execution Instructions`** | Walkthrough of claim submission, OCR extraction, dual-model comparison, and reviewer override. |
| **`11 GitHub Repository`** | Commit history screenshots from all team members, repository links, contribution matrix. |
| **`12 Deployment`** | Local and cloud deployment instructions, credentials, and health check validation. |
| **`13 Demonstration Video`** | Complete walkthrough video (`demo_video.mp4`, 203.3 MB) and 29-scene coverage script. |
| **`14 Technical Blog`** | Published Blogger article link, HTML version (`index.html`), and full markdown draft. |
| **`15 AI Usage Declaration`** | Signed team verification (Sep 24–29, 2026), AI tool disclosure (50% AI / 50% human effort). |
| **`16 Final Submission Checklist`** | Aptech SRS v1.0 reference, bullet-by-bullet SRS coverage matrix (`SRS_BULLET_COVERAGE.csv`). |
