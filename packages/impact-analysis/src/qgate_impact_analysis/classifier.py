from __future__ import annotations

from pathlib import PurePosixPath

from qgate_project_intelligence.models import BehaviorCategory, FileAnalysis, FileRole

from .models import ChangeCategory, ChangedFile


def classify_changed_file(change: ChangedFile, analysis: FileAnalysis | None) -> list[ChangeCategory]:
    categories: set[ChangeCategory] = set()
    path = change.path.lower()
    suffix = PurePosixPath(path).suffix
    text = "\n".join(hunk.excerpt for hunk in change.hunks).lower()

    if analysis is not None:
        if analysis.record.role == FileRole.TEST:
            categories.add(ChangeCategory.TEST)
        if analysis.record.role == FileRole.CONFIG:
            categories.add(ChangeCategory.CONFIG)
        if analysis.record.role == FileRole.ROUTE or analysis.routes:
            categories.add(ChangeCategory.ROUTING)
        if analysis.record.role == FileRole.COMPONENT or analysis.symbols:
            categories.add(ChangeCategory.UI)
        if analysis.behaviors:
            categories.add(ChangeCategory.STATE)
        for behavior in analysis.behaviors:
            mapping = {
                BehaviorCategory.AUTH: ChangeCategory.AUTH,
                BehaviorCategory.PERMISSION: ChangeCategory.AUTH,
                BehaviorCategory.FEATURE_FLAG: ChangeCategory.FEATURE_FLAG,
                BehaviorCategory.STORAGE: ChangeCategory.STORAGE,
                BehaviorCategory.RESPONSIVE: ChangeCategory.RESPONSIVE,
            }
            mapped = mapping.get(behavior.category)
            if mapped is not None:
                categories.add(mapped)

    if suffix in {".css", ".scss", ".sass", ".less", ".styl"} or any(
        token in text for token in ("classname", "style=", "tailwind", "@media", "margin", "padding")
    ):
        categories.add(ChangeCategory.STYLING)
    if any(token in path for token in ("route", "router", "navigation", "pages/", "app/")) or any(
        token in text for token in ("router.push", "redirect(", "navigate(", "href=")
    ):
        categories.add(ChangeCategory.ROUTING)
    if any(token in path for token in ("api", "service", "client", "query", "fetch")) or any(
        token in text for token in ("fetch(", "axios", "usequery", "mutation", "/api/")
    ):
        categories.add(ChangeCategory.API)
    if any(token in text for token in ("auth", "login", "logout", "permission", "role", "session")):
        categories.add(ChangeCategory.AUTH)
    if any(token in text for token in ("featureflag", "feature_flag", "experiment", "variant")):
        categories.add(ChangeCategory.FEATURE_FLAG)
    if any(token in text for token in ("localstorage", "sessionstorage", "cookie")):
        categories.add(ChangeCategory.STORAGE)
    if any(token in text for token in ("matchmedia", "max-width", "min-width", "breakpoint")):
        categories.add(ChangeCategory.RESPONSIVE)
    if any(token in path for token in ("config", "vite", "webpack", "tsconfig", "package.json", "pyproject")):
        categories.add(ChangeCategory.CONFIG)
    if any(token in path for token in ("test", "spec", "__tests__")):
        categories.add(ChangeCategory.TEST)

    if not categories:
        categories.add(ChangeCategory.GENERAL)
    return sorted(categories, key=lambda item: item.value)
