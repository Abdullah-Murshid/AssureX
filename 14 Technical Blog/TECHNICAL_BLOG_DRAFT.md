# Building AssureX Claim Engine with independent models and explicit warranty rules


By Jawad-ul-Bahar, Abdullah Murshid, Umer Tak, Abdul Rehman, Musab-al-Mustafa-Khan  
SFC Karachi Coders | Aptech Shahra-e-Faisal Branch  
Prepared 29 September 2026  
Repository: https://github.com/Musab-Al-Mustafa/Techwiz
Public Blog: https://assurexclaimengine.blogspot.com/2026/09/building-assurex-claim-engine.html

## The warranty decision problem

A warranty claim is a collection of related facts rather than a single classification question. A product has a purchase date, a serial number, an expected coverage period and a reported fault. Its owner may supply an invoice, photographs, a warranty card and repair records. Each document contributes evidence, but the documents can also disagree. A receipt can show a different serial number, a repair can predate the purchase, or a claim can reuse evidence from an earlier submission. A useful application must preserve those distinctions while helping a reviewer understand the case. AssureX explores this problem through a Python web application, two independent classification paths and a configurable policy engine.

## Why a shared workflow is necessary

Customers need to know which evidence is required and what happens after submission. Service-center employees need a consistent way to record repairs. Reviewers need both a recommendation and the evidence behind it, while administrators need visibility into policies and significant actions. These needs motivate a shared workflow rather than isolated prediction scripts. The project does not claim a measured financial saving or reduction in fraud. Its immediate purpose is to make the proposed decision process inspectable: a person should be able to see the submitted information, extracted values, probabilities, rules and later reviewer action. Clear records also make testing easier because an unexpected decision can be traced to a particular input or processing step.

## The proposed solution

AssureX combines a FastAPI backend, Jinja-based pages, SQLite storage, document extraction, a tabular Python model and a separately exported Google Teachable Machine model. Both models receive representations of the same claim facts. The Python model receives structured features. The image model receives a Claim Summary Card generated from those facts. Their predictions are compared, then evaluated alongside warranty rules, missing evidence, contradictions and duplicate indicators. The final recommendation is Likely Valid, Likely Invalid or Manual Review Required. A reviewer may record a different authorized disposition, but that action must not erase the original machine results. This separation makes a recommendation and a human decision independently visible.

## Architecture and module boundaries

The web layer coordinates inputs and results, but several responsibilities live in separate modules. Database declarations describe users, products, claims, documents, repairs and audit records. The OCR parser handles document text and hashes. Derived-feature code calculates intervals and evidence-related fields. Model modules load saved artifacts and return probabilities. Comparison and fusion modules implement distinct parts of the decision process, while JSON policies define category-specific business conditions. These boundaries make a change easier to reason about. Changing a confidence threshold should not require altering a receipt parser. Adding a warranty exclusion should not be confused with retraining a model. The complete project report includes architecture, data-flow, use-case, activity, sequence and decision diagrams.

## Creating a common dataset

The supplied original corpus contains 1,500 synthetic warranty records, balanced across Valid Claim, Invalid Claim and Manual Review. Each class has 500 records. Training, validation and testing contain 1,050, 225 and 225 records respectively, with equal class representation inside each split. The record is the unit of separation: the Claim ID must stay in one split regardless of how many image variants are generated. This matters because the two models consume different formats. A tabular record in the test set cannot have a visual copy in the image training set without undermining the claimed separation. The original supplied ID mapping passed the split-overlap and class-folder checks performed during the audit.

## Dataset challenges and version identity

Counts are only one part of dataset integrity. The project also contains a separate v2 card set. Against the supplied original CSVs, 2,053 of its 2,550 image paths have a conflicting class or split association for the Claim ID. Matching v2 CSVs were not available in the inspected submission. This does not prove every v2 image is intrinsically wrong; it shows that these files cannot be combined with the original CSVs as one verified common corpus. The release package therefore includes the matching original set and records the provenance question explicitly. Final training evidence must identify exact dataset files and hashes. A version name alone does not establish which records trained a saved model.

