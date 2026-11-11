from pathlib import Path


def load_prompt(name:str)->str:
    prompt_path = Path(__file__).parent /'jinja2'/ f"{name}.jinja2"
    return prompt_path.read_text(encoding="utf-8")

