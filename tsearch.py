#!/usr/bin/env python3
"""Terminal Search: multilingual, bilingual, ad-filtered terminal search."""

import atexit
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table


console = Console()
CONFIG_PATH = Path.home() / ".tsearch.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
REQUEST_TIMEOUT = (4, 8)
MAX_ARTICLE_BYTES = 2_000_000
DEFAULT_POOL = ["google", "bing", "duckduckgo", "yahoo", "baidu", "brave"]
CUSTOM_PREFIX = "custom:"
CONFIG_VERSION = 4
BROWSER_MODES = ("off", "chromium", "safari", "edge")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    score: float = 0.0
    score_details: dict = None


class SearchPageError(RuntimeError):
    """A successful HTTP response that is not a readable search-result page."""


class ProviderFallbackError(RuntimeError):
    """All endpoints failed; keep every endpoint's own diagnostic."""


class BrowserUnavailableError(RuntimeError):
    """The selected browser automation backend is unavailable or cannot launch."""


HELP_TEXT = """
Commands / 命令
  :new                 Start a new topic / 开始新话题
  :next / n            Load more results, then next page / 继续抓取并进入下一页
  :prev / p            Previous page / 上一页
  :open <number>       Open a result / 打开指定编号的结果
  :summary <number>    Summarize a result page / 提取指定网页的段落摘要
  :score <number>      Explain a relevance score / 查看指定结果的相关性计算明细
  :stats               Explain the result count / 查看结果数量的处理统计
  :errors              Show detailed engine errors / 查看引擎失败的详细原因
  :pool <names>        Set engines or add domains / 设置引擎或直接添加域名
  :pool reset          Restore the default pool / 恢复默认搜索池
  :lang auto|<code>    Set result language / 设置搜索结果语言
  :filter on|off       Toggle ad and junk filtering / 开关广告及垃圾内容过滤
  :browser off         Static requests only / 仅使用静态请求
  :browser on          Render failed engines in Chromium / 用 Chromium 渲染失败引擎
  :browser safari      Google fallback in your Safari session / Google 使用 Safari 同会话回退
  :browser edge        Google fallback in installed Edge / Google 使用已安装的 Edge 回退
  :browser check       Test Safari permissions with about:blank / 用 about:blank 检测 Safari 权限
  :browser setup       Open Safari permission setup / 打开 Safari 权限设置引导
  :exit / q            Quit / 退出

Language / 语言
  auto means no added language restriction / auto 表示不附加语言限制
  Examples / 示例：:lang zh、:lang en、:lang ja、:lang fr、:lang zh-CN
  This changes the search language, not the bilingual interface.
  此命令只改变搜索语言，不改变中英双语界面。

Search engines / 搜索引擎
  :pool                         List engines / 查看引擎
  :pool google,bing,yahoo      Use named engines / 使用指定内置引擎
  :pool yahoo                  Use Yahoo Global only / 仅使用全球 Yahoo
  :pool yahoojp                Use Yahoo Japan only / 仅使用雅虎日本
  :pool yahoo.hk               Add a custom domain / 添加自定义域名引擎
  :pool google,yahoo.co.jp,baidu.com
                               Mix built-ins and domains / 混合使用内置引擎与域名
  Custom domains use a best-effort parser and follow site redirects.
  自定义域名会尽力解析网页，并跟随网站自身跳转；能否使用取决于网站和网络。
  Browser fallback keeps the same engine URL and never solves CAPTCHA for you.
  浏览器回退使用原引擎地址，不会替你自动破解验证码。
  Safari mode is macOS-only; Edge mode is Windows-only. Both handle Google only.
  Safari 模式仅支持 macOS，Edge 模式仅支持 Windows；两者目前都只处理 Google。
  Edge mode uses a dedicated profile, not your everyday Edge profile.
  Edge 模式使用独立配置，不会读取你的日常 Edge 配置。

Relevance / 相关性
  Score = (3 × title hits + snippet hits) / query token count.
  分数 =（3 × 标题命中数 + 摘要命中数）÷ 查询词元数。
  Scores only sort results and never remove them. / 分数仅排序，从不过滤结果。

Summaries / 摘要
  Result rows preview the first, second, and last available text units.
  搜索结果会预览现有文本的首段、次段和末段。
  :summary <number> fetches that page and previews P1, P2, and Last.
  :summary <编号> 会读取对应网页，并分别显示首段、次段和末段的开头。
""".strip()


AD_HOSTS = {
    "doubleclick.net",
    "googleadservices.com",
    "googlesyndication.com",
    "google-analytics.com",
    "ad.doubleclick.net",
    "adservice.google.com",
    "ads.yahoo.com",
    "adserver.yahoo.com",
    "ads.baidu.com",
}

AD_LABEL_RE = re.compile(
    r"(?:^|[\s|·•\[(【])"
    r"(?:ad|ads|sponsored|promoted|advertisement|广告|推广|赞助内容)"
    r"(?:$|[\s|·•\])】])",
    re.IGNORECASE,
)

BOILERPLATE_RE = re.compile(
    r"^(?:subscribe|sign up|newsletter|advertisement|share this|"
    r"all rights reserved|cookie settings|订阅|注册|广告|分享本文|版权所有)",
    re.IGNORECASE,
)

LANGUAGE_MARKETS = {
    "ar": "ar-SA",
    "de": "de-DE",
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "it": "it-IT",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "nl": "nl-NL",
    "pt": "pt-BR",
    "ru": "ru-RU",
    "zh": "zh-CN",
}

