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
        "--item-type",
        type=str,
        default="guidelines",
        choices=["guidelines", "white_areas"],
        help="Source docs of the items to revise"
    )

    return parser.parse_args()



def build_revision_prompt(candidate_item_to_revise, aspect_of_care, source_doc, stance_matrix, reviewer_critique):
    revision_prompt = f"""

    You are given an extracted treatment recommendation from a clinical guideline or research paper that has been identified as requiring human review before inclusion in a Delphi process.

    Your task is to revise the wording of the extracted recommendation according to the human reviewer's critique while remaining faithful to the source document from which the recommendation was extracted.

    # Inputs

    ## Original recommendation

    {candidate_item_to_revise}

    ## Aspect of Care

    {aspect_of_care}

    ## Source Document

    {source_doc}

    ## Guideline stances

    The list below shows how different clinical guidelines evaluate this recommendation.

    {stance_matrix}

    This information is provided only as context to explain why this recommendation was selected for review. Do not modify the recommendation simply to increase agreement across guidelines. The revised recommendation must remain faithful to the source guideline above.

    ## Human reviewer critique

    {reviewer_critique}


    # Task

    Revise the original recommendation by addressing the reviewer's critique.

    When revising:

    * Use the source document as the authoritative source.
    * Preserve the original clinical intent unless the reviewer identifies that the extracted recommendation does not accurately represent the source document.
    * Do not introduce information that is not supported by the source document.
    * Make the recommendation as clear, specific, and self-contained as possible.
    * Preserve clinically relevant qualifiers whenever they are supported by the source document, including patient population, disease stage, treatment setting, timing, line of therapy, exceptions, contraindications, and recommendation strength.
    * Do not rewrite the recommendation to better match other guideline stances.
    * If the reviewer requests a change that is not supported by the source document, explain this and retain a recommendation that faithfully reflects the source document.


    # Output

    Return only the following JSON object.

    {{
      "revised_recommendation": "<revised recommendation>",
      "rationale": "<brief explanation of how the reviewer critique was addressed and why the revision reflects the source document>",
      "meaning_changed": true | false,
      "reviewer_request_supported_by_document": true | false
    }}

    Where:

    * revised_recommendation is the revised recommendation.
    * rationale briefly explains the revision (1–3 sentences).
    * meaning_changed is true only if the clinical meaning of the recommendation had to be changed to better reflect the source document; otherwise false.
    * reviewer_request_supported_by_document indicates whether the requested revision was supported by the source document.

    Do not include any text outside the JSON object.
    """
    return revision_prompt


if __name__ == '__main__':
    args = parse_args()

    CONFIG = {
        "model": args.model,
        "thinking_budget": args.thinking_budget,
        "item_type": args.item_type,
    }

    google_client = genai.Client(api_key=load_api_key(model_type='google'))

    items_to_revise = load_items_to_revise(item_type=CONFIG['item_type'])
    guideline_documents = load_list_of_pdfs(pdf_type='guidelines')
    consensus_df = load_panel_table(pdf_type=CONFIG['item_type'])

    for idx, item in enumerate(items_to_revise):
        candidate_item = item['item']
        reviewer_critique = item['reviewer_critique']

        item_stance_matrix_context = consensus_df[consensus_df['Recommendation'] == candidate_item]

        aspect_of_care = item_stance_matrix_context['Aspect of Care'].values[0]
        source_document = item_stance_matrix_context['Sources'].values[0].split(', ')[0]

        guideline_stances = []
        for guideline in guideline_documents:
            guideline_stance = item_stance_matrix_context[guideline].values[0]
            if '--------------------' in guideline_stance:
                guideline_stance = guideline_stance.split('------------------')[0]
            guideline_stances.append(guideline + ':\n' + guideline_stance + '\n')
        guideline_stances = '\n'.join(guideline_stances)

        pdf_file_google = load_single_pdf(pdf_name=source_document,
                                          pdf_type=CONFIG['item_type'],
                                          model='google')

        prompt = build_revision_prompt(
            candidate_item_to_revise=candidate_item,
            aspect_of_care=aspect_of_care,
            source_doc=source_document,
            stance_matrix=guideline_stances,
            reviewer_critique=reviewer_critique
        )

        res = send_prompt_to_google(
            client=google_client,
            prompt=prompt,
            model=CONFIG['model'],
            thinking_budget=CONFIG['thinking_budget'],
            pdf_files=[pdf_file_google],
        )

        log_text(text=prompt,
                 log_name=f'item_revision_{CONFIG["item_type"]}_{idx}',
                 text_type='prompt')

        print(res.text)

        log_revised_item(
            revised_item=res.text.strip(),
            item_name=idx,
            item_type=CONFIG['item_type']
        )
