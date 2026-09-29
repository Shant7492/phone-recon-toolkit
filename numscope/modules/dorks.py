"""Search-engine query (dork) generation.

Nothing here touches the network. We only build query strings and URLs;
the analyst decides which ones to open.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Sequence

from core.models import DorkQuery, PhoneMetadata

CATEGORIES: Dict[str, str] = {
    "general": "Exact-match mentions in any format",
    "documents": "Public documents and spreadsheets",
    "paste": "Public paste sites",
    "code": "Public code repositories",
    "directories": "Business / public directory listings",
    "social": "Social-platform footprints",
    "messaging": "Public click-to-chat links (WhatsApp)",
    "classifieds": "Classified-ad marketplaces",
    "reputation": "Spam / scam / caller-ID reports",
}

PASTE_SITES = [
    "pastebin.com", "paste.ee", "justpaste.it", "rentry.co",
    "controlc.com", "dpaste.org", "gist.github.com", "hastebin.com",
]
CODE_SITES = ["github.com", "gitlab.com", "bitbucket.org", "sourceforge.net"]
SOCIAL_SITES = [
    "facebook.com", "linkedin.com", "instagram.com", "x.com",
    "twitter.com", "reddit.com", "t.me", "tiktok.com",
]
CLASSIFIED_SITES = [
    "craigslist.org", "gumtree.com", "olx.com", "kijiji.ca",
    "mercadolibre.com", "ebay.com",
]
REPUTATION_SITES = [
    "800notes.com", "whocalledme.com", "shouldianswer.com", "tellows.com",
    "callercenter.com", "spamcalls.net", "truecaller.com", "sync.me",
]
GLOBAL_DIRECTORIES = ["yelp.com", "foursquare.com", "kompass.com"]
REGIONAL_DIRECTORIES: Dict[str, List[str]] = {
    "US": ["yellowpages.com", "bbb.org", "manta.com"],
    "CA": ["yellowpages.ca", "bbb.org"],
    "GB": ["yell.com", "thomsonlocal.com", "checkatrade.com"],
    "IN": ["justdial.com", "indiamart.com", "sulekha.com"],
    "AU": ["yellowpages.com.au", "truelocal.com.au"],
    "DE": ["gelbeseiten.de", "dasoertliche.de"],
    "FR": ["pagesjaunes.fr"],
}

_GROUP_SIZE = 3
_SITES_PER_QUERY = 4


def _quote(value: str) -> str:
    return '"' + value.replace('"', "") + '"'


def _or_group(values: Sequence[str]) -> str:
    quoted = [_quote(v) for v in values]
    return quoted[0] if len(quoted) == 1 else "(" + " OR ".join(quoted) + ")"


def _site_clause(domains: Iterable[str]) -> str:
    items = [f"site:{d}" for d in domains]
    return items[0] if len(items) == 1 else "(" + " OR ".join(items) + ")"


def _chunks(items: Sequence[str], size: int) -> List[Sequence[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _dedupe(items: Iterable[Optional[str]]) -> List[str]:
    return list(dict.fromkeys(i for i in items if i))


class DorkGenerator:
    """Builds dork queries from a PhoneMetadata record."""

    def __init__(self, meta: PhoneMetadata) -> None:
        self.meta = meta
        self.variants = self._build_variants()
        self.wa_digits = self._whatsapp_digits()
        self._builders: Dict[str, Callable[[], List[DorkQuery]]] = {
            "general": self._general,
            "documents": self._documents,
            "paste": self._paste,
            "code": self._code,
            "directories": self._directories,
            "social": self._social,
            "messaging": self._messaging,
            "classifieds": self._classifieds,
            "reputation": self._reputation,
        }

    # -- variants ---------------------------------------------------------
    def _build_variants(self) -> List[str]:
        m = self.meta
        if m.parsed:
            nsn = m.national_number or ""
            extra: List[str] = []
            if m.country_code == 1 and len(nsn) == 10:
                a, b, c = nsn[:3], nsn[3:6], nsn[6:]
                extra += [f"{a}-{b}-{c}", f"{a}.{b}.{c}", f"({a}) {b}-{c}"]
            if len(nsn) >= 8:
                extra.append(nsn)
            return _dedupe([m.e164, m.international, m.national] + extra)
        if 7 <= len(m.digits) <= 15:
            return _dedupe([m.raw_input.strip(), m.digits])
        return []

    def _whatsapp_digits(self) -> Optional[str]:
        m = self.meta
        if m.parsed:
            return f"{m.country_code}{m.national_number}"
        return m.digits if 7 <= len(m.digits) <= 15 else None

    def _primary(self) -> str:
        return _or_group(self.variants[:_GROUP_SIZE])

    # -- public API -------------------------------------------------------
    def generate(self, categories: Optional[Sequence[str]] = None
                 ) -> List[DorkQuery]:
        if not self.variants:
            return []
        selected = list(categories) if categories else list(CATEGORIES)
        queries: List[DorkQuery] = []
        for name in selected:
            queries.extend(self._builders[name]())
        return queries

    # -- builders ---------------------------------------------------------
    def _site_queries(self, category: str, label: str,
                      domains: Sequence[str]) -> List[DorkQuery]:
        primary = self._primary()
        return [
            DorkQuery(category, f"{label}: {', '.join(chunk)}",
                      f"{primary} {_site_clause(chunk)}")
            for chunk in _chunks(list(domains), _SITES_PER_QUERY)
        ]

    def _general(self) -> List[DorkQuery]:
        out = [DorkQuery("general", "Exact match, main formats",
                         self._primary())]
        alt = self.variants[_GROUP_SIZE:_GROUP_SIZE * 2]
        if alt:
            out.append(DorkQuery("general", "Exact match, alternate formats",
                                 _or_group(alt)))
        out.append(DorkQuery(
            "general", "Mentioned alongside contact keywords",
            f'{self._primary()} ("contact" OR "call" OR "whatsapp" '
            f'OR "phone" OR "mobile")'))
        return out

    def _documents(self) -> List[DorkQuery]:
        p = self._primary()
        return [
            DorkQuery("documents", "Text documents / PDFs",
                      f"{p} (filetype:pdf OR filetype:doc OR filetype:docx "
                      f"OR filetype:txt)"),
            DorkQuery("documents", "Spreadsheets / CSV",
                      f"{p} (filetype:xls OR filetype:xlsx OR filetype:csv "
                      f"OR filetype:ods)"),
        ]

    def _paste(self) -> List[DorkQuery]:
        return self._site_queries("paste", "Paste sites", PASTE_SITES)

    def _code(self) -> List[DorkQuery]:
        return self._site_queries("code", "Code hosts", CODE_SITES)

    def _directories(self) -> List[DorkQuery]:
        region = self.meta.region_code or ""
        domains = _dedupe(REGIONAL_DIRECTORIES.get(region, [])
                          + GLOBAL_DIRECTORIES)
        return self._site_queries("directories", "Directories", domains)

    def _social(self) -> List[DorkQuery]:
        return self._site_queries("social", "Social", SOCIAL_SITES)

    def _classifieds(self) -> List[DorkQuery]:
        return self._site_queries("classifieds", "Classifieds",
                                  CLASSIFIED_SITES)

    def _messaging(self) -> List[DorkQuery]:
        d = self.wa_digits
        if not d:
            return []
        query = (f'("wa.me/{d}" OR "api.whatsapp.com/send?phone={d}" '
                 f'OR "whatsapp.com/send/?phone={d}")')
        return [DorkQuery("messaging", "Public WhatsApp click-to-chat links",
                          query)]

    def _reputation(self) -> List[DorkQuery]:
        out = self._site_queries("reputation", "Reputation sites",
                                 REPUTATION_SITES)
        out.append(DorkQuery(
            "reputation", "Spam/scam keywords (any site)",
            f'{self._primary()} ("scam" OR "spam" OR "fraud" OR "robocall" '
            f'OR "telemarketer")'))
        return out
