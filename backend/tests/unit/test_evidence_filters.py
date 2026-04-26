from app.services.block_data import dataset_catalog, has_dataset_scope, lookup_block, lookup_blocks_for_models
from app.services.evidence_service import EvidenceService


def test_lookup_block_uses_exact_scope_without_fallback():
    result = lookup_block("D", region_id="samarkand-01", mcc_code="7011", limit=5)

    assert result.matched_count > 0
    assert result.sample_rows
    assert all(row["region_id"] == "samarkand-01" for row in result.sample_rows)
    assert all(str(row["mcc_code"]) == "7011" for row in result.sample_rows)


def test_lookup_block_returns_zero_when_requested_region_is_missing():
    result = lookup_block("F", region_id="missing-01", mcc_code="7011", limit=5)

    assert result.matched_count == 0
    assert result.sample_rows == []


def test_evidence_service_rows_stay_within_requested_region_and_mcc():
    result = EvidenceService().find_similar(
        region_id="samarkand-01",
        mcc_code="7011",
        monthly_revenue=18_000,
        initial_investment=220_000,
        limit=10,
        blocks=["D", "F"],
    )

    assert result.total_examined > 0
    assert result.rows
    assert result.total_examined == len(result.rows)
    assert all(row.region_id == "samarkand-01" for row in result.rows)
    assert all(row.mcc_code == "7011" for row in result.rows)
    assert all(block.matched_count > 0 for block in result.blocks)
    assert all(
        row["region_id"] == "samarkand-01" and str(row["mcc_code"]) == "7011"
        for block in result.blocks
        for row in block.sample_rows
    )


def test_lookup_blocks_for_models_returns_no_matches_for_unknown_region():
    lookups = lookup_blocks_for_models(
        ["M-D1", "M-F1"],
        region_id="missing-01",
        mcc_code="7011",
        limit=3,
    )

    assert lookups
    assert all(block.matched_count == 0 for block in lookups.values())


def test_dataset_catalog_and_scope_are_exact():
    catalog = dataset_catalog()

    assert "samarkand-01" in catalog["regions"]
    assert "qashqadaryo-01" not in catalog["regions"]
    assert "5812" in catalog["mcc_codes"]
    assert has_dataset_scope(region_id="samarkand-01", mcc_code="5812")
    assert not has_dataset_scope(region_id="samarkand-01", mcc_code="7230")
