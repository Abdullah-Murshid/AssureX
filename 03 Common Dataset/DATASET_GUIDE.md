# Common dataset evidence

This package contains the original 1500-record CSV corpus and its matching original cards. The canonical labels are Valid Claim, Invalid Claim, Manual Review. Training/validation/testing have 1050/225/225 unique records and 2100/225/225 images. Each class has 350/75/75 records. All 2550 original mapping entries agree with the supplied split/class folders, with no cross-split Claim IDs.

structured/ contains split CSVs, the full dataset, supplied dictionary/statistics and claim-to-image mapping. DATA_DICTIONARY.md is the readable dictionary. dataset_generator/ contains original/v2 generators, scenario definitions and renderers. summary_cards/ contains only the matching original image set. The v2 card set had 2053 split/class mismatches against the original CSVs; it is not presented as matching evidence.

Generate records and assign stratified splits before rendering images. Each training claim needs two visual variations without changing facts or class. Never upload validation/testing cards into GTM training. Exclude target label, Python output and final result from card pixels. Claim IDs/actual_class are not model input features. Independently review scenario labels and boundary cases; balanced counts alone do not establish correct labels.

The supplied data is synthetic. Its scenario labels are not independent real-world adjudications. Invalid Claim as a dataset label must be distinguished from mandatory application manual-review routing for adverse rules.

Final dataset version [[FINAL_DATASET_VERSION]]
Training corpus and model provenance [[TRAINING_DATA_PROVENANCE]]
Seed, generation command and complete run log [[DATASET_GENERATION_LOG]]
Independent card-content and label verification [[DATASET_CONTENT_REVIEW]]

Run ../16 Final Submission Checklist/verify_package.py to check frozen IDs, labels, mappings, counts and file integrity. Pixel-level matching still requires visual/content review. Regenerate in a clean working directory, not over the frozen release files.
