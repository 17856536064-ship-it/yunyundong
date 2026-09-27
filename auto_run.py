#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云运动 · 定时挂机（无 GUI，可后台/计划任务）.

用法:
  python auto_run.py --now          # 立即跑一次
  python auto_run.py                # 常驻，每天 HH:MM 自动跑（读配置）
  python auto_run.py --at 07:30 --days 1,2,3,4,5
"""
from __future__ import annotations

import argparse, json, sys, time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from yunyundong_desktop import API, load_cfg, save_cfg  # noqa: E402


def run_once(tag=""):
    cfg = load_cfg()
    log = lambda s: print(f"[{datetime.now().strftime('%F %T')}] {tag}{s}", flush=True)
    api = API(cfg, log)
    r = api.run_once()
    log(f"DONE {json.dumps(r, ensure_ascii=False)[:240]}")
    return r


def main():
    ap = argparse.ArgumentParser(description="云运动定时跑步")
    ap.add_argument("--now", action="store_true", help="立即执行一次")
    ap.add_argument("--at", default=None, help="HH:MM 覆盖配置中的时刻")
    ap.add_argument("--days", default=None, help="ISO 星期 1-7，逗号分隔")
    ap.add_argument("--loop", action="store_true", help="强制常驻循环")
    a = ap.parse_args()

    cfg = load_cfg()
    if a.at:
        h, m = a.at.split(":")
        cfg["timer_hh"], cfg["timer_mm"] = int(h), int(m)
    if a.days:
        cfg["timer_days"] = a.days
    save_cfg(cfg)

    if a.now:
        run_once("[NOW] ")
        return

    hh, mm = int(cfg["timer_hh"]), int(cfg["timer_mm"])
    days = [int(x) for x in str(cfg.get("timer_days", "1,2,3,4,5,6,7")).split(",") if x]
    print(f"[TIMER] armed {hh:02d}:{mm:02d} days={days} cfg={HERE / 'yunyundong_config.json'}", flush=True)
    fired = None
    while True:
        now = datetime.now()
        stamp = now.strftime("%Y%m%d")
        if (now.isoweekday() in days and now.hour == hh and now.minute == mm
                and fired != stamp):
            fired = stamp
            try:
                run_once("[AUTO] ")
            except Exception as e:
                print(f"[AUTO] FAIL {e}", flush=True)
        time.sleep(20)


if __name__ == "__main__":
    main()
