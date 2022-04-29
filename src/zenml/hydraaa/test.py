from omegaconf import DictConfig, OmegaConf
import hydra

@hydra.compose(config_path=None)
def my_app(cfg: DictConfig) -> None:
    print(OmegaConf.to_yaml(cfg))

if __name__ == "__main__":
    my_app()