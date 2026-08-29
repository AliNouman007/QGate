from __future__ import annotations

from pydantic import BaseModel, Field

from .models import ImpactItem, ImpactReport


class ImpactEvidencePack(BaseModel):
    key: str
    items: list[ImpactItem] = Field(default_factory=list)


def build_impact_evidence_packs(
    report: ImpactReport,
    *,
    max_items_per_pack: int = 6,
    max_packs: int = 20,
) -> list[ImpactEvidencePack]:
    if max_items_per_pack < 1 or max_packs < 1:
        raise ValueError("Impact evidence-pack limits must be positive")

    items = [
        *report.direct_impacts,
        *report.indirect_impacts,
        *report.possible_impacts,
        *report.unknown_impacts,
        *report.affected_routes,
        *report.affected_states,
    ]
    packs: list[ImpactEvidencePack] = []
    for start in range(0, len(items), max_items_per_pack):
        if len(packs) >= max_packs:
            break
        chunk = items[start : start + max_items_per_pack]
        if chunk:
            packs.append(ImpactEvidencePack(key=f"impact-pack-{len(packs) + 1}", items=chunk))
    return packs
