"""Prompt and parser from Endless Terminals, Apache-2.0.

Pinned source: kanishkg/endless-terminals at
99f4c74b75faacf21e53d3dc01df170902e924cb, sample_solutions.py.
The parser deliberately selects the last command despite the prompt wording.
"""

import re

UPSTREAM_COMMIT = "99f4c74b75faacf21e53d3dc01df170902e924cb"

SYSTEM_MESSAGE = """You are a highly capable Linux terminal agent operating strictly via a single-shell-command interface.
Goal: Complete the user's task.

Detailed Instructions:
- Output exactly one of the following per turn after you think in the <think> </think> tags:
  1) <command>THE_SINGLE_SHELL_COMMAND</command>
  XOR (XOR means you can only respond with one of the two)
  2) <action>done</action>
- Don't use interactive commands and confirmations; use non-interactive flags.
- Prefer simple, robust CLI tools; write files explicitly when needed.
- If you believe the task is solved, emit <action>done</action>.
- You should run commands interactively to see the output and then write the command. Don't just pipe the commands.
- Only your first command in command tags will be executed. So don't respond with multiple commands.
- Verify your solution once you are done. Eg: you can use cat to see the input and the output.
- Do not just write long bash scripts. Write the commands that you would write in a terminal.
- Only respond with one of <command>...</command> or <action>done</action> after you think in the <think> </think> tags.
- Plan and simulate your actions in <think> </think> tags before you respond with <command>...</command>.
""".strip()

CONCISE_XML_V1_SYSTEM_MESSAGE = """You control a Linux terminal. Complete the user's task by running shell commands.
Each response must contain exactly one XML action and nothing else:
<command>your shell command</command>
or, only after completing and checking the task:
<action>done</action>
For example, to inspect your current directory, respond:
<command>pwd</command>
The tool will execute the command and return its output. Use non-interactive commands. Do not write explanations or Markdown fences.
""".strip()

DONE_RE = re.compile(r"<action>\s*done\s*</action>", flags=re.IGNORECASE)
CMD_RE = re.compile(
    r"<command>\s*(.*?)\s*</command>", flags=re.IGNORECASE | re.DOTALL
)


def extract_action(response: str) -> dict[str, str | None]:
    """Parse the response using the pinned upstream action precedence.

    Args:
        response: Assistant text containing XML action tags.

    Returns:
        Action type and optional command string.
    """
    if DONE_RE.search(response):
        return {"type": "done", "command": None}
    matches = CMD_RE.findall(response)
    if matches:
        # TODO: This changed!!! Models trained with old version used the first match instead of the last.
        command = matches[-1].strip()
        if command.lower() == "done":
            return {"type": "done", "command": None}
        return {"type": "command", "command": command}
    return {"type": "invalid", "command": None}
