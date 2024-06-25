import sys
from unittest.mock import MagicMock
import json
from pathlib import Path

# get list of all mockers from `mocked_libs.json`
mockers = json.load(open(Path(__file__).parent.resolve() / "mocked_libs.json"))


class DocsMocker(MagicMock):
    """This class is used to mock the modules in the API docs.

    Ultimate goal of it to return meaningful object on any import
    like `from never_existed_library.module import some_function`.
    To achieve this we have to patch `sys.modules` of all import paths
    used in our code base with instance of this class
    ```python
    sys.modules["never_existed_library.module"] = (
        DocsMocker(name="never_existed_library.module")
    )
    ```
    Args:
        _DOCS_BUILDING_MODE: is used to determine if we are in docs
            building mode in source utils
    """

    _DOCS_BUILDING_MODE: bool = True

    def __init__(self, *args, **kwargs):
        """Here we fake magic methods needed for docs generation."""
        super(DocsMocker, self).__init__(*args, **kwargs)

        # Return instance of same class rather standard getter to print properly as text
        self.__getitem__ = DocsMocker._getitem

        # Hack around namings in various places
        self._full_name: str = self._extract_mock_name()
        self.__name__ = self._full_name.split(".")[-1]
        self.__module__ = ".".join(self._full_name.split(".")[:-1])
        self.__version__ = "1.0.0"

        # needed for class inheritance
        # class A(DocsMocker()): pass
        # We inherit from instance, not from class, because we patched
        # all sys.modules with this class instances, so this hack is needed
        self.__mro_entries__ = lambda _: (self._factory(),)

    def _factory(self, name: str = None):
        """This factory method is modifying class metadata.

        In inspect we need `__module__` and `__qualname__` for a class
        to be properly printed in docs. Otherwise we will get
        `class A(DocsMocker):` everywhere it is used as parent.

        If `name` is passed - return instance, class otherwise. Again
        for proper inheritance.
        """
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

# this hack is needed, since associated types will be instances again and not types,
# so we skip validations in base materializer meta class with this flag
BaseMaterializer._DOCS_BUILDING_MODE = True

if __name__ == "__main__":
    import os
    import importlib
    from zenml.logger import get_logger

    logger = get_logger(__name__)

    modules_to_add = []
    # walk through src/zenml and import all python files
    for root, subdirs, files in os.walk("src/zenml"):
        if not root.endswith("__pycache__"):
            root = root[len("src/") :]

            for file in files:
                if file.endswith(".py") and not file == "__init__.py":
                    # removes '.py' and builds something like `zenml.something.something`
                    module_name = root.replace("/", ".") + "." + file[:-3]
                    # if import pass, we are good
                    # if failed - mocker is extended and we repeat
                    # by this iterative approach we ensure that all needed
                    # mocks would be suggested in CI
                    something_added = False
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
                            something_added = True
                        except Exception as e:
                            logger.info("failed importing", module_name)
                            logger.error(e.args[0])
                        else:
                            break
                        if not something_added:
                            exit(1)
    # pretty print modules missing in mockers
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

    # fail for CI to fail
    if modules_to_add:
        logger.error(
            "Returning non-zero status code to indicate that docs building failed. "
            "Please fix the above errors and try again."
        )
        exit(1)
