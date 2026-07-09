"""Load modules from the parent rl_spike example by file path.

Plain `sys.path` insertion is unusable here for two reasons discovered the
hard way: (1) this dir's generation.py shadows the parent's generation.py
(script dir precedes any inserted path), and (2) importing
`steps.run_episode` as a package member runs steps/__init__.py, which pulls
the entire GRPO/vLLM serving stack this venv deliberately doesn't have.
Loading by file path sidesteps both: no package __init__ runs, no module
name enters sys.modules under a collidable name.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

RL_SPIKE_DIR = Path(__file__).resolve().parent.parent


def load_rl_spike_module(relative_path: str) -> ModuleType:
    """Load a module from the parent example without package machinery.

    Args:
        relative_path: Path relative to examples/rl_spike/, e.g.
            "prompts.py" or "steps/run_episode.py".

    Returns:
        The loaded module object.
    """
    path = RL_SPIKE_DIR / relative_path
    name = "rl_spike_reuse_" + relative_path.replace("/", "_").removesuffix(
        ".py"
    )
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
