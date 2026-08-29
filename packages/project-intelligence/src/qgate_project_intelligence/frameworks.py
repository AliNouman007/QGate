from __future__ import annotations

import json
import re
from pathlib import PurePosixPath

from .models import (
    Confidence,
    Evidence,
    FileRecord,
    FrameworkFact,
    FrameworkKind,
    RouteFact,
    SymbolFact,
    SymbolKind,
)

_COMPONENT_PATTERNS = (
    re.compile(r"\bexport\s+default\s+function\s+([A-Z][A-Za-z0-9_]*)"),
    re.compile(r"\bexport\s+function\s+([A-Z][A-Za-z0-9_]*)"),
    re.compile(r"\bfunction\s+([A-Z][A-Za-z0-9_]*)\s*\("),
    re.compile(r"\bexport\s+const\s+([A-Z][A-Za-z0-9_]*)\s*="),
    re.compile(r"\bconst\s+([A-Z][A-Za-z0-9_]*)\s*="),
)
_HOOK_PATTERN = re.compile(r"\b(use[A-Z][A-Za-z0-9_]*)\s*\(")
_CONTEXT_PATTERN = re.compile(
    r"\b(?:export\s+)?const\s+([A-Za-z0-9_]*Context)\s*=\s*createContext(?:\s*<[^>]+>)?\s*\("
)
_PROVIDER_PATTERN = re.compile(r"<([A-Za-z0-9_]+)\.Provider\b")
_TS_INTERFACE = re.compile(r"\b(export\s+)?interface\s+([A-Za-z_][A-Za-z0-9_]*)")
_TS_TYPE = re.compile(r"\b(export\s+)?type\s+([A-Za-z_][A-Za-z0-9_]*)\s*=")
_TS_ENUM = re.compile(r"\b(export\s+)?enum\s+([A-Za-z_][A-Za-z0-9_]*)")
_NEXT_APIS = (
    "useRouter",
    "usePathname",
    "useSearchParams",
    "redirect",
    "notFound",
    "cookies",
    "headers",
)
_NEXT_SPECIAL = {"page", "layout", "loading", "error", "not-found", "template", "route"}


def detect_declared_frontend_frameworks(manifest_texts: list[str]) -> set[FrameworkKind]:
    """Read package manifests as project-level evidence before inferring framework routes."""
    declared: set[FrameworkKind] = set()
    for text in manifest_texts:
        try:
            manifest = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(manifest, dict):
            continue
        package_names: set[str] = set()
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            values = manifest.get(section)
            if isinstance(values, dict):
                package_names.update(str(name) for name in values)
        if "next" in package_names:
            declared.add(FrameworkKind.NEXTJS)
            declared.add(FrameworkKind.REACT)
        if "react" in package_names or "react-dom" in package_names:
            declared.add(FrameworkKind.REACT)
        if "typescript" in package_names:
            declared.add(FrameworkKind.TYPESCRIPT)
    return declared


def extract_framework_knowledge(
    record: FileRecord,
    text: str,
    declared_frameworks: set[FrameworkKind] | None = None,
) -> tuple[list[FrameworkFact], list[RouteFact], list[SymbolFact]]:
    if record.language not in {"javascript", "typescript", "vue", "svelte"}:
        return [], [], []

    declared = declared_frameworks or set()
    lines = text.splitlines()
    frameworks: list[FrameworkFact] = []
    routes: list[RouteFact] = []
    symbols: list[SymbolFact] = []

    react_detected = _looks_like_react(record.path, text, declared)
    next_detected = _looks_like_next(text, declared)
    if react_detected:
        frameworks.append(_framework(record, 1, lines, FrameworkKind.REACT, "react_module"))
    if next_detected:
        frameworks.append(_framework(record, 1, lines, FrameworkKind.NEXTJS, "next_module"))
    if record.language == "typescript":
        frameworks.append(_framework(record, 1, lines, FrameworkKind.TYPESCRIPT, "typed_module"))

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if next_detected and stripped in {'"use client";', "'use client';", '"use client"', "'use client'"}:
            frameworks.append(
                _framework(record, line_number, lines, FrameworkKind.NEXTJS, "boundary", "client")
            )
        if next_detected and stripped in {'"use server";', "'use server';", '"use server"', "'use server'"}:
            frameworks.append(
                _framework(record, line_number, lines, FrameworkKind.NEXTJS, "boundary", "server")
            )

        if react_detected:
            for pattern in _COMPONENT_PATTERNS:
                match = pattern.search(line)
                if match:
                    symbols.append(
                        _symbol(
                            record,
                            line_number,
                            line,
                            match.group(1),
                            SymbolKind.COMPONENT,
                            "export" in line,
                        )
                    )
                    break
            for match in _HOOK_PATTERN.finditer(line):
                symbols.append(
                    _symbol(record, line_number, line, match.group(1), SymbolKind.HOOK, False)
                )
            context_match = _CONTEXT_PATTERN.search(line)
            if context_match:
                symbols.append(
                    _symbol(
                        record,
                        line_number,
                        line,
                        context_match.group(1),
                        SymbolKind.CONTEXT,
                        "export" in line,
                    )
                )
            for match in _PROVIDER_PATTERN.finditer(line):
                symbols.append(
                    _symbol(record, line_number, line, match.group(1), SymbolKind.PROVIDER, False)
                )

        if next_detected:
            for api in _NEXT_APIS:
                if re.search(rf"\b{re.escape(api)}\b", line):
                    frameworks.append(
                        _framework(record, line_number, lines, FrameworkKind.NEXTJS, "runtime_api", api)
                    )

        if record.language == "typescript":
            for pattern, kind in (
                (_TS_INTERFACE, SymbolKind.INTERFACE),
                (_TS_TYPE, SymbolKind.TYPE_ALIAS),
                (_TS_ENUM, SymbolKind.ENUM),
            ):
                match = pattern.search(line)
                if match:
                    symbols.append(
                        _symbol(record, line_number, line, match.group(2), kind, bool(match.group(1)))
                    )

    if next_detected:
        route = _route_fact(record, lines)
        if route is not None:
            routes.append(route)

    return _dedupe_frameworks(frameworks), _dedupe_routes(routes), _dedupe_symbols(symbols)