DUCKDUCKGO_REGIONS = {
    "de": "de-de",
    "en": "us-en",
    "es": "es-es",
    "fr": "fr-fr",
    "it": "it-it",
    "ja": "jp-jp",
    "ko": "kr-kr",
    "nl": "nl-nl",
    "pt": "br-pt",
    "ru": "ru-ru",
    "zh": "cn-zh",
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def shorten(text: str, limit: int) -> str:
    text = clean_text(text)
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def split_text_units(text: str) -> List[str]:
    """Split real paragraphs first; use sentences as a snippet fallback."""
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    paragraphs = [clean_text(p) for p in re.split(r"\n\s*\n|\n", normalized)]
    paragraphs = [p for p in paragraphs if p]
    if len(paragraphs) > 1:
        return paragraphs
    sentences = re.split(
        r"(?<=[。！？!?；;])|(?<=[.!?])\s+(?=[A-Z0-9])",
        paragraphs[0],
    )
    return [clean_text(s) for s in sentences if clean_text(s)]


def paragraph_preview(text_or_paragraphs, width: int = 72) -> str:
    if isinstance(text_or_paragraphs, str):
        units = split_text_units(text_or_paragraphs)
    else:
        units = [clean_text(p) for p in text_or_paragraphs if clean_text(p)]
    if not units:
        return ""
    if len(units) == 1:
        selected = [("P1 首段", units[0])]
    elif len(units) == 2:
        selected = [("P1 首段", units[0]), ("Last 末段", units[-1])]
    else:
        selected = [
            ("P1 首段", units[0]),
            ("P2 次段", units[1]),
            ("Last 末段", units[-1]),
        ]
    return "  |  ".join(f"{label}: {shorten(text, width)}" for label, text in selected)


def tokenize(text: str) -> List[str]:
    """Unicode-friendly tokens; no language-specific query detection."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    words = re.findall(r"[^\W_]+", text, flags=re.UNICODE)
    tokens = list(words)
    for word in words:
        if re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", word):
            tokens.extend(word)
            tokens.extend(word[i : i + 2] for i in range(len(word) - 1))
    return tokens


def relevance_breakdown(query: str, title: str, snippet: str) -> dict:
    """Return a transparent ranking score; it never filters results."""
    query_tokens = set(tokenize(query))
    title_tokens = set(tokenize(title))
    snippet_tokens = set(tokenize(snippet))
    title_matches = sorted(query_tokens & title_tokens)
    snippet_matches = sorted(query_tokens & snippet_tokens)
    query_count = len(query_tokens)
    score = (
        (len(title_matches) * 3.0 + len(snippet_matches)) / query_count
        if query_count
        else 0.0
    )
    return {
        "score": score,
        "query_tokens": sorted(query_tokens),
        "query_count": query_count,
        "title_matches": title_matches,
        "snippet_matches": snippet_matches,
        "title_hits": len(title_matches),
        "snippet_hits": len(snippet_matches),
    }


def relevance_score(query: str, title: str, snippet: str) -> float:
    return relevance_breakdown(query, title, snippet)["score"]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("www."):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if "duckduckgo.com" in host and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                url = unquote(target)
        elif "google." in host and parsed.path == "/url":
            target = parse_qs(parsed.query).get("q", [""])[0]
            if target:
                url = unquote(target)
        elif "search.yahoo." in host and "/RU=" in parsed.path:
            match = re.search(r"/RU=([^/]+)", parsed.path)
            if match:
                url = unquote(match.group(1))
    except (ValueError, UnicodeError):
        pass
    return url


def valid_web_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def is_ad_or_junk(title: str, snippet: str, url: str) -> bool:
    """Filter explicit ad labels and known ad hosts, not ordinary topic words."""
    try:
        host = (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return True
    if any(host == domain or host.endswith("." + domain) for domain in AD_HOSTS):
        return True
    lowered_path = urlparse(url).path.lower()
    if any(marker in lowered_path for marker in ("/adserver", "/doubleclick")):
        return True
    return bool(AD_LABEL_RE.search(f"{title or ''} {snippet or ''}"))


def dedupe(results: Iterable[SearchResult]) -> List[SearchResult]:
    seen = set()
    output = []
    for result in results:
        key = result.url.split("#", 1)[0].rstrip("/").lower()
        if key and key not in seen:
            seen.add(key)
            output.append(result)
    return output


def valid_language_code(code: str) -> bool:
    return code == "auto" or bool(
        re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", code)
    )


def language_name(code: str) -> str:
    if code == "auto":
        return "auto (no restriction / 不限制)"
    return code


def browser_mode_label(mode: str) -> str:
    return {
        "off": "off / 关",
        "chromium": "Chromium",
        "safari": "Safari (Google only / 仅 Google)",
        "edge": "Edge (Google only / 仅 Google)",
    }.get(mode, "off / 关")


def load_config() -> dict:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_config(
    lang: str,
    pool: Sequence[str],
    filter_ads: bool,
    custom_engines: dict = None,
    browser_fallback: bool = False,
    browser_mode: str = None,
) -> None:
    if browser_mode not in BROWSER_MODES:
        browser_mode = "chromium" if browser_fallback else "off"
    data = {
        "config_version": CONFIG_VERSION,
        "lang": lang,
        "pool": list(pool),
        "filter_ads": filter_ads,
        "custom_engines": sorted((custom_engines or {}).values()),
        # Keep the old boolean so an older version does not enable an unknown mode.
        "browser_fallback": browser_mode == "chromium",
        "browser_mode": browser_mode,
    }
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError:
        # Search remains usable if the home directory is not writable.
        pass


def request_headers(lang: str = "auto") -> dict:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        # A wildcard expresses no language preference instead of omitting the header.
        "Accept-Language": "*",
        "Upgrade-Insecure-Requests": "1",
    }
    if lang != "auto":
        headers["Accept-Language"] = lang
    return headers


class BingProvider:
    name = "bing"

    def __init__(self):
        self.session = requests.Session()
        self.next_urls = {}

    def search(
        self, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        key = (query, lang)
        params = {"q": query, "count": 10, "first": (page - 1) * 10 + 1}
        if page > 1:
            params["FORM"] = "PAGING"
        if lang != "auto":
            params["setlang"] = lang
            base_lang = lang.lower().split("-", 1)[0]
            if base_lang in LANGUAGE_MARKETS:
                params["mkt"] = LANGUAGE_MARKETS[base_lang]
        next_url = self.next_urls.get(key) if page > 1 else None
        if next_url:
            response = self.session.get(
                next_url,
                headers=request_headers(lang),
                timeout=REQUEST_TIMEOUT,
            )
        else:
            response = self.session.get(
                "https://www.bing.com/search",
                params=params,
                headers=request_headers(lang),
                timeout=REQUEST_TIMEOUT,
            )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        next_link = soup.select_one("a.sb_pagN[href], a[rel='next'][href]")
        self.next_urls[key] = (
            urljoin(response.url, next_link.get("href")) if next_link else None
        )
        output = []
        for item in soup.select("li.b_algo")[:10]:
            link = item.select_one("h2 a") or item.find("a")
            if not link:
                continue
            paragraph = item.find("p")
            output.append(
                SearchResult(
                    title=link.get_text(" ", strip=True),
                    url=normalize_url(link.get("href", "")),
                    snippet=paragraph.get_text(" ", strip=True) if paragraph else "",
                    source=self.name,
                )
            )
        if output:
            return output
        return parse_search_response(
            response,
            self.name,
            ("li.b_algo",),
            (".b_caption p",),
        )


COMMON_ITEM_SELECTORS = (
    "li.b_algo",
    "div.MjjYud",
    "div.g",
    "div.Gx5Zad",
    "div.tF2Cxc",
    "div.algo",
    "div.snippet",
    "article.result",
    "div.result",
    "div.c-container",
    "div.c-result",
    "li.serp-item",
    "ul.results-standard li",
    "li.res-list",
    "div.vrwrap",
    "div.rb",
    "div.sw-CardBase",
)


def parse_html_results(
    html: str,
    base_url: str,
    source: str,
    item_selectors: Sequence[str] = COMMON_ITEM_SELECTORS,
    snippet_selectors: Sequence[str] = (),
) -> List[SearchResult]:
    """Parse common result layouts, then fall back to result headings."""
    soup = BeautifulSoup(html, "html.parser")
    output = []
    seen = set()

    def add_result(link, container) -> None:
        if not link:
            return
        title = clean_text(link.get_text(" ", strip=True))
        href = link.get("href", "")
        if not title or not href or href.startswith(("javascript:", "mailto:")):
            return
        url = normalize_url(urljoin(base_url, href))
        if not valid_web_url(url):
            return
        try:
            result_host = (urlparse(url).hostname or "").lower()
            base_host = (urlparse(base_url).hostname or "").lower()
            result_path = urlparse(url).path.lower()
            if result_host == base_host and result_path.startswith(
                ("/search", "/preferences", "/settings", "/login")
            ):
                return
        except ValueError:
            return
        key = url.split("#", 1)[0].rstrip("/").lower()
        if key in seen:
            return
        snippet = ""
        if container:
            for selector in snippet_selectors:
                element = container.select_one(selector)
                if element:
                    snippet = clean_text(element.get_text(" ", strip=True))
                    break
            if not snippet:
                paragraph = container.find("p")
                if paragraph:
                    snippet = clean_text(paragraph.get_text(" ", strip=True))
            if not snippet:
                snippet = clean_text(container.get_text(" ", strip=True))[:500]
        seen.add(key)
        output.append(SearchResult(title, url, snippet[:500], source))

    items = soup.select(", ".join(item_selectors)) if item_selectors else []
    for item in items:
        heading = item.find(["h2", "h3"])
        link = None
        if heading:
            link = heading.find("a") or heading.find_parent("a")
        if not link:
            link = item.select_one(
                "h2 a, h3 a, a.result-title, a.result__a, a.result-header"
            )
        add_result(link, item)
        if len(output) >= 10:
            return output[:10]

    if not output:
        for heading in soup.find_all(["h2", "h3"]):
            link = heading.find("a") or heading.find_parent("a")
            container = (
                link.find_parent(["li", "article"])
                if link
                else None
            ) or heading.parent
            add_result(link, container)
            if len(output) >= 10:
                break
    return output[:10]


def page_context(response, soup: BeautifulSoup) -> str:
    """Keep the evidence needed to diagnose a page without dumping its body."""
    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    final_url = clean_text(getattr(response, "url", ""))
    status = getattr(response, "status_code", None)
    transport = "Browser DOM / 浏览器 DOM" if status is None else f"HTTP {status}"
    return (
        f"{transport} | "
        f"Title 标题: {shorten(title or '(none / 无)', 100)} | "
        f"Final URL 最终地址: {shorten(final_url or '(unknown / 未知)', 220)}"
    )


def detect_interstitial(response, soup: BeautifulSoup) -> str:
    """Distinguish verification/consent pages from an unknown result layout."""
    try:
        parsed = urlparse(getattr(response, "url", "") or "")
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
    except ValueError:
        host = ""
        path = ""
    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    title_lower = title.lower()
    text = clean_text(soup.get_text(" ", strip=True))[:2400]
    text_lower = text.lower()
    has_result_links = bool(
        soup.select_one("h2 a[href], h3 a[href], .result__a[href], a.result-link[href]")
    )

    captcha_url = (
        host == "wappass.baidu.com"
        or host.startswith("sorry.google.")
        or "captcha" in path
        or "showcaptcha" in path
    )
    captcha_titles = (
        "百度安全验证",
        "安全验证",
        "unusual traffic",
        "verify you are human",
        "verify that you are human",
        "robot check",
        "just a moment...",
    )
    captcha_text = (
        "unusual traffic from your computer network",
        "complete the following challenge",
        "bots use duckduckgo",
        "verify you are a human",
        "verify you are human",
        "请输入验证码",
        "网络异常，请验证",
        "ロボットではないことを確認",
    )
    if (
        captcha_url
        or any(marker in title_lower for marker in captcha_titles)
        or (not has_result_links and any(marker in text_lower for marker in captcha_text))
    ):
        return "captcha"

    consent_url = host.startswith(("consent.google.", "consent.yahoo.", "guce.yahoo."))
    consent_titles = ("before you continue", "sign in to confirm", "同意并继续")
    consent_text = (
        "before you continue to google",
        "to continue to google search",
        "before you continue to yahoo",
        "同意并继续访问",
    )
    if (
        consent_url
        or any(marker in title_lower for marker in consent_titles)
        or (not has_result_links and any(marker in text_lower for marker in consent_text))
    ):
        return "consent"
    return ""


def reports_no_results(soup: BeautifulSoup) -> bool:
    text = clean_text(soup.get_text(" ", strip=True)).lower()
    markers = (
        "did not match any documents",
        "did not match any results",
        "no results found",
        "we did not find results for",
        "no results were returned",
        "没有找到相关结果",
        "找不到相关结果",
        "很抱歉，没有找到",
        "検索結果はありません",
        "一致する情報は見つかりませんでした",
        "検索結果が見つかりませんでした",
    )
    return any(marker in text for marker in markers)


def parse_search_response(
    response,
    source: str,
    item_selectors: Sequence[str],
    snippet_selectors: Sequence[str],
    result_parser=None,
) -> List[SearchResult]:
    """Parse results or raise a specific diagnostic instead of hiding the page."""
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type and "xhtml" not in content_type:
        raise SearchPageError(
            "The search endpoint returned non-HTML content / 搜索入口返回的不是 HTML 网页: "
            + page_context(response, BeautifulSoup(response.content, "html.parser"))
        )
    soup = BeautifulSoup(response.text, "html.parser")
    interstitial = detect_interstitial(response, soup)
    if interstitial == "captcha":
        raise SearchPageError(
            "CAPTCHA or security verification page, not search results / "
            "返回的是验证码或安全验证页，不是搜索结果。浏览器可能凭 Cookie 或 JavaScript "
            "通过验证，但本程序的静态请求不能: " + page_context(response, soup)
        )
    if interstitial == "consent":
        raise SearchPageError(
            "Consent page instead of search results; the static request cannot complete "
            "the website's browser consent flow / 返回的是同意确认页，不是搜索结果；"
            "静态请求无法完成网站的浏览器同意流程: " + page_context(response, soup)
        )

    parser = result_parser or parse_html_results
    results = parser(
        response.text,
        response.url,
        source,
        item_selectors,
        snippet_selectors,
    )
    if results:
        return results
    if reports_no_results(soup):
        return []
    raise SearchPageError(
        "Page received, but its result layout is not recognized / "
        "已收到网页，但未识别出搜索结果布局（这不是“没有更多结果”的确定证据）: "
        + page_context(response, soup)
    )


def parse_duckduckgo_results(
    html: str,
    base_url: str,
    source: str,
    item_selectors: Sequence[str] = (),
    snippet_selectors: Sequence[str] = (),
) -> List[SearchResult]:
    """Support both the standard HTML endpoint and the table-based Lite page."""
    soup = BeautifulSoup(html, "html.parser")
    output = []
    seen = set()
    for link in soup.select(".result__a[href], a.result-link[href]"):
        title = clean_text(link.get_text(" ", strip=True))
        url = normalize_url(urljoin(base_url, link.get("href", "")))
        key = url.split("#", 1)[0].rstrip("/").lower()
        if not title or not valid_web_url(url) or key in seen:
            continue
        snippet = ""
        parent = link.find_parent("div", class_="result")
        if parent:
            element = parent.select_one(".result__snippet")
            snippet = clean_text(element.get_text(" ", strip=True)) if element else ""
        else:
            row = link.find_parent("tr")
            if row:
                for sibling in row.find_next_siblings("tr", limit=3):
                    element = sibling.select_one(".result-snippet")
                    if element:
                        snippet = clean_text(element.get_text(" ", strip=True))
                        break
        seen.add(key)
        output.append(SearchResult(title, url, snippet[:500], source))
        if len(output) >= 10:
            break
    return output


class HTMLProvider:
    def __init__(
        self,
        name: str,
        endpoint: str,
        query_param: str = "q",
        item_selectors: Sequence[str] = COMMON_ITEM_SELECTORS,
        snippet_selectors: Sequence[str] = (),
        extra_params: dict = None,
        language_param: str = None,
        pagination_style: str = "page",
        method: str = "get",
        result_parser=None,
        language_map: dict = None,
        server_retries: int = 0,
    ):
        self.name = name
        self.endpoint = endpoint
        self.query_param = query_param
        self.item_selectors = tuple(item_selectors)
        self.snippet_selectors = tuple(snippet_selectors)
        self.extra_params = extra_params or {}
        self.language_param = language_param
        self.pagination_style = pagination_style
        self.method = method.lower()
        self.result_parser = result_parser
        self.language_map = language_map or {}
        self.server_retries = max(0, int(server_retries))
        self.session = requests.Session()

    def request_params(self, query: str, lang: str = "auto", page: int = 1) -> dict:
        params = dict(self.extra_params)
        params[self.query_param] = query
        if page > 1:
            if self.pagination_style == "google":
                params["start"] = (page - 1) * 10
            elif self.pagination_style == "baidu":
                params["pn"] = (page - 1) * 10
            elif self.pagination_style == "duckduckgo":
                params["s"] = (page - 1) * 10
            elif self.pagination_style == "yahoo":
                params["b"] = (page - 1) * 10 + 1
            elif self.pagination_style == "brave":
                params["offset"] = page - 1
            elif self.pagination_style == "yandex":
                params["p"] = page - 1
            elif self.pagination_style == "mojeek":
                params["s"] = (page - 1) * 10 + 1
            elif self.pagination_style == "so360":
                params["pageno"] = page
            elif self.pagination_style == "naver":
                params["start"] = (page - 1) * 10 + 1
            else:
                params["page"] = page
        if lang != "auto" and self.language_param:
            base_lang = lang.lower().split("-", 1)[0]
            params[self.language_param] = self.language_map.get(base_lang, lang)
        return params

    def request_url(self, query: str, lang: str = "auto", page: int = 1) -> str:
        separator = "&" if "?" in self.endpoint else "?"
        return self.endpoint + separator + urlencode(self.request_params(query, lang, page))

    def search(
        self, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        params = self.request_params(query, lang, page)
        request_kwargs = {
            "headers": request_headers(lang),
            "timeout": REQUEST_TIMEOUT,
            "allow_redirects": True,
        }
        for attempt in range(self.server_retries + 1):
            if self.method == "post":
                response = self.session.post(self.endpoint, data=params, **request_kwargs)
            else:
                response = self.session.get(self.endpoint, params=params, **request_kwargs)
            if response.status_code < 500 or attempt >= self.server_retries:
                break
            # Retry the same endpoint and same region; never substitute another site.
            time.sleep(0.4)
        response.raise_for_status()
        return parse_search_response(
            response,
            self.name,
            self.item_selectors,
            self.snippet_selectors,
            self.result_parser,
        )


class FallbackProvider:
    """Try documented alternate HTML endpoints and retain every failure reason."""

    def __init__(self, name: str, attempts: Sequence[Tuple[str, HTMLProvider]]):
        self.name = name
        self.attempts = list(attempts)
        self.session = requests.Session()
        for _, provider in self.attempts:
            provider.session = self.session

    def search(
        self, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        errors = []
        for source_label, provider in self.attempts:
            try:
                results = provider.search(query, lang, page=page)
                for result in results:
                    result.source = source_label
                return results
            except Exception as error:
                errors.append(f"{source_label}: {engine_error_message(error)}")
        raise ProviderFallbackError(" | ".join(errors))


class RenderedResponse:
    """Small response adapter for parsing a browser's rendered DOM."""

    def __init__(self, status_code: int, url: str, html: str):
        self.status_code = status_code
        self.url = url
        self.text = html
        self.content = html.encode("utf-8", errors="replace")
        self.encoding = "utf-8"
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def raise_for_status(self) -> None:
        if self.status_code is not None and self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code} for url: {self.url}", response=self
            )


