"""Completion generators: real vLLM batch inference, or the dry-run stub.

Both generators implement the same method with the same return shape, so
the pipeline switches between them with one config value (`dry_run`) and
zero code changes. The contract every generator must honor:

- one episode dict per (task, rollout_index), group_size rollouts per task
- `prompt_ids` / `completion_ids` are token IDs from THE tokenizer that
  the trainer will use. TRL pads and aligns them, and mismatched
  tokenizers corrupt the loss silently.
- `logprobs` has one float per completion token: the log-probability of
  sampling that token under the CURRENT adapter policy. vLLM returns these
  natively; the stub computes them with a forward pass. TRL's rollout_func
  contract requires them.
"""

from typing import Any, Dict, List, Optional


def _make_episode(
    task: Dict[str, Any],
    rollout_index: int,
    prompt_text: str,
    completion_text: str,
    prompt_ids: List[int],
    completion_ids: List[int],
    logprobs: List[float],
) -> Dict[str, Any]:
    from prompts import strip_markdown_fences

    return {
        "task_id": task["id"],
        "rollout_index": rollout_index,
        "prompt_text": prompt_text,
        "completion_text": completion_text,
        "program_text": strip_markdown_fences(completion_text),
        "prompt_ids": list(prompt_ids),
        "completion_ids": list(completion_ids),
        "logprobs": logprobs,
        "spec": task["spec"],
    }


class StubGenerator:
    """Dry-run generator: canned completions, real token IDs and logprobs.

    Loads the actual (tiny) model + current LoRA adapter to tokenize and
    to compute per-token logprobs of the canned completions. This is what
    makes the dry run a real proof of the TRL hand-off: the trainer
    receives exactly the tensor shapes and value semantics the vLLM path
    produces, just with deterministic text.
    """

    def __init__(self, model_name: str, adapter_path: Optional[str] = None):
        """Load tokenizer + tiny model (+ adapter) for stub episodes.

        Args:
            model_name: HF model ID.
            adapter_path: Optional LoRA adapter directory.
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, dtype=torch.float32
        )
        if adapter_path:
            from peft import PeftModel

            model = PeftModel.from_pretrained(model, adapter_path)
        model.eval()
        self.model = model

    def generate(
        self, tasks: List[Dict[str, Any]], group_size: int
    ) -> List[Dict[str, Any]]:
        """Produce group_size canned episodes per task.

        Args:
            tasks: Task records from tasks.jsonl.
            group_size: Rollouts per task (GRPO group size).

        Returns:
            One episode dict per (task, rollout_index).
        """
        import torch
        from prompts import build_prompt
        from stub_completions import canned_completion

        episodes = []
        for task in tasks:
            messages = build_prompt(task["prompt"])
            prompt_ids = self.tokenizer.apply_chat_template(
                messages, add_generation_prompt=True
            )
            prompt_text = self.tokenizer.decode(prompt_ids)
            for rollout_index in range(group_size):
                completion_text = canned_completion(task["id"], rollout_index)
                completion_ids = self.tokenizer(
                    completion_text, add_special_tokens=False
                ).input_ids + [self.tokenizer.eos_token_id]

                full_ids = torch.tensor([prompt_ids + completion_ids])
                with torch.no_grad():
                    logits = self.model(full_ids).logits
                # logits[t] predicts token t+1; completion tokens start at
                # len(prompt_ids), so their predicting positions start one
                # earlier.
                shifted = logits[0, len(prompt_ids) - 1 : -1]
                log_softmax = torch.log_softmax(shifted, dim=-1)
                logprobs = [
                    log_softmax[position, token_id].item()
                    for position, token_id in enumerate(completion_ids)
                ]

                episodes.append(
                    _make_episode(
                        task=task,
                        rollout_index=rollout_index,
                        prompt_text=prompt_text,
                        completion_text=completion_text,
                        prompt_ids=prompt_ids,
                        completion_ids=completion_ids,
                        logprobs=logprobs,
                    )
                )
        return episodes


class VLLMGenerator:
    """Real generator: vLLM offline batch inference with per-call LoRA.

    Loads the vLLM engine in-process (no server — see BREAKAGE_LOG.md
    entry 2), generates group_size samples per task in one batch, and
    reads token IDs and sampled-token logprobs straight from vLLM's
    outputs. UNVERIFIED until Stage 3: requires a GPU.
    """

    def __init__(
        self,
        model_name: str,
        adapter_path: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.9,
    ):
        """Load the vLLM engine (GPU required).

        Args:
            model_name: HF model ID.
            adapter_path: Optional LoRA adapter directory.
            max_tokens: Generation cap per completion.
            temperature: Sampling temperature (>0 for group variance).
        """
        from vllm import LLM

        self.llm = LLM(
            model=model_name,
            enable_lora=adapter_path is not None,
            max_lora_rank=32,
        )
        self.adapter_path = adapter_path
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(
        self, tasks: List[Dict[str, Any]], group_size: int
    ) -> List[Dict[str, Any]]:
        """Batch-generate group_size sampled completions per task.

        Args:
            tasks: Task records from tasks.jsonl.
            group_size: Rollouts per task (GRPO group size).

        Returns:
            One episode dict per (task, rollout_index).
        """
        from prompts import build_prompt
        from vllm import SamplingParams
        from vllm.lora.request import LoRARequest

        sampling = SamplingParams(
            n=group_size,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            logprobs=0,  # sampled token's logprob only
        )
        lora_request = (
            LoRARequest("rl-spike-adapter", 1, self.adapter_path)
            if self.adapter_path
            else None
        )
        conversations = [build_prompt(task["prompt"]) for task in tasks]
        outputs = self.llm.chat(
            conversations, sampling, lora_request=lora_request
        )

        episodes = []
        for task, output in zip(tasks, outputs):
            for rollout_index, sample in enumerate(output.outputs):
                completion_ids = list(sample.token_ids)
                logprobs = [
                    position_logprobs[token_id].logprob
                    for token_id, position_logprobs in zip(
                        completion_ids, sample.logprobs
                    )
                ]
                episodes.append(
                    _make_episode(
                        task=task,
                        rollout_index=rollout_index,
                        prompt_text=output.prompt,
                        completion_text=sample.text,
                        prompt_ids=output.prompt_token_ids,
                        completion_ids=completion_ids,
                        logprobs=logprobs,
                    )
                )
        return episodes


def get_generator(
    dry_run: bool,
    model_name: str,
    adapter_path: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.9,
):
    """The single switch between stub and real inference.

    Args:
        dry_run: True selects the stub; False selects vLLM.
        model_name: HF model ID.
        adapter_path: Local path to the current LoRA adapter directory.
        max_tokens: Generation cap per completion (vLLM path only; the
            stub's completions are canned).
        temperature: Sampling temperature (vLLM path only). Must be > 0:
            greedy sampling would make every rollout in a group identical
            and GRPO's group advantages collapse to zero.

    Returns:
        A generator with a `.generate(tasks, group_size)` method.
    """
    if dry_run:
        return StubGenerator(model_name, adapter_path)
    return VLLMGenerator(
        model_name,
        adapter_path,
        max_tokens=max_tokens,
        temperature=temperature,
    )
