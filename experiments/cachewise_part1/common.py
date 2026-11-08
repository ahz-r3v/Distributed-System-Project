"""Small shared helpers for the frozen Part 1 study."""

import hashlib
import json
import os
from pathlib import Path


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def first_use_tokens(sessions):
    prompt = 0
    output = 0
    transitions = 0
    for session in sessions:
        turns = session["turns"]
        prompt += turns[0]["prompt_tokens"]
        for previous, current in zip(turns, turns[1:]):
            addition = (current["prompt_tokens"] - previous["prompt_tokens"]
                        - previous["output_tokens"])
            if addition < 0:
                raise ValueError("Context shrink inside an unsplit segment")
            prompt += addition
            transitions += 1
        output += sum(t["output_tokens"] for t in turns)
    return {"first_use_prompt_tokens": prompt, "output_tokens": output,
            "useful_tokens": prompt + output, "transitions": transitions}
