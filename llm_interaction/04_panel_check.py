from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_requests import *
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-model configuration")

    parser.add_argument(
        "--google-model",
        type=str,
        default="gemini-2.5-pro",
        help="Google (Gemini) model name"
    )

    parser.add_argument(
        "--openai-model",
        type=str,
        default="gpt-5.1",
        help="OpenAI model name"
    )

    parser.add_argument(
        "--xai-model",
        type=str,
        default="grok-4",
        help="xAI model name"
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for LLM calls"
    )

    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=24576,
        help="Thinking budget for Google models"
    )

    parser.add_argument(
        "--gpt-reasoning-effort",
        type=str,
        default="high",
        choices=["low", "medium", "high"],
        help="Reasoning effort level for GPT models"
    )

    parser.add_argument(
        "--pdf-type",
        type=str,
        default="guidelines",
        choices=["guidelines", "white_areas"],
        help="Type of PDF to generate"
    )

    return parser.parse_args()


formatting_instructions = """
# Formatting Instructions:
Output in JSON format with keys: "error" (True/False) and "suggestion" (description on how to fix the error if error=True, otherwise empty if error=False)
""".strip()


def setup_prompt_for_panel(recommendation, guideline_snippet, guideline):
    prompt = f"""
    # Task:
    You are given the following three components:
    * Guideline - a comprehensive clinical guideline on penile cancer treatment.
    * Treatment Recommendation - a proposed approach or method for treating penile cancer.
    * Extracted Stance - a previously determined stance that classifies the guideline's position toward the recommendation. This stance is one of the following: Recommended, Different Recommendation, or Not Addressed. As well as a concise justification.
    
    Your task is to evaluate whether the extracted stance accurately reflects the guideline's position on the treatment recommendation. Is the extracted justification correct and supported by the given context or does it contain any errors?
    
    
    # Treatment Recommendation:
    {recommendation}
    
    
    # Extracted Stance
    {guideline_snippet}
    
    
    # Guideline (context):
    {guideline}
    """
    return prompt.strip()


