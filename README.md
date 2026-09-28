# AssureX Claim Engine — AI-Powered Warranty Adjudication Platform

[![Aptech Techwiz](https://img.shields.io/badge/Aptech%20Techwiz-NextWave%20AI%20%26%20ML-blue.svg)](https://github.com/Musab-Al-Mustafa/Techwiz)
[![Python 3.11](https://img.shields.io/badge/Python-3.11%20%7C%203.12-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> **Competition / Event:** Aptech Techwiz  
> **Category:** NextWave AI and ML  
> **Theme:** AI-Powered Document Ops  
> **Team Name:** SFC Karachi Coders (Aptech Shahra-e-Faisal Center)  
> **Release Version:** 2.0.0 Enterprise Release  
> **Submission Date:** 29 September 2026  
> **Official Team Repository:** [https://github.com/Musab-Al-Mustafa/Techwiz.git](https://github.com/Musab-Al-Mustafa/Techwiz.git)  
> **Live Technical Blog:** [https://assurexclaimengine.blogspot.com/2026/09/building-assurex-claim-engine.html](https://assurexclaimengine.blogspot.com/2026/09/building-assurex-claim-engine.html)  
> **Demonstration Video:** `13 Demonstration Video/demo_video.mp4` (203.3 MB)

---

## ⚡ Quick Start for Teachers & Evaluators

The application is fully configured and self-contained with a pre-seeded SQLite database.

### One-Click Run (Windows)
Double-click **`run_app.bat`** in the root of this folder.
- Automatically handles background process cleanup on port 8000.
- Boots the Uvicorn FastAPI web server.
- Opens your default web browser automatically at **`http://127.0.0.1:8000`**.

### Manual Command Line (Windows / Linux / macOS)
```bash
# Navigate to the source folder
cd "02 Source Repository"

# Install dependencies (if setting up on a clean machine)
pip install -r requirements.txt

# Run the launcher
python launch.py
```

---

## 🔑 Demo & Evaluation Credentials

Use these pre-configured test accounts to evaluate all role-based flows:

| Role | Email / Username | Password | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@assurex.com` | `admin123` | System analytics dashboard, audit trail, downloadable reports, metric monitoring |
| **Claim Reviewer** | `reviewer@assurex.com` | `reviewer123` | Reviewer Queue adjudication, decision override with required reason logging |
| **Service Center** | `service@assurex.com` | `service123` | Claim intake, receipt OCR verification, warranty check |
| **Customer** | `customer@assurex.com` | `customer123` | Claim submission, product registration, status tracking |

---

## 📂 Deliverables Directory Map (16 Folders per Aptech SRS v1.0)

| Folder | Name | Highlights & Key Files |
| :---: | :--- | :--- |
| **01** | `01 Project Report` | Complete Word document (`AssureX_Project_Report.docx`), Markdown report, architecture diagrams, database dictionary |
| **02** | `02 Source Repository` | Production FastAPI codebase, Jinja2 glassmorphic UI, ML models, DB, tests, `run_app.bat` |
| **03** | `03 Common Dataset` | 1,500 balanced synthetic claim records (CSV), 2,550 visual Claim Summary Cards, data dictionary |
| **04** | `04 Python Model Evidence` | Trained XGBoost model (`best_python_model.joblib`), 91.56% test accuracy, classification metrics |
| **05** | `05 Teachable Machine Evidence` | Exported Google Teachable Machine Keras model (`keras_model.h5`), labels, test predictions |
| **06** | `06 Model Comparison` | 30-claim side-by-side comparison table (`comparison_table.csv`), model agreement & divergence analysis |
| **07** | `07 Warranty Policies` | Configurable JSON rules for Appliances, Electronics, and Automotive; Policy Field Matrix |
| **08** | `08 Test Cases and Results` | Automated pytest results (11 mandatory SRS scenarios passing), smoke test logs |
| **09** | `09 Installation Instructions` | Step-by-step installation manual, environment setup, OCR engine configuration |
| **10** | `10 Execution Instructions` | Complete user manual for intake, OCR verification, review routing, and admin reports |
| **11** | `11 GitHub Repository` | Commit history screenshots from all team members, contribution matrix, repository links |
| **12** | `12 Deployment` | Local launch guide, cloud deployment specs (Docker/PaaS), health check validation |
| **13** | `13 Demonstration Video` | High-definition demonstration video (`demo_video.mp4`, 203.3 MB), 29-scene recording script |
| **14** | `14 Technical Blog` | Published Blogger article link, offline HTML copy (`index.html`), technical article markdown |
| **15** | `15 AI Usage Declaration` | Signed team verification table (Sep 24–29, 2026), AI tools breakdown (50% AI / 50% human) |
| **16** | `16 Final Submission Checklist` | SRS v1.0 reference specification, complete bullet-by-bullet compliance CSV matrix |

---

## 🏗️ System Architecture & Dual-Model AI

AssureX Claim Engine solves warranty adjudication using a multi-stage defense-in-depth pipeline:

1. **Document Ingestion & OCR:** Extracts customer details, purchase dates, and serial numbers with EasyOCR/Tesseract. SHA-256 receipt hashing prevents duplicate claim fraud.
2. **Tabular Machine Learning Model:** An XGBoost classifier trained on 1,500 balanced records predicts claim validity (`Likely Valid`, `Likely Invalid`, `Manual Review`).
3. **Computer Vision Model (Google Teachable Machine):** Generates standardized visual Claim Summary Cards without decision leakage, classified via a Keras Deep Learning CNN (`keras_model.h5`).
4. **Warranty Policy Engine:** JSON-driven rule validation for coverage windows, proof of purchase, authorized repair history, and excluded damages (water, unauthorized modification).
5. **Decision Fusion Engine:** Reconciles model outputs and policy rules:
   - When models agree and policy passes $\rightarrow$ **Auto-Approval Candidate** (`Likely Valid`).
   - When excluded conditions are detected $\rightarrow$ **Auto-Rejection Candidate** (`Likely Invalid`).
   - When models diverge, confidence is low, or documents are missing $\rightarrow$ **Flagged for Human Reviewer** (`Manual Review Required`).

---

## 👥 SFC Karachi Coders Team & Verified Sign-Off

| Name | Role | Responsibilities | Sign-Off Date |
| :--- | :--- | :--- | :--- |
| **Musab-Al-Mustafa** | Team Lead & Full-Stack Architect | Project architecture, UI/UX glassmorphism, tabular ML model, repository management | 29 Sep 2026 |
| **Abdullah Murshid** | Data Engineer & ML Specialist | Dataset generation (1,500 rows), summary card generator, feature engineering | 28 Sep 2026 |
| **Jawad-ul-Bahar** | Integration & Quality Lead | Dual-model comparison fusion, 11 SRS test scenarios, documentation & video script | 27 Sep 2026 |
| **Abdul Rehman** | Backend & Database Engineer | FastAPI routes, SQLite ORM database, OCR pipeline & SHA-256 hash security | 26 Sep 2026 |
| **Umer Tak** | Computer Vision & Teachable Machine | Google Teachable Machine training, Keras H5 export, visual card classification | 25 Sep 2026 |

---

*AssureX Claim Engine — Engineered for Aptech Techwiz 2026 Evaluation.*
