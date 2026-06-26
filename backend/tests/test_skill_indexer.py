from sw_ai_backend.skills.indexer import SkillIndexer


def test_skill_indexer_reads_vendored_skills() -> None:
    index = SkillIndexer.default().build_index()

    assert index.solidworks_available
    assert index.taste_available
    assert any(document.kind == "taste" for document in index.documents)
    assert any(function.module == "sw_session" for function in index.functions)
    assert "solidworks_health_check" in index.mcp_tools
    assert "SolidWorks automation Skill 已加载" in index.context_summary
