from utils import *
import pymupdf4llm


for subfolder in ['guidelines', 'white_areas']:
    pdfs_path = f'{get_root_folder_path()}/input/{subfolder}'
    for file in os.listdir(pdfs_path):
        if file.endswith('pdf'):
            print(file)
            save_folder = f'{get_root_folder_path()}/input/{subfolder}'
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            save_path_file = f'{save_folder}/{"_".join(file.split(".")[:-1])}.md'
            markdown = pymupdf4llm.to_markdown(f'{pdfs_path}/{file}')
            with open(save_path_file, 'w') as out_md:
                out_md.write(markdown)
