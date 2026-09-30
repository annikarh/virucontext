"""Resolve a paper via Europe PMC and require OA full text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from xml.etree import ElementTree as ET

import httpx

SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
OA_PAGE = "https://europepmc.org/article/PMC/{pmcid}"

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
PMC_RE = re.compile(r"PMC\d+", re.I)
PMID_RE = re.compile(r"^(?:PMID:?\s*)?(\d{5,9})$", re.I)

MAX_CHARS = 100_000


class PaperNotFound(Exception):
    pass


class PaperNotOpenAccess(Exception):
    pass


@dataclass
class Paper:
    title: str
    authors: str
    journal: str
    year: str
    doi: str
    pmid: str
    pmcid: str
    is_oa: bool
    abstract: str
    oa_url: str
    full_text: str

    def to_public_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "is_oa": self.is_oa,
            "oa_url": self.oa_url,
            "abstract": self.abstract,
            "full_text_chars": len(self.full_text),
        }

    def meta_block(self) -> str:
        return "\n".join(
            [
                f"Title: {self.title}",
                f"Authors: {self.authors}",
                f"Journal: {self.journal} ({self.year})",
                f"DOI: {self.doi}",
                f"PMID: {self.pmid}",
                f"PMCID: {self.pmcid}",
                f"OA URL: {self.oa_url}",
                f"Abstract: {self.abstract}",
            ]
        )


def _to_query(raw: str) -> str:
    s = raw.strip()
    doi = DOI_RE.search(s)
    if doi:
        return f'DOI:"{doi.group(0).rstrip(").,")}"'
    pmc = PMC_RE.search(s)
    if pmc:
        return f"PMCID:{pmc.group(0).upper()}"
    pmid = PMID_RE.match(s)
    if pmid:
        return f"EXT_ID:{pmid.group(1)}"
    if s.startswith("http") and "pubmed" in s.lower():
        n = re.search(r"(\d{5,9})", s)
        if n:
            return f"EXT_ID:{n.group(1)}"
    if len(s) > 24 and " " in s and not s.startswith("http"):
        return f'TITLE:"{s}"'
    return s


def _search(query: str) -> dict | None:
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": 5,
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.get(SEARCH_URL, params=params)
        r.raise_for_status()
        data = r.json()
    results = (data.get("resultList") or {}).get("result") or []
    return results[0] if results else None


def _xml_to_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes.decode("utf-8", errors="replace")
    chunks: list[str] = []
    for node in root.iter():
        if node.text and node.text.strip():
            chunks.append(node.text.strip())
        if node.tail and node.tail.strip():
            chunks.append(node.tail.strip())
    text = "\n".join(chunks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_CHARS]


def _full_text(pmcid: str) -> str:
    url = FULLTEXT_URL.format(pmcid=pmcid)
    with httpx.Client(timeout=90.0) as client:
        r = client.get(url)
        if r.status_code == 404:
            raise PaperNotOpenAccess(
                f"{pmcid} is listed in Europe PMC but full text XML is not available. "
                "ViruContext will not guess from the abstract alone."
            )
        r.raise_for_status()
        return _xml_to_text(r.content)


def resolve_paper(raw_query: str) -> Paper:
    query = _to_query(raw_query)
    hit = _search(query)
    if hit is None and query.startswith("TITLE:"):
        hit = _search(raw_query.strip())
    if hit is None:
        raise PaperNotFound(
            "No Europe PMC hit for that title/DOI/ID. Check the identifier, or the paper may not be indexed."
        )

    pmcid = (hit.get("pmcid") or "").strip()
    is_oa = str(hit.get("isOpenAccess") or "").lower() in {"y", "yes", "true"}
    title = hit.get("title") or "(no title)"

    if not is_oa or not pmcid:
        raise PaperNotOpenAccess(
            f"'{title}' is not available as open-access full text in Europe PMC/PMC. "
            "ViruContext only summarizes OA full text."
        )

    full_text = _full_text(pmcid)
    if len(full_text) < 400:
        raise PaperNotOpenAccess(
            f"{pmcid} full text was too short to trust. Refusing to summarize."
        )

    return Paper(
        title=title,
        authors=hit.get("authorString") or "",
        journal=hit.get("journalTitle") or "",
        year=str(hit.get("pubYear") or ""),
        doi=hit.get("doi") or "",
        pmid=str(hit.get("pmid") or ""),
        pmcid=pmcid,
        is_oa=True,
        abstract=hit.get("abstractText") or "",
        oa_url=OA_PAGE.format(pmcid=pmcid.replace("PMC", "")) if pmcid else "",
        full_text=full_text,
    )
