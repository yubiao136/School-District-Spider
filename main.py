import argparse

from lib.monitor.config import load_config


def main():
    parser = argparse.ArgumentParser(description="学区房监控工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    run_once = subparsers.add_parser("run-once", help="加载配置并预览本次监控目标范围")
    run_once.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式（仅打印配置，不执行任何采集）",
    )

    args = parser.parse_args()

    if args.command == "run-once":
        cfg = load_config()
        print("=" * 48)
        print("  学区房监控配置预览")
        print("=" * 48)
        if args.dry_run:
            print("  [DRY RUN MODE] 以下仅为配置预览，不会执行任何网络请求")
            print()

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
