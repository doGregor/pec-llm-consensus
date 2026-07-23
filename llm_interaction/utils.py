import os
import re
import io
import ast
import pathlib
import json
import pandas as pd
import numpy as np
import base64
from pydantic import BaseModel


def get_root_folder_path():
    path = os.getcwd()
    path_clean = []
    for x in path.split('/'):
        if x != 'pec-llm-consensus':
            path_clean.append(x)
        else:
            path_clean.append(x)
            break
    return '/'.join(path_clean)


def load_api_key(model_type='google'):
    assert model_type in ['google', 'openai', 'anthropic', 'xai']
    path_to_key = f'{get_root_folder_path()}/{model_type}_api_key.txt'
    with open(path_to_key, 'r') as key_file:
        key = key_file.read()
    return key.strip()


def log_text(text, log_name, text_type='prompt'):
    assert text_type in ['prompt', 'output', 'metadata']
    path_to_folder = f'{get_root_folder_path()}/output/'
    if not os.path.exists(path_to_folder):
        os.makedirs(path_to_folder)
    if text_type in ['prompt', 'metadata']:
        with open(f'{path_to_folder}/{log_name}_{text_type}.txt', 'w') as outfile:
            outfile.write(text)
    else:
        with open(f'{path_to_folder}/{log_name}_{text_type}.md', 'w') as outfile:
            outfile.write(text)


def load_single_pdf(pdf_name, pdf_type='guidelines', model='google'):
    assert model in ['google', 'openai', 'anthropic', 'xai']
    path_name = f'{get_root_folder_path()}/input/{pdf_type}/{pdf_name}.pdf'
    if model == 'google':
        pdf_data = pathlib.Path(path_name).read_bytes()
    elif model == 'openai':
        with open(path_name, 'rb') as f:
            pdf_data = base64.b64encode(f.read()).decode("utf-8")
    elif model == 'xai':
        pdf_data = open(path_name, "rb")
    else:
        with open(path_name, 'rb') as f:
            pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
    return pdf_data


def load_single_markdown(file_name, file_type='guidelines'):
    with open(f"{get_root_folder_path()}/input/{file_type}/{file_name}.md", "r") as f:
        markup_content = f.read()
    return markup_content


def read_markup(file_sub_path):
    with open(f"{get_root_folder_path()}/{file_sub_path}.md", "r") as f:
        markup_content = f.read()
    return markup_content


def get_table_from_markup(markup_text):
    lines = markup_text.splitlines()
    table_lines = []
    capture = False
    for line in lines:
        if '|' in line:
            table_lines.append(line)
            capture = True
        elif capture:
            break
    table_lines = [line for line in table_lines if not re.fullmatch(r'\s*\|?[-:\s|]+\|?\s*', line)]
    table_str = '\n'.join(table_lines)
    df = pd.read_csv(io.StringIO(table_str), sep='|').dropna(axis=1, how='all')
    df.columns = df.columns.str.strip()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df


class PanelDecision(BaseModel):
    error: bool
    suggestion: str


def parse_panel_decision(panel_decision, model_type='google'):
    assert model_type in ['google', 'openai', 'xai']
    panel_decision_log = panel_decision
    try:
        if model_type in ['google']:
            return bool(panel_decision.error), panel_decision.suggestion
        else:
            panel_decision = re.search(r'\{.*?\}', panel_decision, re.DOTALL).group(0)
            panel_decision = panel_decision.replace('false', 'False')
            panel_decision = panel_decision.replace('true', 'True')
            panel_decision = ast.literal_eval(panel_decision)
            return bool(panel_decision["error"]), panel_decision["suggestion"]
    except:
        print(f'[INFO] Parsing Error for {model_type} model given this reply: {panel_decision_log}')
        return None


def load_output_table(recommendations, column_names, pdf_type='guidelines'):
    path_to_folder = f'{get_root_folder_path()}/output/{pdf_type}/output_table/'
    if not os.path.exists(path_to_folder):
        os.makedirs(path_to_folder)
    path_to_table = path_to_folder + 'consensus_table.tsv'
    if os.path.isfile(path_to_table):
        return pd.read_csv(path_to_table, sep='\t')
    else:
        for col in column_names:
            recommendations[col] = np.nan
        return recommendations


def load_panel_table(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table_panel.tsv'
    if os.path.isfile(path_to_table):
        return pd.read_csv(path_to_table, sep='\t')
    else:
        path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table.tsv'
        return pd.read_csv(path_to_table, sep='\t')


def write_output_table(table_df, pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table.tsv'
    table_df.to_csv(path_to_table, sep='\t', index=False)


def write_panel_table(table_df, pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table_panel.tsv'
    table_df.to_csv(path_to_table, sep='\t', index=False)


def load_panel_progress_table(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table_panel_progress.tsv'
    if os.path.isfile(path_to_table):
        return pd.read_csv(path_to_table, sep='\t')
    else:
        path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table.tsv'
        progress_log = pd.read_csv(path_to_table, sep='\t')
        columns_to_zero = [col for col in progress_log.columns if col not in ['Aspect of Care', 'Recommendation', 'Sources', 'Papers']]
        progress_log[columns_to_zero] = 0
        return progress_log


def write_panel_progress_table(table_df, pdf_type='guidelines'):
    path_to_table = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table_panel_progress.tsv'
    table_df.to_csv(path_to_table, sep='\t', index=False)


def log_panel_information(log_data, pdf_type='guidelines'):
    path_to_log = f'{get_root_folder_path()}/output/{pdf_type}/output_table/consensus_table_panel_log.jsonl'
    with open(path_to_log, 'a') as out_file:
        out_file.write(json.dumps(log_data) + '\n')


def load_list_of_processed_pdfs(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    pdfs_path = f'{get_root_folder_path()}/output/{pdf_type}/recommendations'
    if not os.path.exists(pdfs_path):
        os.makedirs(pdfs_path)
    list_of_pdfs = ['_'.join(p[:-3].split('_')[1:-1]) for p in os.listdir(pdfs_path) if p.endswith('md')]
    return list_of_pdfs


def load_list_of_pdfs(pdf_type='guidelines'):
    assert pdf_type in ['guidelines', 'white_areas']
    pdfs_path = f'{get_root_folder_path()}/input/{pdf_type}'
    list_of_pdfs = [p[:-4] for p in os.listdir(pdfs_path) if p.endswith('pdf')]
    return list_of_pdfs


def load_items_to_revise(item_type='guidelines'):
    assert item_type in ['guidelines', 'white_areas']
    path_to_items = f'{get_root_folder_path()}/input/{item_type}/items_to_revise.json'
    with open(path_to_items, "r") as f:
        items_dict = json.load(f)
    return items_dict['items']


def log_revised_item(revised_item, item_name, item_type='guidelines'):
    path_name = f'{get_root_folder_path()}/output/revised_item_{item_type}_{item_name}_output.json'
    if revised_item.startswith("```"):
        revised_item = revised_item.split("```")[1]
        if revised_item.startswith("json"):
            revised_item = revised_item[4:]
        revised_item = revised_item.strip()
    loaded_r = json.loads(revised_item)
    with open(path_name, 'w') as f:
        json.dump(loaded_r, f)
