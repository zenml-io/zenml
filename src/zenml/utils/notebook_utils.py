import json

import ipynbname
from IPython import get_ipython


def get_current_cell_id() -> str:
    cell_id = get_ipython().get_parent()["metadata"]["cellId"]
    return cell_id


def extract_cell_code(cell_id: str, output_path: str) -> None:
    notebook_path = ipynbname.path()

    with open(notebook_path) as f:
        nb = json.loads(f.read())

    for cell in nb["cells"]:
        if cell["id"] == cell_id:
            with open(output_path, "w") as output_file:
                output_file.writelines(cell["source"])

            break
