# from openai import OpenAI
# client = OpenAI()

# batch = client.batches.retrieve("batch_677773eefd3881909a3cf0273088fc57")
# print(batch)


# from openai import OpenAI
# client = OpenAI()

# print(client.batches.list(limit=10))

import json
from openai import OpenAI
client = OpenAI()

file_response = client.files.content("file-UMv9ZpCwa8WpjXLV1rayki")

text = file_response.text

# the text is a jsonl file of the format
# {"id": "batch_req_123", "custom_id": "request-2", "response": {"status_code": 200, "request_id": "req_123", "body": {"id": "chatcmpl-123", "object": "chat.completion", "created": 1711652795, "model": "gpt-3.5-turbo-0125", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello."}, "logprobs": null, "finish_reason": "stop"}], "usage": {"prompt_tokens": 22, "completion_tokens": 2, "total_tokens": 24}, "system_fingerprint": "fp_123"}}, "error": null}
# {"id": "batch_req_456", "custom_id": "request-1", "response": {"status_code": 200, "request_id": "req_789", "body": {"id": "chatcmpl-abc", "object": "chat.completion", "created": 1711652789, "model": "gpt-3.5-turbo-0125", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello! How can I assist you today?"}, "logprobs": null, "finish_reason": "stop"}], "usage": {"prompt_tokens": 20, "completion_tokens": 9, "total_tokens": 29}, "system_fingerprint": "fp_3ba"}}, "error": null}

# we want to extract the response.body.choices.message.content for each line
# and append it to a file to prepare a file that captures the full documentation of zenml

with open("zenml_docs.txt", "w") as f:
    for line in text.splitlines():
        json_line = json.loads(line)
        
        # Extract and format the file path from custom_id, handling any file number
        file_path = "-".join(json_line["custom_id"].split("-")[2:]).replace("_", "/")
        
        # Write the file path and content
        f.write(f"File: {file_path}\n\n")
        f.write(json_line["response"]["body"]["choices"][0]["message"]["content"])
        f.write("\n\n" + "="*80 + "\n\n")