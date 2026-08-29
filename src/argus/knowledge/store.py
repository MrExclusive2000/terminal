"""
Knowledge packs — the layer Claude authors and keeps current.

A pack is a versioned set of *claims*. Each claim has a stable id, a body, a
confidence, a decay date and sources. Stable ids are what make the diff
possible: because a claim persists across versions, the app can show exactly
what was added, revised or retired, and why.

Claims feed the analyst as cached context, so the model reasons from a
maintained brief rather than from whatever it happens to recall.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

def _pack_dir() -> Path:
    """Where the shipped knowledge packs live.

    Resolved through the bundle helper rather than by counting `..` from
    `__file__`: the frozen layout has a different depth, so the arithmetic that
    is right from source lands a directory adrift inside the bundle.
    """
    from ..config import bundled
    return bundled("knowledge", "packs")


PACK_DIR = _pack_dir()


@dataclass(frozen=True)
class Claim:
    id: str
    body: str
    confidence: float
    why_it_matters: str = ""
    sources: tuple[str, ...] = ()
    decays: str | None = None

    @property
    def expired(self) -> bool:
        if not self.decays:
            return False
        try:
            return date.fromisoformat(self.decays) < date.today()
        except ValueError:
            return False

    @property
    def stale_warning(self) -> str | None:
        if self.expired:
            return f"past its review date ({self.decays}) - re-verify before relying on it"
        if self.confidence < 0.6:
            return f"low confidence ({self.confidence:.2f})"
        return None


@dataclass(frozen=True)
class Pack:
    id: str
    version: str
    title: str
    authored_by: str
    authored_at: str
    review_cadence_days: int
    claims: tuple[Claim, ...] = ()

    @property
    def days_since_authored(self) -> int:
        try:
            return (date.today() - date.fromisoformat(self.authored_at)).days
        except ValueError:
            return 0

    @property
    def due_for_review(self) -> bool:
        return self.days_since_authored >= self.review_cadence_days


class PackError(RuntimeError):
    pass


def _claim(d: dict[str, Any]) -> Claim:
    missing = {"id", "body", "confidence"} - d.keys()
    if missing:
        raise PackError(f"claim missing required fields: {sorted(missing)}")
    return Claim(
        id=d["id"], body=d["body"], confidence=float(d["confidence"]),
        why_it_matters=d.get("why_it_matters", ""),
        sources=tuple(d.get("sources", ())), decays=d.get("decays"),
    )


def load_pack(path: Path) -> Pack:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackError(f"{path.name}: invalid JSON - {exc}") from exc
    missing = {"id", "version", "title", "claims"} - d.keys()
    if missing:
        raise PackError(f"{path.name}: missing {sorted(missing)}")
    return Pack(
        id=d["id"], version=d["version"], title=d["title"],
        authored_by=d.get("authored_by", "unknown"),
        authored_at=d.get("authored_at", ""),
        review_cadence_days=int(d.get("review_cadence_days", 30)),
        claims=tuple(_claim(c) for c in d["claims"]),
    )


def load_all(directory: Path | None = None) -> list[Pack]:
    d = directory or PACK_DIR
    if not d.exists():
        return []
    return [load_pack(p) for p in sorted(d.glob("*.json"))]


def as_context(packs: Iterable[Pack], *, include_expired: bool = True) -> str:
    """Render packs for the analyst's cached prefix."""
    out: list[str] = ["MAINTAINED KNOWLEDGE BASE", ""]
    for p in packs:
        out.append(f"## {p.title}  (pack {p.id} v{p.version}, authored {p.authored_at})")
        for c in p.claims:
            if c.expired and not include_expired:
                continue
            flag = f"  [{c.stale_warning}]" if c.stale_warning else ""
            out.append(f"- ({c.confidence:.2f}){flag} {c.body}")
            if c.why_it_matters:
                out.append(f"  WHY: {c.why_it_matters}")
        out.append("")
    return "\n".join(out)


@dataclass
class Diff:
    added: list[Claim] = field(default_factory=list)
    revised: list[tuple[Claim, Claim]] = field(default_factory=list)
    retired: list[Claim] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.added or self.revised or self.retired)

    def summary(self) -> str:
        return (f"+{len(self.added)} added, ~{len(self.revised)} revised, "
                f"-{len(self.retired)} retired")


def diff_packs(old: Pack | None, new: Pack) -> Diff:
    """Claim-level diff. This is what makes 'what changed last night' answerable."""
    d = Diff()
    old_map = {c.id: c for c in (old.claims if old else ())}
    new_map = {c.id: c for c in new.claims}
    for cid, c in new_map.items():
        prev = old_map.get(cid)
        if prev is None:
            d.added.append(c)
        elif prev.body != c.body or prev.confidence != c.confidence:
            d.revised.append((prev, c))
    for cid, c in old_map.items():
        if cid not in new_map:
            d.retired.append(c)
    return d
