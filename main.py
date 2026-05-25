import argparse
import logging
import sys

from lib.monitor.config import load_config
from lib.monitor.output import write_csv
from lib.monitor.scraper import MonitorErShouScraper
from lib.utility.date import get_date_string


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def _show_config_preview(cfg) -> None:
    print("=" * 48)
    print("  学区房监控配置预览")
    print("=" * 48)

    print(f"  城市      : {cfg.city.get('name', '')} ({cfg.city.get('code', '')})")
    print(f"  输出目录  : {cfg.output['dir']}")
    print(f"  预算上限  : {cfg.budget['max_price']:,} {cfg.budget.get('unit', '')}")
    print()

    print(f"  学校分组 ({len(cfg.school_groups)}):")
    for group in cfg.school_groups:
        schools = ", ".join(group.schools)
        print(f"    - {group.name}: [{schools}]")
    print()

    print(f"  目标小区 ({len(cfg.target_xiaoqu)}):")
    for i in range(0, len(cfg.target_xiaoqu), 5):
        chunk = cfg.target_xiaoqu[i : i + 5]
        print("    " + ", ".join(chunk))
    print()

    notify = cfg.notification
    if notify.get("enabled"):
        print(f"  通知      : 已启用 (类型: {notify.get('type', 'N/A')})")
    else:
        print("  通知      : 未启用")
    print("=" * 48)


def main():
    _setup_logging()

    parser = argparse.ArgumentParser(description="学区房监控工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    run_once = subparsers.add_parser(
        "run-once", help="加载配置并执行一次采集"
    )
    run_once.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式（仅打印配置，不执行任何采集）",
    )
    run_once.add_argument(
        "--limit-communities",
        type=int,
        default=0,
        help="限制采集的小区数量（用于测试，0=不限）",
    )

    args = parser.parse_args()

    if args.command != "run-once":
        parser.print_help()
        return

    cfg = load_config()
    _show_config_preview(cfg)

    limit = args.limit_communities if args.limit_communities > 0 else None
    if limit:
        print(f"\n  限制采集前 {limit} 个小区\n")

    if args.dry_run:
        print("[DRY RUN] 跳过真实采集流程。")
        return

    print("开始采集 ...")
    scraper = MonitorErShouScraper(cfg)
    records = scraper.scrape_all(limit=limit)

    date_str = get_date_string()
    csv_path = write_csv(
        records=records,
        output_dir=cfg.output["dir"],
        city=cfg.city["code"],
        date_str=date_str,
    )

    total_communities = len(cfg.target_xiaoqu) if not limit else limit
    print()
    print("=" * 48)
    print("  采集完成")
    print(f"  目标小区          : {total_communities}")
    print(f"  成功采集小区数    : {len(set(r.community for r in records))}")
    print(f"  房源总记录数      : {len(records)}")
    print(f"  输出文件          : {csv_path}")
    print("=" * 48)


if __name__ == "__main__":
    main()