## Synthetic labels need scrutiny

Synthetic scenarios help create normal, incomplete, contradictory and borderline cases without exposing customer data. They also impose assumptions. If a label is a deterministic function of a few visible fields, a classifier may learn the generator's rules more easily than real-world warranty reasoning. Balanced class totals do not prove that ambiguous records have defensible labels. The team should examine scenario definitions and review examples independently, especially near policy boundaries. It should also distinguish a dataset label from an application disposition. An expired-warranty example may be labeled Invalid Claim for model training, while the application's explicit review policy still requires a person to resolve an adverse rule before a final operational action.

## Preprocessing and feature engineering

The tabular path uses numerical, categorical and binary features. Numerical values include price, warranty duration, previous repairs, missing-document count, product age, remaining coverage and reporting delay. Categories include product type, brand, fault, damage and serial status. Binary indicators describe evidence availability, unauthorized repair, contradiction and duplication. StandardScaler transforms numerical features and OneHotEncoder handles categorical values. The baseline excludes identifiers and the target label from the classifier inputs. A consistent training/live contract is still essential: missing evidence must not silently become present, absent OCR must not become an exact serial match, and invalid dates must not produce invented favorable coverage. Calendar semantics also need an explicit policy because the baseline uses fixed 30-day warranty months.

## Comparing Python algorithms

The supplied v2 training script compares Random Forest, Logistic Regression and XGBoost, satisfying the intended minimum of three suitable candidates when all dependencies are available. Its Random Forest uses 120 trees and a maximum depth of nine. Logistic Regression uses C equal to 0.8 and up to 1,000 iterations. XGBoost uses 90 trees, depth four, a learning rate of 0.07 and row/column sampling of 0.85. The script selects the winner using validation accuracy rather than choosing the best test score. The historical report identifies XGBoost as the winner. Historical training evidence is preserved separately from later audit measurements because the original v2 corpus provenance remains unresolved.

## Cross-validation and evaluation discipline

The supplied historical report contains five-fold cross-validation and validation results. There is an implementation detail worth correcting before final release: the script fits preprocessing on the training partition before performing cross-validation. A stricter workflow places preprocessing inside the cross-validation pipeline so each fold learns transformations only from its own training portion. This observation does not justify rewriting the historical results; it identifies a limitation in their interpretation. Training, validation and test evidence should remain clearly separated. Validation may guide model selection and revisions. Once a model is frozen, test results should measure it rather than become another set of tuning instructions. Final logs must identify the source, dataset, environment and exact exported artifacts.

## Designing Claim Summary Cards

The card is a visual representation of claim facts: product age, coverage, fault category, repair history, evidence status, serial information and relevant dates. It is not a visualization of the Python answer. Including the predicted class, Python confidence or final decision would compromise independence. The original image corpus has two visual variations per training record, giving 2,100 training images, and one card for every validation/test record. Variations can change layout or appearance but must preserve the underlying facts. A filename mapping is necessary, yet insufficient: someone should inspect rendered cards for clipped values and incorrect content. The model sees pixels, so unreadable or cropped text can matter even when the CSV and filename are correct.

## Google Teachable Machine training

A reproducible GTM procedure begins with the three exact class names and only the matched training images. With 350 training claims per class and two variants each, the intended upload is 700 images per class. Validation and test images remain outside training. Genuine evidence should show the classes, image counts, settings, observations and any retraining. Exported H5 and label files must be kept together. The provided artifact loads under the release Python 3.11 environment with TensorFlow 2.15.1 and Keras 2.15. That technical fact does not reveal its original epochs, batch size, learning rate or training corpus. Those fields remain explicit blanks until the real project evidence is supplied.

## Integrating the visual model in Python

