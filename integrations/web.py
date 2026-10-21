"""
Web research for the assistant: search + page fetch, cached and SSRF-guarded.

search(): Tavily when TAVILY_API_KEY is set; otherwise Google News RSS (keyless, dated, with the
          publisher) and DuckDuckGo HTML as a last resort (it often answers bots with a challenge page).
fetch():  GET a public http(s) page, extract readable text (trafilatura → BeautifulSoup fallback).
Both cache in `api_cache` for WEB_CACHE_MINUTES. Queries without cricket vocabulary get
"cricket" appended so results stay on topic.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import parse_qs, quote_plus, urlparse

import xml.etree.ElementTree as ET

import httpx

from backend.config import settings
from backend.models import ApiCache

logger = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; XithSenseBot/1.0; +https://github.com/vincenzo-afk/xithsense)"
CRICKET_WORDS = re.compile(
    r"\b(cricket|ipl|t20|odi|test match|bbl|psl|cpl|wpl|wicket|batter|batsman|bowler|innings|over|captain|"
    r"playing xi|squad|toss|pitch|dream11|fantasy|icc|bcci|series|match|team|player|run[s]?|spinner|pacer)\b", re.I)
PREFERRED_DOMAINS = ("espncricinfo.com", "cricbuzz.com", "icc-cricket.com", "bcci.tv", "cricsheet.org",
                     "cricket.com.au", "ecb.co.uk", "iplt20.com", "wisden.com", "thecricketer.com", "news18.com",
                     "indianexpress.com", "hindustantimes.com", "timesofindia.indiatimes.com", "bbc.co.uk",
                     "theguardian.com", "sportstar.thehindu.com")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cricket_query(q: str) -> str:
    q = q.strip()
    return q if CRICKET_WORDS.search(q) else f"{q} cricket"


# ── SSRF guard ────────────────────────────────────────────────────────────────

def _private_ip(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast or a.is_unspecified


async def is_safe_url(url: str) -> bool:
    """Only public http(s) hosts; resolves the name and rejects private / loopback / link-local ranges."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    host = u.hostname.lower()
    if host in ("localhost",) or host.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        infos = await asyncio.get_running_loop().run_in_executor(None, socket.getaddrinfo, host, u.port or 80)
    except socket.gaierror:
        return False
    return bool(infos) and all(not _private_ip(i[4][0]) for i in infos)


# ── cache ─────────────────────────────────────────────────────────────────────

async def _cached(db, key: str):
    row = await db.get(ApiCache, key)
    if row and _now() - row.fetched_at < timedelta(minutes=settings.WEB_CACHE_MINUTES):
        return row.payload
    return None


async def _store(db, key: str, payload) -> None:
    row = await db.get(ApiCache, key)
    if row:
        row.payload, row.fetched_at = payload, _now()
    else:
        db.add(ApiCache(key=key[:300], payload=payload, hits_cost=0, fetched_at=_now()))
    await db.commit()


# ── search ────────────────────────────────────────────────────────────────────

