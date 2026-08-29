from __future__ import annotations

import re
from pathlib import PurePosixPath

from .models import (
    BehaviorCategory,
    BehaviorFact,
    Confidence,
    Evidence,
    FileAnalysis,
    FileRecord,
    ImportFact,
)

_PY_IMPORT = re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)")
_PY_FROM_IMPORT = re.compile(r"^\s*from\s+([.A-Za-z_][\w.]*)\s+import\s+")
_JS_IMPORT = re.compile(r"(?:import\s+(?:.+?\s+from\s+)?|require\s*\()?[\"']([^\"']+)[\"']")
_JS_DYNAMIC_IMPORT = re.compile(r"import\s*\(\s*[\"']([^\"']+)[\"']\s*\)")
_CONDITION_PATTERNS = [
    re.compile(r"\bif\s*\((.+?)\)"),
    re.compile(r"\belse\s+if\s*\((.+?)\)"),
    re.compile(r"^\s*if\s+(.+?):\s*$"),
]
_TERNARY_CONDITION = re.compile(r"(?:\{|\(|=|return\s+)([^?;{}]+?)\s*\?")

_AUTH_TERMS = {"auth", "authenticated", "isloggedin", "loggedin", "session", "currentuser"}
_PERMISSION_TERMS = {
    "permission",
    "permissions",
    "role",
    "roles",
    "canedit",
    "canwrite",
    "isadmin",
    "owner",
}
_FEATURE_TERMS = {"featureflag", "feature_flag", "experiment", "variant", "abtest", "a_b_test"}
_LOADING_TERMS = {"loading", "isloading", "pending", "ispending", "fetching", "isfetching"}
_ERROR_TERMS = {"error", "haserror", "iserror", "failed", "failure"}
_EMPTY_TERMS = {"empty", "isempty", "length===0", "length==0", "count===0", "count==0"}
_STORAGE_TERMS = {"localstorage", "sessionstorage", "document.cookie", "cookie", "cookies"}
_RESPONSIVE_TERMS = {
    "matchmedia",
    "innerwidth",
    "breakpoint",
    "ismobile",
    "isdesktop",
    "tablet",
    "viewport",
}


def analyze_text_file(record: FileRecord, text: str) -> FileAnalysis:
    imports: list[ImportFact] = []
    behaviors: list[BehaviorFact] = []
    for index, line in enumerate(text.splitlines(), start=1):
        imports.extend(_extract_imports(record, line, index))
        behaviors.extend(_extract_behaviors(record, line, index))
        behaviors.extend(_extract_direct_signals(record, line, index))
    return FileAnalysis(
        record=record, imports=_dedupe_imports(imports), behaviors=_dedupe_behaviors(behaviors)
    )


def _extract_imports(record: FileRecord, line: str, line_number: int) -> list[ImportFact]:
    modules: list[str] = []
    if record.language == "python":
        for pattern in (_PY_FROM_IMPORT, _PY_IMPORT):
            match = pattern.search(line)
            if match:
                modules.append(match.group(1))
    elif record.language in {"javascript", "typescript", "vue", "svelte"}:
        stripped = line.strip()
        if stripped.startswith("import ") or "require(" in stripped:
            match = _JS_IMPORT.search(line)
            if match:
                modules.append(match.group(1))
        dynamic = _JS_DYNAMIC_IMPORT.search(line)
        if dynamic:
            modules.append(dynamic.group(1))
    return [
        ImportFact(module=module, evidence=_evidence(record, line_number, line, "import"))
        for module in modules
    ]


def _extract_behaviors(record: FileRecord, line: str, line_number: int) -> list[BehaviorFact]:
    expressions: list[str] = []
    for pattern in _CONDITION_PATTERNS:
        expressions.extend(match.group(1).strip() for match in pattern.finditer(line))
    ternary = _TERNARY_CONDITION.search(line)
    if ternary:
        expressions.append(ternary.group(1).strip())

    facts: list[BehaviorFact] = []
    for expression in expressions:
        if not expression:
            continue
        category, confidence, meaningful = _classify_condition(expression, line)
        facts.append(
            BehaviorFact(
                expression=expression,
                category=category,
                confidence=confidence,
                meaningful=meaningful,
                evidence=_evidence(record, line_number, line, "condition"),
            )
        )
    return facts


