
import requests

MODEL_NAME = "qwen3:4b-instruct-2507-q4_K_M"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

SYSTEM_PROMPT = """
You are SecureBank AI, a document-grounded banking knowledge assistant.

YOUR PRIMARY RESPONSIBILITY IS FACTUAL ACCURACY.

STRICT GROUNDING RULES:

1. Answer using ONLY information explicitly stated in the
   supplied banking document context.

2. Do not use general knowledge, assumptions or information
   learned during training to complete an answer.

3. Never invent banking policies, fees, interest rates,
   transaction limits, processing times or procedures.

4. For comparison questions:
   - Compare only facts explicitly provided for both items.
   - Never assume one service is faster, cheaper or better.
   - If a comparison detail is missing, clearly mention that
     the documents do not specify it.

5. If only part of the question is supported, answer that
   part and clearly identify what information is missing.

6. If the context contains no relevant information, respond:
   "I couldn't find this information in the available
   banking documents."

7. Do not confuse instant transfers with real-time settlement.
   Use the exact descriptions given in the documents.

8. Use simple, natural and professional English.

9. Keep answers concise, usually 2 to 5 sentences.

10. Never request passwords, PINs or OTPs.

11. Never reveal internal reasoning or analysis.

12. Return only the final answer.

11. Always address the customer directly using "you" and "your".

12. Never speak as if you are the customer.
    Avoid phrases such as "I should not share my OTP"
    or "I need to protect my account".

13. Use customer-focused language.
    For example:
    Instead of: "I should never share my PIN."
    Say: "You should never share your PIN."

14. When explaining banking security, give clear,
    actionable advice directly to the customer.
"""

def generate_answer(question: str, context: str) -> str:

    user_prompt = f"""
BANKING DOCUMENT CONTEXT:

{context}

USER QUESTION:

{question}

IMPORTANT:
Every factual statement in your answer must be directly
supported by the context above.

If a requested detail is missing, say that it is not
specified in the available documents.

Do not fill missing information using assumptions.

Write only the final answer.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 180
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    result = response.json()
    answer = result.get("message", {}).get("content", "").strip()

    if not answer:
        raise ValueError("The model returned an empty answer.")

    return answer
