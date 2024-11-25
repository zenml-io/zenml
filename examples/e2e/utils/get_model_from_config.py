# 


from sklearn.base import ClassifierMixin


def get_model_from_config(model_package: str, model_class: str) -> ClassifierMixin:
    if model_package == "sklearn.ensemble":
        import sklearn.ensemble as package

        model_class = getattr(package, model_class)
    elif model_package == "sklearn.tree":
        import sklearn.tree as package

        model_class = getattr(package, model_class)
    else:
        raise ValueError(f"Unsupported model package: {model_package}")

    return model_class
