# AI tool usage declaration

Team: SFC Karachi Coders, Aptech Shahra-e-Faisal Branch.

The team estimates the overall project effort as approximately **50% AI-assisted and 50% human work**. This is a team-reported estimate, not a measured code-line percentage. AI assistance does not transfer responsibility for the submission: all five students must understand, review, modify as necessary, and independently test their assigned work before submission.

## Declared tool and purpose

OpenAI ChatGPT / Codex assisted with source inspection, debugging, dependency compatibility, test design and execution, release packaging, synthetic evaluator data, technical explanations, the project report, and HTML blog preparation. Prompts requested merging the team's final project with prior SRS deliverables, updating the five-person contribution plan, preparing judge data, reducing duplicated files, and verifying the application.

Affected files include src/assurex_claim_engine/web/app.py, db/database.py, models/image_classifier.py, models/tabular_model.py, decision/fusion.py, tests/, seed_demo.py, evaluate_release.py, setup and launch scripts, and the submission documentation. The release fixes cover model readiness, real inference failures, password verification, evidence access, review routing and queue status.

The team supplied the final application, model exports, datasets, names, logos and repository reference. The current source was retained as the base. Per-member changes and verification must be recorded from actual student work in TEAM_VERIFICATION.csv; assigned responsibility is not proof that an independent review has already happened.

## Testing and verification

Agent-executed results are recorded in 08 Test Cases and Results, including automated regression checks, genuine model evaluation, and application smoke checks. These results must not be described as student-executed tests. Proposed verification owners are listed in TEAM_CONTRIBUTIONS.md. Each student must complete the corresponding verification row before final sign-off.

The runtime final claim recommendation uses the Python classifier, the exported Google Teachable Machine model, warranty policies and application logic. It does not call an external generative-AI API to decide claims. The provided Aptech and Techwiz logos were supplied by the team; this work did not generate them with AI. Synthetic demo evidence is explicitly marked as synthetic.

If additional AI tools were used earlier, the team must add their names, purposes, affected files, prompt types, modifications, tests and verifying members to this declaration.
