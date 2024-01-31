import sys
from unittest.mock import MagicMock
import json
from pathlib import Path

mockers = json.load(open(Path(__file__).parent.resolve() / "mocked_libs.json"))


class DocsMocker(MagicMock):
    _DOCS_BUILDING_MODE: bool = True

    def __init__(self, *args, **kwargs):
        super(DocsMocker, self).__init__(*args, **kwargs)
        self.__getitem__ = DocsMocker._getitem
        self._full_name: str = self._extract_mock_name()
        self.__name__ = self._full_name.split(".")[-1]
        self.__module__ = ".".join(self._full_name.split(".")[:-1])
        self.__version__ = "1.0.0"
        self.__mro_entries__ = lambda _: (self._factory(),)

    def _factory(self, name: str = None):
        if name:

            class _(self.__class__):
                __module__ = ".".join(name.split(".")[:-1])
                __qualname__ = name.split(".")[-1]

            return _(name=name)
        else:

            class _(self.__class__):
                __module__ = self.__module__
                __qualname__ = self.__name__

            return _

    @staticmethod
    def _getitem(self: "DocsMocker", item):
        return self._factory()(name=f"{self._full_name}[{item}]")

    def __repr__(self) -> str:
        return self._full_name


for mocker in mockers:
    sys.modules[mocker] = DocsMocker(name=mocker)

from zenml.materializers.base_materializer import BaseMaterializer

BaseMaterializer._DOCS_BUILDING_MODE = True

if __name__ == "__main__":
    import os
    import importlib
    from zenml.logger import get_logger

    logger = get_logger(__name__)

    modules_to_add = []
    empty_dirs = []
    meaningful_files = [".py", ".tf", ".yaml", ".yml"]
    for root, subdirs, files in os.walk("src/zenml"):
        if not root.endswith("__pycache__"):
            root = root[len("src/") :]

            no_meaningful_files = len(subdirs) == 0
            for file in files:
                for mf in meaningful_files:
                    if file.endswith(mf):
                        no_meaningful_files = False
                        break
                if file.endswith(".py") and not file == "__init__.py":
                    # removes '.py' and builds something like `zenml.something.something`
                    module_name = root.replace("/", ".") + "." + file[:-3]
                    while True:
                        try:
                            importlib.import_module(module_name)
                        except ModuleNotFoundError as e:
                            msg: str = e.args[0]
                            # extract failed to import module from error message
                            module = msg[msg.find("'") + 1 :]
                            module = module[: module.find("'")]

                            modules_to_add.append(module)
                            sys.modules[module] = DocsMocker(name=module)
                            logger.warning(msg)
                        except Exception as e:
                            logger.info("failed importing", module_name)
                            logger.error(e.args[0])
                        else:
                            break
            if no_meaningful_files:
                empty_dirs.append(root)
    if modules_to_add:
        modules_to_add = set(modules_to_add)
        missing_modules = sorted(list(modules_to_add.difference(set(mockers))))
        msg = (
            "Consider mocking : \n["
            + ", ".join([f'"{mm}"' for mm in missing_modules])
            + "]\n  To do so, add this list entries to `mocked_libs.json` "
            "in `docs` folder and retry."
        )
        logger.error(msg)

    if empty_dirs:
        logger.warning(
            f"Directories without any 'meaningful_files' {meaningful_files} files detected. This might affect docs building process:",
            empty_dirs,
        )
    if modules_to_add:
        logger.error(
            "Returning non-zero status code to indicate that docs building failed. Please fix the above errors and try again."
        )
        exit(1)
