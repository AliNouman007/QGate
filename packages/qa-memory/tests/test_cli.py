from pathlib import Path

from qgate_qa_memory.cli import main
from qgate_qa_memory.store import JsonQAMemoryStore


def test_cli_add_human_creates_pending_candidate(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "qgate-qa-memory",
            "--store",
            str(tmp_path),
            "add-human",
            "--project-source-id",
            "local:/shop",
            "--title",
            "Checkout wallet label",
            "--invariant",
            "Final payable must show You Pay",
            "--route",
            "/checkout",
            "--state",
            "wallet",
        ],
    )
    main()
    output = capsys.readouterr().out
    assert '"status": "pending"' in output
    candidates = JsonQAMemoryStore(tmp_path).list_candidates()
    assert len(candidates) == 1
    assert candidates[0].routes == ["/checkout"]
    assert candidates[0].states == ["wallet"]
