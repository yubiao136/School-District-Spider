import csv
import logging
import os
from typing import List

from lib.monitor.record import ErShouRecord

logger = logging.getLogger(__name__)


def write_csv(
    records: List[ErShouRecord],
    output_dir: str,
    city: str,
    date_str: str,
) -> str:
    """Write ErShouRecord list to a CSV file (UTF-8 BOM for Excel).

    Returns the absolute path of the written file.
    """
    dir_path = os.path.join(output_dir, "monitor", city, date_str)
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, "target_communities.csv")

    with open(file_path, "w", newline="", encoding="utf_8_sig") as f:
        writer = csv.writer(f)
        writer.writerow(ErShouRecord.csv_header())
        for rec in records:
            writer.writerow(rec.to_csv_row())

    logger.info("房源记录已写入 CSV: %s (%d 条)", file_path, len(records))
    return file_path
