# Results Folder Structure

This folder contains the results of experiments, grouped into two parts:

1. **Guideline-based**
2. **White Area–based**

Accordingly, all outputs are organized into two parallel directory structures.

---

## Overview

```
run_outputs/
├── guidelines/
│   ├── (outputs for guideline-based experiments)
└── white_areas/
    ├── (outputs for White Area–based experiments)
```

Both branches follow the same structure and logic. The only difference lies in the type of source documents processed (clinical guidelines vs. research papers).

---

## Output Data

### Guideline-Based
```
run_outputs/guidelines/
```

This directory contains all intermediate and final outputs related to the guideline-based runs.

---

### 01 – Recommendations per Guideline
```
run_outputs/guidelines/01_recommendations_per_guideline/
```

This folder contains the results of **Step 1**, where all treatment recommendations were extracted from each individual guideline.

For **each guideline**, three files are stored:

1. **Prompt**  
   Example:`0_AUA2020_1762959182_prompt.txt`

    The complete prompt sent to the language model to extract treatment recommendations.

2. **Output Table**  
Example:`0_AUA2020_1762959182_output.md`

   A Markdown table containing all identified treatment recommendations from the guideline, structured into the columns:
   - `Aspect of Care`
   - `Recommendation`

3. **Metadata**  
Example:`0_AUA2020_1762959182_metadata.txt`

    Includes:
   - Number of tokens processed by the LLM
   - Reasoning traces (internal model reasoning)
   - The final model output (duplicated for traceability)

---

### 02 – Unified Recommendations
```
run_outputs/guidelines/02_unified_recommendations/
```

This folder contains the **aggregated and harmonized** treatment recommendations across all processed guidelines.

Workflow:
- All individual recommendation tables from Step 1 were provided to the LLM
- Recommendations were deduplicated and unified

Files are again divided into:

1. **Prompt** – adapted to the unification task  
2. **Output Table** – a single, final Markdown table containing all recommendations  
   - Additional column: `Sources`, indicating which guidelines contributed to each recommendation
3. **Metadata** – analogous to Step 1

---

### 03 – Final Output Tables (Consensus Analysis)
```
run_outputs/guidelines/03_output_table/
```

This folder contains the **final result tables** produced via a three-step process:

#### (1) Extraction of Guideline Positions

- Prompt template: `prompt_guidelines_consensus_table.txt`

- Output: `guideliens_consensus_table.tsv`


This step extracts each guideline's position on each unified treatment recommendation.

---

#### (2) Assessment by Model Panel

- Prompt template: `prompt_guidelines_consensus_table_assessment.txt`


The output of this step is incorporated into the correction step below.

---

#### (3) Correction and Finalization

- Prompt template: `prompt_guidelines_consensus_table_correction.txt`


Generated files:

- **Final consensus table** `guidelines_consensus_table_panel.tsv`

    Based on `guideliens_consensus_table.tsv`, but with corrected entries where necessary.

- **Progress log** `guidelines_consensus_table_panel_progress.tsv`

    Tracks model progress during processing (not relevant for analysis).

- **Detailed correction log** `guidelines_consensus_table_panel_log.jsonl`

    Contains detailed, per-cell explanations from the model panel, documenting how and why corrections were applied. This file provides transparency from the initial extraction to the final corrected consensus table.

---

## White Area–Based
```
run_outputs/white_areas/
```

The **structure and content are identical** to the guideline-based folders described above.

### Key Difference

- Instead of guideline PDFs, **research papers** are processed.
- In `white_areas/01_recommendations_per_paper/` there are significantly more files, as the extraction process was performed for **each paper identified in the literature review (n = 75)**.

---

## Notes

- Markdown (`.md`) files are used for human-readable tables.
- TSV files (`.tsv`) represent structured data suitable for downstream analysis and large output files.
- Metadata and log files ensure reproducibility and transparency of all LLM-based processing steps.