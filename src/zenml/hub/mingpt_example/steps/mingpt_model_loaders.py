from zenml.steps import step

from ..mingpt.model import GPT


@step
def gpt_nano_loader_step() -> GPT:
    model_config = GPT.get_default_config()
    model_config.model_type = "gpt-nano"
    model_config.vocab_size = 50257  # openai's model vocabulary
    model_config.block_size = (
        1024  # openai's model block_size (i.e. input context length)
    )
    model = GPT(model_config)
    return model


@step
def pretrained_gpt_xl_loader_step() -> GPT:
    return GPT.from_pretrained("gpt2-xl")
