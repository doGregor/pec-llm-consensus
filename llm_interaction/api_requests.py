from utils import *
from google import genai
from google.genai import types
from openai import OpenAI
from xai_sdk import Client
from xai_sdk.chat import user, file


def send_prompt_to_google(client,
                          prompt,
                          model='gemini-2.5-pro',
                          thinking_budget=None,
                          pdf_files=None,
                          panel_mode=False):
    contents = []
    if pdf_files:
        for f in pdf_files:
            contents.append(
                types.Part.from_bytes(
                    data=f,
                    mime_type='application/pdf',
                )
            )
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        )
    )
    if panel_mode:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": PanelDecision,
            }
        )
        return response.parsed
    if thinking_budget is not None:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=thinking_budget,
                    include_thoughts=True
                )
            ),
        )
    else:
        response = client.models.generate_content(
            model=model,
            contents=contents
        )
    return response


def send_prompt_to_openai(client, prompt, model='o3-2025-04-16', reasoning_effort='high', panel_mode=False, pdf_file=None, pdf_file_name=''):
    content = []
    if pdf_file is not None:
        content.append({"type": "input_file",
                        "filename": f"{pdf_file_name}.pdf",
                        "file_data": f"data:application/pdf;base64,{pdf_file}",
                        })
    content.append({"type": "input_text",
                    "text": prompt,
                    })
    if panel_mode:
        schema = PanelDecision.schema()
        schema['additionalProperties'] = False
        response = client.responses.create(
            model=model,
            reasoning={"effort": reasoning_effort},
            input=[{"role": "user", "content": content}],
            text={"format": {"type": "json_schema", "name": "PanelDecision", "schema": schema}}
        )
        return response.output_text
    else:
        response = client.responses.create(
            model=model,
            reasoning={"effort": reasoning_effort},
            input=[{"role": "user", "content": content}]
        )
        return response.output_text


def send_prompt_to_xai(client, prompt, model='grok-4', uploaded_file=None):
    chat = client.chat.create(model=model)
    if uploaded_file is not None:
        chat.append(user(prompt, file(uploaded_file.id)))
    else:
        chat.append(user(prompt))
    response = chat.sample()
    return response.content
