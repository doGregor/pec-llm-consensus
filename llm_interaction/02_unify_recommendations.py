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
        input_doc = 'Source'
    else:
        input_doc = 'Paper'
    formatting_instructions = f"""
    # Formatting Instructions:
    
    Output Format: Present findings clearly in a structured table as follows:
    Aspect of Care, Recommendation, {input_doc}s
    
    | Aspect of Care              | Recommendation                     | {input_doc}s                          |
    | :-------------------------- | :----------------------------------| :-------------------------------|
    | **Aspect of Care 1**        | **Recommendation 1**               | {input_doc}1; {input_doc}2; {input_doc}3          |
    | **Aspect of Care 2**        | **Recommendation 2**               | {input_doc}1; {input_doc}2                  |
    
    
    Make sure that all unique recommendations mentioned are listed.
    """.strip()
    return formatting_instructions


def get_task_instructions(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    if pdf_type == 'guidelines':
        input_doc = 'Source'
    else:
        input_doc = 'Paper'
    task_instructions = f"""
    You are given a list of treatment recommendations for penile cancer. Your task is to identify and remove duplicates — that is, recommendations that convey the same clinical advice or intent, even if worded differently.
    However, do not merge or group recommendations that represent distinct treatments, approaches, or clinical decisions, even if they appear under a shared heading or are closely related.
    
    If multiple options are listed under a broader category (e.g., organ-sparing surgery), treat each bullet or treatment modality as a potentially distinct recommendation unless two entries are clearly semantically equivalent.
    
    When removing duplicates, always retain the most comprehensive, specific, or medically precise version. But do not combine multiple unique recommendations into a single, summarized entry.
    
    When in doubt, err on the side of treating treatments as separate unless they are clearly interchangeable.
    
    
    When duplicates are merged, list all the {input_doc}s that provided this unified recommendation in the "{input_doc}s" column.
    
    If a recommendation is unique (not merged), the "{input_doc}s" column should list only the {input_doc}(s) where it appeared.
    
    If multiple recommendations are merged, the "{input_doc}s" column should contain all relevant {input_doc}s, separated by semicolons.
    """
    return task_instructions


def prepare_prompt(recommendations_markup, pdf_type='guidelines'):
    prompt = f"""
    # Task:
    {get_task_instructions(pdf_type=pdf_type)}
    
    
    # List of Treatment Recommendations:
    {recommendations_markup}
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

    if CONFIG["pdf_type"] == 'guidelines':
        input_doc = 'Source'
    else:
        input_doc = 'Paper'

    google_client = genai.Client(api_key=load_api_key(model_type='google'))

    for i in range(CONFIG['num_runs']):

        log_name = f'{CONFIG["pdf_type"]}/recommendations/{i}_unique_recommendation_list'

        list_of_processed_pdfs = load_list_of_processed_pdfs(pdf_type=CONFIG['pdf_type'])
        pdf_recommendations_list = []

        for pdf_name in list_of_processed_pdfs:
            file_sub_path = f'output/{CONFIG["pdf_type"]}/recommendations/{i}_{pdf_name}_output'
            try:
                extracted_paper_recommendations = read_markup(file_sub_path)
                extracted_paper_recommendations = get_table_from_markup(extracted_paper_recommendations)
                extracted_paper_recommendations.insert(0, input_doc, pdf_name)
                pdf_recommendations_list.append(extracted_paper_recommendations)
            except:
                print(f'[INFO] no recommendations for {pdf_name}')

        pdf_recommendations_list = pd.concat(pdf_recommendations_list)
        pdf_recommendations_list = pdf_recommendations_list.to_markdown(index=False)

        prompt = prepare_prompt(recommendations_markup=pdf_recommendations_list,
                                pdf_type=CONFIG['pdf_type'])
        prompt += '\n\n\n' + get_formatting_instructions(pdf_type=CONFIG['pdf_type'])
        print(prompt)

        res = send_prompt_to_google(client=google_client,
                                    prompt=prompt,
                                    model=CONFIG['model'],
                                    thinking_budget=CONFIG['thinking_budget'])

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