class BrowserFetcher:
    """Render a failed engine's original URL in one persistent Chromium profile."""

    result_prefix = "browser:"
    browser_label = "Chromium"

    def __init__(self, headless: bool = None, profile_dir: str = None):
        if headless is None:
            headless = os.environ.get("TSEARCH_BROWSER_HEADLESS", "") == "1"
        self.headless = bool(headless)
        self.profile_dir = Path(
            profile_dir
            or os.environ.get("TSEARCH_BROWSER_PROFILE", "")
            or (Path.home() / ".tsearch-browser-profile")
        )
        self.playwright = None
        self.context = None
        self.page = None
        atexit.register(self.close)

    def close(self) -> None:
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass
        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
        self.page = None
        self.context = None
        self.playwright = None

    def ensure_page(self):
        if self.page is not None:
            try:
                if not self.page.is_closed():
                    return self.page
            except Exception:
                pass
        self.close()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise BrowserUnavailableError(
                "Browser fallback needs Playwright / 浏览器回退需要 Playwright。"
                "Install it with the same Python, then run: python -m playwright install chromium / "
                "请用启动本程序的 Python 安装 playwright，再执行 chromium 安装命令。"
            ) from error
        try:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self.playwright = sync_playwright().start()
            launch_options = {
                "user_data_dir": str(self.profile_dir),
                "headless": self.headless,
                "viewport": {"width": 1280, "height": 900},
            }
            executable = os.environ.get("TSEARCH_BROWSER_EXECUTABLE", "")
            if executable:
                launch_options["executable_path"] = executable
            self.context = self.playwright.chromium.launch_persistent_context(
                **launch_options
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            return self.page
        except Exception as error:
            self.close()
            raise BrowserUnavailableError(
                "Could not launch Chromium / 无法启动 Chromium。"
                "Run: python -m playwright install chromium / "
                "请执行 Chromium 安装命令；在无图形界面的系统上可设置 TSEARCH_BROWSER_HEADLESS=1。"
                f" {shorten(str(error), 180)}"
            ) from error

    def fetch_attempt(
        self,
        source_label: str,
        provider: HTMLProvider,
        query: str,
        lang: str,
        page: int,
    ) -> List[SearchResult]:
        browser_page = self.ensure_page()
        url = provider.request_url(query, lang, page)
        navigation = browser_page.goto(url, wait_until="domcontentloaded", timeout=25000)
        status = navigation.status if navigation is not None else 200
        started = time.monotonic()
        deadline = started + (15 if self.headless else 25)
        manual_notice = False
        last_error = None

        while True:
            response = RenderedResponse(status, browser_page.url, browser_page.content())
            response.raise_for_status()
            try:
                results = parse_search_response(
                    response,
                    provider.name,
                    provider.item_selectors,
                    provider.snippet_selectors,
                    provider.result_parser,
                )
                for result in results:
                    result.source = self.result_prefix + source_label
                return results
            except SearchPageError as error:
                last_error = error
                soup = BeautifulSoup(response.text, "html.parser")
                interstitial = detect_interstitial(response, soup)
                if interstitial and not self.headless:
                    deadline = max(deadline, started + 90)
                    if not manual_notice:
                        console.print(
                            f"[yellow]Complete the verification or consent in the opened {self.browser_label} window; "
                            f"waiting up to 90 seconds / 请在打开的 {self.browser_label} 窗口中完成验证或同意操作，"
                            "最多等待 90 秒。[/yellow]"
                        )
                        manual_notice = True
                if time.monotonic() >= deadline:
                    raise last_error
                browser_page.wait_for_timeout(1200)

    def search_provider(
        self, provider, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        if isinstance(provider, FallbackProvider):
            attempts = provider.attempts[:1]
        elif isinstance(provider, HTMLProvider):
            attempts = [(provider.name, provider)]
        else:
            raise BrowserUnavailableError(
                "This engine has no generic browser endpoint / 此引擎没有通用浏览器入口"
            )
        source_label, html_provider = attempts[0]
        return self.fetch_attempt(source_label, html_provider, query, lang, page)


class EdgeFetcher(BrowserFetcher):
    """Use installed Microsoft Edge on Windows without downloading Chromium."""

    result_prefix = "edge:"
    browser_label = "Edge"

    def __init__(self, headless: bool = None, profile_dir: str = None):
        profile = (
            profile_dir
            or os.environ.get("TSEARCH_EDGE_PROFILE", "")
            or (Path.home() / ".tsearch-edge-profile")
        )
        super().__init__(headless=headless, profile_dir=str(profile))

    def ensure_page(self):
        if sys.platform != "win32":
            raise BrowserUnavailableError(
                "Edge fallback is available only on Windows / Edge 回退仅支持 Windows。"
            )
        if self.page is not None:
            try:
                if not self.page.is_closed():
                    return self.page
            except Exception:
                pass
        self.close()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise BrowserUnavailableError(
                "Edge fallback needs Playwright, but no Chromium download / "
                "Edge 回退需要 Playwright，但不需要下载 Chromium。"
                "Install it with the same Python: python -m pip install playwright / "
                "请用启动本程序的 Python 执行：python -m pip install playwright。"
            ) from error
        try:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self.playwright = sync_playwright().start()
            launch_options = {
                "user_data_dir": str(self.profile_dir),
                "headless": self.headless,
                "viewport": {"width": 1280, "height": 900},
            }
            executable = os.environ.get("TSEARCH_EDGE_EXECUTABLE", "")
            if executable:
                launch_options["executable_path"] = executable
            else:
                launch_options["channel"] = "msedge"
            self.context = self.playwright.chromium.launch_persistent_context(
                **launch_options
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            return self.page
        except Exception as error:
            self.close()
            raise BrowserUnavailableError(
                "Could not launch installed Microsoft Edge / 无法启动已安装的 Microsoft Edge。"
                "Install Edge or use :browser on for separate Chromium; do not run 'playwright "
                "install chromium' for Edge mode / 请安装 Edge，或输入 :browser on 改用独立 Chromium；"
                "Edge 模式不需要执行 Chromium 安装命令。 "
                + shorten(str(error), 180)
            ) from error

    def search_provider(
        self, provider, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        if isinstance(provider, FallbackProvider) and provider.name == "google":
            source_label, html_provider = provider.attempts[0]
        elif isinstance(provider, HTMLProvider) and provider.name == "google":
            source_label, html_provider = "google", provider
        else:
            raise BrowserUnavailableError(
                "Edge mode currently supports Google only / Edge 模式目前仅支持 Google。"
            )
        return self.fetch_attempt(source_label, html_provider, query, lang, page)


class SafariFetcher:
    """Use one dedicated Safari window/tab for Google's rendered search DOM."""

    def __init__(self, runner=None, wait: float = 25, manual_wait: float = 90):
        self.window_id = None
        self.runner = runner
        self.wait = wait
        self.manual_wait = manual_wait
        atexit.register(self.close)

    @staticmethod
    def static_check(platform=None, which=None, exists=None) -> dict:
        """Check local prerequisites without launching Safari or sending Apple Events."""
        platform = sys.platform if platform is None else platform
        which = shutil.which if which is None else which
        exists = (lambda path: Path(path).exists()) if exists is None else exists
        report = {
            "ok": False,
            "macos": platform == "darwin",
            "safari": None,
            "osascript": None,
            "issues": [],
        }
        if platform != "darwin":
            report["issues"].append(
                "Safari mode requires macOS / Safari 模式需要 macOS。"
            )
            return report
        report["osascript"] = which("osascript")
        safari_paths = (
            "/Applications/Safari.app",
            "/System/Applications/Safari.app",
        )
        report["safari"] = next(
            (path for path in safari_paths if exists(path)), None
        )
        if not report["osascript"]:
            report["issues"].append(
                "osascript was not found; check the macOS installation / "
                "未找到 osascript；请检查 macOS 安装。"
            )
        if not report["safari"]:
            report["issues"].append(
                "Safari.app was not found in its standard locations / "
                "未在标准位置找到 Safari.app。"
            )
        report["ok"] = not report["issues"]
        return report

    def close(self) -> None:
        # Never close or inspect the user's existing Safari tabs.
        self.window_id = None

    @staticmethod
    def quote(value: str) -> str:
        return json.dumps(str(value), ensure_ascii=False)

    @staticmethod
    def unavailable(detail: str) -> BrowserUnavailableError:
        text = clean_text(detail)
        lower = text.lower()
        automation = (
            "macOS blocked automation of Safari. Allow your terminal under System Settings "
            "> Privacy & Security > Automation, then retry / macOS 阻止了终端控制 Safari。"
            "请在系统设置 → 隐私与安全性 → 自动化中允许你的终端控制 Safari，然后重试。"
        )
        javascript = (
            "Safari JavaScript automation is disabled. Enable Safari's Develop menu and "
            "'Allow JavaScript from Apple Events', then retry / Safari 的 JavaScript 自动化未开启。"
            "请显示 Safari 的“开发”菜单，启用“允许来自 Apple 事件的 JavaScript”，然后重试。"
        )
        if "javascript" in lower or "1002" in lower:
            message = javascript
        elif "-1743" in lower or "not authorized" in lower or "apple events" in lower:
            message = automation
        elif "tsearch_window_closed" in lower:
            message = (
                "The dedicated Safari tab was closed; run the search again / "
                "专用 Safari 标签页已关闭，请重新搜索。"
            )
        else:
            message = (
                "Safari automation failed. Check Automation permission and 'Allow JavaScript "
                "from Apple Events' / Safari 自动化失败。请检查自动化权限和“允许来自 Apple 事件的 JavaScript”。"
            )
        return BrowserUnavailableError(message + (" " + shorten(text, 180) if text else ""))

    def run_applescript(self, script: str, timeout: float = 30) -> str:
        if sys.platform != "darwin":
            raise BrowserUnavailableError(
                "Safari fallback is available only on macOS / Safari 回退仅支持 macOS。"
            )
        try:
            if self.runner is not None:
                completed = self.runner(script, timeout)
            else:
                completed = subprocess.run(
                    ["osascript", "-"],
                    input=script,
                    text=True,
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
        except (FileNotFoundError, OSError) as error:
            raise BrowserUnavailableError(
                "Could not run macOS Safari automation / 无法运行 macOS Safari 自动化: "
                + shorten(str(error), 180)
            ) from error
        except subprocess.TimeoutExpired as error:
            raise BrowserUnavailableError(
                "Safari automation timed out / Safari 自动化超时。"
            ) from error
        output = getattr(completed, "stdout", "") or ""
        if getattr(completed, "returncode", 1) != 0:
            detail = getattr(completed, "stderr", "") or output
            raise self.unavailable(detail)
        return output.strip()

    def open_setup(self, opener=None) -> None:
        """Open the relevant preferences and Safari; never toggle settings for the user."""
        if sys.platform != "darwin":
            raise BrowserUnavailableError(
                "Safari setup is available only on macOS / Safari 设置引导仅支持 macOS。"
            )
        opener = subprocess.run if opener is None else opener
        commands = (
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation",
            ],
            ["open", "-a", "Safari"],
        )
        errors = []
        for command in commands:
            try:
                completed = opener(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if getattr(completed, "returncode", 1) != 0:
                    detail = (
                        getattr(completed, "stderr", "")
                        or getattr(completed, "stdout", "")
                        or "open command failed"
                    )
                    errors.append(shorten(clean_text(detail), 180))
            except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
                errors.append(shorten(str(error), 180))
        if errors:
            raise BrowserUnavailableError(
                "Could not open all Safari setup destinations; open them manually using "
                "the steps below / 无法打开全部设置位置；请按下方步骤手动操作。 "
                + " | ".join(errors)
            )

    def navigate(self, url: str) -> None:
        if self.window_id is not None:
            script = f"""
tell application \"Safari\"
    if not (exists window id {self.window_id}) then error \"TSEARCH_WINDOW_CLOSED\"
    set URL of tab 1 of window id {self.window_id} to {self.quote(url)}
    activate
end tell
"""
            try:
                self.run_applescript(script)
            except BrowserUnavailableError as error:
                if "closed" not in str(error).lower() and "已关闭" not in str(error):
                    raise
                self.window_id = None
                return self.navigate(url)
            return
        script = f"""
tell application \"Safari\"
    activate
    set newDocument to make new document with properties {{URL:{self.quote(url)}}}
    delay 0.5
    set newWindow to first window where (its document is newDocument)
    return id of newWindow as text
end tell
"""
        output = self.run_applescript(script)
        match = re.search(r"\d+", output)
        if not match:
            raise BrowserUnavailableError(
                "Safari did not return its dedicated window identifier / "
                "Safari 未返回专用窗口标识。"
            )
        self.window_id = int(match.group(0))

    def read_page(self) -> dict:
        if self.window_id is None:
            raise BrowserUnavailableError("Safari is not ready / Safari 尚未就绪。")
        javascript = (
            "JSON.stringify({url:location.href,ready:document.readyState,"
            "html:document.documentElement?document.documentElement.outerHTML:''})"
        )
        script = f"""
tell application \"Safari\"
    if not (exists window id {self.window_id}) then error \"TSEARCH_WINDOW_CLOSED\"
    set searchTab to tab 1 of window id {self.window_id}
    set pageData to do JavaScript {self.quote(javascript)} in searchTab
    return pageData
end tell
"""
        output = self.run_applescript(script)
        try:
            payload = json.loads(output)
        except (TypeError, ValueError) as error:
            raise BrowserUnavailableError(
                "Safari returned unreadable page data / Safari 返回了无法读取的页面数据。"
            ) from error
        if not isinstance(payload, dict) or not isinstance(payload.get("html"), str):
            raise BrowserUnavailableError(
                "Safari returned incomplete page data / Safari 返回的页面数据不完整。"
            )
        return payload

    def check_permissions(self) -> dict:
        """Test Automation, JavaScript, and DOM access using only a dedicated blank page."""
        report = {
            "ok": False,
            "automation": False,
            "javascript": False,
            "dom": False,
            "stage": "automation",
            "url": None,
            "error": None,
        }
        try:
            self.navigate("about:blank")
        except BrowserUnavailableError as error:
            report["error"] = str(error)
            return report
        report["automation"] = True
        report["stage"] = "javascript"
        deadline = time.monotonic() + 5
        while True:
            try:
                payload = self.read_page()
            except BrowserUnavailableError as error:
                report["error"] = str(error)
                return report
            report["javascript"] = True
            report["stage"] = "dom"
            report["url"] = payload.get("url")
            if isinstance(payload.get("html"), str) and payload["html"].strip():
                report["dom"] = True
            if (
                report["dom"]
                and payload.get("url") == "about:blank"
            ):
                report["ok"] = True
                report["stage"] = "done"
                return report
            if time.monotonic() >= deadline:
                report["error"] = (
                    "The dedicated about:blank page did not become readable / "
                    "专用 about:blank 页面未能完成读取。"
                )
                return report
            time.sleep(0.2)

    def fetch_attempt(
        self,
        source_label: str,
        provider: HTMLProvider,
        query: str,
        lang: str,
        page: int,
    ) -> List[SearchResult]:
        if source_label != "google":
            raise BrowserUnavailableError(
                "Safari mode currently supports Google only / Safari 模式目前仅支持 Google。"
            )
        url = provider.request_url(query, lang, page)
        self.navigate(url)
        started = time.monotonic()
        deadline = started + self.wait
        manual_notice = False
        last_error = None

        while True:
            payload = self.read_page()
            if payload.get("ready") != "complete":
                if time.monotonic() >= deadline:
                    raise SearchPageError(
                        "The Safari page did not finish loading in time / "
                        "Safari 页面未能及时加载完成。"
                    )
                time.sleep(1.0)
                continue
            response = RenderedResponse(None, payload.get("url") or url, payload["html"])
            try:
                results = parse_search_response(
                    response,
                    provider.name,
                    provider.item_selectors,
                    provider.snippet_selectors,
                    provider.result_parser,
                )
                for result in results:
                    result.source = "safari:" + source_label
                return results
            except SearchPageError as error:
                last_error = error
                soup = BeautifulSoup(response.text, "html.parser")
                interstitial = detect_interstitial(response, soup)
                if interstitial:
                    deadline = max(deadline, started + self.manual_wait)
                    if not manual_notice:
                        console.print(
                            "[yellow]Complete the verification or consent in the dedicated Safari "
                            "window; waiting up to 90 seconds / 请在专用 Safari 窗口中完成验证或"
                            "同意操作，最多等待 90 秒。[/yellow]"
                        )
                        manual_notice = True
                if time.monotonic() >= deadline:
                    if interstitial:
                        raise SearchPageError(
                            "Safari still shows verification or consent; no results were read / "
                            "Safari 仍显示验证或同意页，未读取到搜索结果。 " + str(last_error)
                        ) from error
                    raise SearchPageError(
                        "Safari rendered the page, but its Google results were not recognized / "
                        "Safari 已渲染页面，但仍未识别出 Google 搜索结果。 " + str(last_error)
                    ) from error
                time.sleep(1.0)

    def search_provider(
        self, provider, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        if isinstance(provider, FallbackProvider) and provider.name == "google":
            source_label, html_provider = provider.attempts[0]
        elif isinstance(provider, HTMLProvider) and provider.name == "google":
            source_label, html_provider = "google", provider
        else:
            raise BrowserUnavailableError(
                "Safari mode currently supports Google only / Safari 模式目前仅支持 Google。"
            )
        return self.fetch_attempt(source_label, html_provider, query, lang, page)


def custom_provider(target: str) -> Tuple[str, HTMLProvider]:
    """Create a domain provider, with one explicit Yahoo Japan alias fix."""
    value = (target or "").strip()
    if not value or re.search(r"\s", value):
        raise ValueError("empty or invalid domain")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("enter a domain only")
    host = parsed.hostname.lower().rstrip(".")
    if not host or ("." not in host and host != "localhost"):
        raise ValueError("invalid domain")
    netloc = parsed.netloc.lower()
    bare_netloc = netloc[4:] if netloc.startswith("www.") else netloc
    bare_host = host[4:] if host.startswith("www.") else host
    scheme = parsed.scheme
    if bare_host == "yahoo.jp":
        # The user-intended Yahoo Japan service uses yahoo.co.jp, not yahoo.jp.
        host = "yahoo.co.jp"
        bare_host = "yahoo.co.jp"
        netloc = "yahoo.co.jp"
        bare_netloc = "yahoo.co.jp"

    query_param = "q"
    extra_params = {}
    item_selectors = COMMON_ITEM_SELECTORS
    snippet_selectors = ()
    pagination_style = "page"

    if "yahoo." in bare_host:
        search_host = netloc if bare_host.startswith("search.") else f"search.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/search"
        query_param = "p"
        pagination_style = "yahoo"
        item_selectors = ("div.algo", "div.dd.algo")
        snippet_selectors = (".compText", ".lh-16", ".fc-falcon")
    elif "google." in bare_host:
        search_host = netloc if bare_host.startswith("www.") else f"www.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/search"
        extra_params = {"num": 10}
        pagination_style = "google"
        item_selectors = ("div.MjjYud", "div.g")
        snippet_selectors = (".VwiC3b", ".yXK7lf", ".aCOpRe")
    elif "baidu." in bare_host:
        search_host = netloc if bare_host.startswith("www.") else f"www.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/s"
        query_param = "wd"
        extra_params = {"rn": 10}
        pagination_style = "baidu"
        item_selectors = ("div.result", "div.c-container")
    elif "duckduckgo." in bare_host:
        search_host = netloc if bare_host.startswith("html.") else f"html.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/html/"
        pagination_style = "duckduckgo"
        item_selectors = ("div.result",)
        snippet_selectors = (".result__snippet",)
    elif "brave." in bare_host:
        search_host = netloc if bare_host.startswith("search.") else f"search.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/search"
        pagination_style = "brave"
        item_selectors = ("div.snippet", "div.result")
        snippet_selectors = (".snippet-description", ".result-description")
    elif "ecosia." in bare_host:
        search_host = netloc if bare_host.startswith("www.") else f"www.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/search"
        item_selectors = ("article.result", "div.result")
        snippet_selectors = (".result__description", ".result-description")
    elif "yandex." in bare_host:
        endpoint = f"{scheme}://{netloc}/search/"
        query_param = "text"
        pagination_style = "yandex"
        item_selectors = ("li.serp-item",)
        snippet_selectors = (".OrganicTextContentSpan", ".TextContainer")
    elif "mojeek." in bare_host:
        search_host = netloc if bare_host.startswith("www.") else f"www.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/search"
        pagination_style = "mojeek"
        item_selectors = ("ul.results-standard li",)
        snippet_selectors = ("p.s",)
    elif "sogou." in bare_host:
        search_host = netloc if bare_host.startswith("www.") else f"www.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/web"
        query_param = "query"
        item_selectors = ("div.vrwrap", "div.rb")
    elif bare_host == "so.com" or bare_host.endswith(".so.com"):
        search_host = netloc if bare_host.startswith("www.") else f"www.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/s"
        pagination_style = "so360"
        item_selectors = ("li.res-list",)
        snippet_selectors = (".res-desc",)
    elif "naver." in bare_host:
        search_host = netloc if bare_host.startswith("search.") else f"search.{bare_netloc}"
        endpoint = f"{scheme}://{search_host}/search.naver"
        query_param = "query"
        pagination_style = "naver"
    else:
        endpoint = f"{scheme}://{netloc}/search"

    display_name = bare_host + (f":{parsed.port}" if parsed.port else "")
    provider = HTMLProvider(
        display_name,
        endpoint,
        query_param,
        item_selectors,
        snippet_selectors,
        extra_params,
        pagination_style=pagination_style,
    )
    return display_name, provider


class SearXNGProvider:
    name = "searxng"

    def __init__(self, base_url: str = "http://127.0.0.1:8888"):
        self.base_url = base_url.rstrip("/")

    def search(
        self, query: str, lang: str = "auto", page: int = 1
    ) -> List[SearchResult]:
        params = {"q": query, "format": "json", "pageno": page}
        if lang != "auto":
            params["language"] = lang
        response = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers=request_headers(lang),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        output = []
        for item in data.get("results", [])[:10]:
            output.append(
                SearchResult(
                    title=clean_text(item.get("title", "")),
                    url=normalize_url(item.get("url", "")),
                    snippet=clean_text(item.get("content", "")),
                    source=self.name,
                )
            )
        return output


def engine_error_message(error: Exception) -> str:
    text = clean_text(str(error))
    if isinstance(error, (SearchPageError, ProviderFallbackError)):
        return text
    if isinstance(error, requests.HTTPError) and error.response is not None:
        status = error.response.status_code
        if status == 429:
            return f"HTTP 429 rate limit; retry later / 引擎限流，请稍后重试: {shorten(text, 150)}"
        if status in (401, 403):
            return f"HTTP {status} access denied or bot check / 拒绝访问或自动化检查: {shorten(text, 150)}"
        return f"HTTP {status} / HTTP 错误: {shorten(text, 150)}"
    if isinstance(error, requests.Timeout):
        return f"Connection or read timeout / 连接或读取超时: {shorten(text, 150)}"
    if "NameResolutionError" in text:
        return f"DNS lookup failed; check the domain / 域名解析失败，请检查域名: {shorten(text, 150)}"
    if isinstance(error, requests.ConnectionError):
        return f"Connection failed / 连接失败: {shorten(text, 150)}"
    return f"{type(error).__name__}: {shorten(text or 'Unknown error', 180)}"


class Engine:
    def __init__(self):
        config = load_config()
        self.lang = config.get("lang", "auto")
        if not isinstance(self.lang, str) or not valid_language_code(self.lang):
            self.lang = "auto"
        self.lang = self.lang.lower()
        self.page_size = 10
        # Alternate static HTML endpoints need enough time after a primary failure.
        self.timeout = 30
        self.filter_ads = bool(config.get("filter_ads", True))
        browser_mode = config.get("browser_mode")
        if browser_mode not in BROWSER_MODES:
            browser_mode = "chromium" if config.get("browser_fallback", False) else "off"
        self.browser_mode = browser_mode
        self.browser_fetcher = None
        self.current_query = None
        self.current_page = 1
        self.raw_results = []
        self.all_results = []
        self.last_failed = []
        self.last_errors = {}
        self.last_stats = {}
        self.has_fetched = False
        self.provider_page = 1
        self.exhausted = False
        self.providers = {
            "google": FallbackProvider(
                "google",
                [
                    (
                        "google",
                        HTMLProvider(
                            "google",
                            "https://www.google.com/search",
                            item_selectors=(
                                "div.MjjYud",
                                "div.g",
                                "div.Gx5Zad",
                                "div.tF2Cxc",
                            ),
                            snippet_selectors=(".VwiC3b", ".yXK7lf", ".aCOpRe"),
                            extra_params={"num": 10},
                            language_param="hl",
                            pagination_style="google",
                        ),
                    ),
                    (
                        "google-basic",
                        HTMLProvider(
                            "google-basic",
                            "https://www.google.com/search",
                            item_selectors=(
                                "div.MjjYud",
                                "div.g",
                                "div.Gx5Zad",
                                "div.tF2Cxc",
                            ),
                            snippet_selectors=(".VwiC3b", ".yXK7lf", ".aCOpRe"),
                            extra_params={"num": 10, "gbv": 1},
                            language_param="hl",
                            pagination_style="google",
                        ),
                    ),
                ],
            ),
            "bing": BingProvider(),
            "duckduckgo": FallbackProvider(
                "duckduckgo",
                [
                    (
                        "ddg-html",
                        HTMLProvider(
                            "ddg-html",
                            "https://html.duckduckgo.com/html/",
                            item_selectors=("div.result",),
                            snippet_selectors=(".result__snippet",),
                            language_param="kl",
                            language_map=DUCKDUCKGO_REGIONS,
                            pagination_style="duckduckgo",
                            method="post",
                            result_parser=parse_duckduckgo_results,
                        ),
                    ),
                    (
                        "ddg-get",
                        HTMLProvider(
                            "ddg-get",
                            "https://html.duckduckgo.com/html/",
                            item_selectors=("div.result",),
                            snippet_selectors=(".result__snippet",),
                            language_param="kl",
                            language_map=DUCKDUCKGO_REGIONS,
                            pagination_style="duckduckgo",
                            result_parser=parse_duckduckgo_results,
                        ),
                    ),
                    (
                        "ddg-lite",
                        HTMLProvider(
                            "ddg-lite",
                            "https://lite.duckduckgo.com/lite/",
                            snippet_selectors=(".result-snippet",),
                            language_param="kl",
                            language_map=DUCKDUCKGO_REGIONS,
                            pagination_style="duckduckgo",
                            result_parser=parse_duckduckgo_results,
                        ),
                    ),
                ],
            ),
            "yahoo": HTMLProvider(
                "yahoo.com",
                "https://search.yahoo.com/search",
                query_param="p",
                item_selectors=("div.algo", "div.dd.algo"),
                snippet_selectors=(".compText", ".lh-16", ".fc-falcon"),
                extra_params={"ei": "UTF-8"},
                pagination_style="yahoo",
                server_retries=1,
            ),
            "yahoojp": HTMLProvider(
                "yahoo.co.jp",
                "https://search.yahoo.co.jp/search",
                query_param="p",
                item_selectors=COMMON_ITEM_SELECTORS + ("div.sw-CardBase",),
                snippet_selectors=(".compText", ".lh-16", ".fc-falcon"),
                pagination_style="yahoo",
            ),
            "baidu": FallbackProvider(
                "baidu",
                [
                    (
                        "baidu",
                        HTMLProvider(
                            "baidu",
                            "https://www.baidu.com/s",
                            query_param="wd",
                            item_selectors=("div.result", "div.c-container"),
                            extra_params={"rn": 10},
                            pagination_style="baidu",
                        ),
                    ),
                    (
                        "baidu-mobile",
                        HTMLProvider(
                            "baidu-mobile",
                            "https://m.baidu.com/s",
                            query_param="word",
                            item_selectors=(
                                "div.c-result",
                                "div.c-container",
                                "div.result",
                            ),
                            snippet_selectors=(".c-abstract", ".c-color-text"),
                            extra_params={"rn": 10},
                            pagination_style="baidu",
                        ),
                    ),
                ],
            ),
            "brave": HTMLProvider(
                "brave",
                "https://search.brave.com/search",
                item_selectors=("div.snippet", "div.result"),
                snippet_selectors=(".snippet-description", ".result-description"),
                pagination_style="brave",
            ),
            "ecosia": HTMLProvider(
                "ecosia",
                "https://www.ecosia.org/search",
                item_selectors=("article.result", "div.result"),
                snippet_selectors=(".result__description", ".result-description"),
            ),
            "yandex": HTMLProvider(
                "yandex",
                "https://yandex.com/search/",
                query_param="text",
                item_selectors=("li.serp-item",),
                snippet_selectors=(".OrganicTextContentSpan", ".TextContainer"),
                pagination_style="yandex",
            ),
            "mojeek": HTMLProvider(
                "mojeek",
                "https://www.mojeek.com/search",
                item_selectors=("ul.results-standard li",),
                snippet_selectors=("p.s",),
                pagination_style="mojeek",
            ),
            "sogou": HTMLProvider(
                "sogou",
                "https://www.sogou.com/web",
                query_param="query",
                item_selectors=("div.vrwrap", "div.rb"),
            ),
            "searxng": SearXNGProvider(
                os.environ.get("TSEARCH_SEARXNG_URL", "http://127.0.0.1:8888")
            ),
        }
        self.custom_engines = {}
        self.invalid_engines = []
        raw_custom = config.get("custom_engines", [])
        if isinstance(raw_custom, list):
            for target in raw_custom:
                if not isinstance(target, str):
                    continue
                try:
                    self.register_custom(target)
                except (ValueError, TypeError):
                    continue
        raw_pool = config.get("pool") or DEFAULT_POOL
        if (
            config.get("config_version", 1) != CONFIG_VERSION
            and raw_pool == ["bing", "duckduckgo"]
        ):
            # Migrate the previous implicit two-engine default to the expanded pool.
            raw_pool = DEFAULT_POOL
        if not isinstance(raw_pool, list):
            raw_pool = DEFAULT_POOL
        raw_pool = [
            "custom:yahoo.co.jp" if name == "custom:yahoo.jp" else name
            for name in raw_pool
        ]
        self.pool = [
            name
            for name in raw_pool
            if isinstance(name, str) and name in self.providers
        ]
        if not self.pool:
            self.pool = list(DEFAULT_POOL)

    def register_custom(self, target: str) -> str:
        name, provider = custom_provider(target)
        key = CUSTOM_PREFIX + name
        self.providers[key] = provider
        self.custom_engines[key] = target
        return key

    def display_engine(self, key: str) -> str:
        provider = self.providers.get(key)
        return provider.name if provider and key.startswith(CUSTOM_PREFIX) else key

    def pool_display(self) -> str:
        return ", ".join(self.display_engine(name) for name in self.pool)

    @property
    def browser_fallback(self) -> bool:
        return self.browser_mode != "off"

    @browser_fallback.setter
    def browser_fallback(self, enabled: bool) -> None:
        self.browser_mode = "chromium" if enabled else "off"

    def save(self) -> None:
        save_config(
            self.lang,
            self.pool,
            self.filter_ads,
            self.custom_engines,
            self.browser_fallback,
            browser_mode=self.browser_mode,
        )

    def set_browser(self, mode) -> None:
        if isinstance(mode, bool):
            mode = "chromium" if mode else "off"
        mode = str(mode).lower()
        if mode == "on":
            mode = "chromium"
        if mode not in BROWSER_MODES:
            raise ValueError("unknown browser mode")
        changed = mode != self.browser_mode
        self.browser_mode = mode
        if (changed or mode == "off") and self.browser_fetcher is not None:
            self.browser_fetcher.close()
            self.browser_fetcher = None
        # Re-selecting the same mode is also an explicit retry after permission changes.
        # Never reuse a previous static failure for the same query in the new browser context.
        self.invalidate_search()
        self.save()

    def get_browser_fetcher(self):
        if self.browser_fetcher is None:
            if self.browser_mode == "safari":
                self.browser_fetcher = SafariFetcher()
            elif self.browser_mode == "edge":
                self.browser_fetcher = EdgeFetcher()
            else:
                self.browser_fetcher = BrowserFetcher()
        return self.browser_fetcher

    def invalidate_failed_google_search(self) -> bool:
        """Allow a previously failed Google query to retry after permission repair."""
        if (
            self.current_query
            and self.has_fetched
            and "google" in self.last_failed
        ):
            self.invalidate_search()
            return True
        return False

    def close(self) -> None:
        if self.browser_fetcher is not None:
            self.browser_fetcher.close()
            self.browser_fetcher = None

    def invalidate_search(self) -> None:
        self.current_page = 1
        self.raw_results = []
        self.all_results = []
        self.last_failed = []
        self.last_errors = {}
        self.last_stats = {}
        self.has_fetched = False
        self.provider_page = 1
        self.exhausted = False

    def set_pool(self, names: Sequence[str]) -> List[str]:
        valid = []
        self.invalid_engines = []
        for raw_name in names:
            name = raw_name.strip()
            if not name:
                continue
            key = name if name in self.providers else name.lower()
            if key not in self.providers:
                try:
                    key = self.register_custom(name)
                except (ValueError, TypeError):
                    self.invalid_engines.append(name)
                    continue
            if key not in valid:
                valid.append(key)
        if valid:
            self.pool = valid
            self.invalidate_search()
            self.save()
        return valid

    def set_lang(self, lang: str) -> bool:
        lang = lang.lower()
        if lang == "all":
            lang = "auto"
        if not valid_language_code(lang):
            return False
        self.lang = lang
        self.invalidate_search()
        self.save()
        return True

    def set_filter(self, enabled: bool) -> None:
        self.filter_ads = enabled
        self.save()
        if self.has_fetched and self.current_query:
            self.all_results = self.process_results(self.current_query, self.raw_results)
            self.current_page = 1

    def new_topic(self, query: str) -> None:
        self.current_query = query
        self.invalidate_search()

    def fetch(
        self, query: str, page: int = 1
    ) -> Tuple[List[SearchResult], List[str]]:
        result_queue = queue.Queue()
        failed = set()
        self.last_errors = {}

        def worker(name):
            try:
                results = self.providers[name].search(query, self.lang, page=page)
                error = "" if results else (
                    "The engine explicitly reported no results on this page / "
                    "引擎明确报告此页没有搜索结果（不是相关度过滤）"
                )
                result_queue.put((name, results, error))
            except Exception as error:
                result_queue.put((name, [], engine_error_message(error)))

        threads = []
        for name in self.pool:
            thread = threading.Thread(target=worker, args=(name,), daemon=True)
            thread.start()
            threads.append((name, thread))

        collected = []
        deadline = time.monotonic() + self.timeout
        finished = set()
        while len(finished) < len(threads):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                name, results, error = result_queue.get(timeout=min(0.25, remaining))
                finished.add(name)
                if error:
                    failed.add(name)
                    self.last_errors[name] = error
                else:
                    collected.extend(results)
            except queue.Empty:
                if all(not thread.is_alive() for _, thread in threads):
                    break

        for name, thread in threads:
            if name not in finished and thread.is_alive():
                failed.add(name)
                self.last_errors[name] = "Request timed out / 请求超时"
        if self.browser_fallback and failed:
            self.browser_retry(failed, collected, query, page)
        return collected, sorted(failed)

    def browser_retry(
        self,
        failed: set,
        collected: List[SearchResult],
        query: str,
        page: int,
    ) -> None:
        safari_mode = self.browser_mode == "safari"
        edge_mode = self.browser_mode == "edge"
        self.get_browser_fetcher()
        for name in sorted(list(failed)):
            if (safari_mode or edge_mode) and name != "google":
                # Scoped modes deliberately leave every other provider unchanged.
                continue
            provider = self.providers.get(name)
            if not isinstance(provider, (HTMLProvider, FallbackProvider)):
                continue
            static_error = self.last_errors.get(name, "")
            if "HTTP 429" in static_error:
                # Do not hammer a rate-limited service again through another client.
                continue
            if safari_mode:
                mode_label = "Safari fallback / Safari 回退"
            elif edge_mode:
                mode_label = "Edge fallback / Edge 回退"
            else:
                mode_label = "Browser fallback / 浏览器回退"
            console.print(
                f"[dim]{mode_label}: {self.display_engine(name)} — "
                "opening the original search URL / 正在打开原搜索地址。[/dim]"
            )
            try:
                results = self.browser_fetcher.search_provider(
                    provider, query, self.lang, page=page
                )
                if results:
                    collected.extend(results)
                    failed.discard(name)
                    self.last_errors.pop(name, None)
                else:
                    self.last_errors[name] = (
                        "The browser also reported no results / 浏览器也确认没有搜索结果"
                    )
            except BrowserUnavailableError as error:
                self.last_errors[name] = static_error + " | " + mode_label + ": " + str(error)
                break
            except Exception as error:
                self.last_errors[name] = (
                    static_error
                    + " | "
                    + mode_label
                    + ": "
                    + engine_error_message(error)
                )

    def process_results(
        self, query: str, results: Iterable[SearchResult]
    ) -> List[SearchResult]:
        cleaned = []
        stats = {"received": 0, "invalid": 0, "ads": 0, "duplicates": 0, "kept": 0}
        for result in results:
            stats["received"] += 1
            result.title = clean_text(result.title)
            result.snippet = (result.snippet or "").strip()
            result.url = normalize_url(result.url)
            if not result.title or not valid_web_url(result.url):
                stats["invalid"] += 1
                continue
            if self.filter_ads and is_ad_or_junk(result.title, result.snippet, result.url):
                stats["ads"] += 1
                continue
            result.score_details = relevance_breakdown(query, result.title, result.snippet)
            result.score = result.score_details["score"]
            cleaned.append(result)
        unique = dedupe(cleaned)
        stats["duplicates"] = len(cleaned) - len(unique)
        stats["kept"] = len(unique)
        self.last_stats = stats
        return sorted(unique, key=lambda item: item.score, reverse=True)

    def search(self, query: str):
        if query != self.current_query:
            self.new_topic(query)
        if not self.has_fetched:
            self.raw_results, self.last_failed = self.fetch(query, page=1)
            self.provider_page = 1
            self.all_results = self.process_results(query, self.raw_results)
            self.has_fetched = True
            self.exhausted = not self.raw_results
        return self.page(self.current_page)

    @property
    def page_count(self) -> int:
        return max(1, (len(self.all_results) + self.page_size - 1) // self.page_size)

    def page(self, page: int) -> List[SearchResult]:
        start = (page - 1) * self.page_size
        return self.all_results[start : start + self.page_size]

    def next_page(self) -> bool:
        if self.current_page < self.page_count:
            self.current_page += 1
            return True
        if not self.current_query or self.exhausted:
            return False

        next_provider_page = self.provider_page + 1
        new_raw, self.last_failed = self.fetch(
            self.current_query, page=next_provider_page
        )
        self.provider_page = next_provider_page
        if not new_raw:
            self.last_stats = {
                "received": 0,
                "invalid": 0,
                "ads": 0,
                "duplicates": 0,
                "kept": 0,
            }
            self.exhausted = True
            return False

        new_results = self.process_results(self.current_query, new_raw)
        self.raw_results.extend(new_raw)
        existing = {
            result.url.split("#", 1)[0].rstrip("/").lower()
            for result in self.all_results
        }
        unique_new = []
        for result in new_results:
            key = result.url.split("#", 1)[0].rstrip("/").lower()
            if key not in existing:
                existing.add(key)
                unique_new.append(result)
        self.last_stats["duplicates"] += len(new_results) - len(unique_new)
        self.last_stats["kept"] = len(unique_new)
        if not unique_new:
            self.exhausted = True
            return False

        self.all_results.extend(unique_new)
        self.current_page += 1
        return True

    def prev_page(self) -> bool:
        if self.current_page <= 1:
            return False
        self.current_page -= 1
        return True

    def result_at(self, number: int) -> SearchResult:
        if number < 1 or number > len(self.all_results):
            raise IndexError(number)
        return self.all_results[number - 1]


def extract_article_paragraphs(url: str) -> List[str]:
    response = requests.get(
        url,
        headers=request_headers(),
        timeout=REQUEST_TIMEOUT,
        stream=True,
        allow_redirects=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type and "text/plain" not in content_type:
        raise ValueError("not an HTML or text page / 不是 HTML 或文本网页")

    chunks = []
    size = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_ARTICLE_BYTES:
            raise ValueError("page is too large / 网页内容过大")
        chunks.append(chunk)
    content = b"".join(chunks)

    if "text/plain" in content_type:
        text = content.decode(response.encoding or "utf-8", errors="replace")
        return [clean_text(p) for p in re.split(r"\n\s*\n|\n", text) if clean_text(p)]

    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(
        ["script", "style", "noscript", "svg", "form", "nav", "footer", "aside"]
    ):
        tag.decompose()
    for tag in soup.select(
        ".advertisement, .ads, .ad-container, .social-share, .related-posts, "
        "[class*='cookie'], [id*='cookie'], [aria-label='advertisement']"
    ):
        tag.decompose()

    root = (
        soup.select_one("article")
        or soup.select_one("main")
        or soup.select_one(".article-content, .post-content, .entry-content")
        or soup.body
        or soup
    )
    paragraphs = []
    seen = set()
    for element in root.find_all("p"):
        text = clean_text(element.get_text(" ", strip=True))
        if len(text) < 2 or BOILERPLATE_RE.search(text) or text in seen:
            continue
        seen.add(text)
        paragraphs.append(text)
    if not paragraphs:
        text = root.get_text("\n", strip=True)
        for line in re.split(r"\n\s*\n|\n", text):
            line = clean_text(line)
            if len(line) >= 20 and not BOILERPLATE_RE.search(line) and line not in seen:
                seen.add(line)
                paragraphs.append(line)
    if not paragraphs:
        raise ValueError("no readable paragraphs found / 未找到可读段落")
    return paragraphs


def show_results(engine: Engine, results: Sequence[SearchResult]) -> None:
    start = (engine.current_page - 1) * engine.page_size
    table = Table(
        title=f"Results 结果 | {engine.current_query} | Page 页 {engine.current_page}"
    )
    table.add_column("#", justify="right", style="cyan", width=4)
    table.add_column("Title 标题", style="magenta", max_width=34, overflow="fold")
    table.add_column("Score 相关度", justify="right", style="cyan", width=12)
    table.add_column("Summary 摘要", style="white", max_width=62, overflow="fold")
    table.add_column("URL 网址", style="green", max_width=42, overflow="fold")
    table.add_column("Source 来源", style="yellow", width=18)
    for index, result in enumerate(results, start=start + 1):
        table.add_row(
            str(index),
            result.title,
            f"{result.score:.2f}",
            paragraph_preview(result.snippet, width=54),
            result.url,
            result.source,
        )
    console.print(table)
    console.print(
        f"[dim]Loaded results / 已加载结果: {len(engine.all_results)} | "
        f"Engine pages fetched / 已抓取引擎页: {engine.provider_page} | "
        "Relevance sorts only; it never filters / 相关性仅排序，不过滤。[/dim]"
    )


def show_score(engine: Engine, number: int) -> None:
    try:
        result = engine.result_at(number)
    except IndexError:
        console.print("Invalid result number. / 无效的结果编号。")
        return
    details = result.score_details or relevance_breakdown(
        engine.current_query or "", result.title, result.snippet
    )
    query_tokens = shorten(", ".join(details["query_tokens"]), 260) or "none / 无"
    title_matches = shorten(", ".join(details["title_matches"]), 260) or "none / 无"
    snippet_matches = shorten(", ".join(details["snippet_matches"]), 260) or "none / 无"
    if details["query_count"]:
        formula = (
            f"({details['title_hits']} × 3 + {details['snippet_hits']} × 1) "
            f"/ {details['query_count']} = {details['score']:.4f}"
        )
    else:
        formula = "No query tokens; score = 0 / 没有查询词元，分数为 0"
    text = (
        f"Result / 结果: {result.title}\n"
        f"Query tokens ({details['query_count']}) / 查询词元: {query_tokens}\n"
        f"Title hits ({details['title_hits']}, weight 3) / 标题命中（权重 3）: {title_matches}\n"
        f"Snippet hits ({details['snippet_hits']}, weight 1) / 摘要命中（权重 1）: {snippet_matches}\n"
        f"Formula / 计算式: {formula}\n\n"
        "Range: 0–4. It is a ranking index, not a probability or percentage.\n"
        "范围为 0–4。它是排序指数，不是概率或百分比。\n"
        "CJK tokenization uses whole words, single characters, and adjacent bigrams.\n"
        "中日韩文本使用整词、单字和相邻二字词元。相关性只排序，从不过滤结果。"
    )
    console.print(Panel(escape(text), title="Relevance details / 相关性明细"))


def show_stats(engine: Engine) -> None:
    if not engine.last_stats:
        console.print("Run a search first. / 请先搜索。")
        return
    stats = engine.last_stats
    text = (
        "Last processing batch / 最近一次处理批次\n"
        f"Received from engines / 引擎返回: {stats['received']}\n"
        f"Invalid or incomplete / 无效或信息不完整: {stats['invalid']}\n"
        f"Ad or junk filtered / 广告及垃圾内容过滤: {stats['ads']}\n"
        f"Duplicate URLs removed / 重复网址移除: {stats['duplicates']}\n"
        f"Kept in this batch / 本批保留: {stats['kept']}\n"
        f"Total currently loaded / 当前累计加载: {len(engine.all_results)}\n"
        "Removed for low relevance / 因相关性低而删除: 0（相关性从不用于过滤）"
    )
    console.print(Panel(text, title="Result count / 结果数量统计"))


def show_engine_errors(engine: Engine) -> None:
    if not engine.last_errors:
        console.print("No engine errors recorded. / 暂无引擎错误记录。")
        return
    lines = [
        f"{engine.display_engine(name)}: {message}"
        for name, message in sorted(engine.last_errors.items())
    ]
    console.print(
        Panel(escape("\n\n".join(lines)), title="Engine errors / 引擎错误详情")
    )


def show_article_summary(engine: Engine, number: int) -> None:
    try:
        result = engine.result_at(number)
    except IndexError:
        console.print("Invalid result number. / 无效的结果编号。")
        return
    console.print("Fetching page… / 正在读取网页……")
    try:
        paragraphs = extract_article_paragraphs(result.url)
    except Exception as error:
        detail = shorten(str(error), 160)
        console.print(
            escape(f"Could not summarize this page. / 无法生成网页摘要。 {detail}")
        )
        return
    console.print(escape(f"{result.title}\n{result.url}"))
    console.print(
        Panel(
            escape(paragraph_preview(paragraphs, width=140)),
            title="Paragraph summary / 段落摘要",
            border_style="cyan",
        )
    )


def print_language(engine: Engine) -> None:
    console.print(
        f"Search language / 搜索语言: {language_name(engine.lang)}\n"
        "Use :lang auto for no restriction, or a code such as zh, en, ja, fr.\n"
        "使用 :lang auto 解除限制，或输入 zh、en、ja、fr 等语言代码。"
    )


def show_safari_startup_check(engine: Engine) -> None:
    """At startup, inspect static prerequisites only; never launch Safari here."""
    if engine.browser_mode != "safari":
        return
    report = SafariFetcher.static_check()
    if report["ok"]:
        console.print(
            "[dim]Safari static check passed: macOS, Safari.app, and osascript were found. "
            "Permissions are not tested at startup; use :browser check. / "
            "Safari 静态检查通过：已找到 macOS、Safari.app 和 osascript。"
            "启动时不会检测权限；请输入 :browser check。[/dim]"
        )
        return
    console.print(
        "[yellow]Safari static check failed / Safari 静态检查未通过：\n- "
        + escape("\n- ".join(report["issues"]))
        + "\nUse :browser setup on macOS, or choose another browser mode. / "
        "请在 macOS 上使用 :browser setup，或选择其他浏览器模式。[/yellow]"
    )


def run_safari_permission_check(engine: Engine) -> bool:
    if engine.browser_mode != "safari":
        console.print(
            "Select Safari mode first with :browser safari. / "
            "请先输入 :browser safari 启用 Safari 模式。"
        )
        return False
    static = SafariFetcher.static_check()
    if not static["ok"]:
        console.print(
            "[yellow]Safari prerequisites are unavailable / Safari 前置条件不可用：\n- "
            + escape("\n- ".join(static["issues"]))
            + "\nUse :browser setup on macOS. / 请在 macOS 上使用 :browser setup。[/yellow]"
        )
        return False
    console.print(
        "Testing Safari with one dedicated about:blank page; no Google page, cookies, "
        "history, or existing tabs are read. / 正在使用一个专用 about:blank 页面检测 Safari；"
        "不会读取 Google 页面、Cookie、历史记录或现有标签页。"
    )
    report = engine.get_browser_fetcher().check_permissions()
    if report["ok"]:
        retry = engine.invalidate_failed_google_search()
        console.print(
            "[green]Safari check passed: Automation, JavaScript from Apple Events, and DOM "
            "reading all work. / Safari 检测通过：自动化、来自 Apple 事件的 JavaScript "
            "和 DOM 读取均可用。[/green]"
        )
        if retry:
            console.print(
                "The previous Google failure was cleared; enter the same query to retry. / "
                "此前的 Google 失败缓存已清除；再次输入同一搜索词即可重试。"
            )
        return True
    stage_labels = {
        "automation": "Automation / 自动化",
        "javascript": "JavaScript from Apple Events / 来自 Apple 事件的 JavaScript",
        "dom": "Blank-page DOM reading / 空白页 DOM 读取",
    }
    stage = stage_labels.get(report.get("stage"), "Safari page / Safari 页面")
    console.print(
        "[yellow]Safari check failed at "
        + stage
        + " / Safari 检测在此阶段失败。\n"
        + escape(report.get("error") or "Unknown error / 未知错误")
        + "\nRun :browser setup, change any required permission yourself, then run "
        ":browser check again. / 请运行 :browser setup，由你本人修改所需权限，然后再次运行 "
        ":browser check。[/yellow]"
    )
    return False


def run_safari_setup() -> bool:
    if sys.platform != "darwin":
        console.print(
            "Safari setup is available only on macOS / Safari 设置引导仅支持 macOS。"
        )
        return False
    steps = (
        "Safari setup / Safari 设置引导\n"
        "1. System Settings → Privacy & Security → Automation → your terminal → Safari.\n"
        "   系统设置 → 隐私与安全性 → 自动化 → 你的终端 → Safari。\n"
        "2. Safari → Settings → Advanced → Show features for web developers.\n"
        "   Safari → 设置 → 高级 → 显示网页开发者功能。\n"
        "3. Develop → Allow JavaScript from Apple Events. On some newer versions: "
        "Develop → Developer Settings.\n"
        "   开发 → 允许来自 Apple 事件的 JavaScript。部分新版位于：开发 → 开发者设置。\n"
        "4. Enter any requested Mac password yourself; this program never receives it.\n"
        "   如系统要求 Mac 密码，请你本人输入；本程序不会取得该密码。\n"
        "5. Return here and run :browser check. Enable the mode with :browser safari if needed.\n"
        "   返回此处运行 :browser check；如尚未启用，请再输入 :browser safari。"
    )
    console.print(Panel(steps, title="Safari setup / Safari 设置", border_style="cyan"))
    try:
        SafariFetcher().open_setup()
    except BrowserUnavailableError as error:
        console.print("[yellow]" + escape(str(error)) + "[/yellow]")
        return False
    console.print(
        "Opened Automation settings and Safari. The program does not toggle sensitive "
        "settings or enable Allow Remote Automation. / 已打开自动化设置和 Safari。"
        "程序不会替你切换敏感设置，也不需要开启“允许远程自动化”。"
    )
    return True


def main() -> None:
    engine = Engine()
    filter_state = "on / 开" if engine.filter_ads else "off / 关"
    browser_state = browser_mode_label(engine.browser_mode)
    console.print(
        Panel.fit(
            "[bold]Terminal Search / 终端搜索[/bold]\n"
            f"Search language / 搜索语言: {language_name(engine.lang)}\n"
            f"Search pool / 搜索池: {engine.pool_display()}\n"
            f"Ad filtering / 广告过滤: {filter_state}\n"
            f"Browser fallback / 浏览器回退: {browser_state}\n"
            "[dim]Type :help for commands. / 输入 :help 查看命令。[/dim]",
            border_style="cyan",
        )
    )
    show_safari_startup_check(engine)

    while True:
        try:
            user_input = console.input("[bold cyan]Search 搜索 > [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye! / 再见！")
            engine.close()
            break
        if not user_input:
            continue

        if not user_input.startswith(":"):
            results = engine.search(user_input)
            if engine.last_failed:
                console.print(
                    "[yellow]Engines failed, timed out, or returned no usable response / "
                    "引擎失败、超时或未返回可用响应: "
                    f"{', '.join(engine.display_engine(name) for name in engine.last_failed)}[/yellow]"
                )
                console.print(
                    "[dim]Use :errors for detailed reasons. / "
                    "输入 :errors 查看详细原因。[/dim]"
                )
                if "searxng" in engine.last_failed:
                    console.print(
                        "[dim]SearXNG is optional; use :pool reset to skip it. / "
                        "SearXNG 是可选项；输入 :pool reset 即可不使用它。[/dim]"
                    )
            if not results:
                console.print("No results found. / 没有找到结果。")
            else:
                show_results(engine, results)
            continue

        parts = user_input[1:].split()
        command = parts[0].lower()
        args = parts[1:]

        if command in ("exit", "q"):
            console.print("Bye! / 再见！")
            engine.close()
            break
        if command == "help":
            console.print(Panel(HELP_TEXT, title="Help / 帮助"))
        elif command == "errors":
            show_engine_errors(engine)
        elif command == "stats":
            show_stats(engine)
        elif command == "lang":
            if not args:
                print_language(engine)
            elif engine.set_lang(args[0]):
                console.print(
                    f"Search language saved / 搜索语言已保存: {language_name(engine.lang)}\n"
                    "Run a search to use the new setting. / 重新搜索后生效。"
                )
            else:
                console.print(
                    "Invalid language code. Examples: auto, zh, en, ja, fr, zh-CN.\n"
                    "无效语言代码。示例：auto、zh、en、ja、fr、zh-CN。"
                )
        elif command == "pool":
            builtin = ", ".join(
                name for name in engine.providers if not name.startswith(CUSTOM_PREFIX)
            )
            if not args:
                custom = ", ".join(
                    engine.display_engine(name) for name in engine.custom_engines
                ) or "none / 无"
                console.print(
                    f"Built-in engines / 内置引擎: {builtin}\n"
                    f"Custom engines / 自定义引擎: {custom}\n"
                    f"Current pool / 当前搜索池: {engine.pool_display()}\n"
                    "Add a domain directly, e.g. :pool yahoo.hk / "
                    "可直接添加域名，例如 :pool yahoo.hk"
                )
            else:
                if len(args) == 1 and args[0].lower() == "reset":
                    names = list(DEFAULT_POOL)
                else:
                    names = " ".join(args).split(",")
                valid = engine.set_pool(names)
                if engine.invalid_engines:
                    console.print(
                        escape(
                            "Invalid entries / 无效条目: "
                            + ", ".join(engine.invalid_engines)
                        )
                    )
                if valid:
                    if any("yahoo.jp" in name.lower() for name in names):
                        console.print(
                            "Yahoo Japan alias corrected to yahoo.co.jp. / "
                            "雅虎日本别名已更正为 yahoo.co.jp。"
                        )
                    console.print(
                        f"Search pool saved / 搜索池已保存: {engine.pool_display()}\n"
                        "Run a search to use the new pool. / 重新搜索后生效。"
                    )
                else:
                    console.print(
                        f"No valid engine. / 没有有效引擎。\n"
                        f"Built-in engines / 内置引擎: {builtin}"
                    )
        elif command == "filter":
            if not args:
                state = "on / 开" if engine.filter_ads else "off / 关"
                console.print(f"Ad and junk filtering / 广告及垃圾内容过滤: {state}")
            elif args[0].lower() in ("on", "off"):
                engine.set_filter(args[0].lower() == "on")
                state = "on / 开" if engine.filter_ads else "off / 关"
                console.print(f"Filtering saved / 过滤设置已保存: {state}")
                if engine.current_query and engine.all_results:
                    show_results(engine, engine.page(engine.current_page))
            else:
                console.print("Use :filter on or :filter off. / 请使用 :filter on 或 :filter off。")
        elif command == "browser":
            if not args:
                console.print(
                    "Browser fallback / 浏览器回退: "
                    + browser_mode_label(engine.browser_mode)
                )
            elif args[0].lower() == "check":
                run_safari_permission_check(engine)
            elif args[0].lower() == "setup":
                run_safari_setup()
            elif args[0].lower() in ("on", "off", "safari", "edge"):
                engine.set_browser(args[0].lower())
                state = browser_mode_label(engine.browser_mode)
                if engine.browser_mode == "safari":
                    detail = (
                        "After a static Google failure, a dedicated Safari tab opens the original URL. "
                        "Allow Safari automation and JavaScript from Apple Events; CAPTCHA requires your action. / "
                        "静态 Google 失败后，专用 Safari 标签页会打开原地址。请允许 Safari 自动化及"
                        "“来自 Apple 事件的 JavaScript”；验证码需要你本人完成。"
                    )
                elif engine.browser_mode == "edge":
                    detail = (
                        "After a static Google failure, installed Edge opens the original URL with a "
                        "dedicated persistent profile; no Chromium download. CAPTCHA requires your action. / "
                        "静态 Google 失败后，已安装的 Edge 会使用独立持久配置打开原地址，无需下载 Chromium；"
                        "验证码需要你本人完成。"
                    )
                elif engine.browser_mode == "chromium":
                    detail = (
                        "Chromium opens only after a static engine failure; CAPTCHA requires your action. / "
                        "仅在静态引擎失败后打开 Chromium；验证码需要你本人完成。"
                    )
                else:
                    detail = "Static requests only / 仅使用静态请求。"
                console.print(
                    f"Browser fallback saved / 浏览器回退设置已保存: {state}\n{detail}"
                )
                if engine.browser_mode == "safari":
                    run_safari_permission_check(engine)
            else:
                console.print(
                    "Use :browser off, :browser on, :browser safari, :browser edge, "
                    ":browser check, or :browser setup. / 请使用 :browser off、:browser on、"
                    ":browser safari、:browser edge、:browser check 或 :browser setup。"
                )
        elif command == "new":
            engine.current_query = None
            engine.invalidate_search()
            console.print("New topic ready. / 新话题已就绪。")
        elif command in ("next", "n"):
            if not engine.current_query:
                console.print("Run a search first. / 请先搜索。")
            else:
                if engine.current_page >= engine.page_count and not engine.exhausted:
                    console.print(
                        f"Fetching engine page {engine.provider_page + 1}… / "
                        f"正在抓取引擎第 {engine.provider_page + 1} 页……"
                    )
                if engine.next_page():
                    show_results(engine, engine.page(engine.current_page))
                    if engine.last_failed:
                        console.print(
                            "[dim]Some engines failed or returned no more results; use :errors. / "
                            "部分引擎失败或没有返回更多结果；可输入 :errors 查看。[/dim]"
                        )
                else:
                    console.print(
                        "No more new results from the selected engines. / "
                        "所选引擎没有更多新结果。"
                    )
                    if engine.last_errors:
                        console.print(
                            "[dim]Use :errors for details. / 输入 :errors 查看详情。[/dim]"
                        )
        elif command in ("prev", "p"):
            if not engine.current_query:
                console.print("Run a search first. / 请先搜索。")
            elif engine.prev_page():
                show_results(engine, engine.page(engine.current_page))
            else:
                console.print("No previous page. / 没有上一页。")
        elif command == "open":
            if not args or not engine.current_query:
                console.print("Use :open <number> after a search. / 搜索后使用 :open <编号>。")
                continue
            try:
                result = engine.result_at(int(args[0]))
            except (ValueError, IndexError):
                console.print("Invalid result number. / 无效的结果编号。")
                continue
            console.print(escape(f"Opening / 正在打开: {result.url}"))
            try:
                opened = webbrowser.open(result.url)
                if not opened:
                    console.print("Copy the URL above into your browser. / 请将上方网址复制到浏览器。")
            except webbrowser.Error:
                console.print("Could not open a browser. / 无法打开浏览器。")
        elif command == "score":
            if not args or not engine.current_query:
                console.print(
                    "Use :score <number> after a search. / 搜索后使用 :score <编号>。"
                )
                continue
            try:
                number = int(args[0])
            except ValueError:
                console.print("Invalid result number. / 无效的结果编号。")
                continue
            show_score(engine, number)
        elif command in ("summary", "sum"):
            if not args or not engine.current_query:
                console.print(
                    "Use :summary <number> after a search. / 搜索后使用 :summary <编号>。"
                )
                continue
            try:
                number = int(args[0])
            except ValueError:
                console.print("Invalid result number. / 无效的结果编号。")
                continue
            show_article_summary(engine, number)
        else:
            console.print("Unknown command. Type :help. / 未知命令，请输入 :help。")


if __name__ == "__main__":
    main()
