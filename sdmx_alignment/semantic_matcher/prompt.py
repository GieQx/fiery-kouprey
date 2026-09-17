import json

from sdmx_alignment.models.semantic import SemanticMatchRequest


SYSTEM_PROMPT = """You compare SDMX concepts for a statistical producer. Use only the supplied metadata.
Return one JSON object with suggested_reference_id, relation, confidence, and explanation.
Allowed relations: equivalent, similar, broader, narrower, uncertain, incompatible.
Confidence must be between 0 and 1. Do not invent definitions. If evidence is insufficient, use uncertain."""


def user_prompt(request: SemanticMatchRequest) -> str:
    return json.dumps(request.model_dump(), ensure_ascii=True, indent=2)