def _looks_like_react(
    path: str,
    text: str,
    declared: set[FrameworkKind],
) -> bool:
    suffix = PurePosixPath(path).suffix.lower()
    direct_evidence = bool(
        re.search(r"from\s+['\"]react['\"]|\bReact\.|\bcreateContext\s*\(", text)
    )
    return direct_evidence or (FrameworkKind.REACT in declared and suffix in {".jsx", ".tsx"})


def _looks_like_next(text: str, declared: set[FrameworkKind]) -> bool:
    direct_evidence = "next/" in text or "from 'next'" in text or 'from "next"' in text
    return direct_evidence or FrameworkKind.NEXTJS in declared


def _route_fact(record: FileRecord, lines: list[str]) -> RouteFact | None:
    path = PurePosixPath(record.path)
    parts = list(path.parts)
    stem = path.stem

    app_index = _first_router_index(parts, "app")
    if app_index is not None and stem in _NEXT_SPECIAL:
        route_parts = parts[app_index + 1 : -1]
        route = _route_from_segments(route_parts)
        return RouteFact(
            route=route,
            router="next_app",
            kind=stem,
            dynamic=_is_dynamic(route_parts),
            evidence=_evidence(record, 1, _line(lines, 1), "next_route"),
        )

    pages_index = _first_router_index(parts, "pages")
    if pages_index is not None and path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx"}:
        if stem.startswith("_"):
            return None
        route_parts = parts[pages_index + 1 : -1] + ([] if stem == "index" else [stem])
        route = _route_from_segments(route_parts)
        kind = "api" if route_parts and route_parts[0] == "api" else "page"
        return RouteFact(
            route=route,
            router="next_pages",
            kind=kind,
            dynamic=_is_dynamic(route_parts),
            evidence=_evidence(record, 1, _line(lines, 1), "next_route"),
        )
    return None


def _first_router_index(parts: list[str], name: str) -> int | None:
    for index, part in enumerate(parts):
        if part == name and (index == 0 or parts[index - 1] == "src"):
            return index
    return None


def _route_from_segments(parts: list[str]) -> str:
    rendered: list[str] = []
    for part in parts:
        if part.startswith("(") and part.endswith(")"):
            continue
        if part.startswith("[[...") and part.endswith("]]" ):
            rendered.append(f"*{part[5:-2]}?")
        elif part.startswith("[...") and part.endswith("]"):
            rendered.append(f"*{part[4:-1]}")
        elif part.startswith("[") and part.endswith("]"):
            rendered.append(f":{part[1:-1]}")
        else:
            rendered.append(part)
    return "/" + "/".join(rendered) if rendered else "/"


def _is_dynamic(parts: list[str]) -> bool:
    return any(part.startswith("[") and part.endswith("]") for part in parts)


def _framework(
    record: FileRecord,
    line_number: int,
    lines: list[str],
    framework: FrameworkKind,
    feature: str,
    value: str | None = None,
) -> FrameworkFact:
    return FrameworkFact(
        framework=framework,
        feature=feature,
        value=value,
        confidence=Confidence.HIGH,
        evidence=_evidence(record, line_number, _line(lines, line_number), "framework"),
    )


def _symbol(
    record: FileRecord,
    line_number: int,
    line: str,
    name: str,
    kind: SymbolKind,
    exported: bool,
) -> SymbolFact:
    return SymbolFact(
        name=name,
        kind=kind,
        exported=exported,
        evidence=_evidence(record, line_number, line, "symbol"),
    )


def _evidence(record: FileRecord, line: int, excerpt: str, kind: str) -> Evidence:
    return Evidence(path=record.path, line=line, excerpt=excerpt.strip()[:240], kind=kind)


def _line(lines: list[str], line_number: int) -> str:
    if not lines:
        return ""
    index = max(0, min(line_number - 1, len(lines) - 1))
    return lines[index]


def _dedupe_frameworks(facts: list[FrameworkFact]) -> list[FrameworkFact]:
    seen: set[tuple[FrameworkKind, str, str | None, int]] = set()
    result: list[FrameworkFact] = []
    for fact in facts:
        key = (fact.framework, fact.feature, fact.value, fact.evidence.line)
        if key not in seen:
            seen.add(key)
            result.append(fact)
    return result


def _dedupe_routes(facts: list[RouteFact]) -> list[RouteFact]:
    seen: set[tuple[str, str, str]] = set()
    result: list[RouteFact] = []
    for fact in facts:
        key = (fact.route, fact.router, fact.kind)
        if key not in seen:
            seen.add(key)
            result.append(fact)
    return result


def _dedupe_symbols(facts: list[SymbolFact]) -> list[SymbolFact]:
    seen: set[tuple[str, SymbolKind, int]] = set()
    result: list[SymbolFact] = []
    for fact in facts:
        key = (fact.name, fact.kind, fact.evidence.line)
        if key not in seen:
            seen.add(key)
            result.append(fact)
    return result