The release runs the web application and exported H5 model in one Python 3.11 environment using TensorFlow 2.15.1. The live preprocessing converts a card to RGB, resizes it to 224 by 224 pixels and normalizes values to minus one through one. Output indices use the exported labels file. These details form a prediction contract: changing a resize policy can change measured accuracy, even when the weights are identical. The current evaluation therefore calls the same inference function as the application.

Readiness now checks that both actual model objects loaded. A missing dependency or failed artifact no longer produces an invented probability distribution or a PyTorch result presented as GTM. The health page reports the individual states. Submission waits for initialization and returns a clear readiness error when inference is unavailable. This makes diagnosis easier for evaluators and prevents a successful web page response from being mistaken for a working classifier.

## Comparing predictions and confidence

Each model provides three class probabilities and a top class. The application checks whether the top classes match and calculates the absolute difference between the two top confidences. These are separate questions: equally confident models can disagree, while agreeing models can have a large confidence gap. The baseline configuration uses a minimum confidence of 0.60, a strong-match gap below 0.10 and an acceptable gap up to 0.25. The resulting categories are Strong Match, Acceptable Match, Weak Match, Model Disagreement and Uncertain Result. Exact boundary values deserve tests. An unavailable model has no valid confidence gap; it must not be displayed as perfect agreement through a fabricated zero.

## What the measured results show

The Python model achieved 91.56% and the Teachable Machine model achieved 36.89% on the supplied 225-record test corpus. These are fresh agent-run measurements using the release inference code. Original training provenance is not independently established. The SRS requires at least 85% accuracy for each model.

The package contains every observed probability, class-wise precision, recall and F1, confusion matrices, and representative errors. The 30 paired cases retain structured facts, a corresponding card reference, both predictions, confidence differences, rule outcomes and the final explanation. Results on supplied data are useful reproducibility evidence, but original training logs are still needed to establish which data the artifacts saw. A separate check evaluates the first 30 records using the current application card renderer so rendering differences remain visible. The release does not invent a successful training run or replace a failed target with a historical number.

## Understanding disagreements without inventing causes

The paired comparison report records actual disagreements and the resulting review recommendations. An individual wrong class does not reveal its own causal explanation. Dataset-version differences, training provenance, rendering consistency and model quality all warrant investigation, but a report should not attribute a specific error to one factor without testing that explanation. Reviewers should be able to inspect the structured input, its card, both probability distributions, the policy results and the final routing. The next experiment should use a validation set and a documented hypothesis. Repeatedly adjusting the model to improve the already-inspected test cases would weaken the meaning of a later unseen-test claim unless a new untouched test set were established.

## Warranty-rule design

Warranty conditions are explicit business constraints rather than hidden learned weights. The supplied JSON policies cover electronics, appliances and automotive products, with durations, grace periods, reporting deadlines, fault lists, exclusions, required documents and rule groups. Registered handlers evaluate supported conditions and return descriptions of what passed or failed. Some required policy fields, such as complete start and replacement conditions, still need team definition and implementation. The deliverables package preserves the runtime policies and supplies separate completion templates. Adding an unused JSON key is not the same as implementing its behavior. A policy change needs a test showing that the changed configuration actually affects the intended claim condition.

## Document processing and duplicate checks

The document path extracts embedded PDF text where available and uses OCR for scanned evidence. Extracted values should be displayed for correction because OCR can confuse characters or miss fields. Evidence verification is especially important for dates, invoice numbers, serial numbers and amounts. SHA-256 hashes can identify identical uploaded bytes across documents. They do not establish authenticity, semantic equivalence or anonymization. A cropped or recompressed receipt can have a different hash, so hash checks should not be marketed as complete fraud detection. Claim-level comparison also considers stored serial/invoice details. Broader evidence matching, complete extraction fields and final preparation workflows remain implementation tasks and must be tested on realistic synthetic documents.

## Final decisions and manual review

