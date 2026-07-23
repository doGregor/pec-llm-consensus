# Penile Cancer LLM Consensus Analysis

A LLM-based framework for automated extraction, harmonization, and consensus analysis of treatment recommendations from clinical guidelines and "white area" literature using Large Language Models (LLMs).

## Overview

This framework uses state-of-the-art LLMs to systematically analyze clinical guidelines and white area papers in a case study on penile cancer treatment. The pipeline extracts treatment recommendations, identifies consensus and disagreements across multiple guidelines, and generates comprehensive comparative analyses.

## Experimental Results

The results from applying the framework to penile cancer (clinical guidelines and "white area" literature) can be found in the `study_results/` directory of this repository. For more details, please check out [this README](study_results/README.md).

## Installation

### Prerequisites

- Python 3.10 or higher
- PDF documents of clinical guidelines and/or white area papers

### Setup

1. Clone the repository:
```bash
git clone https://github.com/doGregor/pec-llm-consensus.git
cd pec-llm-consensus
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API keys:

Create API key files in the project root directory:
- `google_api_key.txt` - For Google Gemini models
- `openai_api_key.txt` - For OpenAI models
- `xai_api_key.txt` - For xAI models

Each file should contain only the API key string.

4. Prepare input data:

Place your documents in the appropriate subdirectories:
```
input/
├── guidelines/        # Clinical guideline PDFs
└── white_areas/       # White area paper PDFs
```

## Usage

### Complete Pipeline

Run all steps sequentially for full analysis:

#### Step 0: Document Preparation
```bash
python llm_interaction/prepare_documents.py
```
Extracts text content from PDFs and converts them to Markdown format for LLM processing.

#### Step 1: Recommendation Extraction
```bash
python llm_interaction/01_recommendation_extraction.py \
    --model gemini-2.5-pro \
    --thinking-budget 24576 \
    --num-runs 1 \
    --pdf-type guidelines
```
Extracts treatment recommendations from all guideline documents. For white areas, set `--pdf-type white_areas`.

**Options:**
- `--model`: LLM model to use (default: `gemini-2.5-pro`)
- `--thinking-budget`: Computational thinking budget for the model (default: `24576`)
- `--num-runs`: Number of independent extraction runs (default: `1`)
- `--pdf-type`: Document type to process - `guidelines` or `white_areas` (default: `guidelines`)

#### Step 2: Recommendation Harmonization
```bash
python llm_interaction/02_unify_recommendations.py \
    --model gemini-2.5-pro \
    --thinking-budget 24576 \
    --num-runs 1 \
    --pdf-type guidelines
```
Identifies and merges duplicate or semantically equivalent recommendations while preserving distinct treatment recommendations.

**Options:** Same as Step 1. For white areas, set `--pdf-type white_areas`.

#### Step 3: Guideline Stance Analysis
```bash
python llm_interaction/03_guideline_stances.py \
    --model gemini-2.5-pro \
    --thinking-budget 24576 \
    --pdf-type guidelines
```
Analyzes each guideline's stance towards the unified recommendations, classifying stances as:
- **R (Recommended)**: Guideline supports the recommendation
- **DR (Different Recommendation)**: Guideline suggests alternative approach
- **NA (Not Addressed)**: Recommendation not mentioned in guideline

For white areas, set `--pdf-type white_areas`.

**Options:**
- `--model`: LLM model to use
- `--thinking-budget`: Computational thinking budget
- `--pdf-type`: Input type to analyze

#### Step 4: Panel Verification
```bash
python llm_interaction/04_panel_check.py
```
Runs a validation panel (model ensemble) to verify the stance classifications from Step 3. For white areas, set `--pdf-type white_areas`.

#### (optional) Step 5: Revise Specific Items
```bash
python llm_interaction/05_item_revision.py
```
Revises Items based on human reviewer assessments. This requires a JSON file with the items to be revised and the human reviewer assessments. The output will be a revised set of items including justification.

The JSON file should be structured as follows (placed in the `input/[item-type]` directory, named `items_to_revise.json`):
```json
{
  "items": [
    {
      "item": "Full item 1 text here",
      "reviewer_critique": "Full critique text here"
    },
    {
      "item": "Full item 2 text here",
      "reviewer_critique": "Full critique text here"
    }
  ]
}
```

**Options:**
- `--model`: LLM model to use
- `--thinking-budget`: Computational thinking budget
- `--item-type`: Source of the items (i.e. items to reviser were identified in guideline or white area documents)


### Output

Results are saved in the `output/` directory, organized by document type:
```
output/
├── guidelines/
│   ├── recommendations/     # Extracted and unified recommendations
│   └── output_table/        # Stance classification matrices
└── white_areas/
    ├── recommendations/
    └── output_table/
```

## Project Structure

```
pec-llm-consensus/
├── llm_interaction/           # Core processing modules
│   ├── prepare_documents.py   # PDF to Markdown conversion
│   ├── 01_recommendation_extraction.py
│   ├── 02_unify_recommendations.py
│   ├── 03_guideline_stances.py
│   ├── 04_panel_check.py
│   ├── 05_item_revision.py
│   ├── api_requests.py        # LLM API interaction handlers
│   └── utils.py               # Utility functions
├── input/                     # Input documents
├── output/                    # Generated results
├── requirements.txt           # Python dependencies
└── README.md
```

## Dependencies

See `requirements.txt` for complete list of dependencies.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

Details TBD.


## Contact

For questions or issues, please open an issue on GitHub or contact the maintainer.

---

**Note**: This is a research prototype. Clinical decisions should always be made by qualified healthcare professionals based on complete clinical information and current evidence-based guidelines.
