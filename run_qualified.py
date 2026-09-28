#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按学校打卡点生成合格跑步：6 点踩 5 个，约 3.0km，配速/步频落在规则内。"""
from __future__ import annotations

import json, math, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yundong_run import (
    api, get_home_run_info, run_start, split_point, run_finish,
    DEVICE_NAME, SYS_EDITION, APP_EDITION,
)

# 主校区 6 个打卡点（getHomeRunInfo.points，E 现场拉取）
CHECKPOINTS = [
    (117.596597, 31.608729),
    (117.596941, 31.608327),
    (117.597305, 31.607937),
    (117.596005, 31.608317),
    (117.596259, 31.608032),
    (117.596523, 31.607543),
]
MARK_Y = [0, 1, 2, 3, 5]  # 踩 5 个 = raDislikes
DIST_KM = 3.0
DURATION_S = 840          # 3km / 840s ≈ 4.67 min/km
PACE = round(DURATION_S / 60 / DIST_KM, 2)  # min/km
CADENCE = 170
STRIDES = 0.8


def haversine_m(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def path_length(route):
    return sum(haversine_m(route[i], route[i + 1]) for i in range(len(route) - 1))


def densify(route, n_total):
    """按累计弧长等距插值到 n_total 个点."""
    segs = [haversine_m(route[i], route[i + 1]) for i in range(len(route) - 1)]
    total = sum(segs) or 1.0
    out, acc, si, seg_acc = [], 0.0, 0, 0.0
    for i in range(n_total):
        target = total * i / (n_total - 1)
        while si < len(segs) - 1 and seg_acc + segs[si] < target:
            seg_acc += segs[si]
            si += 1
        t = 0.0 if segs[si] == 0 else (target - seg_acc) / segs[si]
        x1, y1 = route[si]
        x2, y2 = route[si + 1]
        # 微抖动，避免完美直线
        jx = random.uniform(-2e-6, 2e-6)
        jy = random.uniform(-2e-6, 2e-6)
        out.append((x1 + (x2 - x1) * t + jx, y1 + (y2 - y1) * t + jy))
    return out


def build_route():
    # 顺序串起全部 6 点，再回到起点附近凑够里程
    route = list(CHECKPOINTS)
    # 闭环再绕一圈抬里程
    route += CHECKPOINTS[1:] + [CHECKPOINTS[0]]
    # 拉长到 ≈3km
    length = path_length(route)
    if length < DIST_KM * 1000 * 0.95:
        # 在最长边上加绕行
        route = route + [CHECKPOINTS[2], CHECKPOINTS[4], CHECKPOINTS[0]]
    return route


def make_points(n=50):
    route = build_route()
    coords = densify(route, n)
    # 按弧长分配 runMileage / runTime
    segs = [haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    total = sum(segs) or 1.0
    # 目标总里程
    target_m = DIST_KM * 1000
    scale = target_m / total
    pts, acc_m, acc_s = [], 0.0, 0
    ts0 = int(time.time()) - DURATION_S
    for i, (lon, lat) in enumerate(coords):
        if i > 0:
            acc_m += segs[i - 1] * scale
        acc_s = int(DURATION_S * i / (n - 1))
        pts.append({
            "point": f"{lon:.8f},{lat:.8f}",
            "runStatus": "1",
            "speed": f"{random.uniform(4.6, 5.2):.2f}",
            "isFence": "Y",
            "isMock": False,
            "runMileage": f"{acc_m:.4f}",
            "runTime": f"{acc_s}",
            "ts": str(ts0 + acc_s),
        })
    return pts


def manage_list():
    out = []
    for idx, (lon, lat) in enumerate(CHECKPOINTS):
        marked = "Y" if idx in MARK_Y else "N"
        out.append({
            "point": f"{lon},{lat}",
            "marked": marked,
            "index": str(idx if marked == "Y" else ""),
        })
    return out


def run_once():
    home = get_home_run_info()
    info = home["data"]["cralist"][0]
    print("task", info["id"], info["raName"], "min", info["raSingleMileageMin"],
          "max", info["raSingleMileageMax"], "pace", info.get("raPaceMin"), info.get("raPaceMax"))
    start = run_start(info["raRunArea"], info["raType"], info["id"])
    print("start", json.dumps(start, ensure_ascii=False)[:240])
    if start.get("code") != 200:
        return start
    rec_id = start["data"]["id"]
    rec_start = start["data"].get("recordStartTime", "")
    student = start["data"].get("studentId", "")
    meta = {
        "crsRunRecordId": rec_id,
        "schoolId": info.get("schoolId", 100),
        "userName": student,
        "strides": STRIDES,
        "speeds": f"{PACE:.2f}",
        "cadence_min": CADENCE,
        "cadence_max": CADENCE + 5,
    }
    pts = make_points(50)
    print("points", len(pts), "lastMileage", pts[-1]["runMileage"], "lastTime", pts[-1]["runTime"])
    splits = []
    for i in range(0, len(pts), 10):
        chunk = pts[i:i + 10]
        if len(chunk) < 2:
            continue
        r = split_point(chunk, meta)
        splits.append(r)
        print("split", i, json.dumps(r, ensure_ascii=False)[:180])
        time.sleep(1.5)
    mg = manage_list()
    print("manage", json.dumps(mg, ensure_ascii=False))
    fin = run_finish({
        "recordMileage": f"{DIST_KM:.2f}",
        "recodeCadence": str(CADENCE),
        "recodePace": f"{PACE:.2f}",
        "deviceName": DEVICE_NAME,
        "sysEdition": SYS_EDITION,
        "appEdition": APP_EDITION,
        "raIsStartPoint": "Y",
        "raIsEndPoint": "Y",
        "raRunArea": info["raRunArea"],
        "recodeDislikes": str(len(MARK_Y)),
        "raId": str(info["id"]),
        "raType": info["raType"],
        "id": str(rec_id),
        "duration": str(DURATION_S),
        "recordStartTime": rec_start,
        "manageList": mg,
        "remake": "1",
    })
    print("finish", json.dumps(fin, ensure_ascii=False))
    return {"recordId": rec_id, "finish": fin, "splits": splits}


if __name__ == "__main__":
    random.seed()
    run_once()
