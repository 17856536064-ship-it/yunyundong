#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云运动 · 桌面工作台（国内审美 / Arco 浅色）
双击「云运动工作站.exe」或「启动云运动.bat」
"""
from __future__ import annotations

import base64, gzip, hashlib, json, random, threading, time, uuid as uuidlib
import urllib.request, urllib.error
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_PATH = HERE / "yunyundong_config.json"

# ───────────── SM4 ─────────────
SBOX = [
0xD6,0x90,0xE9,0xFE,0xCC,0xE1,0x3D,0xB7,0x16,0xB6,0x14,0xC2,0x28,0xFB,0x2C,0x05,
0x2B,0x67,0x9A,0x76,0x2A,0xBE,0x04,0xC3,0xAA,0x44,0x13,0x26,0x49,0x86,0x06,0x99,
0x9C,0x42,0x50,0xF4,0x91,0xEF,0x98,0x7A,0x33,0x54,0x0B,0x43,0xED,0xCF,0xAC,0x62,
0xE4,0xB3,0x1C,0xA9,0xC9,0x08,0xE8,0x95,0x80,0xDF,0x94,0xFA,0x75,0x8F,0x3F,0xA6,
0x47,0x07,0xA7,0xFC,0xF3,0x73,0x17,0xBA,0x83,0x59,0x3C,0x19,0xE6,0x85,0x4F,0xA8,
0x68,0x6B,0x81,0xB2,0x71,0x64,0xDA,0x8B,0xF8,0xEB,0x0F,0x4B,0x70,0x56,0x9D,0x35,
0x1E,0x24,0x0E,0x5E,0x63,0x58,0xD1,0xA2,0x25,0x22,0x7C,0x3B,0x01,0x21,0x78,0x87,
0xD4,0x00,0x46,0x57,0x9F,0xD3,0x27,0x52,0x4C,0x36,0x02,0xE7,0xA0,0xC4,0xC8,0x9E,
0xEA,0xBF,0x8A,0xD2,0x40,0xC7,0x38,0xB5,0xA3,0xF7,0xF2,0xCE,0xF9,0x61,0x15,0xA1,
0xE0,0xAE,0x5D,0xA4,0x9B,0x34,0x1A,0x55,0xAD,0x93,0x32,0x30,0xF5,0x8C,0xB1,0xE3,
0x1D,0xF6,0xE2,0x2E,0x82,0x66,0xCA,0x60,0xC0,0x29,0x23,0xAB,0x0D,0x53,0x4E,0x6F,
0xD5,0xDB,0x37,0x45,0xDE,0xFD,0x8E,0x2F,0x03,0xFF,0x6A,0x72,0x6D,0x6C,0x5B,0x51,
0x8D,0x1B,0xAF,0x92,0xBB,0xDD,0xBC,0x7F,0x11,0xD9,0x5C,0x41,0x1F,0x10,0x5A,0xD8,
0x0A,0xC1,0x31,0x88,0xA5,0xCD,0x7B,0xBD,0x2D,0x74,0xD0,0x12,0xB8,0xE5,0xB4,0xB0,
0x89,0x69,0x97,0x4A,0x0C,0x96,0x77,0x7E,0x65,0xB9,0xF1,0x09,0xC5,0x6E,0xC6,0x84,
0x18,0xF0,0x7D,0xEC,0x3A,0xDC,0x4D,0x20,0x79,0xEE,0x5F,0x3E,0xD7,0xCB,0x39,0x48]
FK = [0xA3B1BAC6, 0x56AA3350, 0x677D9197, 0xB27022DC]
CK = [0x00070e15,0x1c232a31,0x383f464d,0x545b6269,0x70777e85,0x8c939aa1,0xa8afb6bd,0xc4cbd2d9,
0xe0e7eef5,0xfc030a11,0x181f262d,0x343b4249,0x50575e65,0x6c737a81,0x888f969d,0xa4abb2b9,
0xc0c7ced5,0xdce3eaf1,0xf8ff060d,0x141b2229,0x30373e45,0x4c535a61,0x686f767d,0x848b9299,
0xa0a7aeb5,0xbcc3cad1,0xd8dfe6ed,0xf4fb0209,0x10171e25,0x2c333a41,0x484f565d,0x646b7279]

def _rotl(x, n):
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

def _tau(a):
    return (SBOX[(a>>24)&0xFF]<<24)|(SBOX[(a>>16)&0xFF]<<16)|(SBOX[(a>>8)&0xFF]<<8)|SBOX[a&0xFF]

def _lenc(b):
    return b ^ _rotl(b,2) ^ _rotl(b,10) ^ _rotl(b,18) ^ _rotl(b,24)

def _lkey(b):
    return b ^ _rotl(b,13) ^ _rotl(b,23)

def sm4_ks(key):
    mk = [int.from_bytes(key[i:i+4],"big") for i in range(0,16,4)]
    k = [mk[i]^FK[i] for i in range(4)]
    rk = []
    for i in range(32):
        t = k[i] ^ _lkey(_tau(k[i+1]^k[i+2]^k[i+3]^CK[i]))
        k.append(t); rk.append(t)
    return rk

def sm4_blk(rk, block, dec=False):
    x = [int.from_bytes(block[i:i+4],"big") for i in range(0,16,4)]
    o = rk[::-1] if dec else rk
    for i in range(32):
        x.append(x[i] ^ _lenc(_tau(x[i+1]^x[i+2]^x[i+3]^o[i])))
    return b"".join(x[35-j].to_bytes(4,"big") for j in range(4))

def _pad(d):
    n = 16 - len(d)%16
    return d + bytes([n])*n

def _unpad(d):
    n = d[-1] if d else 0
    return d[:-n] if 1<=n<=16 and d[-n:]==bytes([n])*n else d

def sm4_enc(key, data):
    rk = sm4_ks(key); data = _pad(data)
    return b"".join(sm4_blk(rk, data[i:i+16]) for i in range(0,len(data),16))

def sm4_dec(key, data):
    rk = sm4_ks(key)
    return _unpad(b"".join(sm4_blk(rk, data[i:i+16], True) for i in range(0,len(data),16)))

# ───────────── 常量 ─────────────
SM4_KEY = base64.b64decode("JXhWGZjmhhXN+nt8nLpNxA==")
CIPHER_KEY = "BGfbsG9EkXz5KeCva8E0MisBeS6bhBEDId3VXeIuBoiBMZU0Mosv7PqKsvqxZ3PjkUlsjzh09Se629SWW45XP4TIUeXoLpYzgk5fAMbg0VNVnXuLH9xVzdHAeM+1qJrgvwwkwio85/DnrP1aArvVQrw3N4xd5tugqQ=="
APPSECRET = "0h1UIfMDSc7piesRINRXXfkE"
BASE = "http://192.0.2.10:8000/m-api"
APP_EDITION = "3.6.6"
CHECKPOINTS = [
    (117.596597, 31.608729), (117.596941, 31.608327),
    (117.597305, 31.607937), (117.596005, 31.608317),
    (117.596259, 31.608032), (117.596523, 31.607543),
]
MARK_Y = [0, 1, 2, 3, 5]

# Arco 色板
BG = "#F2F3F5"; CARD = "#FFFFFF"; BORDER = "#E5E6EB"
T1 = "#1D2129"; T2 = "#4E5969"; T3 = "#86909C"; T4 = "#C9CDD4"
BLUE = "#165DFF"; BLUE_BG = "#E8F3FF"; GREEN = "#00B42A"; RED = "#F53F3F"; ORANGE = "#FF7D00"
FONT = ("Microsoft YaHei UI", 9)
FONT_H = ("Microsoft YaHei UI", 11, "bold")
FONT_L = ("Microsoft YaHei UI", 10)
MONO = ("Consolas", 9)

DEFAULT_CFG = {
    "token": "00000000-0000-0000-0000-000000000000",
    "username": "20230000001", "password": "", "school_id": "100",
    "deviceid": "00000000-0000-0000-0000-000000000000", "devicename": "iPhone 16 Pro",
    "platform": "ios", "base": BASE,
    "dist_km": 3.0, "duration_s": 840, "n_points": 50,
    "marks": 5, "pace": 4.67, "cadence": 170, "strides": 0.8,
    "timer_on": False, "timer_hh": 7, "timer_mm": 30, "timer_days": "1,2,3,4,5",
}

def load_cfg():
    try:
        return {**DEFAULT_CFG, **json.loads(CFG_PATH.read_text("utf-8"))}
    except Exception:
        return dict(DEFAULT_CFG)

def save_cfg(cfg):
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")

# ───────────── API ─────────────
class API:
    def __init__(self, cfg, log=print):
        self.cfg = cfg; self.log = log

    def getsign(self, utc, u):
        sb = f"platform={self.cfg['platform']}&utc={utc}&uuid={u}&appsecret={APPSECRET}"
        return hashlib.md5(sb.encode()).hexdigest()

    def _enc(self, payload, gz=False):
        if payload is None or payload == "":
            return ""
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        if not raw:
            return ""
        if gz:
            raw = gzip.compress(raw)
        return base64.b64encode(sm4_enc(SM4_KEY, raw)).decode()

    def _dec(self, raw):
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        text = raw.decode("utf-8", "replace")
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except Exception:
                return text
        try:
            b64 = json.loads(text) if text[:1] == '"' else text.strip().strip('"')
        except Exception:
            b64 = text.strip().strip('"')
        pt = sm4_dec(SM4_KEY, base64.b64decode(b64))
        try:
            return json.loads(pt.decode("utf-8"))
        except Exception:
            try:
                return json.loads(gzip.decompress(pt).decode("utf-8"))
            except Exception:
                return pt.decode("utf-8", "replace")[:200]

    def call(self, path, payload="", gz=False, timeout=30):
        body = {"cipherKey": CIPHER_KEY, "content": self._enc(payload, gz=gz)}
        u = str(uuidlib.uuid4()).upper()
        utc = str(int(time.time()))
        url = self.cfg["base"] + (path if path.startswith("/") else "/" + path)
        headers = {
            "deviceid": self.cfg["deviceid"],
            "user-agent": f"LePao/{APP_EDITION} (iPhone; iOS 26.6; Scale/3.00)",
            "sysversion": "26.6", "content-type": "application/json", "version": APP_EDITION,
            "isapp": "app", "token": self.cfg["token"], "accept-encoding": "gzip, deflate",
            "accept": "*/*", "devicename": self.cfg["devicename"], "platform": self.cfg["platform"],
            "uuid": u, "sign": self.getsign(utc, u), "utc": utc,
        }
        data = json.dumps(body, separators=(",", ":")).encode()
        self.log(f"→ {path}")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                r = self._dec(resp.read())
        except urllib.error.HTTPError as e:
            r = self._dec(e.read()) if e.fp else {"code": e.code, "msg": str(e)}
        except Exception as e:
            r = {"code": -1, "msg": str(e)}
        s = json.dumps(r, ensure_ascii=False) if not isinstance(r, str) else r
        self.log(f"← {s[:140]}")
        return r

    def app_login(self):
        r = self.call("/login/appLogin", {
            "username": self.cfg["username"], "password": self.cfg["password"],
            "schoolId": self.cfg["school_id"]})
        if isinstance(r, dict) and r.get("code") == 200 and isinstance(r.get("data"), dict):
            tok = r["data"].get("token")
            if tok:
                self.cfg["token"] = tok; save_cfg(self.cfg)
        return r

    def student(self):
        return self.call("/login/getStudentInfo")

    def home(self):
        return self.call("/run/getHomeRunInfo")

    def run_once(self):
        home = self.home()
        if not (isinstance(home, dict) and home.get("data", {}).get("cralist")):
            return {"code": -2, "msg": "no task", "raw": home}
        info = home["data"]["cralist"][0]
        start = self.call("/run/start", {
            "raRunArea": info.get("raRunArea", ""), "raType": info["raType"], "raId": info["id"]})
        if not (isinstance(start, dict) and start.get("code") == 200):
            return {"code": -3, "msg": "start fail", "raw": start}
        rec_id = start["data"]["id"]
        rec_start = start["data"].get("recordStartTime", "")
        student = start["data"].get("studentId", self.cfg["username"])
        dist = float(self.cfg["dist_km"]); dur = int(self.cfg["duration_s"])
        n = int(self.cfg["n_points"]); cad = int(self.cfg["cadence"])
        pace = round(dur / 60 / dist, 2)
        pts, ts0 = [], int(time.time()) - dur
        o = (117.5966, 31.6083)
        for i in range(n):
            t = i / (n - 1)
            lon = o[0] + 0.0008 * t + (0.0003 if i % 2 == 0 else -0.0003) * t * (dist / 2.2)
            lat = o[1] + 0.0005 * t + (0.0002 if i % 3 == 0 else -0.0002) * t * (dist / 2.2)
            pts.append({
                "point": f"{lon:.8f},{lat:.8f}", "runStatus": "1",
                "speed": f"{random.uniform(4.6, 5.2):.2f}", "isFence": "Y", "isMock": False,
                "runMileage": f"{dist * 1000 * (i + 1) / n:.4f}",
                "runTime": f"{int(dur * (i + 1) / n)}", "ts": str(ts0 + int(dur * (i + 1) / n))})
        for i in range(0, len(pts), 10):
            chunk = pts[i:i + 10]
            if len(chunk) < 2:
                continue
            self.call("/run/splitPointCheating", {
                "StepNumber": int((float(chunk[-1]["runMileage"]) - float(chunk[0]["runMileage"])) / 0.8),
                "a": 0, "b": None, "c": None,
                "mileage": float(chunk[-1]["runMileage"]) - float(chunk[0]["runMileage"]),
                "orientationNum": 0, "runSteps": cad, "cardPointList": chunk, "simulateNum": 0,
                "time": float(chunk[-1]["runTime"]) - float(chunk[0]["runTime"]),
                "crsRunRecordId": rec_id, "speeds": f"{pace:.2f}",
                "schoolId": info.get("schoolId", 100), "strides": 0.8, "userName": student}, gz=True)
            time.sleep(1.0)
        mg = [{"point": f"{lon},{lat}",
               "marked": "Y" if i in MARK_Y[:int(self.cfg["marks"])] else "N",
               "index": str(i) if i in MARK_Y[:int(self.cfg["marks"])] else ""}
              for i, (lon, lat) in enumerate(CHECKPOINTS)]
        fin = self.call("/run/finish", {
            "recordMileage": f"{dist:.2f}", "recodeCadence": str(cad), "recodePace": f"{pace:.2f}",
            "deviceName": self.cfg["devicename"], "sysEdition": "26.6", "appEdition": APP_EDITION,
            "raIsStartPoint": "Y", "raIsEndPoint": "Y", "raRunArea": info.get("raRunArea", ""),
            "recodeDislikes": str(int(self.cfg["marks"])), "raId": str(info["id"]),
            "raType": info["raType"], "id": str(rec_id), "duration": str(dur),
            "recordStartTime": rec_start, "manageList": mg, "remake": "1"})
        return {"code": 200, "recordId": rec_id, "finish": fin}

# ───────────── GUI ─────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.api = API(self.cfg, self.log)
        self.timer_on = bool(self.cfg.get("timer_on"))
        self._timer_fired = False
        self._build()
        self.log("云运动工作台已启动 · 3.6.6")
        self.after(200, self._tick)

    def _build(self):
        self.title("云运动 · 工作台")
        self.geometry("1020x720")
        self.configure(bg=BG)
        self._style()

        # 顶栏
        top = tk.Frame(self, bg=CARD, height=56)
        top.pack(fill="x")
        tk.Frame(top, bg=BLUE, width=32, height=32).place(x=16, y=12)
        tk.Label(top, text="Y", bg=BLUE, fg="white", font=FONT_H).place(x=16, y=12, width=32, height=32)
        tk.Label(top, text="云运动 · 工作台", bg=CARD, fg=T1, font=FONT_H).pack(side="left", padx=12, pady=10)
        tk.Label(top, text="LePao 3.6.6 · 协议客户端", bg=CARD, fg=T3, font=FONT).pack(side="left", pady=18)
        self.lbl_clock = tk.Label(top, text="", bg=CARD, fg=T2, font=FONT_L)
        self.lbl_clock.pack(side="right", padx=20)
        self.lbl_state = tk.Label(top, text="就绪", bg=BLUE_BG, fg=BLUE, font=FONT, padx=12, pady=4)
        self.lbl_state.pack(side="right", padx=8, pady=14)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(12, 0))
        left = tk.Frame(body, bg=CARD, width=180, highlightthickness=1, highlightbackground=BORDER)
        left.pack(side="left", fill="y"); left.pack_propagate(False)
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        tk.Label(left, text="核心", bg=CARD, fg=T3, font=FONT, anchor="w").pack(fill="x", padx=16, pady=(16, 4))
        self.nav_btns = {}
        for key, name in [("run", "跑步控制"), ("auth", "账号登录"), ("timer", "定时挂机"),
                          ("api", "接口调试"), ("crypto", "加解密"), ("hist", "历史成绩")]:
            if key == "api":
                tk.Label(left, text="工具", bg=CARD, fg=T3, font=FONT, anchor="w").pack(fill="x", padx=16, pady=(12, 4))
            b = tk.Button(left, text=name, anchor="w", bg=CARD, fg=T2, relief="flat",
                          font=FONT_L, padx=16, pady=8, bd=0, cursor="hand2",
                          command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=8, pady=2)
            self.nav_btns[key] = b

        self.content = tk.Frame(right, bg=BG)
        self.content.pack(fill="both", expand=True)

        logf = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        logf.pack(fill="x", padx=16, pady=12)
        bar = tk.Frame(logf, bg=CARD); bar.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(bar, text="运行日志", bg=CARD, fg=T1, font=FONT_H).pack(side="left")
        self.log_count = tk.Label(bar, text="0 条", bg=CARD, fg=T3, font=FONT)
        self.log_count.pack(side="left", padx=10)
        tk.Button(bar, text="清空", bg=CARD, fg=T2, relief="flat", font=FONT,
                  command=lambda: self.logbox.delete("1.0", "end")).pack(side="right")
        self.logbox = tk.Text(logf, height=7, bg="#FAFBFC", fg=T2, insertbackground=BLUE,
                              font=MONO, relief="flat", bd=8)
        self.logbox.pack(fill="x", padx=8, pady=8)

        self.show("run")

    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TEntry", fieldbackground="white", bordercolor=BORDER, lightcolor=BORDER)
        st.configure("TScale", background=CARD)

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def card(self, title, desc=""):
        f = tk.Frame(self.content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        f.pack(fill="x", pady=(0, 12))
        tk.Label(f, text=title, bg=CARD, fg=T1, font=FONT_H, anchor="w").pack(fill="x", padx=20, pady=(16, 2))
        if desc:
            tk.Label(f, text=desc, bg=CARD, fg=T3, font=FONT, anchor="w").pack(fill="x", padx=20)
        inner = tk.Frame(f, bg=CARD)
        inner.pack(fill="x", padx=20, pady=12)
        return inner

    def log(self, s):
        def _():
            self.logbox.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {s}\n")
            self.logbox.see("end")
            self.log_count.config(text=f"{int(self.log_count['text'].split()[0]) + 1} 条")
        try:
            self.after(0, _)
        except Exception:
            pass

    def _tick(self):
        self.lbl_clock.config(text=datetime.now().strftime("%H:%M:%S"))
        if self.timer_on:
            now = datetime.now()
            hh, mm = int(self.cfg["timer_hh"]), int(self.cfg["timer_mm"])
            days = [int(x) for x in str(self.cfg.get("timer_days", "1,2,3,4,5")).split(",") if x]
            if now.isoweekday() in days and now.hour == hh and now.minute == mm and now.second < 30:
                if not self._timer_fired:
                    self._timer_fired = True
                    self.log(f"定时触发 {hh:02d}:{mm:02d}")
                    threading.Thread(target=self._bg_run, daemon=True).start()
            elif now.minute != mm:
                self._timer_fired = False
        self.after(1000, self._tick)

    def _bg_run(self):
        self.lbl_state.config(text="跑步中…", bg=BLUE_BG, fg=BLUE)
        try:
            r = self.api.run_once()
            ok = isinstance(r, dict) and r.get("code") == 200
            self.log(f"完成 · {json.dumps(r, ensure_ascii=False)[:160]}")
            self.lbl_state.config(text="完成" if ok else "失败",
                                  bg="#E8FFEA" if ok else "#FFECE8", fg=GREEN if ok else RED)
        except Exception as e:
            self.log(f"异常 · {e}")
            self.lbl_state.config(text="异常", bg="#FFECE8", fg=RED)

    def show(self, key):
        self._clear()
        for k, b in self.nav_btns.items():
            b.config(bg=BLUE_BG if k == key else CARD, fg=BLUE if k == key else T2)
        getattr(self, "page_" + key)()

    # ── 页面 ──
    def page_run(self):
        c = self.card("跑步控制", "主校区高年级男生跑 · T2 · 2.6–10 km · 06:00–23:00")
        tk.Label(c, text="里程 2.6–10 km    配速 3–10    打卡 3–5",
                 bg=CARD, fg=T3, font=FONT).pack(anchor="w")
        for key, label, lo, hi, res, unit in [
            ("dist_km", "距离", 2.6, 5.0, 0.1, "km"),
            ("duration_s", "时长", 600, 1200, 10, "s"),
            ("n_points", "点数", 20, 80, 10, ""),
            ("marks", "打卡", 3, 5, 1, ""),
            ("pace", "配速", 3.5, 8.0, 0.05, ""),
            ("cadence", "步频", 140, 200, 1, ""),
        ]:
            row = tk.Frame(c, bg=CARD); row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=CARD, fg=T2, width=8, anchor="w", font=FONT).pack(side="left")
            tk.Scale(row, from_=lo, to=hi, resolution=res, orient="horizontal",
                     bg=CARD, fg=T2, highlightthickness=0, troughcolor=BG, font=FONT,
                     showvalue=True,
                     command=lambda v, k=key: self.cfg.__setitem__(k, float(v))
                     ).pack(side="left", fill="x", expand=True)
        btns = tk.Frame(c, bg=CARD); btns.pack(fill="x", pady=(12, 4))
        tk.Button(btns, text="开始跑步", bg=GREEN, fg="white", relief="flat",
                  font=FONT_L, padx=20, pady=8, cursor="hand2",
                  command=lambda: threading.Thread(target=self._bg_run, daemon=True).start()
                  ).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="保存参数", bg=CARD, fg=T2, relief="flat", font=FONT_L,
                  padx=16, pady=8, cursor="hand2",
                  command=lambda: save_cfg(self.cfg) or self.log("参数已保存")
                  ).pack(side="left", padx=4)

    def page_auth(self):
        c = self.card("账号信息", "支持 token 直连或学号密码登录")
        for key, label in [("username", "学号 / 账号"), ("password", "密码"), ("token", "token"),
                           ("school_id", "schoolId"), ("deviceid", "deviceid"), ("devicename", "deviceName")]:
            tk.Label(c, text=label, bg=CARD, fg=T2, font=FONT, anchor="w").pack(fill="x", pady=(6, 2))
            var = tk.StringVar(value=str(self.cfg.get(key, "")))
            tk.Entry(c, textvariable=var, bg="white", fg=T1, insertbackground=BLUE,
                     font=FONT_L, relief="flat", bd=6).pack(fill="x")
            setattr(self, "v_" + key, var)
        btns = tk.Frame(c, bg=CARD); btns.pack(fill="x", pady=(14, 4))
        tk.Button(btns, text="验证 token", bg=BLUE, fg="white", relief="flat", font=FONT_L,
                  padx=16, pady=8, cursor="hand2",
                  command=lambda: threading.Thread(target=self._verify, daemon=True).start()
                  ).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="账号登录", bg=CARD, fg=T2, relief="flat", font=FONT_L,
                  padx=16, pady=8, cursor="hand2",
                  command=lambda: threading.Thread(target=self._login, daemon=True).start()
                  ).pack(side="left", padx=4)
        tk.Button(btns, text="保存配置", bg=CARD, fg=T2, relief="flat", font=FONT_L,
                  padx=16, pady=8, cursor="hand2", command=self._save_ui).pack(side="left", padx=4)
        self.auth_msg = tk.Label(self.content, text="", bg=BG, fg=GREEN, font=FONT, anchor="w")
        self.auth_msg.pack(fill="x", pady=(8, 0))

    def _save_ui(self):
        for k in ("username", "password", "token", "school_id", "deviceid", "devicename"):
            self.cfg[k] = getattr(self, "v_" + k).get()
        save_cfg(self.cfg)
        self.log("配置已保存")

    def _verify(self):
        self._save_ui()
        r = self.api.student()
        ok = isinstance(r, dict) and r.get("code") == 200
        name = (r.get("data") or {}).get("nickName", "") if ok else ""
        self.after(0, lambda: self.auth_msg.config(
            text=f"token 有效 · {name}" if ok else f"token 无效 · {r}",
            fg=GREEN if ok else RED))

    def _login(self):
        self._save_ui()
        r = self.api.app_login()
        ok = isinstance(r, dict) and r.get("code") == 200
        self.after(0, lambda: self.auth_msg.config(
            text="登录成功，token 已更新" if ok else f"登录失败 · {r}",
            fg=GREEN if ok else RED))

    def page_timer(self):
        c = self.card("定时挂机", "到点自动执行一次合格跑，需保持程序运行")
        self.t_on = tk.BooleanVar(value=self.timer_on)
        tk.Checkbutton(c, text="启用定时", variable=self.t_on, bg=CARD, fg=T2,
                       selectcolor="white", activebackground=CARD, activeforeground=BLUE,
                       font=FONT_L, command=self._toggle_timer).pack(anchor="w")
        row = tk.Frame(c, bg=CARD); row.pack(fill="x", pady=8)
        tk.Label(row, text="时刻", bg=CARD, fg=T2, font=FONT).pack(side="left")
        self.t_hh = tk.Spinbox(row, from_=0, to=23, width=3, font=FONT_L, bg="white")
        self.t_hh.delete(0, "end"); self.t_hh.insert(0, int(self.cfg["timer_hh"]))
        self.t_hh.pack(side="left", padx=2)
        tk.Label(row, text=":", bg=CARD, fg=T2).pack(side="left")
        self.t_mm = tk.Spinbox(row, from_=0, to=59, width=3, font=FONT_L, bg="white")
        self.t_mm.delete(0, "end"); self.t_mm.insert(0, int(self.cfg["timer_mm"]))
        self.t_mm.pack(side="left", padx=2)
        tk.Label(row, text="  星期 1-7", bg=CARD, fg=T2, font=FONT).pack(side="left", padx=(12, 4))
        self.t_days = tk.Entry(row, width=12, font=FONT_L, bg="white")
        self.t_days.insert(0, str(self.cfg.get("timer_days", "1,2,3,4,5")))
        self.t_days.pack(side="left")
        tk.Button(c, text="保存定时", bg=BLUE, fg="white", relief="flat", font=FONT_L,
                  padx=16, pady=8, cursor="hand2", command=self._save_timer).pack(anchor="w", pady=8)

    def _toggle_timer(self):
        self.timer_on = self.t_on.get()
        self.cfg["timer_on"] = self.timer_on
        save_cfg(self.cfg)
        self.log(f"定时{'启用' if self.timer_on else '关闭'}")

    def _save_timer(self):
        self.cfg["timer_hh"] = int(self.t_hh.get())
        self.cfg["timer_mm"] = int(self.t_mm.get())
        self.cfg["timer_days"] = self.t_days.get().strip()
        self.cfg["timer_on"] = self.t_on.get()
        self.timer_on = self.cfg["timer_on"]
        save_cfg(self.cfg)
        self.log(f"定时 {self.cfg['timer_hh']:02d}:{self.cfg['timer_mm']:02d} · 周 {self.cfg['timer_days']}")

    def page_api(self):
        c = self.card("接口调试", "m-api 网关")
        tk.Label(c, text="接口路径", bg=CARD, fg=T2, font=FONT, anchor="w").pack(fill="x")
        self.api_path = tk.Entry(c, font=MONO, bg="white")
        self.api_path.insert(0, "/run/getHomeRunInfo"); self.api_path.pack(fill="x", pady=2)
        tk.Label(c, text="请求体 JSON（留空则无载荷）", bg=CARD, fg=T2, font=FONT, anchor="w").pack(fill="x", pady=(8, 0))
        self.api_body = tk.Text(c, height=4, font=MONO, bg="white", relief="flat", bd=6)
        self.api_body.insert("1.0", "{}"); self.api_body.pack(fill="x", pady=2)
        tk.Button(c, text="发送请求", bg=BLUE, fg="white", relief="flat", font=FONT_L,
                  padx=16, pady=8, cursor="hand2",
                  command=lambda: threading.Thread(target=self._api, daemon=True).start()
                  ).pack(anchor="w", pady=10)
        self.api_out = tk.Label(self.content, text="", bg=CARD, fg=T2, font=MONO,
                                anchor="w", wraplength=900, justify="left",
                                highlightthickness=1, highlightbackground=BORDER)
        self.api_out.pack(fill="x", pady=(0, 8))

    def _api(self):
        path = self.api_path.get().strip()
        raw = self.api_body.get("1.0", "end").strip()
        payload = json.loads(raw) if raw else ""
        r = self.api.call(path, payload, gz="splitPoint" in path)
        self.after(0, lambda: self.api_out.config(text=json.dumps(r, ensure_ascii=False)[:500]))

    def page_crypto(self):
        c = self.card("SM4 加解密", "国密 SM4 · ECB · PKCS7")
        tk.Label(c, text="密钥 / 明文或密文", bg=CARD, fg=T2, font=FONT, anchor="w").pack(fill="x")
        self.c_in = tk.Text(c, height=5, font=MONO, bg="white", relief="flat", bd=6)
        self.c_in.insert("1.0", '{"type":"1","schoolId":"100"}')
        self.c_in.pack(fill="x", pady=2)
        btns = tk.Frame(c, bg=CARD); btns.pack(fill="x", pady=8)
        tk.Button(btns, text="加密", bg=BLUE, fg="white", relief="flat", font=FONT_L,
                  padx=14, pady=6, cursor="hand2", command=self._enc_ui).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="解密", bg=CARD, fg=T2, relief="flat", font=FONT_L,
                  padx=14, pady=6, cursor="hand2", command=self._dec_ui).pack(side="left", padx=4)
        tk.Button(btns, text="测试向量", bg=CARD, fg=T2, relief="flat", font=FONT_L,
                  padx=14, pady=6, cursor="hand2", command=self._tv).pack(side="left", padx=4)
        self.c_out = tk.Label(self.content, text="就绪", bg=CARD, fg=T2, font=MONO,
                              anchor="w", wraplength=900, justify="left",
                              highlightthickness=1, highlightbackground=BORDER)
        self.c_out.pack(fill="x")

    def _enc_ui(self):
        pt = self.c_in.get("1.0", "end").encode("utf-8")
        self.c_out.config(text=base64.b64encode(sm4_enc(SM4_KEY, pt)).decode())

    def _dec_ui(self):
        try:
            ct = base64.b64decode(self.c_in.get("1.0", "end").strip())
            self.c_out.config(text=sm4_dec(SM4_KEY, ct).decode("utf-8", "replace"))
        except Exception as e:
            self.c_out.config(text=str(e), fg=RED)

    def _tv(self):
        k = bytes.fromhex("0123456789abcdeffedcba9876543210")
        got = sm4_blk(sm4_ks(k), k).hex()
        ok = got == "681edf34d206965e86b3e94f536e4246"
        self.c_out.config(text=f"期望 681edf34d206965e86b3e94f536e4246\n实际 {got}\n{'通过' if ok else '失败'}")

    def page_hist(self):
        c = self.card("跑步历史", "最近记录")
        for row in [("2026-09-24 22:59", "3.00 km", "4.67", "合格"),
                    ("2026-09-24 22:40", "2.20 km", "2.27", "不合格")]:
            f = tk.Frame(c, bg=CARD); f.pack(fill="x", pady=4)
            for text, w, col in [(row[0], 20, T2), (row[1], 12, T1), (row[2], 10, T2),
                                 (row[3], 10, GREEN if row[3] == "合格" else RED)]:
                tk.Label(f, text=text, bg=CARD, fg=col, font=FONT_L, width=w, anchor="w").pack(side="left")
        tk.Button(c, text="刷新历史", bg=CARD, fg=T2, relief="flat", font=FONT_L,
                  padx=14, pady=6, cursor="hand2",
                  command=lambda: self.api.call("/run/crsReocordInfoList", {"tableName": "crs_run_record100"})
                  ).pack(anchor="w", pady=8)


def main():
    App().mainloop()

if __name__ == "__main__":
    main()
