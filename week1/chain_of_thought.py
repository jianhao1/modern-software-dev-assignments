import os
import re
from dotenv import load_dotenv
from ollama import chat

load_dotenv()

NUM_RUNS_TIMES = 5

# TODO: Fill this in!
YOUR_SYSTEM_PROMPT = """
Solve modular exponentiation problems by providing concise reasoning first.
Use the examples as the style to follow.
Do not assume a cycle length. Compute successive residues until a residue repeats or until the residue becomes 1, then use that verified cycle.

<example>
Problem: what is 11^37 (mod 100)?
Reasoning: Compute powers of 11 modulo 100 until a cycle appears.
11^1 = 11, 11^2 = 21, 11^3 = 31, 11^4 = 41, 11^5 = 51,
11^6 = 61, 11^7 = 71, 11^8 = 81, 11^9 = 91, 11^10 = 1.
Since 11^10 = 1 mod 100, the residues repeat every 10 powers.
Reduce the exponent: 37 mod 10 = 7.
The needed residue is 11^7 mod 100 = 71.
Answer: 71
</example>

<example>
Problem: what is 7^43 (mod 100)?
Reasoning: Compute powers of 7 modulo 100 and look for a cycle.
7^1 = 7, 7^2 = 49, 7^3 = 43, 7^4 = 1.
The cycle length is 4. Reduce the exponent: 43 mod 4 = 3.
The needed residue is 7^3 mod 100 = 43.
Answer: 43
</example>

<example>
Problem: what is 9^58 (mod 100)?
Reasoning: Compute powers of 9 modulo 100 and look for a cycle.
9^1 = 9, 9^2 = 81, 9^3 = 29, 9^4 = 61, 9^5 = 49, 9^6 = 41, 9^7 = 69, 9^8 = 21, 9^9 = 89, 9^10 = 1.
The cycle length is 10. Reduce the exponent: 58 mod 10 = 8.
The needed residue is 9^8 mod 100 = 21.
Answer: 21
</example>
"""


USER_PROMPT = """
Solve this problem, then give the final answer on the last line as "Answer: <number>".

what is 3^{12345} (mod 100)?
"""


# For this simple example, we expect the final numeric answer only
EXPECTED_OUTPUT = "Answer: 43"


def extract_final_answer(text: str) -> str:
    """Extract the final 'Answer: ...' line from a verbose reasoning trace.

    - Finds the LAST line that starts with 'Answer:' (case-insensitive)
    - Normalizes to 'Answer: <number>' when a number is present
    - Falls back to returning the matched content if no number is detected
    """
    matches = re.findall(r"(?mi)^\s*answer\s*:\s*(.+)\s*$", text)
    if matches:
        value = matches[-1].strip()
        # Prefer a numeric normalization when possible (supports integers/decimals)
        num_match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if num_match:
            return f"Answer: {num_match.group(0)}"
        return f"Answer: {value}"
    return text.strip()


def test_your_prompt(system_prompt: str) -> bool:
    """Run up to NUM_RUNS_TIMES and return True if any output matches EXPECTED_OUTPUT.

    Prints "SUCCESS" when a match is found.
    """
    for idx in range(NUM_RUNS_TIMES):
        print(f"Running test {idx + 1} of {NUM_RUNS_TIMES}")
        response = chat(
            model="llama3.1:8b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT},
            ],
            options={"temperature": 0.3},
        )
        output_text = response.message.content
        final_answer = extract_final_answer(output_text)
        if final_answer.strip() == EXPECTED_OUTPUT.strip():
            print("SUCCESS")
            return True
        else:
            print(f"Expected output: {EXPECTED_OUTPUT}")
            print(f"Actual output: {final_answer}")
    return False


if __name__ == "__main__":
    test_your_prompt(YOUR_SYSTEM_PROMPT)


