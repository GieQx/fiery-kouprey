from __future__ import annotations

import hashlib
import json

from sdmx_alignment.models.alignment import AnswerEvaluation
from sdmx_alignment.models.structures import DSDStructure


FIXED_QUESTION = (
    "Assess how the local DSD can interoperate with the selected reference DSD. "
    "Identify which concepts and codelists can be reused, which code mappings are required, "
    "which elements are legitimate local extensions, which reference elements are missing locally, "
    "and which issues remain unresolved. Cite the DSD element IDs supporting every recommendation."
)


def dsd_context(local: DSDStructure, reference: DSDStructure) -> dict:
    def compact(structure: DSDStructure):
        return {
            "identity": {"agency": structure.agency_id, "id": structure.id, "version": structure.version},
            "dimensions": [
                {
                    "id": item.id,
                    "name": item.label,
                    "description": item.description,
                    "concept": item.concept_ref.id if item.concept_ref else None,
                    "codelist": item.codelist_ref.id if item.codelist_ref else None,
                }
                for item in structure.dimensions
            ],
            "attributes": [{"id": item.id, "name": item.label} for item in structure.attributes],
        }
    return {"local": compact(local), "reference": compact(reference)}


def context_hash(context: dict) -> str:
    encoded = json.dumps(context, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_evaluation(**kwargs) -> AnswerEvaluation:
    return AnswerEvaluation(fixed_question=FIXED_QUESTION, **kwargs)

