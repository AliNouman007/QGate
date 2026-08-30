from pathlib import Path

from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.models import SemanticStateKind
from qgate_project_intelligence.source import LocalPathSource


def test_assignment_literal_comparison_becomes_concrete_user_state(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/shop-context.js").write_text(
        "export function checkout(userMode, total) {\n"
        "  const hasWallet = userMode === 'wallet';\n"
        "  return hasWallet ? total - 10 : total;\n"
        "}\n",
        encoding="utf-8",
    )

    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))
    wallet_states = [
        state
        for state in knowledge.semantic_states
        if state.label == "Wallet"
        and state.kind == SemanticStateKind.USER_STATE
        and state.evidence
        and state.evidence[0].path == "src/shop-context.js"
    ]

    assert len(wallet_states) == 1
    assert wallet_states[0].evidence[0].line == 2
