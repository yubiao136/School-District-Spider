import dataclasses
from typing import List


@dataclasses.dataclass
class ErShouRecord:
    community: str
    total_price: str
    unit_price: str
    area: str
    layout: str
    orientation: str
    floor: str
    listing_url: str
    listing_date: str = ""

    @staticmethod
    def csv_header() -> List[str]:
        return [
            "小区名称",
            "总价(万)",
            "单价(元/平米)",
            "面积(平米)",
            "户型",
            "朝向",
            "楼层",
            "详情页URL",
            "挂牌时间",
        ]

    def to_csv_row(self) -> List[str]:
        return [
            self.community,
            self.total_price,
            self.unit_price,
            self.area,
            self.layout,
            self.orientation,
            self.floor,
            self.listing_url,
            self.listing_date,
        ]