def _extract_direct_signals(record: FileRecord, line: str, line_number: int) -> list[BehaviorFact]:
    category = _category_for(_normalize(line))
    if category not in {BehaviorCategory.STORAGE, BehaviorCategory.RESPONSIVE}:
        return []
    return [
        BehaviorFact(
            expression=line.strip(),
            category=category,
            confidence=Confidence.HIGH,
            meaningful=True,
            evidence=_evidence(record, line_number, line, "runtime_signal"),
        )
    ]


def _classify_condition(
    expression: str, full_line: str
) -> tuple[BehaviorCategory, Confidence, bool]:
    normalized = _normalize(expression)
    category = _category_for(normalized)
    if category != BehaviorCategory.GENERAL:
        return category, Confidence.HIGH, True

    if _looks_like_technical_guard(normalized, _normalize(full_line)):
        return BehaviorCategory.TECHNICAL_GUARD, Confidence.MEDIUM, False
    return BehaviorCategory.GENERAL, Confidence.MEDIUM, True


def _category_for(normalized: str) -> BehaviorCategory:
    if _contains_any(normalized, _STORAGE_TERMS):
        return BehaviorCategory.STORAGE
    if _contains_any(normalized, _RESPONSIVE_TERMS):
        return BehaviorCategory.RESPONSIVE
    if _contains_any(normalized, _PERMISSION_TERMS):
        return BehaviorCategory.PERMISSION
    if _contains_any(normalized, _AUTH_TERMS):
        return BehaviorCategory.AUTH
    if _contains_any(normalized, _FEATURE_TERMS):
        return BehaviorCategory.FEATURE_FLAG
    if _contains_any(normalized, _LOADING_TERMS):
        return BehaviorCategory.LOADING
    if _contains_any(normalized, _ERROR_TERMS):
        return BehaviorCategory.ERROR
    if _contains_any(normalized, _EMPTY_TERMS):
        return BehaviorCategory.EMPTY
    return BehaviorCategory.GENERAL


def _looks_like_technical_guard(expression: str, full_line: str) -> bool:
    nil_check = bool(
        re.fullmatch(
            r"!?[\w.]+(?:\s*(?:===?|!==?|is|isnot)\s*(?:none|null|undefined))?",
            expression,
        )
    )
    early_exit = any(token in full_line for token in ("return", "continue", "break", "raise"))
    infrastructure_terms = any(
        token in expression
        for token in ("node", "element", "ref.current", "response", "client", "connection")
    )
    return (nil_check and early_exit) or (infrastructure_terms and early_exit)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _contains_any(value: str, terms: set[str]) -> bool:
    return any(term.replace(" ", "") in value for term in terms)


def _evidence(record: FileRecord, line: int, excerpt: str, kind: str) -> Evidence:
    return Evidence(path=record.path, line=line, excerpt=excerpt.strip()[:240], kind=kind)


def _dedupe_imports(imports: list[ImportFact]) -> list[ImportFact]:
    seen: set[tuple[str, int]] = set()
    result: list[ImportFact] = []
    for item in imports:
        key = (item.module, item.evidence.line)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _dedupe_behaviors(behaviors: list[BehaviorFact]) -> list[BehaviorFact]:
    seen: set[tuple[str, int, BehaviorCategory]] = set()
    result: list[BehaviorFact] = []
    for item in behaviors:
        key = (item.expression, item.evidence.line, item.category)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def import_candidates(source_path: str, module: str, language: str | None) -> list[str]:
    source = PurePosixPath(source_path)
    if language == "python":
        if module.startswith("."):
            level = len(module) - len(module.lstrip("."))
            base = source.parent
            for _ in range(max(level - 1, 0)):
                base = base.parent
            module_path = module.lstrip(".").replace(".", "/")
            prefix = base / module_path if module_path else base
        else:
            prefix = PurePosixPath(module.replace(".", "/"))
        return [f"{prefix}.py", f"{prefix}/__init__.py"]

    if language in {"javascript", "typescript", "vue", "svelte"} and module.startswith("."):
        prefix = (source.parent / module).as_posix()
        suffixes = [".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte"]
        candidates = [f"{prefix}{suffix}" for suffix in suffixes]
        candidates.extend(f"{prefix}/index{suffix}" for suffix in suffixes[:4])
        return candidates
    return []
