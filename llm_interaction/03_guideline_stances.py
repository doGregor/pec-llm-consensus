from api_requests import *
from utils import *
from tqdm import tqdm
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
        "--pdf-type",
        type=str,
        default="guidelines",
        choices=["guidelines", "white_areas"],
        help="Type of input to process (guidelines or white_areas)"
    )

    return parser.parse_args()


formatting_instructions = """
# Formatting Instructions:
Provide a classification code that can be one out of [R (Recommended); DR (Different Recommendation); NA (Not Addressed)] and a summary that justifies that classification referencing key elements from both the recommendation and the guideline.
""".strip()


def prepare_prompt(treatment_recommendation, guideline):
    prompt = f"""
    # Task:
    You are given two texts:
    * Treatment Recommendation - a proposed approach or method for treating penile cancer.
    * Guideline - an comprehensive clinical guideline on penile cancer treatment.

    Your task is to analyze the stance of the guideline toward the recommendation and classify it using one of the following labels:
    * R (Recommended) - The guideline supports or aligns with the treatment recommendation.
    * DR (Different Recommendation) - The guideline suggests a different treatment or approach compared to the recommendation.
    * NA (Not Addressed) - The guideline does not mention or address the treatment recommendation at all.

    Additionally, provide a concise justification (2–4 sentences) summarizing why you selected that stance, referencing key elements from both the recommendation and the guideline.
    
    
    # Treatment Recommendation:
    {treatment_recommendation}
    
    # Guideline (context):
    {guideline}
    
    
    
    """.strip()
    return prompt


if __name__ == '__main__':
    args = parse_args()

    CONFIG = {
        "model": args.model,
        "thinking_budget": args.thinking_budget,
        "pdf_type": args.pdf_type,
    }

    guideline_names = load_list_of_pdfs(pdf_type='guidelines')

    unique_recommendations_path = f'output/{CONFIG["pdf_type"]}/recommendations/0_unique_recommendation_list_output'
    recommendations = get_table_from_markup(read_markup(unique_recommendations_path))

    consensus_df = load_output_table(recommendations=recommendations,
                                     column_names=guideline_names,
                                     pdf_type=CONFIG['pdf_type'])

    google_client = genai.Client(api_key=load_api_key(model_type='google'))

    for guideline_name in guideline_names:
        guideline_pdf = load_single_pdf(pdf_name=guideline_name,
                                        pdf_type='guidelines',
                                        model='google')
        guideline_text = load_single_markdown(file_name=guideline_name,
                                              file_type='guidelines')

        print(f'[INFO] processing guideline {guideline_name}')
        for recommendation in tqdm(consensus_df['Recommendation'].tolist()):
            row = consensus_df[consensus_df['Recommendation'] == recommendation]
            if pd.isna(row.iloc[0][guideline_name]):

                prompt = prepare_prompt(treatment_recommendation=recommendation,
                                        guideline=guideline_text)

                prompt += '\n\n\n' + formatting_instructions

                res = send_prompt_to_google(client=google_client,
                                            prompt=prompt,
                                            model=CONFIG['model'],
                                            thinking_budget=CONFIG['thinking_budget'],
                                            pdf_files=[guideline_pdf])

                consensus_df.loc[consensus_df['Recommendation'] == recommendation, guideline_name] = res.text.replace('\t', ' ')

                write_output_table(consensus_df)
