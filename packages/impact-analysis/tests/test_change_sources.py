from __future__ import annotations

import subprocess
from pathlib import Path

from qgate_impact_analysis.models import FileChangeStatus
from qgate_impact_analysis.source import LocalGitSource, UnifiedDiffSource


def test_unified_diff_parses_modified_added_deleted_and_renamed_files() -> None:
    patch = """diff --git a/src/Card.tsx b/src/Card.tsx
index 111..222 100644
--- a/src/Card.tsx
+++ b/src/Card.tsx
@@ -10,2 +10,3 @@
-old
+new
+extra
 context
diff --git a/src/new.ts b/src/new.ts
new file mode 100644
--- /dev/null
+++ b/src/new.ts
@@ -0,0 +1 @@
+export const x = 1;
diff --git a/src/old.ts b/src/old.ts
deleted file mode 100644
--- a/src/old.ts
+++ /dev/null
@@ -1 +0,0 @@
-old
diff --git a/src/a.ts b/src/b.ts
similarity index 100%
rename from src/a.ts
rename to src/b.ts
"""
    change_set = UnifiedDiffSource(patch).load()
    by_path = {item.path: item for item in change_set.files}

    assert by_path["src/Card.tsx"].status == FileChangeStatus.MODIFIED
    assert by_path["src/Card.tsx"].additions == 2
    assert by_path["src/Card.tsx"].deletions == 1
    assert by_path["src/new.ts"].status == FileChangeStatus.ADDED
    assert by_path["src/old.ts"].status == FileChangeStatus.DELETED
    assert by_path["src/b.ts"].status == FileChangeStatus.RENAMED
    assert by_path["src/b.ts"].old_path == "src/a.ts"


def test_local_git_source_reads_diff_without_mutating_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "qgate@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "QGate Test"], cwd=tmp_path, check=True)
    file_path = tmp_path / "app.ts"
    file_path.write_text("export const value = 1;\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=tmp_path, check=True, capture_output=True)
    file_path.write_text("export const value = 2;\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "change"], cwd=tmp_path, check=True, capture_output=True)

    before = subprocess.run(["git", "status", "--porcelain"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout
    change_set = LocalGitSource(tmp_path, base_ref="main", head_ref="feature").load()
    after = subprocess.run(["git", "status", "--porcelain"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout

    assert before == after == ""
    assert [item.path for item in change_set.files] == ["app.ts"]
