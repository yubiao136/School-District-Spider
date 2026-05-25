import os
import unittest

from lib.monitor.record import ErShouRecord
from lib.monitor.scraper import (
    _parse_listing_date,
    check_html_blocked,
    extract_total_pages_from_html,
    parse_listings_from_html,
)

_FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures",
)


class TestErShouRecord(unittest.TestCase):
    def test_create_record(self):
        rec = ErShouRecord(
            community="惠安里",
            total_price="98",
            unit_price="14980元/平米",
            area="65.43",
            layout="2室1厅",
            orientation="南 北",
            floor="中楼层(共6层)",
            listing_url="https://tj.ke.com/ershoufang/123.html",
            listing_date="30天前",
        )
        self.assertEqual(rec.community, "惠安里")
        self.assertEqual(rec.total_price, "98")
        self.assertEqual(rec.listing_date, "30天前")

    def test_csv_header_count(self):
        header = ErShouRecord.csv_header()
        self.assertEqual(len(header), 9)

    def test_to_csv_row(self):
        rec = ErShouRecord(
            community="惠安里",
            total_price="98",
            unit_price="14980元/平米",
            area="65.43",
            layout="2室1厅",
            orientation="南 北",
            floor="中楼层(共6层)",
            listing_url="https://tj.ke.com/ershoufang/123.html",
            listing_date="30天前",
        )
        row = rec.to_csv_row()
        self.assertEqual(len(row), 9)
        self.assertEqual(row[0], "惠安里")
        self.assertEqual(row[1], "98")
        self.assertEqual(row[7], "https://tj.ke.com/ershoufang/123.html")

    def test_default_listing_date_is_empty(self):
        rec = ErShouRecord(
            community="测试",
            total_price="",
            unit_price="",
            area="",
            layout="",
            orientation="",
            floor="",
            listing_url="",
        )
        self.assertEqual(rec.listing_date, "")


class TestParseListingDate(unittest.TestCase):
    def test_standard_date(self):
        self.assertEqual(
            _parse_listing_date("2024-01-15发布"), "2024-01-15"
        )

    def test_days_ago(self):
        self.assertEqual(_parse_listing_date("30天前发布"), "30天前")

    def test_with_follow_count(self):
        self.assertEqual(
            _parse_listing_date("3人关注 / 45天前发布"), "45天前"
        )

    def test_empty_input(self):
        self.assertEqual(_parse_listing_date(""), "")
        self.assertEqual(_parse_listing_date(None), "")

    def test_no_date_info(self):
        self.assertEqual(_parse_listing_date("3人关注"), "")


class TestCheckHtmlBlocked(unittest.TestCase):
    def test_normal_page(self):
        html = "<html><body><ul class='sellListContent'><li>...</li></ul></body></html>"
        self.assertFalse(check_html_blocked(html))

    def test_captcha_page(self):
        html = "<html><body>验证码</body></html>"
        self.assertTrue(check_html_blocked(html))

    def test_blocked_keywords(self):
        for kw in ["验证码", "访问受限", "too many requests", "请开启JavaScript"]:
            with self.subTest(keyword=kw):
                html = f"<html><body>{kw}</body></html>"
                self.assertTrue(check_html_blocked(html))

    def test_empty_html(self):
        self.assertFalse(check_html_blocked(""))


class TestExtractTotalPagesFromHtml(unittest.TestCase):
    def test_single_page(self):
        html = """<div class="page-box"
                       page-data='{"totalPage":1,"curPage":1}'>
                 </div>"""
        self.assertEqual(extract_total_pages_from_html(html), 1)

    def test_multiple_pages(self):
        html = """<div class="page-box"
                       page-data='{"totalPage":5,"curPage":1}'>
                 </div>"""
        self.assertEqual(extract_total_pages_from_html(html), 5)

    def test_no_page_box(self):
        html = "<html><body>no page data</body></html>"
        self.assertEqual(extract_total_pages_from_html(html), 1)

    def test_malformed_data(self):
        html = """<div class="page-box" page-data="not-json"></div>"""
        self.assertEqual(extract_total_pages_from_html(html), 1)


class TestParseListingsFromHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_path = os.path.join(_FIXTURE_DIR, "sample_ershou_listing.html")
        with open(fixture_path, "r", encoding="utf-8") as f:
            cls.fixture_html = f.read()

    def test_parse_single_listing(self):
        records = parse_listings_from_html(self.fixture_html)
        self.assertEqual(len(records), 1)

        rec = records[0]
        self.assertEqual(rec.community, "惠安里")
        self.assertEqual(rec.total_price, "98")
        self.assertEqual(rec.unit_price, "14980元/平米")
        self.assertEqual(rec.area, "65.43")
        self.assertEqual(rec.layout, "2室1厅")
        self.assertEqual(rec.orientation, "南 北")
        self.assertEqual(rec.floor, "中楼层(共6层)")
        self.assertEqual(
            rec.listing_url,
            "https://tj.ke.com/ershoufang/12345678.html",
        )
        self.assertEqual(rec.listing_date, "30天前")

    def test_empty_listing_page(self):
        html = "<html><body><ul class='sellListContent'></ul></body></html>"
        records = parse_listings_from_html(html)
        self.assertEqual(len(records), 0)

    def test_no_listing_container(self):
        html = "<html><body>no content</body></html>"
        records = parse_listings_from_html(html)
        self.assertEqual(len(records), 0)


if __name__ == "__main__":
    unittest.main()
