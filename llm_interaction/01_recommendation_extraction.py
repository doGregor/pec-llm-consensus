from api_requests import *
from utils import *
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Run model configuration")

    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-pro",
        help="Model name to use"
    )

    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=24576,
        help="Thinking budget (omit to disable)"
    )

    parser.add_argument(
        "--num-runs",
        type=int,
        default=1,
        help="Number of runs"
    )

    parser.add_argument(
        "--pdf-type",
        type=str,
        default="guidelines",
        choices=["guidelines", "white_areas"],
        help="Type of input to process (guidelines or white_areas)"
    )

    return parser.parse_args()


def get_formatting_instructions(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    if pdf_type == 'guidelines':
        input_doc = 'guideline'
    else:
        input_doc = 'paper'
    formatting_instructions = f"""
    # Formatting Instructions:
    
    Output Format: Present all findings clearly in a single structured table as follows:
    Aspect of Care, Recommendation
    
    | Aspect of Care              | Recommendation                     |
    | :-------------------------- | :----------------------------------|
    | **Aspect of Care 1**        | **Recommendation 1**               |
    | **Aspect of Care 2**        | **Recommendation 2**               |
    
    Make sure that the table is exhaustive and that all recommendations mentioned in the {input_doc} are listed.
    """.strip()
    return formatting_instructions


def get_task_instructions(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    if pdf_type == 'guidelines':
        input_doc = 'guideline'
    else:
        input_doc = 'paper'
    task_instructions = f"""
    From the provided {input_doc} on penile cancer, identify and extract all explicit treatment recommendations. For each recommendation, ensure the following elements are included and clearly presented:
    
    1. Aspect of Care: Categorize according to the relevant clinical area (e.g., diagnosis, primary treatment, lymph node management, systemic therapy, follow-up care).
    
    2. Specific Clinical Indications:
    
    * Stage-specific details: Clearly specify applicable T-stages (e.g., PeIN, Ta, Tis, T1, T2, etc.) or relevant classification (e.g., grade, invasive vs. non-invasive).
    
    * Grading information: Include tumor grade where mentioned (e.g., G1/G2/G3).
    
    * Anatomical specifics: Clarify the anatomical location (e.g., prepuce, glans, shaft).
    
    3. Treatment Modality with Precise Conditions:
    
    * Include precise treatment modality (e.g., laser therapy, wide local excision, glansectomy) along with qualification clauses (e.g., "if clinically feasible", "if facilities available", "not recommended after failed treatment").
    
    * Indications of treatment limitations: Clearly state any limitations (e.g., "off-label use", "not to be repeated after failure").
    
    4. Additional Clinical Clarifications:
    
    * For recommendations involving lymph node management, explicitly clarify if they refer to palpable or non-palpable nodes.
    
    * For topical therapies or surveillance, specify applicable stages (e.g., PeIN/Tis/Ta), and include any mandatory control assessments (e.g., biopsy after treatment).
    
    * For follow-up, explicitly state if it applies after curative treatment and specify follow-up frequency and duration.
    """
    return task_instructions


def prepare_prompt(guideline_text, pdf_type='guidelines'):
    prompt = f"""
    # Task:
    {get_task_instructions(pdf_type=pdf_type)}
    
    
    
    # Guideline (context):
    
    {guideline_text.strip()}
    """.strip()
    return prompt


if __name__ == '__main__':
    args = parse_args()

    CONFIG = {
        "model": args.model,
        "thinking_budget": args.thinking_budget,
        "num_runs": args.num_runs,
        "pdf_type": args.pdf_type,
    }

    google_client = genai.Client(api_key=load_api_key(model_type='google'))

    for i in range(CONFIG['num_runs']):

        list_of_processed_pdfs = load_list_of_processed_pdfs(pdf_type=CONFIG['pdf_type'])
        list_of_pdfs = load_list_of_pdfs(pdf_type=CONFIG['pdf_type'])

        for pdf_name in list_of_pdfs:
            if pdf_name in list_of_processed_pdfs:
                print(f'[INFO] skipping already processed PDF: {pdf_name}')
                continue

            log_name = f'{CONFIG["pdf_type"]}/recommendations/{i}_{pdf_name}'

            print(pdf_name)
            pdf_file = load_single_pdf(pdf_name=pdf_name,
                                       pdf_type=CONFIG['pdf_type'])

            guideline_text = load_single_markdown(file_name=pdf_name,
                                                  file_type=CONFIG['pdf_type'])

            prompt = prepare_prompt(guideline_text=guideline_text,
                                    pdf_type=CONFIG['pdf_type'])

            prompt += '\n\n\n' + get_formatting_instructions(pdf_type=CONFIG['pdf_type'])
            print(prompt)

            res = send_prompt_to_google(client=google_client,
                                        prompt=prompt,
                                        model=CONFIG['model'],
                                        thinking_budget=CONFIG['thinking_budget'],
                                        pdf_files=[pdf_file])

            log_text(text=prompt,
                     log_name=log_name,
                     text_type='prompt')

            print(res.text)

            log_text(text=res.text,
                     log_name=log_name,
                     text_type='output')

            thought = ''
            for c in res.candidates:
                thought += ' '.join([part.text for part in c.content.parts if part.thought])
            out_text = ''
            for c in res.candidates:
                out_text += ' '.join([part.text for part in c.content.parts])
            log_text(text=f'{CONFIG["model"]}\n\n\n{res.usage_metadata}\n\n\n{thought}\n\n\n{out_text}',
                     log_name=log_name,
                     text_type='metadata')
