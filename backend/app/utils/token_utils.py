# USE: Import List and Dict generic type collections from Python's typing standard library.
# WHY: Documents and type-checks the input signature of functions accepting sequences of message objects.
# HOW: Used by IDE type-checkers (e.g. Pyright, Mypy) to enforce list and dictionary types at design time.
from typing import List, Dict

# USE: Function definition for estimating token consumption from a plain text string.
# WHY: Token counts are needed to ensure prompts fit within LLM context window limits without slow BPE tokenizer library overhead.
# HOW: Uses the well-established industry rule-of-thumb that 1 token roughly corresponds to 4 English characters.
def estimate_tokens(text: str) -> int:
    # USE: Guard check testing if the input text is falsy, empty, or None.
    # WHY: An empty string consumes zero tokens and avoids unnecessary integer division math.
    # HOW: Evaluates truthiness of 'text'; returns integer 0 immediately if empty or None.
    if not text:
        # USE: Return zero tokens for empty or None text inputs.
        # WHY: Accurate representation of an empty payload.
        # HOW: Immediately exits the function returning 0.
        return 0
    # USE: Calculate token approximation using length division with a minimum floor of 1.
    # WHY: Non-empty strings must count as at least 1 token even if under 4 characters (e.g. single letters or punctuation).
    # HOW: len(text) // 4 performs integer floor division; max(1, ...) ensures the count is never less than 1.
    return max(1, len(text) // 4)

# USE: Function definition to estimate aggregate token count for a complete conversation history list.
# WHY: Evaluates cumulative prompt size before sending conversation history to the LLM or triggering summarization.
# HOW: Iterates through each message dictionary, sums token counts of role and content, and adds framing overhead.
def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    # USE: Initialize the running total token counter variable to zero.
    # WHY: Serves as the accumulator for summing token approximations across all message items.
    # HOW: Creates a local integer variable starting at 0.
    total = 0
    # USE: Iterate over every message dictionary contained in the input messages list.
    # WHY: Each conversational turn in history contributes tokens to the context payload.
    # HOW: Standard Python for-in loop traversing the list of dicts.
    for msg in messages:
        # USE: Add token estimate for the message's role string (e.g. 'user', 'assistant', 'system').
        # WHY: The LLM API includes the role identifier in its request payload, consuming tokens.
        # HOW: msg.get("role", "") safely retrieves role string, estimate_tokens calculates size, and += adds to total.
        total += estimate_tokens(msg.get("role", ""))
        # USE: Add token estimate for the message's actual content text.
        # WHY: The message text represents the bulk of token consumption in prompt history.
        # HOW: msg.get("content", "") extracts the body string, estimate_tokens calculates size, and += adds to total.
        total += estimate_tokens(msg.get("content", ""))
        # USE: Add fixed 4-token structural framing overhead for each message object.
        # WHY: LLM tokenizers (like OpenAI and Gemini) wrap each message turn with special delimiter tokens (e.g. <|im_start|>, newlines).
        # HOW: Increments accumulator by 4 for every message turn in the loop.
        total += 4
    # USE: Return the aggregated estimated token total for the full messages list.
    # WHY: Provides callers with the total estimated prompt tokens for context window budgeting.
    # HOW: Returns the final integer accumulator value to the caller.
    return total
