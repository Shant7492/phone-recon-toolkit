"""Rendering: rich tables, plain text, and JSON."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Sequence

from core import __version__
from core.models import ENGINE_LABELS, ScanReport


def report_to_dict(report: ScanReport, engines: Sequence[str]) -> Dict[str, Any]:
    data = asdict(report)
    data["dorks"] = [
        {
            "category": d.category,
            "description": d.description,
            "query": d.query,
            "urls": {e: d.url(e) for e in engines},
        }
        for d in report.dorks
    ]
    return data


def render_json(reports: Sequence[ScanReport], engines: Sequence[str]) -> str:
    payload = {
        "tool": "numscope",
        "version": __version__,
        "results": [report_to_dict(r, engines) for r in reports],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _metadata_rows(report: ScanReport) -> List[tuple]:
    m = report.metadata
    if not m.parsed:
        return [("Input", m.raw_input), ("Parsed", "no"),
                ("Reason", m.parse_error or "-")]
    return [
        ("Input", m.raw_input),
        ("E.164", m.e164),
        ("International", m.international),
        ("National", m.national),
        ("RFC 3966", m.rfc3966),
        ("Country / region", f"{m.country or '-'} ({m.region_code}), "
                             f"+{m.country_code}"),
        ("Possible", f"{'yes' if m.is_possible else 'no'} - "
                     f"{m.possible_reason}"),
        ("Valid", "yes" if m.is_valid else "no"),
        ("Line type", m.number_type),
        ("Carrier (original)", m.carrier or "unknown / not published"),
        ("Location", m.location or "unknown"),
        ("Time zones", ", ".join(m.timezones) or "unknown"),
    ]


def render_plain(reports: Sequence[ScanReport], engines: Sequence[str]) -> str:
    lines: List[str] = []
    for r in reports:
        lines.append("=" * 72)
        lines.append(f"TARGET: {r.metadata.e164 or r.metadata.raw_input}")
        lines.append("=" * 72)
        lines.append("[Metadata]")
        lines += [f"  {k:<20} {v}" for k, v in _metadata_rows(r)]
        if r.risk:
            lines.append(f"\n[Risk] {r.risk.score}/100  {r.risk.level}")
            lines += [f"  +{f.points:<3} {f.name}: {f.detail}"
                      for f in r.risk.factors] or ["  (no risk factors)"]
            lines += [f"  note: {n}" for n in r.risk.notes]
        if r.providers:
            lines.append("\n[Providers]")
            for p in r.providers:
                if p.ok:
                    lines.append(f"  {p.provider}: " + ", ".join(
                        f"{k}={v}" for k, v in p.data.items()))
                else:
                    lines.append(f"  {p.provider}: ERROR {p.error}")
                lines += [f"    note: {n}" for n in p.notes]
        if r.dorks:
            lines.append("\n[Search queries]")
            for d in r.dorks:
                lines.append(f"  [{d.category}] {d.description}")
                lines.append(f"    {d.query}")
                lines += [f"    {ENGINE_LABELS[e]}: {d.url(e)}"
                          for e in engines]
        lines.append("")
    return "\n".join(lines)


def render_rich(reports: Sequence[ScanReport], engines: Sequence[str]) -> None:
    from rich import box
    from rich.console import Console
    from rich.markup import escape
    from rich.panel import Panel
    from rich.style import Style
    from rich.table import Table
    from rich.text import Text

    console = Console()
    level_style = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red",
                   "CRITICAL": "bold white on red"}

    for r in reports:
        title = r.metadata.e164 or r.metadata.raw_input
        console.rule(f"[bold cyan]{escape(title)}")

        table = Table(box=box.ROUNDED, show_header=False, title="Metadata")
        table.add_column(style="bold")
        table.add_column()
        for key, value in _metadata_rows(r):
            table.add_row(key, escape(str(value)))
        console.print(table)

        if r.risk:
            style = level_style.get(r.risk.level, "white")
            body = Table(box=None, show_header=False, padding=(0, 1))
            body.add_column(justify="right")
            body.add_column(style="bold")
            body.add_column()
            for f in r.risk.factors:
                body.add_row(f"+{f.points}", escape(f.name), escape(f.detail))
            if not r.risk.factors:
                body.add_row("", "No risk factors triggered", "")
            notes = "\n".join(f"[dim]note: {escape(n)}[/dim]"
                              for n in r.risk.notes)
            console.print(Panel.fit(
                Text(f"{r.risk.score}/100  {r.risk.level}", style=style),
                title="Risk score", border_style=style.split()[-1]))
            console.print(body)
            console.print(notes)

        if r.providers:
            ptable = Table(box=box.SIMPLE_HEAVY, title="Provider results")
            ptable.add_column("Provider", style="bold")
            ptable.add_column("Result")
            for p in r.providers:
                if p.ok:
                    text = ", ".join(f"{k}={v}" for k, v in p.data.items())
                else:
                    text = f"[red]ERROR[/red] {p.error}"
                text += "".join(f"\n[dim]{escape(n)}[/dim]" for n in p.notes)
                ptable.add_row(p.provider, text)
            console.print(ptable)

        if r.dorks:
            dtable = Table(box=box.ROUNDED, title="Search queries (click to open)",
                           show_lines=True)
            dtable.add_column("Category", style="bold magenta")
            dtable.add_column("Query", overflow="fold", ratio=3)
            dtable.add_column("Open", no_wrap=True)
            for d in r.dorks:
                links = Text()
                for engine in engines:
                    links.append(ENGINE_LABELS[engine], style=Style(
                        link=d.url(engine), color="cyan", underline=True))
                    links.append("  ")
                dtable.add_row(d.category,
                               f"[dim]{escape(d.description)}[/dim]\n"
                               f"{escape(d.query)}", links)
            console.print(dtable)
        console.print()