def parse_ddg_html(html: str, limit: int = 8) -> List[dict]:
    """Parse DuckDuckGo's HTML results page into [{title, url, snippet}]."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    out: List[dict] = []
    for res in soup.select(".result"):
        a = res.select_one("a.result__a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        if "uddg=" in href:
            href = parse_qs(urlparse(href).query).get("uddg", [href])[0]
        if href.startswith("//"):
            href = "https:" + href
        snippet_el = res.select_one(".result__snippet")
        out.append({"title": a.get_text(" ", strip=True), "url": href,
                    "snippet": snippet_el.get_text(" ", strip=True) if snippet_el else ""})
        if len(out) >= limit:
            break
    return out


def parse_google_news_rss(xml_text: str, limit: int = 8) -> List[dict]:
    """Google News RSS → [{title, url, snippet, source, published}]. The description HTML carries the
    publisher link, which fetch_page can read directly; the news.google.com link is the fallback."""
    from bs4 import BeautifulSoup
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out: List[dict] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc_html = item.findtext("description") or ""
        soup = BeautifulSoup(desc_html, "lxml")
        a = soup.find("a", href=True)
        url = a["href"] if a and a["href"].startswith("http") and "news.google.com" not in a["href"] else link
        src = item.find("source")
        source = (src.text or "").strip() if src is not None else ""
        snippet = soup.get_text(" ", strip=True)
        if source and snippet.endswith(source):
            snippet = snippet[: -len(source)].strip(" -–|")
        if title and url:
            out.append({"title": title, "url": url, "snippet": snippet[:300], "source": source,
                        "published": (item.findtext("pubDate") or "").strip()})
        if len(out) >= limit:
            break
    return out


def _rank(results: List[dict]) -> List[dict]:
    def score(r):
        host = urlparse(r.get("url", "")).hostname or ""
        return 0 if any(host.endswith(d) for d in PREFERRED_DOMAINS) else 1
    return sorted(results, key=score)


async def search(db, query: str, max_results: int = 5) -> List[dict]:
    """Web search limited to cricket context. Returns [] when disabled or the provider fails."""
    if not settings.WEB_SEARCH_ENABLED:
        return []
    q = cricket_query(query)[:200]
    key = f"web:search:{q.lower()}"
    cached = await _cached(db, key)
    if cached is not None:
        return cached[:max_results]
    results: List[dict] = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": UA}) as client:
            if settings.TAVILY_API_KEY:
                r = await client.post("https://api.tavily.com/search",
                                      json={"api_key": settings.TAVILY_API_KEY, "query": q, "max_results": 8,
                                            "search_depth": "basic", "include_answer": False})
                r.raise_for_status()
                results = [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": (x.get("content") or "")[:300],
                            "source": urlparse(x.get("url", "")).hostname or ""} for x in r.json().get("results", [])]
            if not results:
                r = await client.get("https://news.google.com/rss/search",
                                     params={"q": q, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
                if r.status_code == 200:
                    results = parse_google_news_rss(r.text)
            if not results:
                r = await client.post("https://html.duckduckgo.com/html/", data={"q": q},
                                      headers={"Content-Type": "application/x-www-form-urlencoded"})
                if r.status_code == 200:
                    results = parse_ddg_html(r.text)
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("web search failed for %r: %s", q, e)
    results = _rank([x for x in results if x.get("url", "").startswith("http")])
    if results:
        await _store(db, key, results)
    return results[:max_results]


# ── fetch ─────────────────────────────────────────────────────────────────────

def extract_text(html: str, url: str = "") -> tuple[str, str]:
    """(title, readable text) from HTML."""
    title, text = "", ""
    try:
        import trafilatura
        text = trafilatura.extract(html, url=url or None, include_comments=False, include_tables=True) or ""
        meta = trafilatura.extract_metadata(html)
        title = (meta.title if meta else "") or ""
    except Exception:  # pragma: no cover - optional dependency path
        pass
    if len(text) < 200:          # tiny / boilerplate-heavy pages: strip chrome ourselves
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for t in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
            t.decompose()
        title = title or (soup.title.get_text(strip=True) if soup.title else "")
        text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    return title.strip(), text.strip()


async def fetch(db, url: str) -> Optional[dict]:
    """Fetch a public page and return {url, title, text, fetched_at}; None when blocked or failed."""
    if not settings.WEB_SEARCH_ENABLED or not await is_safe_url(url):
        return None
    key = f"web:page:{url}"
    cached = await _cached(db, key)
    if cached:
        return cached
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": UA}) as client:
            async with client.stream("GET", url) as r:
                if r.status_code >= 400:
                    return None
                ctype = r.headers.get("content-type", "")
                if not any(t in ctype for t in ("text/html", "text/plain", "application/xhtml")):
                    return None
                body = b""
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > 2_000_000:
                        break
                html = body.decode(r.encoding or "utf-8", errors="replace")
    except httpx.HTTPError as e:
        logger.warning("fetch failed for %s: %s", url, e)
        return None
    title, text = await asyncio.get_running_loop().run_in_executor(None, extract_text, html, url)
    page = {"url": url, "title": title, "text": text[: settings.WEB_FETCH_MAX_CHARS],
            "truncated": len(text) > settings.WEB_FETCH_MAX_CHARS, "fetched_at": _now().isoformat()}
    await _store(db, key, page)
    return page


def search_url(query: str) -> str:
    return f"https://duckduckgo.com/?q={quote_plus(cricket_query(query))}"
