import json

import gradio as gr
import requests
import torch

from zenml.hub.mingpt_example.mingpt.bpe import BPETokenizer


class QuestionAnsweringFrontend:
    def __init__(self, deployed_model_url: str) -> None:
        self.deployed_model_url = deployed_model_url

    def send_request_to_deployed_model(
        self, data: torch.Tensor
    ) -> torch.Tensor:
        response = requests.post(
            headers={"Content-Type": "application/json"},
            url=self.deployed_model_url,
            data=json.dumps({"instances": data.numpy().tolist()}),
        ).json()
        if "predictions" in response:
            return torch.tensor(response["predictions"])
        else:
            raise Exception(response)

    def generate(self, prompt: str, num_words: int = 20) -> str:
        # TODO: do this as part of postprocessing custom deployment maybe?
        if not prompt:
            return "Please enter a prompt."
        tokenizer = BPETokenizer()
        tokens = tokenizer(prompt)
        for _ in range(num_words):
            logits = self.send_request_to_deployed_model(tokens)
            _, idx_next = torch.topk(logits, k=1, dim=-1)
            tokens = torch.cat((tokens, idx_next.reshape(tokens.shape)), dim=1)
        return tokenizer.decode(tokens.flatten())

    def answer_question(self, question: str) -> str:
        prompt = "Question: " + question + "\nAnswer: "
        result = self.generate(prompt=prompt)
        answer = result.split("\n")[1][8:].split(".")[0] + "."
        return answer

    def launch(self) -> None:
        gr.Interface(
            title="My ZenML Chatbot",
            fn=self.answer_question,
            inputs=["text"],
            outputs=["text"],
        ).launch()
