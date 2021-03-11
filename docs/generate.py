"""
Generate ZenML documentation.

This script will:
- generate pydoc3 docstring documentation
- generate and merge jupyter-book table of contents
"""
import subprocess
import os

def generate_docstrings(source='zenml/core', target='docs/book/reference'):
    cmd = f"pdoc {source} -o {target} --skip-errors".split(" ")
    run_in_shell = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
    stdout, stderr = run_in_shell.communicate()
    if stderr:
        raise Exception(stderr)

    # convert index.md lists into links
    directories = []
    for root, subdirs, files in os.walk(target):
        for dir in subdirs:
            # collect directories with their path for later usage
            directories.append(
                f'{os.path.join(root, dir)}'.replace(target, '/reference'))
        for filename in files:
            if filename == 'index.md':
                file_path = os.path.join(root, filename)
                with open(file_path, 'r+') as f:
                    content = f.read()
                    new_content = ''
                    for line in content.split('\n'):
                        new_line = line
                        if line.startswith('* '):
                            module_python_path = line.replace('* ', '')
                            module_path = f'/reference/{module_python_path.replace(".", "/")}'
                            # check filetype
                            filetype = '.md'
                            if module_path in directories:
                                filetype = '/index.md'

                            module_link = f'{module_path}{filetype}'
                            new_line = f'* [{module_python_path}]({module_link})  '
                        new_content += f'{new_line}\n'
                    f.seek(0)  # jump to beginning of the file
                    f.write(new_content)
                    f.truncate()  # cut of remaining text, if any


def generate_toc(target='docs/book/reference', toc_file='docs/book/_toc.yml'):
    cmd = f'jupyter-book toc {target}'.split(' ')
    run_in_shell = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
    stdout, stderr = run_in_shell.communicate()
    if stderr:
        raise Exception(stderr)

    new_toc = '''
- part: Reference
  chapters:
    '''
    skip_header = 'file: index\nsections:\n'

    with open(f'{target}/_toc.yml', 'r') as raw_toc:
        generated_toc = raw_toc.read().replace(skip_header, '')
        generated_toc = generated_toc.replace('file: ', '- file: reference/')
        generated_toc = generated_toc.replace('\n', '\n    ')  # indentation
        generated_toc += '\n\n'
        new_toc += generated_toc
    os.remove(f'{target}/_toc.yml')  # cleanup

    with open(toc_file, 'a') as final_toc:
        final_toc.write(new_toc)

if __name__ == '__main__':
    generate_docstrings()
    generate_toc()
