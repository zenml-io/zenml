import os
import shutil
from pathlib import Path
from typing import Dict, Text

SPACER = '  '


def recurse_write(single_layer_dict, file_handler, layer_depth: int = 0,
                  prefix: Text = None, f_prefix: Text = ''):
    file_handler.write('\n')
    for k, v in single_layer_dict.items():
        file_handler.write(layer_depth * SPACER + '* ')
        if prefix is None:
            prefix = k
        else:
            prefix = prefix + '.' + k
        title = ' '.join(k.capitalize().split('_'))
        file_handler.write(f'[{title}]({f_prefix}{prefix}.html)')
        if type(v) is dict:
            recurse_write(v, file_handler, layer_depth + 1, prefix, f_prefix)

        # remove added prefix
        a = prefix.split('.')
        a.pop(-1)
        prefix = '.'.join(a)


def write_multi_layer(multi_layer_dict: Dict, f_path: Text, root_path: Text):
    with open(f_path, 'a') as f:
        f.write('\n')
        recurse_write(multi_layer_dict, f, f_prefix=root_path)


def add_element(key, value, layer):
    if len(value) == 0:
        layer.update({key: {}})
    else:
        layer.update(
            {key: add_element(value[0], value[1:], layer.get(key, {}))})
    return layer


sphinx_docs_path = Path(__file__).parent / 'sphinx_docs' / '_build' / 'html'
user_guide_path = Path(__file__).parent / 'book'
toc_path = user_guide_path / 'toc.md'
base_toc_path = user_guide_path / 'toc_base.md'

all_files = os.listdir(sphinx_docs_path)

zenml_files = [x for x in all_files if
               x.startswith('zenml') and x.endswith('.html')]

zenml_files.remove('zenml.html')

# Replace bath toc
shutil.copy(base_toc_path, toc_path)

with open(toc_path, 'a') as f:
    f.write('\n')
    f.write('## API Reference')

    the_great_dict = {}
    zenml_files = sorted(zenml_files)
    for html_file in zenml_files:
        inner_list = html_file.split('.')[:-1]
        the_great_dict = add_element(inner_list[0], inner_list[1:],
                                     the_great_dict)

write_multi_layer(the_great_dict, str(toc_path), '../sphinx_docs/_build/html/')
