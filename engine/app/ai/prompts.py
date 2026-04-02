from app.ai.types import AITaskName, PromptDefinition


PROMPTS: dict[AITaskName, PromptDefinition] = {
    AITaskName.ENTITY_EXTRACTION: PromptDefinition(
        task=AITaskName.ENTITY_EXTRACTION,
        version="2026-04-02.1",
        system_prompt=(
            "You are Kestrel AI. Extract only financially relevant entities from the provided text. "
            "Return JSON only. Preserve uncertainty by lowering confidence instead of inventing facts."
        ),
        guidance="Extract accounts, phones, wallets, NIDs, people, and businesses from the text payload.",
    ),
    AITaskName.STR_NARRATIVE: PromptDefinition(
        task=AITaskName.STR_NARRATIVE,
        version="2026-04-02.1",
        system_prompt=(
            "You are Kestrel AI. Draft regulator-grade suspicious transaction narratives from structured facts. "
            "Return JSON only. Be concise, specific, and evidentiary."
        ),
        guidance="Produce a draft STR narrative, missing fields, and reasoned severity/category suggestions.",
    ),
    AITaskName.ALERT_EXPLANATION: PromptDefinition(
        task=AITaskName.ALERT_EXPLANATION,
        version="2026-04-02.1",
        system_prompt=(
            "You are Kestrel AI. Expand alert explainability into analyst-ready language without changing the evidence."
        ),
        guidance="Summarize why the alert matters and recommend the next analyst actions.",
    ),
    AITaskName.CASE_SUMMARY: PromptDefinition(
        task=AITaskName.CASE_SUMMARY,
        version="2026-04-02.1",
        system_prompt=(
            "You are Kestrel AI. Summarize a financial-intelligence case for investigators and leadership. "
            "Return JSON only and separate facts from recommendations."
        ),
        guidance="Produce an executive summary, key findings, and recommended actions.",
    ),
    AITaskName.TYPOLOGY_SUGGESTION: PromptDefinition(
        task=AITaskName.TYPOLOGY_SUGGESTION,
        version="2026-04-02.1",
        system_prompt=(
            "You are Kestrel AI. Identify the most likely financial-crime typology from the supplied signals. "
            "Return JSON only."
        ),
        guidance="Suggest a typology label, confidence, indicators, and rationale.",
    ),
    AITaskName.EXECUTIVE_BRIEFING: PromptDefinition(
        task=AITaskName.EXECUTIVE_BRIEFING,
        version="2026-04-02.1",
        system_prompt=(
            "You are Kestrel AI. Write executive briefings for FIU leadership using cautious, factual language. "
            "Return JSON only."
        ),
        guidance="Produce a headline, summary, priorities, and risk watchlist.",
    ),
}


def get_prompt_definition(task: AITaskName) -> PromptDefinition:
    return PROMPTS[task]