Fusion must consider models and explicit evidence together. A confident prediction does not erase a missing receipt or contradictory date. In the merged release, adverse rules, warnings, duplicates, contradictions and uncertain model results force manual review. Unavailable required models block submission until readiness is restored. With no review trigger, aligned valid or invalid predictions can support the corresponding recommendation. Reviewers must provide meaningful reasons when approving, rejecting or requesting information. Original model outputs should remain stored, while the review decision is recorded separately with an audit trail. The review queue should reflect current workflow status; otherwise completed cases can remain misleadingly visible as pending. These behaviors are testable independently of whether a model meets its accuracy target.

## Testing the whole system

The current automated regression run reported 35 passed, 12 warnings in 76.69s (0:01:16). The recorded checks cover role restrictions, authentication, evidence actions, PDF extraction, claim reports, thresholds, derived features and scenario routing. They run against a separate SQLite database, protecting the prepared judging records. Additional workflow smoke checks exercise the actual app and both models. All of these are agent-executed results; the five students must still conduct and record their own review.

Judges receive synthetic accounts, a compact database, evidence documents, CSV sample records and eleven mandatory scenario fixtures. Real model outputs are preserved in demo dossiers rather than replaced with desirable answers. Routing fixtures deliberately use controlled probabilities to test specific branches and are labeled accordingly. A complete acceptance review also needs load tests, mobile usability checks and deployed uptime evidence. Passing local tests is valuable but narrower than those operational claims.

## Security and privacy considerations

Protecting evidence requires more than protecting the main dashboard. Uploaded files and generated cards need authenticated ownership checks. Password storage should use salted password hashing rather than a fast unsalted digest. Deployed session secrets should not be published in source. The prepared repository snapshot excludes live databases, uploaded customer evidence, interpreter environments and secret files. Final release review still needs to examine every route, file-content validation, request limits, login behavior and deployment configuration. Synthetic evaluator credentials belong only to a demonstration instance. The team must also choose a retention policy and responsible contact, because keeping a document indefinitely is an operational decision that a hash function or access check does not resolve.

## Difficulties and lessons from the evidence

The inspected project illustrates three practical difficulties. First, a virtual environment copied from another computer can retain an unusable interpreter path. Second, a web server can start while a required model remains unavailable. Third, multiple dataset versions can appear complete individually while their IDs and labels no longer form one common training/evaluation corpus. These observations support a simple release discipline: identify exact versions, verify real dependencies, check model readiness separately from liveness and preserve actual measurement output. They also show why a checklist marked Ready is not enough. Every important claim should point to the file, test, screenshot, run log or public resource that substantiates it.

## Limitations and future work

The merged package now has a shared compatible runtime and current reports, but release acceptance still has meaningful limits. The supplied GTM model must meet the minimum accuracy requirement on a defensibly unseen common corpus; the current measured result and training provenance must be considered together. Authentic project screenshots, settings, retraining records and student verification are not recoverable from an H5 file alone. They need to come from the real development process.

The application also retains fixed 30-day warranty months, limited cross-document contradiction checks and model-version labels without complete historical policy snapshots. Load capacity, five-second complete processing across representative documents, mobile usability and availability require broader measurement. Future work can improve evidence extraction, calibration, versioned decisions, accessibility and similarity checks. The mandatory video and deployment link are reserved for the team, and this local HTML article still needs publication on a free blogging platform.

## Reproducibility and publication details

The canonical local submission is AssureX_Final_Submission. Its source comes from the team's latest project, while the earlier documentation, matched original card corpus and diagrams have been refreshed against that source. Virtual environments, logs, unused model backups and duplicated image sets are excluded from distribution. The original inputs remain separate recovery copies. Model and dataset hashes identify the evaluated files.

The five team members estimate overall effort at 50% AI assistance and 50% human work. Each has an equal proposed share of human responsibility, with specific verification duties recorded separately. This estimate does not imply verified commit authorship. The repository reference is https://github.com/Musab-Al-Mustafa/Techwiz. The team will add the MP4 and deployment URL, publish this HTML article, enter its public URL in the checklist, and complete genuine training and independent verification records before submission.

