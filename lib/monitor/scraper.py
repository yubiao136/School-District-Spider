import json
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from lib.monitor.config import MonitorConfig
from lib.monitor.record import ErShouRecord

logger = logging.getLogger(__name__)

_PAGE_TIMEOUT_MS = 30_000
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
_BLOCKED_KEYWORDS = ["验证码", "访问受限", "too many requests", "请开启JavaScript"]


class AntiScrapeError(RuntimeError):
    """Raised when the target page returns an anti-scraping / captcha page."""


# ------------------------------------------------------------------
# Standalone parsing helpers (testable without Playwright)
# ------------------------------------------------------------------


def check_html_blocked(html: str) -> bool:
    """Return True if the HTML indicates a captcha / anti-scrape page."""
    for kw in _BLOCKED_KEYWORDS:
        if kw in html:
            return True
    return False


def extract_total_pages_from_html(html: str) -> int:
    """Read total-page count from the page-box element's page-data attribute."""
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one(".page-box")
    if not box:
        return 1
    raw = box.get("page-data") or "{}"
    try:
        data = json.loads(raw)
        return int(data.get("totalPage", 1))
    except (ValueError, TypeError):
        return 1


def _parse_listing_date(follow_info: str) -> str:
    """Extract listing date from followInfo text.

    Handles formats like:
      - "45天前发布"
      - "2024-01-15发布"
    Returns empty string when no date information is found.
    """
    if not follow_info:
        return ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", follow_info)
    if m:
        return m.group(1)
    m = re.search(r"(\d+)天前发布", follow_info)
    if m:
        return f"{m.group(1)}天前"
    return ""


def parse_listings_from_html(html: str) -> List[ErShouRecord]:
    """Parse ErShouRecord list from raw ke.com listing page HTML."""
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("ul.sellListContent > li.clear")
    records: List[ErShouRecord] = []

    for item in items:
        title_el = item.select_one(".title a")
        house_info_el = item.select_one(".houseInfo")
        total_price_el = item.select_one(".totalPrice span")
        unit_price_el = item.select_one(".unitPrice span")
        community_el = item.select_one(".communityName a")
        follow_info_el = item.select_one(".followInfo")

        house_info = house_info_el.get_text(strip=True) if house_info_el else ""
        parts = [p.strip() for p in house_info.split("|")]

        listing_url = title_el["href"] if title_el and title_el.has_attr("href") else ""
        layout = parts[0] if len(parts) > 0 else ""
        area_raw = parts[1] if len(parts) > 1 else ""
        orientation = parts[2] if len(parts) > 2 else ""
        floor = parts[4] if len(parts) > 4 else ""
        total_price = total_price_el.get_text(strip=True) if total_price_el else ""
        unit_price = unit_price_el.get_text(strip=True) if unit_price_el else ""
        community = community_el.get_text(strip=True) if community_el else ""
        follow_info = follow_info_el.get_text(strip=True) if follow_info_el else ""

        area = area_raw.replace("平米", "").strip()
        listing_date = _parse_listing_date(follow_info)

        records.append(
            ErShouRecord(
                community=community,
                total_price=total_price,
                unit_price=unit_price,
                area=area,
                layout=layout,
                orientation=orientation,
                floor=floor,
                listing_url=listing_url,
                listing_date=listing_date,
            )
        )
    return records


# ------------------------------------------------------------------
# Playwright-based scraper
# ------------------------------------------------------------------


class MonitorErShouScraper:
    def __init__(self, config: MonitorConfig, headless: bool = True):
        self.config = config
        self.city_code = config.city["code"]
        self.headless = headless

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_all(
        self, limit: Optional[int] = None
    ) -> List[ErShouRecord]:
        """Scrape every community listed in config.target_xiaoqu."""
        communities = self.config.target_xiaoqu
        if limit is not None and limit > 0:
            communities = communities[:limit]

        all_records: List[ErShouRecord] = []
        failed_communities: List[str] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=_DEFAULT_UA,
                locale="zh-CN",
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
            )

            for community in communities:
                try:
                    records = self._scrape_single(context, community)
                    all_records.extend(records)
                    logger.info(
                        "小区 [%s] 采集完成，获取 %d 条房源",
                        community,
                        len(records),
                    )
                except AntiScrapeError as e:
                    failed_communities.append(community)
                    logger.error("小区 [%s] 采集失败: %s", community, e)
                except Exception as e:
                    failed_communities.append(community)
                    logger.exception("小区 [%s] 采集异常: %s", community, e)

            context.close()
            browser.close()

        total_failed = len(failed_communities)
        logger.info(
            "采集汇总: 目标小区 %d 个, 成功 %d 个, 失败 %d 个, "
            "房源总记录 %d 条",
            len(communities),
            len(communities) - total_failed,
            total_failed,
            len(all_records),
        )
        return all_records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_search_url(city_code: str, community: str) -> str:
        return f"https://{city_code}.ke.com/ershoufang/rs{community}/"

    def _scrape_single(
        self, context, community: str
    ) -> List[ErShouRecord]:
        """Scrape all pages of listings for a single community."""
        page = context.new_page()
        page.set_default_timeout(_PAGE_TIMEOUT_MS)

        url = self._build_search_url(self.city_code, community)
        logger.info("正在采集小区 [%s]: %s", community, url)

        try:
            page.goto(url, wait_until="networkidle")
            html = page.content()

            if check_html_blocked(html):
                raise AntiScrapeError(
                    f"检测到反爬页面，当前 URL: {page.url}"
                )

            try:
                page.wait_for_selector(
                    "ul.sellListContent", timeout=10_000
                )
            except Exception:
                logger.warning("小区 [%s] 无挂牌房源或页面结构异常", community)
                return []

            total_pages = extract_total_pages_from_html(html)
            logger.info("小区 [%s]: 共 %d 页", community, total_pages)

            records: List[ErShouRecord] = []
            for pg in range(1, total_pages + 1):
                if pg > 1:
                    page_num_url = f"{url}pg{pg}/"
                    logger.debug(
                        "小区 [%s] 翻页: %s", community, page_num_url
                    )
                    page.goto(page_num_url, wait_until="networkidle")
                    html = page.content()
                    if check_html_blocked(html):
                        raise AntiScrapeError(
                            f"翻页时检测到反爬页面，URL: {page.url}"
                        )
                    page.wait_for_selector(
                        "ul.sellListContent", timeout=10_000
                    )
                else:
                    # First page: re-use the HTML we already fetched
                    pass

                page_html = page.content()
                page_records = parse_listings_from_html(page_html)
                records.extend(page_records)
                logger.debug(
                    "小区 [%s] 第 %d 页: %d 条",
                    community,
                    pg,
                    len(page_records),
                )

            return records

        finally:
            page.close()
