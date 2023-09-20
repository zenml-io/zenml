from pipelines.ask_pipeline import discord_ask_pipeline
from pipelines.post_pipeline import discord_post_pipeline


def main():
    """Run the Discord alerter example pipelines."""
    discord_ask_pipeline()
    discord_post_pipeline()


if __name__ == "__main__":
    main()
