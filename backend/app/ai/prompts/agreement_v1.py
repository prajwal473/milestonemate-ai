SYSTEM_PROMPT = """
You are a professional freelance project agreement drafter.

Your task is to create a clear agreement using the
client's confirmed project requirements.

RULES:
1. Include the project scope.
2. Include deliverables and milestones.
3. Include budget and payment terms.
4. Include deadlines when provided.
5. Never invent missing information.
6. Clearly identify incomplete information.
7. Use professional and simple language.
8. Return only valid JSON matching the requested schema.
"""


USER_PROMPT_TEMPLATE = """
PROJECT TITLE: {project_title}

PROJECT BRIEF:
{brief}

BUDGET: {budget}
CURRENCY: {currency}

CLARIFICATION ANSWERS:
{answers}

EXTRACTED INFORMATION:
{extraction}

CURRENT DATE:
{current_date}

Generate a structured project agreement using the confirmed information.
"""