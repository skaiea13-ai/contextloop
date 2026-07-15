from __future__ import annotations

from .models import ImpactAction, ImpactAssessment


def fixture_impact(
    *,
    affected_asset_count: int,
    owner_names: list[str],
    business_reporting_asset_count: int,
    evidence: list[str],
) -> ImpactAssessment:
    owners = owner_names or ["Data Platform Team"]
    action_titles = [
        "Replace the dropped column or update dependent transformations before deployment.",
        "Validate downstream semantic models against the revised schema.",
        "Run revenue and margin quality checks after the change.",
        "Notify the owners of every affected reporting asset.",
        "Record the decision and rollback path in DataHub.",
    ]
    actions = [
        ImpactAction(id=index + 1, title=title, owner=owners[index % len(owners)])
        for index, title in enumerate(action_titles)
    ]
    return ImpactAssessment(
        severity="P1",
        headline="Revenue reporting at risk",
        summary=(
            "Dropping discount_amount can break downstream revenue and product-performance "
            "reporting that relies on the selected column lineage."
        ),
        why_it_matters=(
            "The column is propagated into analytics and BI assets. Removing it without a "
            "replacement risks failed refreshes, incomplete measures, and inconsistent "
            "executive reporting."
        ),
        affected_asset_count=affected_asset_count,
        owner_count=len(set(owners)),
        business_reporting_asset_count=business_reporting_asset_count,
        evidence=evidence,
        actions=actions,
    )
