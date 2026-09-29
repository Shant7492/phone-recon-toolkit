#!/usr/bin/env python3
"""numscope - offline-first phone number OSINT / metadata CLI."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence

import phonenumbers

from core import __version__
from core import report as reporting
from core.analyzer import PhoneAnalyzer
from core.config import Config
from core.models import ENGINE_LABELS, ProviderResult, ScanReport
from modules.dorks import CATEGORIES, DorkGenerator
from modules.providers import PROVIDERS, load_providers
from modules.providers.base import BaseProvider
from modules.risk import RiskScorer

BANNER = (
    f"numscope {__version__} - authorised OSINT and security research only.\n"
    "Do not use it to stalk, harass or profile individuals. You are "
    "responsible for complying with applicable law (GDPR, CCPA, TCPA...)."
)


def _csv(valid: Sequence[str]) -> Callable[[str], List[str]]:
    def parse(value: str) -> List[str]:
        items = [v.strip().lower() for v in value.split(",") if v.strip()]
        bad = [i for i in items if i not in valid]
        if bad:
            raise argparse.ArgumentTypeError(
                f"unknown value(s): {', '.join(bad)} "
                f"(choose from: {', '.join(valid)})")
        return items
    return parse


def _region(value: str) -> str:
    code = value.strip().upper()
    if code not in phonenumbers.SUPPORTED_REGIONS:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a supported ISO 3166-1 alpha-2 region")
    return code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="numscope",
        description="Phone number metadata, dork generation and risk scoring.",
        epilog="Example: python cli.py '+1 415 555 2671' --format json")
    p.add_argument("numbers", nargs="*", metavar="NUMBER",
                   help="phone number(s); prefer international format")
    p.add_argument("-f", "--file", type=Path,
                   help="file with one number per line (# comments allowed)")
    p.add_argument("-r", "--region", type=_region, metavar="CC",
                   help="default region for national-format numbers, and the "
                        "'home' region for the origin check (e.g. US, IN)")
    p.add_argument("--offline", action="store_true",
                   help="guarantee zero network calls (skips all providers)")
    p.add_argument("--provider", action="append", choices=sorted(PROVIDERS),
                   help="restrict to a provider (repeatable)")
    p.add_argument("--no-dorks", action="store_true",
                   help="skip search-query generation")
    p.add_argument("--no-risk", action="store_true",
                   help="skip risk scoring")
    p.add_argument("--categories", type=_csv(list(CATEGORIES)),
                   metavar="LIST",
                   help="comma-separated dork categories: "
                        + ", ".join(CATEGORIES))
    p.add_argument("--engines", type=_csv(list(ENGINE_LABELS)),
                   default=list(ENGINE_LABELS), metavar="LIST",
                   help="comma-separated engines (default: all)")
    p.add_argument("--format", choices=("table", "plain", "json"),
                   default="table", help="output format (default: table)")
    p.add_argument("-o", "--output", type=Path,
                   help="write output to a file (table falls back to plain)")
    p.add_argument("--env-file", help="path to a .env file")
    p.add_argument("--no-banner", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version",
                   version=f"numscope {__version__}")
    return p


def gather_numbers(args: argparse.Namespace) -> List[str]:
    numbers = list(args.numbers)
    if args.file:
        try:
            lines = args.file.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise SystemExit(f"error: cannot read {args.file}: {exc}")
        numbers += [ln.strip() for ln in lines
                    if ln.strip() and not ln.lstrip().startswith("#")]
    return list(dict.fromkeys(numbers))


def _safe_lookup(provider: BaseProvider, meta) -> ProviderResult:
    try:
        return provider.lookup(meta)
    except Exception as exc:  # noqa: BLE001 - plugins must never crash us
        logging.getLogger(__name__).debug("provider failure", exc_info=True)
        return ProviderResult(provider.name, False,
                              error=f"unexpected {type(exc).__name__}")


def scan(raw: str, analyzer: PhoneAnalyzer, scorer: RiskScorer,
         providers: Sequence[BaseProvider], categories: Optional[List[str]],
         run_dorks: bool, run_risk: bool) -> ScanReport:
    meta = analyzer.analyze(raw)
    dorks = DorkGenerator(meta).generate(categories) if run_dorks else []

    results: List[ProviderResult] = []
    for provider in providers:
        if not meta.is_possible:
            results.append(ProviderResult(
                provider.name, False,
                error="skipped: offline check says number is not possible"))
        else:
            results.append(_safe_lookup(provider, meta))

    risk = scorer.assess(meta, results) if run_risk else None
    return ScanReport(meta, dorks, risk, results)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    numbers = gather_numbers(args)
    if not numbers:
        parser.error("provide at least one NUMBER or --file")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    if not args.no_banner:
        print(BANNER, file=sys.stderr)

    config = Config.from_env(args.env_file)
    providers: List[BaseProvider] = []
    if not args.offline:
        try:
            providers, skipped = load_providers(config, args.provider)
        except ValueError as exc:
            parser.error(str(exc))
        if skipped and args.verbose:
            print(f"info: providers without credentials skipped: "
                  f"{', '.join(skipped)}", file=sys.stderr)

    analyzer = PhoneAnalyzer(default_region=args.region)
    scorer = RiskScorer(home_region=args.region)
    reports = [scan(n, analyzer, scorer, providers, args.categories,
                    not args.no_dorks, not args.no_risk) for n in numbers]

    if args.format == "json":
        text: Optional[str] = reporting.render_json(reports, args.engines)
    elif args.format == "plain" or args.output:
        text = reporting.render_plain(reports, args.engines)
    else:
        text = None

    if args.output:
        args.output.write_text(text or "", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    elif text is not None:
        print(text)
    else:
        reporting.render_rich(reports, args.engines)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # e.g. `numscope ... | head`
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