def process_guideline(guideline_name, consensus_df, consensus_check_progress, CONFIG):
    pdf_file_google = load_single_pdf(pdf_name=guideline_name,
                                      pdf_type='guidelines',
                                      model='google')
    pdf_file_openai = load_single_pdf(pdf_name=guideline_name,
                                      pdf_type='guidelines',
                                      model='openai')
    pdf_file_xai = load_single_pdf(pdf_name=guideline_name,
                                   pdf_type='guidelines',
                                   model='xai')
    guideline_text = load_single_markdown(file_name=guideline_name,
                                          file_type='guidelines')

    google_client = genai.Client(api_key=load_api_key(model_type='google'))
    openai_client = OpenAI(api_key=load_api_key(model_type='openai'))
    xai_client = Client(api_key=load_api_key(model_type='xai'))
    xai_uploaded_file = xai_client.files.upload(pdf_file_xai, filename=f"{guideline_name}.pdf")

    print(f'[INFO] Processing guideline {guideline_name}')
    for recommendation in tqdm(consensus_df['Recommendation'].tolist(), desc=guideline_name):
        panel_log = {'guideline': guideline_name}

        progress_tracking = consensus_check_progress.loc[consensus_check_progress['Recommendation'] == recommendation, guideline_name].tolist()[0]
        if str(progress_tracking) == '1':
            continue

        panel_log['recommendation'] = recommendation
        guideline_snippet = consensus_df.loc[consensus_df['Recommendation'] == recommendation, guideline_name].tolist()[0]
        panel_log['guideline_snippet'] = guideline_snippet

        prompt = setup_prompt_for_panel(
            recommendation=recommendation,
            guideline=guideline_text,
            guideline_snippet=guideline_snippet
        )
        prompt += '\n\n\n' + formatting_instructions

        assessments = []
        suggestions = []

        # Google API call
        gemini_judge = send_prompt_to_google(
            client=google_client,
            prompt=prompt,
            model=CONFIG['google_model'],
            pdf_files=[pdf_file_google],
            panel_mode=True
        )
        gemini_judge_reply = parse_panel_decision(gemini_judge, model_type='google')

        if gemini_judge_reply is not None:
            assessments.append(gemini_judge_reply[0])
            suggestions.append(gemini_judge_reply[1])
        else:
            assessments.append(False)
            suggestions.append('')

        # OpenAI API call
        openai_judge = send_prompt_to_openai(
            client=openai_client,
            prompt=prompt,
            model=CONFIG['openai_model'],
            pdf_file=pdf_file_openai,
            panel_mode=True,
            pdf_file_name=guideline_name,
            reasoning_effort=CONFIG['gpt_reasoning_effort']
        )
        openai_judge_reply = parse_panel_decision(openai_judge, model_type='openai')

        if openai_judge_reply is not None:
            assessments.append(openai_judge_reply[0])
            suggestions.append(openai_judge_reply[1])
        else:
            assessments.append(False)
            suggestions.append('')

        # XAI API call
        xai_judge = send_prompt_to_xai(
            client=xai_client,
            prompt=prompt,
            model=CONFIG['xai_model'],
            uploaded_file=xai_uploaded_file
        )
        xai_judge_reply = parse_panel_decision(xai_judge, model_type='xai')

        if xai_judge_reply is not None:
            assessments.append(xai_judge_reply[0])
            suggestions.append(xai_judge_reply[1])
        else:
            assessments.append(False)
            suggestions.append('')

        panel_log['assessments'] = f'{assessments}'
        panel_log['suggestions'] = f'{suggestions}'

        if sum(assessments) >= 2:
            print('ERROR, need to correct this field')
            suggestions = '\n\n'.join([s for s in suggestions if len(s) > 0])

            correction_prompt = f"""
            # Task
            You are given the following components:
            * Guideline - a comprehensive clinical guideline on penile cancer treatment.
            * Treatment Recommendation - a proposed approach or method for treating penile cancer.
            * Extracted Stance - a previously determined stance that classifies the guideline's position toward the recommendation. This stance is one of the following: Recommended, Different Recommendation, or Not Addressed. As well as a concise justification.
            * Correction Suggestions – an evaluative assessment of the guideline's position on the recommended treatment.

            Based on the suggestions on correction, formulate a corrected version of the guideline's stance on the recommended treatment.

            # Treatment Recommendation:
            {recommendation}


            # Extracted Stance
            {guideline_snippet}


            # Guideline (context):
            {guideline_text}


            # Correction Suggestions
            {suggestions}


            # Formatting Instructions:
            Provide an updated classification code that can be one out of [R (Recommended); DR (Different Recommendation); NA (Not Addressed)] and an updated summary that justifies that classification referencing key elements from both the recommendation and the guideline.
            """.strip()

            if assessments[0]:
                res = send_prompt_to_google(
                    client=google_client,
                    prompt=correction_prompt,
                    model=CONFIG['google_model'],
                    thinking_budget=CONFIG['thinking_budget'],
                    pdf_files=[pdf_file_google]
                )
                updated_text = res.text.replace('\t', ' ')
            elif assessments[1]:
                res = send_prompt_to_openai(
                    client=openai_client,
                    prompt=correction_prompt,
                    model=CONFIG['openai_model'],
                    pdf_file=pdf_file_openai,
                    pdf_file_name=guideline_name,
                    reasoning_effort=CONFIG['gpt_reasoning_effort']
                )
                updated_text = res.replace('\t', ' ')
        else:
            print('no error, proceed')
            updated_text = ''

        if len(updated_text) > 0:
            consensus_df.loc[consensus_df['Recommendation'] == recommendation, guideline_name] = updated_text + '\n' + 20*'-' + '\n' + guideline_snippet
            write_panel_table(consensus_df, pdf_type=CONFIG['pdf_type'])
            panel_log['updated_text'] = updated_text

        consensus_check_progress.loc[consensus_check_progress['Recommendation'] == recommendation, guideline_name] = 1
        write_panel_progress_table(consensus_check_progress, pdf_type=CONFIG['pdf_type'])
        log_panel_information(panel_log, pdf_type=CONFIG['pdf_type'])


if __name__ == '__main__':
    args = parse_args()

    CONFIG = {
        "google_model": args.google_model,
        "openai_model": args.openai_model,
        "xai_model": args.xai_model,
        "max_retries": args.max_retries,
        "thinking_budget": args.thinking_budget,
        "gpt_reasoning_effort": args.gpt_reasoning_effort,
        "pdf_type": args.pdf_type,
    }

    consensus_df = load_panel_table(pdf_type=CONFIG['pdf_type'])
    consensus_check_progress = load_panel_progress_table(pdf_type=CONFIG['pdf_type'])

    guidelines = load_list_of_pdfs(pdf_type='guidelines')

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(process_guideline, guideline_name, consensus_df, consensus_check_progress, CONFIG): guideline_name
            for guideline_name in guidelines
        }

        for future in as_completed(futures):
            guideline_name = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f'[ERROR] Guideline {guideline_name} failed: {str(e)}')

    write_panel_table(consensus_df,
                      pdf_type=CONFIG['pdf_type'])
