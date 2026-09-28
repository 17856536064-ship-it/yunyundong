#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云运动 · 全功能工作站（完整版）
覆盖：登录/切校/设备随机、任务卡、真实轨迹、打表/快速、实时配速步频、
     历史成绩排行、晨跑日跑、公告问卷、定时批量、GUI+CLI
"""
from __future__ import annotations

import argparse, base64, gzip, hashlib, json, math, os, random, sys, threading, time, uuid as uuidlib
import urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

HERE = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CFG = HERE / "yunyundong_config.json"

# ═══════════ SM4 ═══════════
SBOX=[0xD6,0x90,0xE9,0xFE,0xCC,0xE1,0x3D,0xB7,0x16,0xB6,0x14,0xC2,0x28,0xFB,0x2C,0x05,
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
FK=[0xA3B1BAC6,0x56AA3350,0x677D9197,0xB27022DC]
CK=[0x00070e15,0x1c232a31,0x383f464d,0x545b6269,0x70777e85,0x8c939aa1,0xa8afb6bd,0xc4cbd2d9,
0xe0e7eef5,0xfc030a11,0x181f262d,0x343b4249,0x50575e65,0x6c737a81,0x888f969d,0xa4abb2b9,
0xc0c7ced5,0xdce3eaf1,0xf8ff060d,0x141b2229,0x30373e45,0x4c535a61,0x686f767d,0x848b9299,
0xa0a7aeb5,0xbcc3cad1,0xd8dfe6ed,0xf4fb0209,0x10171e25,0x2c333a41,0x484f565d,0x646b7279]
def _rotl(x,n): return ((x<<n)|(x>>(32-n)))&0xFFFFFFFF
def _tau(a): return (SBOX[(a>>24)&255]<<24)|(SBOX[(a>>16)&255]<<16)|(SBOX[(a>>8)&255]<<8)|SBOX[a&255]
def _lenc(b): return b^_rotl(b,2)^_rotl(b,10)^_rotl(b,18)^_rotl(b,24)
def _lkey(b): return b^_rotl(b,13)^_rotl(b,23)
def sm4_ks(key):
    mk=[int.from_bytes(key[i:i+4],"big") for i in range(0,16,4)]
    k=[mk[i]^FK[i] for i in range(4)]; rk=[]
    for i in range(32):
        t=k[i]^_lkey(_tau(k[i+1]^k[i+2]^k[i+3]^CK[i])); k.append(t); rk.append(t)
    return rk
def sm4_blk(rk,b,dec=False):
    x=[int.from_bytes(b[i:i+4],"big") for i in range(0,16,4)]
    o=rk[::-1] if dec else rk
    for i in range(32): x.append(x[i]^_lenc(_tau(x[i+1]^x[i+2]^x[i+3]^o[i])))
    return b"".join(x[35-j].to_bytes(4,"big") for j in range(4))
def _pad(d):
    n=16-len(d)%16; return d+bytes([n])*n
def _unpad(d):
    n=d[-1] if d else 0
    return d[:-n] if 1<=n<=16 and d[-n:]==bytes([n])*n else d
def sm4_enc(key,data):
    rk=sm4_ks(key); data=_pad(data)
    return b"".join(sm4_blk(rk,data[i:i+16]) for i in range(0,len(data),16))
def sm4_dec(key,data):
    rk=sm4_ks(key)
    return _unpad(b"".join(sm4_blk(rk,data[i:i+16],True) for i in range(0,len(data),16)))

# ═══════════ 常量 ═══════════
SM4_KEY=base64.b64decode("JXhWGZjmhhXN+nt8nLpNxA==")
CIPHER_KEY="BGfbsG9EkXz5KeCva8E0MisBeS6bhBEDId3VXeIuBoiBMZU0Mosv7PqKsvqxZ3PjkUlsjzh09Se629SWW45XP4TIUeXoLpYzgk5fAMbg0VNVnXuLH9xVzdHAeM+1qJrgvwwkwio85/DnrP1aArvVQrw3N4xd5tugqQ=="
APPSECRET="0h1UIfMDSc7piesRINRXXfkE"
M_API="http://192.0.2.10:8000/m-api"
S_API="https://sports.aiyyd.com:9011/api/app"
APP_VER="3.6.6"
UA=f"LePao/{APP_VER} (iPhone; iOS 26.6; Scale/3.00)"

DEVICES=[
    ("00000000-0000-0000-0000-000000000000","iPhone 16 Pro"),
    ("A3B1C2D4-E5F6-4A7B-8C9D-0E1F2A3B4C5D","iPhone 15"),
    ("B4C5D6E7-F8A9-4B0C-1D2E-3F4A5B6C7D8E","iPhone 14 Pro Max"),
    ("C5D6E7F8-A9B0-4C1D-2E3F-4A5B6C7D8E9F","iPhone 13"),
    ("D6E7F8A9-B0C1-4D2E-3F4A-5B6C7D8E9F0A","iPhone 12"),
    ("E7F8A9B0-C1D2-4E3F-4A5B-6C7D8E9F0A1B","iPhone 11"),
    ("F8A9B0C1-D2E3-4F4A-5B6C-7D8E9F0A1B2C","HUAWEI Mate 60"),
    ("A9B0C1D2-E3F4-4A5B-6C7D-8E9F0A1B2C3D","HUAWEI P60"),
    ("B0C1D2E3-F4A5-4B6C-7D8E-9F0A1B2C3D4E","Xiaomi 14"),
    ("C1D2E3F4-A5B6-4C7D-8E9F-0A1B2C3D4E5F","OPPO Find X7"),
    ("D2E3F4A5-B6C7-4D8E-9F0A-1B2C3D4E5F6A","vivo X100"),
    ("E3F4A5B6-C7D8-4E9F-0A1B-2C3D4E5F6A7B","Samsung S24"),
]

DEFAULT_CFG={
    "token":"00000000-0000-0000-0000-000000000000","username":"20230000001","password":"",
    "school_id":"100","school_name":"XX学院","school_url":M_API,
    "deviceid":DEVICES[0][0],"devicename":DEVICES[0][1],"platform":"ios",
    "dist_km":3.0,"duration_s":840,"n_points":50,"marks":5,"pace":4.67,"cadence":170,"strides":0.8,
    "drift":True,"multi_route":True,"run_mode":"track","quick_extra_km":0.0,
    "timer_on":False,"timer_hh":7,"timer_mm":30,"timer_days":"1,2,3,4,5",
    "batch_configs":[],
    "accounts":[],  # 多账户 [{username,password,school_id,token,school_url,school_name}]"auto_random_device":True,"auto_random_school":False,
}
def load_cfg():
    try: return {**DEFAULT_CFG,**json.loads(CFG.read_text("utf-8"))}
    except Exception: return dict(DEFAULT_CFG)
def save_cfg(cfg):
    CFG.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),"utf-8")

def rand_device():
    return random.choice(DEVICES)
def rand_uuid():
    return str(uuidlib.uuid4()).upper()

# ═══════════ 轨迹 ═══════════
CHECKPOINTS=[(117.596597,31.608729),(117.596941,31.608327),(117.597305,31.607937),
             (117.596005,31.608317),(117.596259,31.608032),(117.596523,31.607543)]
MARK_Y=[0,1,2,3,5]
# 多套路线（绕圈/往返/8字）
ROUTES={
    "loop":[(117.5966,31.6083),(117.5970,31.6085),(117.5973,31.6080),(117.5970,31.6076),
            (117.5965,31.6075),(117.5961,31.6079),(117.5960,31.6083),(117.5963,31.6086)],
    "outback":[(117.5961,31.6083),(117.5973,31.6080),(117.5961,31.6083)],
    "eight":[(117.5966,31.6083),(117.5971,31.6086),(117.5966,31.6083),(117.5961,31.6080),(117.5966,31.6083)],
}

def haversine(a,b):
    lon1,lat1,lon2,lat2=map(math.radians,[a[0],a[1],b[0],b[1]])
    dlon,dlat=lon2-lon1,lat2-lat1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*6371000*math.asin(math.sqrt(h))

def build_track_via_cps(dist_km,duration_s,n,cps,marks=5,drift=True):
    """轨迹必过打卡点（合格关键），再闭环补里程."""
    ys=MARK_Y[:max(3,marks)]
    ordered=[cps[i] for i in ys if i<len(cps)]
    if not ordered: ordered=list(cps)
    # 串点 + 绕圈
    ctrl=list(ordered)+list(ordered)
    dense=[]
    for i in range(len(ctrl)-1):
        a,b=ctrl[i],ctrl[i+1]; sgm=haversine(a,b) or 0.001
        steps=max(3,int(sgm/12))
        for t in range(steps):
            f=t/steps
            dense.append((a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f))
    dense.append(ctrl[-1])
    # 按目标里程放大绕圈
    total=sum(haversine(dense[i],dense[i+1]) for i in range(len(dense)-1)) or 1
    need=dist_km*1000
    reps=max(1,int(need/total)+1)
    path=[]
    for _ in range(reps):
        path.extend(dense)
    path.append(path[-1])
    # 等距重采样 n 点
    out=[]; acc=0.0; target=need
    for i in range(n):
        f=i/(n-1)
        idx=min(len(path)-1,int(f*(len(path)-1)))
        lon,lat=path[idx]
        if drift:
            lon,lat=add_drift((lon,lat),5.0)
        out.append({
            "point":f"{lon:.8f},{lat:.8f}","runStatus":"1",
            "speed":f"{random.uniform(4.5,5.2):.2f}","isFence":"Y","isMock":False,
            "runMileage":f"{target*(i+1)/n:.4f}",
            "runTime":f"{int(duration_s*(i+1)/n)}",
            "ts":str(int(time.time())-duration_s+int(duration_s*(i+1)/n)),
        })
    return out

def add_drift(p,amp=8.0):
    """经纬度加米级漂移."""
    lat_m=111320.0; lon_m=111320.0*math.cos(math.radians(p[1]))
    return (p[0]+random.uniform(-amp,amp)/lon_m, p[1]+random.uniform(-amp,amp)/lat_m)

def build_track(dist_km,duration_s,n,origin,route_key="loop",drift=True):
    ctrl=ROUTES.get(route_key,ROUTES["loop"])
    # 重复环绕到目标里程
    pts=[]; total=0.0; i=0
    while total<dist_km*1000*1.02 and len(pts)<n*3:
        a=ctrl[i%len(ctrl)]; b=ctrl[(i+1)%len(ctrl)]
        seg=haversine(a,b); total+=seg; pts.append(a); i+=1
        if i>500: break
    # 等距重采样到 n 点
    if len(pts)<2: pts=[origin,add_drift(origin,20)]
    out=[]; acc=0.0; target_total=dist_km*1000
    segs=[]
    dense=[]
    for i in range(len(pts)-1):
        a,b=pts[i],pts[i+1]; s=haversine(a,b) or 0.001
        steps=max(2,int(s/15))
        for t in range(steps):
            f=t/steps
            dense.append((a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f))
    dense.append(pts[-1])
    step=max(1,len(dense)//n)
    picked=dense[::step][:n]
    if len(picked)<n:
        picked += [picked[-1]]*(n-len(picked))
    ts0=int(time.time())-duration_s
    res=[]
    for i,(lon,lat) in enumerate(picked[:n]):
        if drift:
            lon,lat=add_drift((lon,lat),amp=5.0)
        mile=target_total*(i+1)/n
        sec=int(duration_s*(i+1)/n)
        res.append({
            "point":f"{lon:.8f},{lat:.8f}","runStatus":"1",
            "speed":f"{random.uniform(4.4,5.4):.2f}","isFence":"Y","isMock":False,
            "runMileage":f"{mile:.4f}","runTime":f"{sec}","ts":str(ts0+sec),
        })
    return res

# ═══════════ API ═══════════
class API:
    def __init__(self,cfg,log=print):
        self.cfg=cfg; self.log=log
        if cfg.get("auto_random_device"):
            d=rand_device(); self.cfg["deviceid"],self.cfg["devicename"]=d
    def getsign(self,utc,u):
        return hashlib.md5(f"platform={self.cfg['platform']}&utc={utc}&uuid={u}&appsecret={APPSECRET}".encode()).hexdigest()
    def _enc(self,payload,gz=False):
        if payload is None or payload=="": return ""
        if isinstance(payload,dict): payload=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
        raw=payload if isinstance(payload,bytes) else payload.encode()
        if not raw: return ""
        if gz: raw=gzip.compress(raw)
        return base64.b64encode(sm4_enc(SM4_KEY,raw)).decode()
    def _dec(self,raw):
        if raw[:2]==b"\x1f\x8b": raw=gzip.decompress(raw)
        t=raw.decode("utf-8","replace")
        if t.startswith("{") or t.startswith("["):
            try: return json.loads(t)
            except Exception: return t
        try: b64=json.loads(t) if t[:1]=='"' else t.strip().strip('"')
        except Exception: b64=t.strip().strip('"')
        pt=sm4_dec(SM4_KEY,base64.b64decode(b64))
        for c in (pt,None):
            if c is None:
                try: c=gzip.decompress(pt)
                except Exception: break
            try: return json.loads(c.decode())
            except Exception: pass
        try: return pt.decode()[:300]
        except Exception: return str(pt[:120])
    def call(self,path,payload="",base=None,gz=False,timeout=30):
        body={"cipherKey":CIPHER_KEY,"content":self._enc(payload,gz=gz)}
        u=rand_uuid(); utc=str(int(time.time()))
        url=(base or self.cfg.get("school_url") or M_API)+(path if path.startswith("/") else "/"+path)
        headers={"deviceid":self.cfg["deviceid"],"user-agent":UA,"sysversion":"26.6",
            "content-type":"application/json","version":APP_VER,"isapp":"app",
            "token":self.cfg["token"],"accept-encoding":"gzip, deflate","accept":"*/*",
            "devicename":self.cfg["devicename"],"platform":self.cfg["platform"],
            "uuid":u,"sign":self.getsign(utc,u),"utc":utc}
        req=urllib.request.Request(url,data=json.dumps(body,separators=(",",":")).encode(),
                                   headers=headers,method="POST")
        self.log(f"→ {path}")
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                res=self._dec(r.read())
        except urllib.error.HTTPError as e:
            res=self._dec(e.read()) if e.fp else {"code":e.code,"msg":str(e)}
        except Exception as e:
            res={"code":-1,"msg":str(e)}
        self.log(f"← {json.dumps(res,ensure_ascii=False)[:140] if not isinstance(res,str) else res[:140]}")
        return res
    def sports(self,path,payload=""):
        return self.call(path,payload,base=S_API)
    # —— 学校 ——
    def list_schools(self):
        r=self.sports("/lisshtcool",{})
        data=r.get("data") if isinstance(r,dict) else None
        return data or []
    def pick_school(self,school_code=None):
        sc=self.list_schools()
        if not sc: return None
        row=next((x for x in sc if str(x.get("schoolCode"))==str(school_code)),None) if school_code else None
        if not row: row=random.choice(sc)
        self.cfg["school_id"]=str(row.get("schoolCode") or "100")
        self.cfg["school_name"]=row.get("schoolName") or self.cfg["school_id"]
        url=row.get("schoolUrl") or M_API
        if not url.startswith("http"): url="http://"+url
        self.cfg["school_url"]=url.rstrip("/")+"/m-api" if "/m-api" not in url else url
        save_cfg(self.cfg)
        self.log(f"[SCHOOL] {self.cfg['school_name']} id={self.cfg['school_id']} base={self.cfg['school_url']}")
        return row
    def randomize_device(self):
        d=rand_device()
        self.cfg["deviceid"],self.cfg["devicename"]=d
        save_cfg(self.cfg)
        self.log(f"[DEV] {d[1]} {d[0][:8]}…")
        return d
    # —— 登录 ——
    def app_login(self,u=None,p=None):
        # E21: 服务端字段 userName/password/schoolId/type=1
        r=self.call("/login/appLogin",{"userName":u or self.cfg["username"],
            "password":p or self.cfg["password"],
            "schoolId":str(self.cfg["school_id"]),"type":"1"})
        if isinstance(r,dict) and r.get("code")==200 and isinstance(r.get("data"),dict):
            tok=r["data"].get("token")
            if tok: self.cfg["token"]=tok; save_cfg(self.cfg)
        return r
    def student(self): return self.call("/login/getStudentInfo")
    def sign_out(self): return self.call("/login/signOut")
    def update_user(self,**f): return self.call("/login/updateUser",f)
    # —— 任务 ——
    def home(self): return self.call("/run/getHomeRunInfo")
    def task_card(self):
        h=self.home()
        if not (isinstance(h,dict) and h.get("data",{}).get("cralist")):
            return None
        d=h["data"]; t=d["cralist"][0]
        return {
            "today_km":d.get("distance","0"),"qualified":d.get("qualifiedCount",0),
            "target":d.get("raTargetNum",50),"is_morning":d.get("isMorning","N"),
            "raId":t.get("id"),"raType":t.get("raType"),"raName":t.get("raName"),
            "min":t.get("raSingleMileageMin"),"max":t.get("raSingleMileageMax"),
            "pace_min":t.get("raPaceMin"),"pace_max":t.get("raPaceMax"),
            "cad_min":t.get("raCadenceMin"),"cad_max":t.get("raCadenceMax"),
            "dislikes":t.get("raDislikes"),"min_dislikes":t.get("raMinDislikes"),
            "day_start":t.get("dayStartTime"),"day_end":t.get("dayEndTime"),
            "morning_s":t.get("morningStartTime"),"morning_e":t.get("morningEndTime"),
            "morning_num":t.get("morningNum"),"day_km":t.get("dayKm"),
            "points":(t.get("points") or "").split("|") if t.get("points") else [],
            "schoolId":t.get("schoolId"),"campusId":t.get("campusId"),
            "raRunArea":t.get("raRunArea"),"raTargetNum":t.get("raTargetNum"),
            "week":t.get("raWeekTime"),"raId_raw":t,"raw":h,
        }
    # —— 跑步 ——
    def run_start(self,info):
        return self.call("/run/start",{"raRunArea":info.get("raRunArea",""),
            "raType":info.get("raType",""),"raId":info.get("raId")})
    def split(self,points,meta):
        body={"StepNumber":int((float(points[-1]["runMileage"])-float(points[0]["runMileage"]))/(meta.get("strides",0.8) or 0.8)),
            "a":0,"b":None,"c":None,
            "mileage":float(points[-1]["runMileage"])-float(points[0]["runMileage"]),
            "orientationNum":0,"runSteps":random.uniform(meta.get("cad",170),meta.get("cad",170)+8),
            "cardPointList":points,"simulateNum":0,
            "time":float(points[-1]["runTime"])-float(points[0]["runTime"]),
            "crsRunRecordId":meta["crsRunRecordId"],"speeds":meta.get("speeds","5.50"),
            "schoolId":meta.get("schoolId",100),"strides":meta.get("strides",0.8),
            "userName":meta.get("userName",self.cfg["username"])}
        return self.call("/run/splitPointCheating",body,gz=True)
    def finish(self,payload): return self.call("/run/finish",payload)
    def is_standard(self,payload): return self.call("/run/isStandard",payload)
    def pause(self,st="pause"): return self.call("/run/pauseOrGoon",{"status":st})
    # —— 历史成绩 ——
    def history_list(self,tbl=None):
        return self.call("/run/crsReocordInfoList",{"tableName":tbl or f"crs_run_record{self.cfg['school_id']}"})
    def history_info(self,rid,tbl=None):
        return self.call("/run/crsReocordInfo",{"id":rid,"tableName":tbl or f"crs_run_record{self.cfg['school_id']}"})
    def my_run_info(self): return self.call("/run/myInfoCrsRunInfo")
    def score_list(self): return self.call("/score/list",{})
    def xn_list(self): return self.call("/run/listXnYearXqByStudentId")
    def rank(self): return self.call("/run/getRank")
    # —— 公告问卷 ——
    def home_list(self): return self.call("/homePageApi/list")
    def news(self): return self.call("/appNewsApi/list",{})
    def popup(self): return self.call("/homePageApi/msg/isPopupList")
    def questions(self): return self.call("/questionNaire/getQuestionList")
    # —— 完整跑步 ——
    def run_full(self,dist_km=3.0,duration_s=840,n=50,marks=5,route="loop",
                 drift=True,on_point=None,quick=False):
        card=self.task_card()
        if not card: return {"code":-2,"msg":"no task"}
        info={"raRunArea":card["raRunArea"],"raType":card["raType"],"raId":card["raId"],
              "schoolId":card["schoolId"]}
        st=self.run_start(info)
        if not (isinstance(st,dict) and st.get("code")==200):
            return {"code":-3,"msg":"start fail","raw":st}
        rec_id=st["data"]["id"]; rec_start=st["data"].get("recordStartTime","")
        student=st["data"].get("studentId",self.cfg["username"])
        pace=round(duration_s/60/dist_km,2)
        cps0=[]
        for s0 in (card["points"] or []):
            if s0:
                a=s0.split(","); cps0.append((float(a[0]),float(a[1])))
        if not cps0: cps0=CHECKPOINTS
        pts=build_track_via_cps(dist_km,duration_s,max(n,50),cps0,marks,drift)
        meta={"crsRunRecordId":rec_id,"schoolId":info["schoolId"],"userName":student,
              "strides":float(self.cfg["strides"]),"speeds":f"{pace:.2f}",
              "cad":int(self.cfg["cadence"])}
        splits=[]
        if not quick:
            for i in range(0,len(pts),10):
                chunk=pts[i:i+10]
                if len(chunk)<2: continue
                splits.append(self.split(chunk,meta))
                if on_point:
                    on_point(i+10,len(pts),chunk)
                time.sleep(0.8)
        cps=cps0
        ys=MARK_Y[:max(3,marks)]
        mg=[{"point":f"{c[0]},{c[1]}","marked":"Y" if i in ys else "N",
             "index":str(i) if i in ys else ""}
            for i,c in enumerate(cps)]
        fin=self.finish({
            "recordMileage":f"{dist_km:.2f}","recodeCadence":str(int(self.cfg["cadence"])),
            "recodePace":f"{pace:.2f}","deviceName":self.cfg["devicename"],
            "sysEdition":"26.6","appEdition":APP_VER,"raIsStartPoint":"Y","raIsEndPoint":"Y",
            "raRunArea":info["raRunArea"],"recodeDislikes":str(marks),
            "raId":str(info["raId"]),"raType":info["raType"],"id":str(rec_id),
            "duration":str(duration_s),"recordStartTime":rec_start,"manageList":mg,"remake":"1"})
        return {"code":200,"recordId":rec_id,"finish":fin,"points":pts,"splits":splits,
                "pace":pace,"card":card}

# ═══════════ CLI ═══════════
def cli_run(api,args):
    r=api.run_full(dist_km=args.dist,duration_s=args.dur,n=args.pts,marks=args.marks,
                   route=args.route,drift=not args.no_drift,quick=args.quick)
    print(json.dumps({k:v for k,v in r.items() if k not in ("points","splits","card")},
                     ensure_ascii=False,indent=2)[:800])

def cli_main():
    ap=argparse.ArgumentParser(description="云运动全功能")
    ap.add_argument("cmd",choices=["run","quick","login","schools","school","device",
                                   "home","hist","score","news","questions","timer","gui","batch"])
    ap.add_argument("--dist",type=float,default=3.0)
    ap.add_argument("--dur",type=int,default=840)
    ap.add_argument("--pts",type=int,default=50)
    ap.add_argument("--marks",type=int,default=5)
    ap.add_argument("--route",default="loop",choices=list(ROUTES))
    ap.add_argument("--no-drift",action="store_true")
    ap.add_argument("--quick",action="store_true")
    ap.add_argument("--school",default="")
    ap.add_argument("--user",default=""); ap.add_argument("--pass","-p",dest="pwd",default="")
    ap.add_argument("--at",default=""); ap.add_argument("--days",default="")
    ap.add_argument("--config",default="")
    a=ap.parse_args()
    cfg=load_cfg()
    if a.config:
        cfg={**cfg,**json.loads(Path(a.config).read_text("utf-8"))}
    api=API(cfg,lambda s:print(s,flush=True))
    if a.cmd=="gui":
        run_gui(cfg,api); return
    if a.cmd=="login":
        if a.user: cfg["username"]=a.user
        if a.pwd: cfg["password"]=a.pwd
        print(json.dumps(api.app_login(),ensure_ascii=False)[:400])
    elif a.cmd=="schools":
        for s in api.list_schools():
            print(s.get("schoolCode"),s.get("schoolName"),s.get("schoolUrl"))
    elif a.cmd=="school":
        api.pick_school(a.school or None)
    elif a.cmd=="device":
        api.randomize_device()
    elif a.cmd=="home":
        print(json.dumps(api.task_card() or {},ensure_ascii=False,indent=2)[:1200])
    elif a.cmd in ("run","quick"):
        cli_run(api,a if a.cmd=="run" else argparse.Namespace(dist=a.dist,dur=a.dur,
                pts=a.pts,marks=a.marks,route=a.route,no_drift=a.no_drift,quick=True))
    elif a.cmd=="hist":
        print(json.dumps(api.history_list(),ensure_ascii=False)[:800])
    elif a.cmd=="score":
        print(json.dumps(api.score_list(),ensure_ascii=False)[:500])
    elif a.cmd=="news":
        print(json.dumps(api.news(),ensure_ascii=False)[:500])
    elif a.cmd=="questions":
        print(json.dumps(api.questions(),ensure_ascii=False)[:500])
    elif a.cmd=="timer":
        if a.at:
            h,m=a.at.split(":"); cfg["timer_hh"],cfg["timer_mm"]=int(h),int(m)
        if a.days: cfg["timer_days"]=a.days
        cfg["timer_on"]=True; save_cfg(cfg)
        hh,mm=cfg["timer_hh"],cfg["timer_mm"]
        days=[int(x) for x in str(cfg["timer_days"]).split(",") if x]
        print(f"[TIMER] {hh:02d}:{mm:02d} days={days}")
        fired=None
        while True:
            now=datetime.now()
            if now.isoweekday() in days and now.hour==hh and now.minute==mm and fired!=now.strftime("%Y%m%d"):
                fired=now.strftime("%Y%m%d")
                cli_run(api,argparse.Namespace(dist=cfg["dist_km"],dur=cfg["duration_s"],
                        pts=cfg["n_points"],marks=cfg["marks"],route="loop",no_drift=False,quick=False))
            time.sleep(20)
    elif a.cmd=="batch":
        for i,c in enumerate(cfg.get("batch_configs") or []):
            c2={**cfg,**c}
            api2=API(c2,lambda s,i=i:print(f"[B{i}] {s}",flush=True))
            cli_run(api2,argparse.Namespace(dist=c2["dist_km"],dur=c2["duration_s"],
                    pts=c2["n_points"],marks=c2["marks"],route="loop",no_drift=False,
                    quick=c2.get("run_mode")=="quick"))

# ═══════════ GUI · Web 工作台（IDE Dark · 程序员风） ═══════════
WEB_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>云运动 · DEV CONSOLE</title>
<style>
:root{
  --bg:#0d1117; --panel:#161b22; --panel2:#1c2330; --border:#2d333b; --border2:#444c56;
  --fg:#c9d1d9; --fg-dim:#8b949e; --fg-faint:#6e7681;
  --blue:#58a6ff; --green:#3fb950; --red:#f85149; --purple:#bc8cff; --orange:#d29922;
  --mono:ui-monospace,"Cascadia Code","JetBrains Mono",Consolas,"Courier New",monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;overflow:hidden}
::-webkit-scrollbar{width:9px;height:9px}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:5px}
::-webkit-scrollbar-track{background:transparent}

#app{display:grid;grid-template-columns:208px 1fr;grid-template-rows:52px 1fr 190px;height:100vh}
/* ── header ── */
header{grid-column:1/3;display:flex;align-items:center;gap:14px;padding:0 18px;background:var(--panel);border-bottom:1px solid var(--border)}
.logo{font-family:var(--mono);font-weight:700;font-size:15px;color:#fff;display:flex;align-items:center;gap:8px}
.logo svg{width:20px;height:20px}
.logo .ver{font-size:11px;color:var(--fg-faint);font-weight:400}
.hsep{color:var(--border2)}
.school{font-size:12px;color:var(--fg-dim)}
.pill{margin-left:auto;font-family:var(--mono);font-size:12px;padding:3px 12px;border-radius:20px;border:1px solid var(--border2);color:var(--fg-dim);display:flex;align-items:center;gap:7px}
.pill .dot{width:8px;height:8px;border-radius:50%;background:var(--green)}
.pill.run .dot{background:var(--orange);animation:blink 1s infinite}
.pill.err .dot{background:var(--red)}
@keyframes blink{50%{opacity:.25}}
.clock{font-family:var(--mono);font-size:12px;color:var(--fg-faint)}

/* ── sidebar ── */
aside{background:var(--panel);border-right:1px solid var(--border);padding:12px 8px;display:flex;flex-direction:column;gap:2px}
aside .cap{font-size:11px;color:var(--fg-faint);letter-spacing:2px;padding:4px 12px 8px;font-family:var(--mono)}
.nav{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:7px;color:var(--fg-dim);cursor:pointer;font-size:13px;border:1px solid transparent;user-select:none}
.nav:hover{background:var(--panel2);color:var(--fg)}
.nav.on{background:linear-gradient(90deg,rgba(88,166,255,.14),rgba(88,166,255,.03));color:#fff;border-color:rgba(88,166,255,.25)}
.nav .ic{width:17px;height:17px;flex:none}
.nav .kbd{margin-left:auto;font-size:10px;color:var(--fg-faint);font-family:var(--mono)}
aside .foot{margin-top:auto;font-family:var(--mono);font-size:10px;color:var(--fg-faint);padding:8px 12px;line-height:1.8}

/* ── main ── */
main{overflow-y:auto;padding:18px 22px}
.page{display:none;max-width:980px}
.page.on{display:block;animation:fade .18s}
.tabpane{animation:fade .15s}
@keyframes fade{from{opacity:0;transform:translateY(4px)}}
.ph{margin-bottom:16px}
.ph h1{font-size:19px;font-weight:650;color:#fff;display:flex;align-items:center;gap:10px}
.ph h1 .tag{font-size:11px;font-weight:400;color:var(--blue);background:rgba(88,166,255,.12);border:1px solid rgba(88,166,255,.3);padding:2px 9px;border-radius:12px;font-family:var(--mono)}
.ph p{font-size:12.5px;color:var(--fg-dim);margin-top:4px}

.grid{display:grid;gap:14px}
.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(4,1fr)}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px 18px}
.card .ct{font-size:12px;color:var(--fg-dim);margin-bottom:10px;display:flex;align-items:center;gap:8px;font-family:var(--mono)}
.card .ct::before{content:"";width:3px;height:12px;background:var(--blue);border-radius:2px}

.btn{display:inline-flex;align-items:center;gap:7px;background:#21262d;border:1px solid var(--border2);color:var(--fg);padding:7px 16px;border-radius:7px;font-size:13px;cursor:pointer;font-family:inherit;transition:.15s;user-select:none}
.btn:hover{background:#2d333b;border-color:#59616c}
.btn:active{transform:scale(.97)}
.btn.pri{background:#1f6feb;border-color:#1f6feb;color:#fff}
.btn.pri:hover{background:#388bfd;border-color:#388bfd}
.btn.ok{background:#238636;border-color:#238636;color:#fff}
.btn.ok:hover{background:#2ea043}
.btn.warn{background:#9e6a03;border-color:#9e6a03;color:#fff}
.btn.sm{padding:4px 11px;font-size:12px}
.btn:disabled{opacity:.45;cursor:not-allowed;transform:none}

/* sliders */
.slider-row{margin-bottom:6px}
.slider-row .sl-head{display:flex;justify-content:space-between;font-size:12.5px;color:var(--fg-dim);margin-bottom:2px}
.slider-row output{font-family:var(--mono);color:var(--blue);font-weight:600}
input[type=range]{width:100%;height:22px;accent-color:#1f6feb;cursor:pointer;background:transparent}

/* inputs */
.inp{width:100%;background:#0d1117;border:1px solid var(--border2);color:var(--fg);padding:8px 12px;border-radius:7px;font:13px var(--mono);outline:none;transition:.15s}
.inp:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(31,111,235,.2)}
label.lab{display:block;font-size:12px;color:var(--fg-dim);margin:12px 0 5px;font-family:var(--mono)}

/* switch */
.sw{position:relative;width:38px;height:21px;flex:none;cursor:pointer}
.sw input{opacity:0;width:0;height:0}
.sw i{position:absolute;inset:0;background:#30363d;border-radius:20px;transition:.2s}
.sw i::after{content:"";position:absolute;width:15px;height:15px;border-radius:50%;background:#8b949e;top:3px;left:3px;transition:.2s}
.sw input:checked+i{background:#1f6feb}
.sw input:checked+i::after{transform:translateX(17px);background:#fff}
.swrow{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--fg-dim);padding:7px 0;cursor:pointer;user-select:none}

/* segmented */
.seg{display:flex;gap:6px;flex-wrap:wrap}
.seg .opt{padding:5px 15px;border-radius:16px;border:1px solid var(--border2);font-size:12.5px;color:var(--fg-dim);cursor:pointer;font-family:var(--mono);transition:.15s}
.seg .opt:hover{color:var(--fg)}
.seg .opt.on{background:rgba(31,111,235,.18);border-color:var(--blue);color:var(--blue)}

/* stat */
.stat{text-align:center;padding:10px 6px}
.stat .v{font:700 26px var(--mono);color:#fff}
.stat .v em{font-size:13px;color:var(--fg-dim);font-style:normal;font-weight:400}
.stat .k{font-size:12px;color:var(--fg-dim);margin-top:2px}
.stat .v.g{color:var(--green)}.stat .v.b{color:var(--blue)}.stat .v.p{color:var(--purple)}

pre.term{background:#010409;border:1px solid var(--border);border-radius:9px;padding:13px 15px;font:12px/1.75 var(--mono);color:#7ee787;overflow:auto;max-height:340px;white-space:pre-wrap;word-break:break-all}
pre.term .dim{color:var(--fg-faint)}

table.tb{width:100%;border-collapse:collapse;font-size:12.5px}
table.tb th{color:var(--fg-faint);text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);font-family:var(--mono);font-weight:400;font-size:11px}
table.tb td{padding:7px 10px;border-bottom:1px solid #21262d;color:var(--fg)}
table.tb tr:hover td{background:rgba(177,186,196,.04)}

/* big run btn */
.runbtn{width:100%;padding:15px;border-radius:11px;border:none;font-size:16px;font-weight:650;color:#fff;cursor:pointer;background:linear-gradient(135deg,#238636,#1f6feb);letter-spacing:3px;transition:.2s;font-family:inherit}
.runbtn:hover{filter:brightness(1.15);box-shadow:0 4px 22px rgba(35,134,54,.35)}
.runbtn:disabled{opacity:.5;cursor:not-allowed;filter:none;box-shadow:none}
.prog{height:5px;background:#21262d;border-radius:3px;overflow:hidden;margin-top:10px}
.prog i{display:block;height:100%;width:0;background:linear-gradient(90deg,#1f6feb,#3fb950);border-radius:3px;transition:width .3s}

/* chips */
.chips{display:flex;gap:7px;flex-wrap:wrap}
.chip{padding:5px 13px;border-radius:7px;border:1px solid var(--border2);font-size:12.5px;color:var(--fg-dim);cursor:pointer;font-family:var(--mono)}
.chip.on{background:rgba(31,111,235,.18);border-color:var(--blue);color:var(--blue)}

/* modal */
.mask{position:fixed;inset:0;background:rgba(1,4,9,.7);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;z-index:50}
.mask.on{display:flex}
.modal{width:560px;max-height:72vh;background:var(--panel);border:1px solid var(--border2);border-radius:12px;display:flex;flex-direction:column;overflow:hidden;animation:fade .15s}
.modal .mh{display:flex;align-items:center;padding:14px 18px;border-bottom:1px solid var(--border);font-weight:600;color:#fff}
.modal .mh .x{margin-left:auto;cursor:pointer;color:var(--fg-dim);font-size:18px;padding:0 4px}
.modal .mh .x:hover{color:#fff}
.modal .mb{overflow-y:auto;padding:10px}
.school-item{padding:9px 12px;border-radius:7px;cursor:pointer;font-size:13px;display:flex;gap:12px}
.school-item:hover{background:var(--panel2)}
.school-item .code{font-family:var(--mono);color:var(--blue);width:52px;flex:none}

/* map */
#amap{width:100%;height:430px;background:#0d1117;border:1px solid var(--border);border-radius:9px;position:relative;overflow:hidden;cursor:grab;user-select:none}
#amap:active{cursor:grabbing}
#amap img{position:absolute;pointer-events:none;-webkit-user-drag:none;user-select:none}
#amap .mload{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--fg-dim);font:12px var(--mono);background:var(--panel);pointer-events:none}

/* bottom log */
#logwrap{grid-column:1/3;background:var(--panel);border-top:1px solid var(--border);display:flex;flex-direction:column}
#logwrap .lh{display:flex;align-items:center;padding:5px 16px;font-size:11px;color:var(--fg-faint);font-family:var(--mono);gap:14px}
#logwrap .lh .tt{color:var(--fg-dim)}
#logwrap .lh .clr{margin-left:auto;cursor:pointer}
#logwrap .lh .clr:hover{color:var(--red)}
#log{flex:1;overflow-y:auto;padding:2px 16px 10px;font:12px/1.7 var(--mono);color:#7ee787;white-space:pre-wrap;word-break:break-all}
#log .t{color:var(--fg-faint)}
#log .e{color:var(--red)}
#log .i{color:#79c0ff}
.toast{position:fixed;top:64px;right:22px;background:var(--panel2);border:1px solid var(--border2);border-left:3px solid var(--blue);padding:10px 18px;border-radius:8px;font-size:13px;z-index:99;animation:fade .2s;box-shadow:0 6px 24px rgba(0,0,0,.5)}
.toast.err{border-left-color:var(--red)}
.toast.ok{border-left-color:var(--green)}
</style>
</head>
<body>
<div id="app">
<header>
  <div class="logo"><svg viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19a4.5 4.5 0 0 0 .42-8.98 6 6 0 0 0-11.7-1.4A5.5 5.5 0 0 0 6.5 19h11z"/></svg>云运动 <span style="color:var(--fg-faint);font-weight:400">·</span> DEV CONSOLE <span class="ver">v3.6.6</span></div>
  <span class="hsep">|</span><span class="school" id="hSchool">--</span>
  <div class="pill" id="pill"><span class="dot"></span><span id="pillTx">READY</span></div>
  <span class="clock" id="clock"></span>
</header>

<aside>
  <div class="cap">WORKSPACE</div>
  <div class="nav on" data-p="home"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg>任务卡<span class="kbd">01</span></div>
  <div class="nav" data-p="run"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 17c4-9 8 3 12-6"/><path d="M14 5l5 5-4 1-2-3z"/></svg>跑步<span class="kbd">02</span></div>
  <div class="nav" data-p="map"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>地图轨迹<span class="kbd">03</span></div>
  <div class="nav" data-p="hist"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5M12 8v4l3 2"/></svg>历史成绩<span class="kbd">04</span></div>
  <div class="nav" data-p="news"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9h18M7 5v14"/></svg>公告问卷<span class="kbd">05</span></div>
  <div class="nav" data-p="timer"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6"/></svg>定时批量<span class="kbd">06</span></div>
  <div class="nav" data-p="device"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/></svg>设备工具<span class="kbd">07</span></div>
  <div class="nav" data-p="auth"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/></svg>登录 / 学校<span class="kbd">08</span></div>
  <div class="nav" data-p="acc"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="8" r="3"/><circle cx="16" cy="9" r="2.5"/><path d="M3 20c0-3 2.5-5 6-5s6 2 6 5"/><path d="M15 20c0-2 1.5-3.5 4-3.5s3 1 3 3"/></svg>多账户<span class="kbd">08</span></div>
  <div class="foot">LOCALHOST:<span id="pt"></span><br>PROTOCOL SM4 · LE-PAO<br>BUILD 2026.09.27</div>
</aside>

<main>
<!-- ══ 任务卡 ══ -->
<section class="page on" id="p-home">
  <div class="ph"><h1>任务卡 <span class="tag">DASHBOARD</span></h1><p>今日进度 · 里程目标 · 配速步频规则</p></div>
  <div class="grid g4" style="margin-bottom:14px">
    <div class="card stat"><div class="v b" id="stToday">--<em> km</em></div><div class="k">今日里程</div></div>
    <div class="card stat"><div class="v g" id="stOk">--</div><div class="k">合格次数</div></div>
    <div class="card stat"><div class="v p" id="stTarget">--</div><div class="k">学期目标</div></div>
    <div class="card stat"><div class="v" id="stName">--</div><div class="k">当前任务</div></div>
  </div>
  <div class="card">
    <div class="ct">任务规则 RUN RULES</div>
    <div id="homeRules" style="font:13px var(--mono);color:var(--fg-dim);line-height:2.1">点击「刷新任务」拉取最新任务卡…</div>
    <div style="margin-top:14px"><button class="btn pri" onclick="loadHome()">⟳ 刷新任务</button></div>
  </div>
</section>

<!-- ══ 跑步 ══ -->
<section class="page" id="p-run">
  <div class="ph"><h1>跑步 <span class="tag">RUN ENGINE</span></h1><p>打表 / 快速模式 · 真实轨迹 + GPS 漂移</p></div>
  <div class="grid g2">
    <div class="card">
      <div class="ct">参数 PARAMS</div>
      <div class="slider-row"><div class="sl-head"><span>距离</span><output id="o_dist_km">3.0 km</output></div><input type="range" id="s_dist_km" min="2.6" max="5" step="0.1"></div>
      <div class="slider-row"><div class="sl-head"><span>时长</span><output id="o_duration_s">840 s</output></div><input type="range" id="s_duration_s" min="600" max="1200" step="10"></div>
      <div class="slider-row"><div class="sl-head"><span>轨迹点数</span><output id="o_n_points">50</output></div><input type="range" id="s_n_points" min="20" max="80" step="10"></div>
      <div class="slider-row"><div class="sl-head"><span>打卡点</span><output id="o_marks">5</output></div><input type="range" id="s_marks" min="3" max="5" step="1"></div>
      <div class="slider-row"><div class="sl-head"><span>配速</span><output id="o_pace">4.67 min/km</output></div><input type="range" id="s_pace" min="3.5" max="8" step="0.05"></div>
      <div class="slider-row"><div class="sl-head"><span>步频</span><output id="o_cadence">170 spm</output></div><input type="range" id="s_cadence" min="140" max="200" step="1"></div>
    </div>
    <div class="card">
      <div class="ct">模式 MODE</div>
      <label class="lab">路线 ROUTE</label>
      <div class="seg" id="segRoute">
        <span class="opt on" data-v="loop">loop 绕圈</span>
        <span class="opt" data-v="outback">outback 往返</span>
        <span class="opt" data-v="eight">eight 8字</span>
      </div>
      <label class="lab">选项 OPTIONS</label>
      <div class="swrow"><label class="sw"><input type="checkbox" id="ckDrift" checked><i></i></label>GPS 漂移（米级抖动，更像真人）</div>
      <div class="swrow"><label class="sw"><input type="checkbox" id="ckQuick"><i></i></label>快速模式（不传轨迹，秒完成）</div>
      <div style="margin-top:18px">
        <button class="runbtn" id="btnRun" onclick="startRun()">▶ 开始跑步</button>
        <div class="prog"><i id="progBar"></i></div>
        <div id="runStatus" style="font:12px var(--mono);color:var(--fg-dim);margin-top:8px">就绪 · 等指令</div>
      </div>
    </div>
  </div>
</section>

<!-- ══ 地图 ══ -->
<section class="page" id="p-map">
  <div class="ph"><h1>地图轨迹 <span class="tag">GPS PLOT</span></h1><p>服务端生成真实轨迹 · 坐标系 GCJ-02</p></div>
  <div class="card">
    <div class="ct">高德地图 · 实时轨迹 AMAP LIVE</div>
    <div id="amap" style="position:relative;width:100%;height:430px;background:#0b0e14;border:1px solid var(--border);border-radius:9px;overflow:hidden;cursor:grab;user-select:none"></div>
    <div style="display:flex;gap:10px;margin-top:12px;align-items:center;flex-wrap:wrap">
      <button class="btn" onclick="genTrack()">⟳ 生成轨迹</button>
      <button class="btn" onclick="refreshCps()">◎ 同步任务打卡点</button>
      <button class="btn ok" onclick="startRun(true)">▶ 带轨迹跑</button>
      <span style="display:flex;gap:6px;margin-left:auto">
        <button class="btn sm" onclick="zoomMap(1)">＋</button>
        <button class="btn sm" onclick="zoomMap(-1)">－</button>
      </span>
      <span id="mapInfo" style="font:12px var(--mono);color:var(--fg-dim)">拖拽移动 · 滚轮缩放</span>
    </div>
  </div>
</section>

<!-- ══ 历史 ══ -->

<!-- ══ 多账户 ══ -->
<section class="page" id="p-acc">
  <div class="ph"><h1>多账户 <span class="tag">BATCH</span></h1><p>批量账号管理 · 一键批量跑步</p></div>
  <div class="card">
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
      <input id="accUser" placeholder="学号" style="padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--panel2);color:var(--fg);min-width:140px">
      <input id="accPass" placeholder="密码" type="password" style="padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--panel2);color:var(--fg);min-width:140px">
      <input id="accSchool" placeholder="schoolId" value="100" style="padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--panel2);color:var(--fg);width:90px">
      <button class="btn pri" onclick="accAdd()">＋ 添加</button>
      <button class="btn" onclick="accRefresh()">⟳ 刷新</button>
      <button class="btn" onclick="batchRun()">▶ 批量跑步</button>
    </div>
    <div id="accBody"><p style="color:var(--fg-faint);font-size:13px">点击「刷新」加载多账户…</p></div>
    <div style="margin-top:10px;font-size:12px;color:var(--fg-dim)">批量跑步会依次登录每个账号并执行一次合格跑；请确保每个账号密码正确。</div>
  </div>
</section>

<section class="page" id="p-hist">
  <div class="ph"><h1>历史成绩 <span class="tag">DATA RECALL</span></h1><p>跑步记录 · 个人汇总 · 成绩 · 学期</p></div>
  <div class="card">
    <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap">
      <button class="btn pri" onclick="loadBlock('history')">⟳ 加载数据</button>
      <div class="seg" id="histTabs">
        <span class="opt on" data-t="history">历史记录</span>
        <span class="opt" data-t="summary">个人汇总</span>
        <span class="opt" data-t="score">成绩</span>
        <span class="opt" data-t="term">学期</span>
      </div>
    </div>
    <div id="histBody"><p style="color:var(--fg-faint);font-size:13px">点击「加载数据」，各分类以表格形式展示…</p></div>
  </div>
  <div class="card" style="margin-top:12px">
    <h2 style="margin-bottom:10px">历史真实轨迹复现</h2>
    <p style="color:var(--fg-dim);font-size:12px;margin-bottom:10px">选择一次历史跑步，按原始轨迹点完整重放上传（GPS 坐标/里程/时间均来自该次记录）。</p>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
      <button class="btn" onclick="loadReplayList()">⟳ 加载跑步记录</button>
      <select id="replaySel" style="flex:1;min-width:220px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--panel2);color:var(--fg)"></select>
      <button class="btn pri" onclick="startReplay()">▶ 复现这次跑步</button>
    </div>
    <div id="replayInfo" style="margin-top:10px;font:12px var(--mono);color:var(--fg-dim)"></div>
    <div id="replayPts" style="margin-top:10px;max-height:280px;overflow:auto"></div>
  </div>
</section>

<!-- ══ 公告 ══ -->
<section class="page" id="p-news">
  <div class="ph"><h1>公告问卷 <span class="tag">MESSAGE BOARD</span></h1><p>首页资讯 · 弹窗 · 问卷</p></div>
  <div class="card">
    <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap">
      <button class="btn pri" onclick="loadBlock('news')">⟳ 加载消息</button>
      <div class="seg" id="newsTabs">
        <span class="opt on" data-t="home">首页</span>
        <span class="opt" data-t="news">资讯公告</span>
        <span class="opt" data-t="popup">弹窗</span>
        <span class="opt" data-t="survey">问卷</span>
      </div>
    </div>
    <div id="newsBody"><p style="color:var(--fg-faint);font-size:13px">点击「加载消息」…</p></div>
  </div>
</section>

<!-- ══ 定时 ══ -->
<section class="page" id="p-timer">
  <div class="ph"><h1>定时批量 <span class="tag">CRON / BATCH</span></h1><p>到点自动跑 · 多账号批量</p></div>
  <div class="grid g2">
    <div class="card">
      <div class="ct">定时任务 SCHEDULE</div>
      <label class="lab">执行时间（每天）</label>
      <input type="time" class="inp" id="tmTime">
      <label class="lab">生效星期</label>
      <div class="chips" id="dayChips">
        <span class="chip" data-d="1">周一</span><span class="chip" data-d="2">周二</span><span class="chip" data-d="3">周三</span><span class="chip" data-d="4">周四</span><span class="chip" data-d="5">周五</span><span class="chip" data-d="6">周六</span><span class="chip" data-d="7">周日</span>
      </div>
      <div class="swrow" style="margin-top:12px"><label class="sw"><input type="checkbox" id="ckTimer"><i></i></label>启用定时</div>
      <p style="font-size:12px;color:var(--fg-faint);margin:6px 0 0;line-height:1.7">程序内置定时器，保持本程序运行到点自动执行，无需另开挂机程序。</p>
      <div style="margin-top:12px"><button class="btn pri" onclick="saveTimer()">保存设置</button></div>
    </div>
    <div class="card">
      <div class="ct">批量 BATCH</div>
      <p style="font-size:13px;color:var(--fg-dim);line-height:1.9">把多个 <code style="font-family:var(--mono);color:var(--blue)">yunyundong_config*.json</code> 放在程序同目录，命令行执行：</p>
      <pre class="term" style="max-height:110px;margin-top:10px">python yunyundong_full.py batch</pre>
    </div>
  </div>
</section>

<!-- ══ 设备 ══ -->
<section class="page" id="p-device">
  <div class="ph"><h1>设备工具 <span class="tag">DEVICE SPOOFER</span></h1><p>设备指纹 · 随机化</p></div>
  <div class="grid g2">
    <div class="card">
      <div class="ct">当前指纹 CURRENT</div>
      <div style="background:#010409;border:1px solid var(--border);border-radius:9px;padding:16px;font:13px var(--mono);color:#7ee787" id="devInfo">--</div>
      <div style="margin-top:14px"><button class="btn warn" onclick="randDevice()">⚄ 随机换设备</button></div>
    </div>
    <div class="card">
      <div class="ct">策略 POLICY</div>
      <div class="swrow"><label class="sw"><input type="checkbox" id="ckAutoDev" checked><i></i></label>每次请求自动随机设备</div>
      <p style="font-size:12.5px;color:var(--fg-faint);margin-top:10px;line-height:1.8">开启后每个 API 请求都会携带随机机型指纹，避免单一设备特征被标记。</p>
    </div>
  </div>
</section>

<!-- ══ 登录 ══ -->
<section class="page" id="p-auth">
  <div class="ph"><h1>登录 / 学校 <span class="tag">AUTH</span></h1><p>学号密码登录 · 切换学校</p></div>
  <div class="grid g2">
    <div class="card">
      <div class="ct">账号 ACCOUNT</div>
      <label class="lab">学号</label><input class="inp" id="inUser">
      <label class="lab">密码</label><input class="inp" id="inPass" type="password">
      <label class="lab">Token（可留空）</label><input class="inp" id="inToken">
      <div style="margin-top:16px;display:flex;gap:10px">
        <button class="btn pri" onclick="doLogin()">登录</button>
        <button class="btn" onclick="loadSchools()">学校列表</button>
        <button class="btn" onclick="randSchool()">随机学校</button>
      </div>
    </div>
    <div class="card">
      <div class="ct">当前学校 SCHOOL</div>
      <div style="background:#010409;border:1px solid var(--border);border-radius:9px;padding:16px;font:13px var(--mono);color:#79c0ff" id="authSchool">--</div>
    </div>
  </div>
</section>
</main>

<div id="logwrap">
  <div class="lh"><span class="tt">TERMINAL</span><span>local · utf-8 · sm4</span><span class="clr" onclick="document.getElementById('log').innerHTML=''">✕ 清空</span></div>
  <div id="log"></div>
</div>
</div>

<div class="mask" id="mask">
  <div class="modal">
    <div class="mh">选择学校<span class="x" onclick="mask.classList.remove('on')">✕</span></div>
    <div style="padding:10px 14px 0"><input class="inp" id="schFilter" placeholder="搜索学校名称 / 代码…" oninput="renderSchools()"></div>
    <div class="mb" id="schList"></div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
document.addEventListener('DOMContentLoaded',()=>{const e=document.getElementById('pt');if(e)e.textContent=location.port;});
let CUR={}, ROUTE='loop', mask=$('mask'), SCHOOLS=[];
async function api(path,body){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
  return r.json();
}
function toast(msg,cls){const t=document.createElement('div');t.className='toast '+(cls||'');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),2600)}
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}

/* nav */
document.querySelectorAll('.nav').forEach(n=>n.onclick=()=>{
  document.querySelectorAll('.nav').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('on'));
  n.classList.add('on'); $('p-'+n.dataset.p).classList.add('on');
  if(n.dataset.p==='map'){ initMap(); setTimeout(renderMap,60); }
});



/* ── 多账户 ── */
async function accRefresh(){
  const r=await api('/api/accounts');
  const list=r.data||[];
  const el=$('accBody'); if(!el)return;
  if(!list.length){el.innerHTML='<p style="color:var(--fg-faint)">暂无账户，先添加</p>';return}
  let h='<table style="width:100%;font:12px var(--mono);border-collapse:collapse">';
  h+='<tr style="color:var(--fg-faint)"><th style="text-align:left;padding:6px">学号</th><th>schoolId</th><th>token</th><th>操作</th></tr>';
  for(const a of list){
    h+=`<tr><td style="padding:6px">${esc(a.username||'')}</td><td style="text-align:center">${esc(a.school_id||'')}</td><td style="text-align:center">${(a.token||'').slice(0,8)||'--'}</td>`;
    h+=`<td style="text-align:center"><button class="btn" style="padding:2px 8px;font-size:11px" onclick="accLogin('${esc(a.username)}')">登录</button> `;
    h+=`<button class="btn" style="padding:2px 8px;font-size:11px" onclick="accDel('${esc(a.username)}')">删</button></td></tr>`;
  }
  h+='</table>';
  el.innerHTML=h;
}
async function accAdd(){
  const u=$('accUser').value.trim(), p=$('accPass').value, sc=$('accSchool').value.trim()||'100';
  if(!u){toast('学号不能为空','err');return}
  const r=await api('/api/account_add',{username:u,password:p,school_id:sc});
  if(r.ok){toast('已添加'); $('accUser').value=''; $('accPass').value=''; accRefresh()}
  else toast(r.error||'失败','err');
}
async function accDel(u){
  if(!confirm('删除账号 '+u+' ?'))return;
  const r=await api('/api/account_del',{username:u});
  if(r.ok){toast('已删除');accRefresh()}else toast(r.error||'失败','err');
}
async function accLogin(u){
  toast('登录 '+u+' …');
  const r=await api('/api/account_login',{username:u});
  if(r.ok){toast('登录成功');accRefresh()}else toast(r.error||'失败','err');
}
async function batchRun(){
  if(!confirm('开始批量跑步？每个账号依次执行一次。'))return;
  const r=await api('/api/batch_run',{});
  if(r.ok) toast('批量已启动，看日志');
  else toast(r.error||'失败','err');
}

/* ── 历史真实轨迹复现 ── */
async function loadReplayList(){
  toast('加载跑步记录…');
  const r=await api('/api/history');
  const hist=(r.data&&r.data.history)||{};
  const rows=[];
  for(const g of (hist.data&&hist.data.rank)||[]){
    for(const it of (g.rankList||[])) rows.push(it);
  }
  const sel=$('replaySel'); sel.innerHTML='';
  if(!rows.length){ sel.innerHTML='<option value="">无记录</option>'; toast('无历史记录','err'); return }
  rows.sort((a,b)=>String(b.recordEndTime||'').localeCompare(String(a.recordEndTime||'')));
  for(const it of rows){
    const o=document.createElement('option');
    o.value=it.id;
    o.textContent=`${it.recordEndTime||''}  ${it.recordMileage}km  ${it.isQualified=='1'?'合格':'不合格'}  ${it.raName||''}`;
    sel.appendChild(o);
  }
  toast(`共 ${rows.length} 条`);
  const id=sel.value; if(id) previewReplay(id);
  sel.onchange=()=>previewReplay(sel.value);
}
async function previewReplay(id){
  if(!id) return;
  const r=await api('/api/history_points',{id});
  if(!r.ok){ $('replayInfo').textContent=r.error||'加载失败'; return }
  const d=r.data||{};
  $('replayInfo').textContent=`id=${d.id}  点数=${d.n}  里程=${d.mileage}km  时长=${d.duration}s  配速=${d.pace}  ${d.startTime||''} → ${d.endTime||''}`;
  const pts=d.points||[];
  let html='<table style="width:100%;font:12px var(--mono);border-collapse:collapse">';
  html+='<tr style="color:var(--fg-faint)"><th style="text-align:left;padding:4px">#</th><th style="text-align:left">坐标</th><th>里程m</th><th>时间s</th><th>配速</th></tr>';
  const show=pts.slice(0,20);
  for(let i=0;i<show.length;i++){
    const p=show[i];
    html+=`<tr><td style="padding:3px 6px;color:var(--fg-faint)">${i+1}</td><td style="padding:3px 6px">${p.lon.toFixed(6)},${p.lat.toFixed(6)}</td><td style="text-align:right">${p.runMileage}</td><td style="text-align:right">${p.runTime}</td><td style="text-align:right">${p.speed}</td></tr>`;
  }
  if(pts.length>20) html+=`<tr><td colspan="5" style="padding:4px 6px;color:var(--fg-faint)">… 共 ${pts.length} 点</td></tr>`;
  html+='</table>';
  $('replayPts').innerHTML=html;
}
async function startReplay(){
  const id=$('replaySel')&&$('replaySel').value;
  if(!id){toast('请先选择一次跑步记录','err');return}
  if(!confirm('确定按该次真实轨迹复现吗？将 start→split→finish 完整上传。'))return;
  toast('开始复现…');
  const r=await api('/api/replay',{id});
  if(r.ok) toast('复现已启动，看日志面板');
  else toast(r.error||'失败','err');
}

/* clock */
setInterval(()=>{$('clock').textContent=new Date().toLocaleTimeString('zh-CN',{hour12:false})},500);

/* config init */
(async()=>{
  const r=await api('/api/config'); CUR=r.data||{};
  const S=[['dist_km','km',''],['duration_s','s',''],['n_points','',''],['marks','',''],['pace','min/km',''],['cadence','spm','']];
  for(const [k,u] of S){
    const el=$('s_'+k); if(el){el.value=CUR[k]; $('o_'+k).textContent=CUR[k]+' '+u; el.oninput=()=>{ $('o_'+k).textContent=el.value+' '+u; api('/api/config',{[k]:parseFloat(el.value)}); }}
  }
  $('ckDrift').checked=CUR.drift!==false; $('ckDrift').onchange=e=>api('/api/config',{drift:e.target.checked});
  $('ckQuick').checked=!!CUR.quick_mode; $('ckQuick').onchange=e=>api('/api/config',{quick_mode:e.target.checked});
  $('ckAutoDev').checked=!!CUR.auto_random_device; $('ckAutoDev').onchange=e=>api('/api/config',{auto_random_device:e.target.checked});
  ROUTE=CUR.route||'loop';
  document.querySelectorAll('#segRoute .opt').forEach(o=>{ if(o.dataset.v===ROUTE)o.classList.add('on'); else o.classList.remove('on');
    o.onclick=()=>{ document.querySelectorAll('#segRoute .opt').forEach(x=>x.classList.remove('on')); o.classList.add('on'); ROUTE=o.dataset.v; api('/api/config',{route:ROUTE}); };});
  $('hSchool').textContent=CUR.school_name||'--'; $('authSchool').textContent='▸ '+(CUR.school_name||'--')+' ('+(CUR.school_id||'')+')';
  $('inUser').value=CUR.username||''; $('inToken').value=CUR.token||'';
  $('devInfo').textContent='▸ '+(CUR.devicename||'--')+'\n▸ '+(CUR.deviceid||'');
  $('tmTime').value=String(CUR.timer_hh||7).padStart(2,'0')+':'+String(CUR.timer_mm||30).padStart(2,'0');
  (CUR.timer_days||'1,2,3,4,5').split(',').forEach(d=>{const c=document.querySelector('.chip[data-d="'+d+'"]'); if(c)c.classList.add('on')});
  $('ckTimer').checked=!!CUR.timer_on;
  document.querySelectorAll('#dayChips .chip').forEach(c=>c.onclick=()=>c.classList.toggle('on'));
})();

/* task card */
async function loadHome(){
  toast('拉取任务卡…');
  const r=await api('/api/home');
  if(!r.ok){toast(r.error||'失败','err');return}
  const d=r.data; if(!d){$('homeRules').textContent='!! 今日无任务'; toast('无任务','err'); return}
  $('stToday').innerHTML=d.today_km+'<em> km</em>'; $('stOk').textContent=d.qualified;
  $('stTarget').textContent=d.target; $('stName').textContent=d.raName||'--';
  $('homeRules').innerHTML=
   'TASK   ▸ '+esc(d.raName)+'  T'+(d.raType||'?')+'\n'+
   'DIST   ▸ '+d.min+' – '+d.max+' km\n'+
   'PACE   ▸ '+d.pace_min+' – '+d.pace_max+' min/km\n'+
   'CAD    ▸ '+d.cad_min+' – '+d.cad_max+' spm\n'+
   'MARK   ▸ '+d.min_dislikes+' – '+d.dislikes+' 个打卡点\n'+
   'TIME   ▸ '+d.day_start+' – '+d.day_end+'   AM ▸ '+(d.morning_s||'')+'–'+(d.morning_e||'')+' ('+d.morning_num+')\n'+
   'CAP    ▸ '+d.day_km+' km/日   WEEK ▸ '+(d.week||'--');
  toast('任务卡已更新','ok');
}

/* run */
let running=false;
async function startRun(fromMap){
  if(running)return;
  running=true; $('btnRun').disabled=true; $('runStatus').textContent='执行中…'; $('progBar').style.width='5%';
  toast('开始跑步…');
  const r=await api('/api/run',{route:ROUTE});
  if(!r.ok){toast(r.error||'启动失败','err');}
  running=false; $('btnRun').disabled=false;
}

/* map · 高德瓦片地图 */
const MC={lon:117.5966,lat:31.6083,z:16};
let TRK=null, CPS=[], mapInit=false, MAP={drag:null};
function ll2g(lon,lat,z){
  const sc=Math.pow(2,z)*256;
  const x=(lon+180)/360*sc;
  const s=Math.sin(lat*Math.PI/180);
  const y=(0.5-Math.log((1+s)/(1-s))/(4*Math.PI))*sc;
  return [x,y];
}
function g2ll(px,py,z){
  const sc=Math.pow(2,z)*256;
  const lon=px/sc*360-180;
  const n=Math.PI-2*Math.PI*py/sc;
  const lat=Math.atan(0.5*(Math.exp(n)-Math.exp(-n)))*180/Math.PI;
  return [lon,lat];
}
function parseCps(list){
  return (list||[]).map(s=>{
    if(Array.isArray(s)) return s;
    const m=String(s).split(/[,\s]+/).map(Number).filter(v=>!isNaN(v));
    return m.length>=2?[m[0],m[1]]:null;
  }).filter(Boolean);
}
function initMap(){
  if(mapInit)return;
  mapInit=true;
  const el=$('amap');
  el.addEventListener('mousedown',e=>{MAP.drag={x:e.clientX,y:e.clientY,lon:MC.lon,lat:MC.lat};e.preventDefault();});
  window.addEventListener('mousemove',e=>{
    if(!MAP.drag)return;
    const sc=Math.pow(2,MC.z)*256;
    const dx=e.clientX-MAP.drag.x, dy=e.clientY-MAP.drag.y;
    const cx=ll2g(MAP.drag.lon,MAP.drag.lat,MC.z);
    const ll=g2ll(cx[0]-dx,cx[1]-dy,MC.z);
    MC.lon=ll[0];MC.lat=ll[1];
    renderMap();
  });
  window.addEventListener('mouseup',()=>{MAP.drag=null;});
  el.addEventListener('wheel',e=>{
    e.preventDefault();
    zoomMap(e.deltaY<0?1:-1);
  },{passive:false});
  renderMap();
  refreshCps();
}
function renderMap(){
  const el=$('amap');
  if(!el)return;
  const W=el.clientWidth||el.offsetWidth||900, H=el.clientHeight||430;
  const c=ll2g(MC.lon,MC.lat,MC.z), ox=c[0]-W/2, oy=c[1]-H/2;
  const seen={};
  for(let tx=Math.floor(ox/256);tx<=Math.floor((ox+W)/256);tx++){
    for(let ty=Math.floor(oy/256);ty<=Math.floor((oy+H)/256);ty++){
      const k=MC.z+'/'+tx+'/'+ty, seen_k=k;
      seen[seen_k]=1;
      let img=el.querySelector('img[data-k="'+k+'"]');
      if(!img){
        img=document.createElement('img');
        img.dataset.k=k;
        img.src='/tiles/'+k+'.png';
        img.style.left=(tx*256-ox)+'px';
        img.style.top=(ty*256-oy)+'px';
        img.onerror=()=>{img.style.display='none';};
        el.appendChild(img);
      }else{
        img.style.left=(tx*256-ox)+'px';
        img.style.top=(ty*256-oy)+'px';
      }
    }
  }
  el.querySelectorAll('img[data-k]').forEach(img=>{
    if(!seen[img.dataset.k])img.remove();
    else img.style.display='';
  });
  drawOverlay(ox,oy,W,H);
}
function drawOverlay(ox,oy,W,H){
  const el=$('amap');
  let svg=el.querySelector('svg.mapov');
  if(!svg){
    svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('class','mapov');
    svg.style.cssText='position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;';
    el.appendChild(svg);
  }
  let s='';
  CPS.forEach((cp,i)=>{
    const [x,y]=ll2g(cp[0],cp[1],MC.z);
    const px=x-ox, py=y-oy;
    if(px<-30||py<-30||px>W+30||py>H+30)return;
    s+='<circle cx="'+px+'" cy="'+py+'" r="7" fill="#3fb950" stroke="#0d1117" stroke-width="2"/>';
    s+='<text x="'+(px+11)+'" y="'+(py+4)+'" fill="#fff" font-size="12" font-family="var(--mono),monospace" style="paint-order:stroke" stroke="#0d1117" stroke-width="3">'+(i+1)+'</text>';
  });
  if(TRK&&TRK.length>1){
    let d='';
    TRK.forEach(p=>{
      const ll=Array.isArray(p)?p:String(p).split(/[,\s]+/).map(Number);
      if(!ll||ll.length<2)return;
      const [x,y]=ll2g(+ll[0],+ll[1],MC.z);
      d+=(d?'L':'M')+(x-ox)+' '+(y-oy);
    });
    s+='<path d="'+d+'" fill="none" stroke="#1f6feb" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>';
    const p0=Array.isArray(TRK[0])?TRK[0]:String(TRK[0]).split(/[,\s]+/).map(Number);
    const p1=Array.isArray(TRK[TRK.length-1])?TRK[TRK.length-1]:String(TRK[TRK.length-1]).split(/[,\s]+/).map(Number);
    [[p0,'#3fb950'],[p1,'#f85149']].forEach(([p,c])=>{
      const [x,y]=ll2g(+p[0],+p[1],MC.z);
      s+='<circle cx="'+(x-ox)+'" cy="'+(y-oy)+'" r="6" fill="'+c+'" stroke="#fff" stroke-width="2"/>';
    });
  }
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  svg.innerHTML=s;
}
async function refreshCps(){
  const r=await api('/api/task_points');
  if(r.ok&&r.data&&r.data.length){
    CPS=parseCps(r.data);
    MC.lon=CPS[0][0];MC.lat=CPS[0][1];
    renderMap();
    $('mapInfo').textContent='打卡点 '+CPS.length+' 个 · 已定位到任务区域';
  }
}
async function genTrack(){
  const r=await api('/api/track');
  if(!r.ok){toast(r.error||'生成失败','err');return}
  TRK=r.data||[];
  if(!TRK.length){toast('未生成轨迹','err');return}
  const pts=parseCps(TRK);
  const lons=pts.map(p=>p[0]), lats=pts.map(p=>p[1]);
  const mnx=Math.min(...lons),mxx=Math.max(...lons),mny=Math.min(...lats),mxy=Math.max(...lats);
  const cx=(mnx+mxx)/2, cy=(mny+mxy)/2;
  for(let z=18;z>=15;z--){
    const [x1,y1]=ll2g(mnx,mxy,z), [x2,y2]=ll2g(mxx,mny,z);
    if(Math.abs(x2-x1)<( $('amap').clientWidth||900)*0.7 && Math.abs(y2-y1)<430*0.7){MC.z=z;break;}
  }
  MC.lon=cx;MC.lat=cy;
  renderMap();
  $('mapInfo').textContent=TRK.length+' 点 · '+CUR.dist_km+' km · '+CUR.duration_s+' s · 蓝色为拟合轨迹';
}
function zoomMap(d){
  MC.z=Math.min(18,Math.max(15,MC.z+d));
  renderMap();
}

/* data blocks · 语义化渲染 */
const HIST_LABEL={history:'历史记录',summary:'个人汇总',score:'成绩',term:'学期'};
const NEWS_LABEL={home:'首页',news:'资讯公告',popup:'弹窗',survey:'问卷'};
const KEY_CN={isLiveStatus:'直播状态',isLive:'直播中',sumKm:'累计里程',sumNumber:'跑步次数',morningNum:'晨跑次数',isMorning:'晨跑时段',rank:'月度排行',rankList:'跑步记录',year:'年份',month:'月份',monthKm:'当月里程',id:'记录ID',endTime:'结束时间',recordEndTime:'完成时间',recordStartTime:'开始时间',startTime:'开始时间',recodePace:'配速(min/km)',recodeCadence:'步频(spm)',recordMileage:'里程(km)',duration:'时长(秒)',qualified:'是否合格',isQualified:'合格状态',speeds:'速度',userName:'用户',schoolId:'学校ID',schoolName:'学校',raName:'任务名称',raType:'任务类型',createTime:'创建时间',updateTime:'更新时间',title:'标题',content:'内容',msg:'消息',code:'状态码',name:'名称',key:'标识',value:'值',xq:'学期',sjd:'时间段',xnYear:'学年',dayKm:'今日里程',distance:'距离',qualifiedCount:'合格次数',raTargetNum:'目标次数',calorie:'消耗(千卡)',stepNumber:'步数',status:'状态',peScore:'体育成绩',score:'分数',totalScore:'总分',xn:'学年',week:'周次',list:'列表',rows:'数据'};
const cn=k=>KEY_CN[k]||k;
function trunc(t,n){t=String(t);return t.length>n?t.slice(0,n)+'…':t;}
function fmtCell(k,v,depth){
  if(v===null||v===undefined) return '<span style="color:var(--fg-faint)">—</span>';
  if(Array.isArray(v)){
    if(v.length&&typeof v[0]==='object'&&v[0]&&depth<2) return miniTable(v,depth+1);
    return '<code style="font-family:var(--mono);font-size:11.5px;color:var(--purple)">'+esc(trunc(JSON.stringify(v),90))+'</code>';
  }
  if(typeof v==='object'){
    return '<code style="font-family:var(--mono);font-size:11.5px;color:var(--purple)">'+esc(trunc(JSON.stringify(v),90))+'</code>';
  }
  let t=esc(String(v));
  if(!isNaN(parseFloat(v))&&String(v).trim()!==''){
    if(/km$/i.test(k)) t+=' <span style="color:var(--fg-faint);font-size:11px">km</span>';
    if(/Pace/.test(k)) t+=' <span style="color:var(--fg-faint);font-size:11px">min/km</span>';
  }
  return t;
}
function miniTable(arr,depth){
  depth=depth||0;
  const keys=[...new Set(arr.slice(0,10).flatMap(o=>Object.keys(o)))].slice(0,6);
  return '<table class="tb" style="margin:4px 0"><tr>'+keys.map(k=>'<th>'+esc(cn(k))+'</th>').join('')+'</tr>'
    +arr.slice(0,8).map(o=>'<tr>'+keys.map(k=>'<td>'+fmtCell(k,o[k],depth)+'</td>').join('')+'</tr>').join('')+'</table>'
    +(arr.length>8?'<span style="color:var(--fg-faint);font-size:11px">… 共 '+arr.length+' 条</span>':'');
}
function statCards(data){
  const keys=Object.keys(data).filter(k=>{
    const v=data[k];
    return typeof v!=='object'&&v!==null&&v!==''&&!isNaN(parseFloat(v))&&!/code|id|status/i.test(k);
  }).slice(0,4);
  if(keys.length<2) return '';
  return '<div class="grid g4" style="margin:4px 0 14px">'+keys.map(k=>
    '<div class="card stat" style="padding:12px 6px"><div class="v b">'+esc(String(data[k]))+
    '</div><div class="k">'+esc(cn(k))+'</div></div>').join('')+'</div>';
}
function renderBlock(box,title,data){
  let h='<div class="ct" style="margin-top:6px">'+esc(title)+'</div>';
  if(typeof data==='string'&&data.startsWith('ERR')){h+='<p style="color:var(--red);font-size:13px">'+esc(data)+'</p>';box.innerHTML=h;return;}
  // 解包服务器信封 {code,msg,data}
  if(data&&typeof data==='object'&&!Array.isArray(data)&&'data' in data&&'code' in data){
    if(data.code!==200){h+='<p style="color:var(--red);font-size:13px">接口返回异常：'+esc(data.msg||data.code)+'</p>';box.innerHTML=h;return;}
    data=(typeof data.data==='string')?null:data.data;
    if(!data){h+='<p style="color:var(--fg-faint);font-size:13px">暂无数据</p>';box.innerHTML=h;return;}
  }
  if(Array.isArray(data)){
    if(!data.length){h+='<p style="color:var(--fg-faint);font-size:13px">暂无数据</p>';}
    else if(typeof data[0]==='object'&&data[0]){
      const keys=[...new Set(data.slice(0,30).flatMap(o=>Object.keys(o)))].slice(0,9);
      h+='<div style="overflow-x:auto"><table class="tb"><tr>'+keys.map(k=>'<th>'+esc(cn(k))+'</th>').join('')+'</tr>'
        +data.slice(0,60).map(o=>'<tr>'+keys.map(k=>'<td>'+fmtCell(k,o[k],0)+'</td>').join('')+'</tr>').join('')+'</table></div>';
      if(data.length>60)h+='<p style="color:var(--fg-faint);font-size:12px;margin-top:6px">… 共 '+data.length+' 条，显示前 60</p>';
    } else h+='<pre class="term">'+esc(JSON.stringify(data,null,1))+'</pre>';
  } else if(data&&typeof data==='object'){
    h+=statCards(data);
    const keys=Object.keys(data).slice(0,20);
    if(keys.length) h+='<table class="tb">'+keys.map(k=>'<tr><th style="width:200px">'+esc(cn(k))+'</th><td>'+fmtCell(k,data[k],0)+'</td></tr>').join('')+'</table>';
    else h+='<p style="color:var(--fg-faint);font-size:13px">暂无数据</p>';
  } else h+='<p style="font-size:13px">'+esc(String(data))+'</p>';
  box.innerHTML=h;
}
function switchTab(tabsId,key,bodyId){
  document.querySelectorAll('#'+tabsId+' .opt').forEach(o=>o.classList.toggle('on',o.dataset.t===key));
  document.querySelectorAll('#'+bodyId+' > .tabpane').forEach(p=>p.style.display=p.dataset.k===key?'block':'none');
}
async function loadBlock(kind){
  toast('拉取数据…');
  const r=await api('/api/'+kind);
  const body=$(kind==='history'?'histBody':'newsBody'), tabs=$(kind==='history'?'histTabs':'newsTabs');
  if(!r.ok){body.innerHTML='<p style="color:var(--red);font-size:13px">加载失败：'+esc(r.error||'未知错误')+'</p>';toast('加载失败','err');return;}
  const label=kind==='history'?HIST_LABEL:NEWS_LABEL;
  body.innerHTML='';
  Object.keys(label).forEach(k=>{
    const pane=document.createElement('div');
    pane.className='tabpane';pane.dataset.k=k;pane.style.display='none';
    body.appendChild(pane);
    renderBlock(pane,label[k],r.data?r.data[k]:null);
  });
  tabs.querySelectorAll('.opt').forEach(o=>o.onclick=()=>switchTab(tabs.id,o.dataset.t,body.id));
  switchTab(tabs.id,Object.keys(label)[0],body.id);
  toast('数据已加载','ok');
}

/* timer */
function saveTimer(){
  const [h,m]=$('tmTime').value.split(':');
  const days=[...document.querySelectorAll('#dayChips .chip.on')].map(c=>c.dataset.d).join(',');
  api('/api/timer',{timer_on:$('ckTimer').checked,timer_hh:+h,timer_mm:+m,timer_days:days}).then(r=>toast(r.ok?'已保存':'保存失败',r.ok?'ok':'err'));
}

/* device */
function randDevice(){
  api('/api/device/random').then(r=>{ if(r.ok){$('devInfo').textContent='▸ '+r.data.name+'\n▸ '+r.data.id; toast('已换设备','ok');} else toast(r.error,'err'); });
  document.querySelector('.nav[data-p=device]').click===0;
}

/* auth */
function doLogin(){
  api('/api/login',{username:$('inUser').value,password:$('inPass').value,token:$('inToken').value})
   .then(r=>toast(r.ok?'登录成功':'登录失败 '+(r.error||''),r.ok?'ok':'err'));
}
async function loadSchools(){
  toast('拉取学校列表…');
  const r=await api('/api/schools');
  if(!r.ok){toast(r.error,'err');return}
  SCHOOLS=r.data||[]; renderSchools(); mask.classList.add('on');
}
function renderSchools(){
  const q=($('schFilter').value||'').toLowerCase();
  $('schList').innerHTML=SCHOOLS.filter(s=>!q||String(s.schoolName).toLowerCase().includes(q)||String(s.schoolCode).includes(q))
    .map(s=>'<div class="school-item" onclick="pickSchool(\''+s.schoolCode+'\')"><span class="code">'+esc(s.schoolCode)+'</span><span>'+esc(s.schoolName)+'</span></div>').join('')||'<div style="padding:20px;color:var(--fg-dim)">无匹配结果</div>';
}
async function pickSchool(code){
  const r=await api('/api/pick_school',{code});
  if(r.ok){ $('hSchool').textContent=r.data.school_name; $('authSchool').textContent='▸ '+r.data.school_name+' ('+r.data.school_id+')'; mask.classList.remove('on'); toast('已切换学校','ok'); }
}
async function randSchool(){
  const r=await api('/api/random_school');
  if(r.ok){ $('hSchool').textContent=r.data.school_name; $('authSchool').textContent='▸ '+r.data.school_name+' ('+r.data.school_id+')'; toast('随机换校完成','ok'); }
}

/* log polling */
let after=0;
setInterval(async()=>{
  try{
    const r=await fetch('/api/logs?after='+after); const d=await r.json();
    after=d.next;
    if(d.lines&&d.lines.length){
      const lg=$('log');
      d.lines.forEach(s=>{
        const cls=s.includes('←')?'i':(s.includes('code')&&!s.includes('200')?'e':'');
        lg.innerHTML+='<div><span class="t">'+esc(s.slice(0,10))+'</span> '+esc(s.slice(11))+'</div>';
      });
      lg.scrollTop=lg.scrollHeight;
      const m=d.lines.join('\n').match(/轨迹 (\d+)\/(\d+)/);
      if(m){ $('progBar').style.width=(m[1]/m[2]*100)+'%'; $('runStatus').textContent='轨迹 '+m[1]+'/'+m[2]; }
      if(d.lines.join('\n').includes('DONE')){ $('runStatus').textContent='✓ 完成'; $('progBar').style.width='100%'; toast('跑步完成','ok'); }
    }
    const pill=$('pill'); pill.className='pill'+(d.running?' run':(d.state==='FAIL'?' err':''));
    $('pillTx').textContent=d.running?'RUNNING':(d.state||'READY');
  }catch(e){}
},700);
</script>
</body>
</html>
"""

class _WebLog:
    """线程安全日志环形缓冲."""
    def __init__(self):
        self.lock=threading.Lock(); self.buf=[]
    def __call__(self,s):
        with self.lock:
            self.buf.append(f"[{datetime.now().strftime('%H:%M:%S')}] {s}")
            if len(self.buf)>600: self.buf=self.buf[-600:]

def run_gui(cfg,api):
    """启动本地 Web 工作台并打开浏览器."""
    import http.server, urllib.parse, webbrowser
    wlog=_WebLog(); api.log=wlog
    state={"running":False,"last":"READY"}
    CFG_KEYS=("dist_km","duration_s","n_points","marks","pace","cadence","drift",
              "quick_mode","route","timer_on","timer_hh","timer_mm","timer_days",
              "auto_random_device","username","password","token")

    def fire_run():
        """后台执行一次完整跑步（按钮与定时器共用）."""
        if state["running"]: return False
        def job():
            state["running"]=True; state["last"]="RUNNING"
            def onp(i,n,chunk):
                wlog(f"轨迹 {i}/{n}  里程 {chunk[-1]['runMileage']}m  配速 {chunk[-1]['speed']}")
            try:
                r=api.run_full(float(cfg["dist_km"]),int(cfg["duration_s"]),
                               int(cfg["n_points"]),int(cfg["marks"]),
                               cfg.get("route","loop"),cfg.get("drift",True),
                               onp,cfg.get("quick_mode",False))
                ok=isinstance(r,dict) and r.get("code")==200
                state["last"]="DONE" if ok else "FAIL"
                if isinstance(r,dict):
                    wlog(("DONE " if ok else "FAIL ")+f"record={r.get('recordId')} pace={r.get('pace')}")
                else:
                    wlog("FAIL")
            except Exception as e:
                state["last"]="FAIL"; wlog(f"FAIL {e}")
            finally:
                state["running"]=False
        threading.Thread(target=job,daemon=True).start()
        return True

    def cron_loop():
        """内置定时器：到点自动跑一次（读配置 timer_*，界面改动即时生效）."""
        wlog("[CRON] 定时器线程已启动")
        fired=None
        while True:
            time.sleep(20)
            if not cfg.get("timer_on"): continue
            now=datetime.now()
            try:
                days=[int(x) for x in str(cfg.get("timer_days","1,2,3,4,5")).split(",") if x]
                hh,mm=int(cfg["timer_hh"]),int(cfg["timer_mm"])
            except Exception:
                continue
            if (now.isoweekday() in days and now.hour==hh and now.minute==mm
                    and fired!=now.strftime("%Y%m%d")):
                fired=now.strftime("%Y%m%d")
                wlog(f"[CRON] 定时触发 {hh:02d}:{mm:02d} 自动跑步")
                fire_run()

    def _route(path,b):
        if path=="/api/config":
            return {"ok":True,"data":{k:cfg.get(k) for k in
                    CFG_KEYS+("school_name","school_id","devicename","deviceid")}}
        if path=="/api/task_points":
            card=api.task_card()
            pts=[]
            if card and card.get("points"):
                for s0 in card["points"]:
                    if s0:
                        a=s0.split(","); pts.append([float(a[0]),float(a[1])])
            if not pts: pts=[list(c) for c in CHECKPOINTS]
            return {"ok":True,"data":pts}
        if path=="/api/home":
            card=api.task_card()
            return {"ok":True,"data":card}
        if path=="/api/track":
            pts=build_track(float(cfg["dist_km"]),int(cfg["duration_s"]),
                            int(cfg["n_points"]),(117.5966,31.6083),
                            cfg.get("route","loop"),True)
            xy=[[float(p["point"].split(",")[0]),float(p["point"].split(",")[1])] for p in pts]
            return {"ok":True,"data":xy,"cps":[list(c) for c in CHECKPOINTS]}
        if path=="/api/run":
            if not fire_run(): return {"ok":False,"error":"已有任务在执行"}
            return {"ok":True}
        if path=="/api/login":
            for k in ("username","password","token"):
                if b.get(k): cfg[k]=b[k]
            save_cfg(cfg)
            r=api.app_login()
            code=r.get("code") if isinstance(r,dict) else None
            return {"ok":code==200,"data":r if code==200 else None,
                    "error":None if code==200 else (r.get("msg") if isinstance(r,dict) else str(r))}
        if path=="/api/schools":
            return {"ok":True,"data":api.list_schools()}
        if path in ("/api/pick_school","/api/random_school"):
            row=api.pick_school(b.get("code") if path=="/api/pick_school" else None)
            if not row: return {"ok":False,"error":"未找到学校"}
            return {"ok":True,"data":{"school_name":cfg["school_name"],"school_id":cfg["school_id"]}}
        if path=="/api/device/random":
            d=api.randomize_device()
            return {"ok":True,"data":{"name":d[1],"id":d[0]}}
        if path=="/api/timer":
            for k in ("timer_on","timer_hh","timer_mm","timer_days"):
                if k in b: cfg[k]=b[k]
            save_cfg(cfg)
            return {"ok":True}
        if path=="/api/history":
            out={}
            for fn,name in [(api.history_list,"history"),(api.my_run_info,"summary"),
                            (api.score_list,"score"),(api.xn_list,"term")]:
                try: out[name]=fn()
                except Exception as e: out[name]=f"ERR {e}"
            return {"ok":True,"data":out}


        if path=="/api/accounts":
            return {"ok":True,"data":cfg.get("accounts") or []}
        if path=="/api/account_add":
            u=str(b.get("username") or "").strip()
            if not u: return {"ok":False,"error":"用户名不能为空"}
            accs=cfg.get("accounts") or []
            if any(a.get("username")==u for a in accs):
                return {"ok":False,"error":"账号已存在"}
            acc={"username":u,"password":str(b.get("password") or ""),
                 "school_id":str(b.get("school_id") or cfg.get("school_id") or "100"),
                 "school_url":b.get("school_url") or cfg.get("school_url") or "",
                 "school_name":b.get("school_name") or cfg.get("school_name") or "",
                 "token":""}
            accs.append(acc); cfg["accounts"]=accs; save_cfg(cfg)
            return {"ok":True,"data":accs}
        if path=="/api/account_update":
            u=str(b.get("username") or "")
            accs=cfg.get("accounts") or []
            hit=False
            for a in accs:
                if a.get("username")==u:
                    for k in ("password","school_id","school_url","school_name","token"):
                        if k in b: a[k]=b[k]
                    hit=True
            if not hit: return {"ok":False,"error":"账号不存在"}
            cfg["accounts"]=accs; save_cfg(cfg)
            return {"ok":True,"data":accs}
        if path=="/api/account_del":
            u=str(b.get("username") or "")
            accs=[a for a in (cfg.get("accounts") or []) if a.get("username")!=u]
            cfg["accounts"]=accs; save_cfg(cfg)
            return {"ok":True,"data":accs}
        if path=="/api/account_login":
            u=str(b.get("username") or "")
            accs=cfg.get("accounts") or []
            acc=next((a for a in accs if a.get("username")==u), None)
            if not acc: return {"ok":False,"error":"账号不存在"}
            # 临时切换上下文登录
            old=dict(cfg)
            try:
                cfg["username"]=acc.get("username"); cfg["password"]=acc.get("password")
                cfg["school_id"]=acc.get("school_id") or cfg.get("school_id")
                if acc.get("school_url"): cfg["school_url"]=acc.get("school_url")
                r=api.app_login()
                code=r.get("code") if isinstance(r,dict) else None
                tok=(r.get("data") or {}).get("token") if isinstance(r,dict) else None
                if tok:
                    acc["token"]=tok; cfg["accounts"]=accs
                    cfg["username"]=old.get("username"); cfg["password"]=old.get("password")
                    cfg["school_id"]=old.get("school_id"); cfg["school_url"]=old.get("school_url")
                    cfg["token"]=old.get("token")
                    save_cfg(cfg)
                return {"ok":code==200,"data":{"username":u,"token":tok} if tok else None,
                        "error":None if code==200 else (r.get("msg") if isinstance(r,dict) else str(r))}
            finally:
                pass
        if path=="/api/batch_run":
            accs=cfg.get("accounts") or []
            if not accs: return {"ok":False,"error":"无多账户，请先添加"}
            if state.get("running"): return {"ok":False,"error":"已有任务在执行"}
            def batch_job():
                state["running"]=True; state["last"]="BATCH"
                old=dict(cfg)
                results=[]
                for i,acc in enumerate(accs,1):
                    try:
                        cfg["username"]=acc.get("username") or ""
                        cfg["password"]=acc.get("password") or ""
                        cfg["school_id"]=acc.get("school_id") or old.get("school_id")
                        if acc.get("school_url"): cfg["school_url"]=acc["school_url"]
                        if acc.get("token"): cfg["token"]=acc["token"]
                        wlog(f"[BATCH {i}/{len(accs)}] {acc.get('username')} 登录…")
                        lr=api.app_login()
                        code=lr.get("code") if isinstance(lr,dict) else None
                        if code!=200:
                            wlog(f"[BATCH {i}] 登录失败 {lr}")
                            results.append({"user":acc.get("username"),"ok":False,"msg":"login fail"}); continue
                        def onp(ii,nn,chunk):
                            wlog(f"[BATCH {i}] 轨迹 {ii}/{nn} mile={chunk[-1]['runMileage']}")
                        r=api.run_full(float(cfg.get("dist_km") or 3.0),
                                       int(cfg.get("duration_s") or 840),
                                       int(cfg.get("n_points") or 50),
                                       int(cfg.get("marks") or 5),
                                       cfg.get("route","loop"),True,onp,False)
                        ok=isinstance(r,dict) and r.get("code")==200
                        msg=(r.get("finish") or {}).get("msg") if isinstance(r,dict) else str(r)
                        wlog(f"[BATCH {i}] {acc.get('username')} {'DONE' if ok else 'FAIL'} {msg}")
                        results.append({"user":acc.get("username"),"ok":ok,"msg":msg,"recordId":r.get("recordId") if isinstance(r,dict) else None})
                    except Exception as e:
                        wlog(f"[BATCH {i}] ERR {e}")
                        results.append({"user":acc.get("username"),"ok":False,"msg":str(e)})
                # 恢复主上下文
                for k in ("username","password","school_id","school_url","token"):
                    if k in old: cfg[k]=old[k]
                save_cfg(cfg)
                n_ok=sum(1 for x in results if x.get("ok"))
                wlog(f"[BATCH] 完成 {n_ok}/{len(results)} 成功")
                state["last"]="BATCH_DONE"
                state["running"]=False
            threading.Thread(target=batch_job,daemon=True).start()
            return {"ok":True}

        if path=="/api/history_points":
            rid=str(b.get("id") or "")
            if not rid: return {"ok":False,"error":"缺 id"}
            try:
                info=api.history_info(rid)
                pts=(info.get("data") or {}).get("pointsList") or []
                meta=(info.get("data") or {})
                xy=[]
                for pt in pts:
                    a=str(pt.get("point","")).split(",")
                    if len(a)>=2:
                        xy.append({
                            "lon":float(a[0]),"lat":float(a[1]),
                            "speed":float(pt.get("speed") or 0),
                            "runTime":pt.get("runTime"),
                            "runMileage":pt.get("runMileage"),
                            "ts":pt.get("ts"),
                            "isFence":pt.get("isFence","Y"),
                            "runStatus":pt.get("runStatus",1),
                        })
                return {"ok":True,"data":{"id":rid,"n":len(xy),"points":xy,
                        "mileage":meta.get("recordMileage"),
                        "pace":meta.get("recodePace"),
                        "duration":meta.get("duration"),
                        "startTime":meta.get("recordStartTime"),
                        "endTime":meta.get("recordEndTime")}}
            except Exception as e:
                return {"ok":False,"error":str(e)}
        if path=="/api/replay":
            rid=str(b.get("id") or "")
            if not rid: return {"ok":False,"error":"缺 id"}
            if state.get("running"): return {"ok":False,"error":"已有任务在执行"}
            def replay_job():
                state["running"]=True; state["last"]="REPLAY"
                try:
                    info=api.history_info(rid)
                    meta=info.get("data") or {}
                    pts=meta.get("pointsList") or []
                    if not pts:
                        wlog("REPLAY FAIL 该记录无轨迹点"); state["last"]="FAIL"; return
                    card=api.task_card()
                    st=api.run_start({"raRunArea":card["raRunArea"],"raType":card["raType"],"raId":card["raId"]})
                    if not (isinstance(st,dict) and st.get("code")==200):
                        wlog("REPLAY FAIL start "+str(st)[:120]); state["last"]="FAIL"; return
                    rec_id=st["data"]["id"]; rec_start=st["data"].get("recordStartTime","")
                    student=st["data"].get("studentId",cfg.get("username",""))
                    # 按原始 pointsList 逐 10 点 split
                    raw=[]
                    for pt in pts:
                        raw.append({
                            "point":str(pt.get("point","")),
                            "runStatus":"1",
                            "speed":str(pt.get("speed") or "5.00"),
                            "isFence":"Y","isMock":False,
                            "runMileage":str(pt.get("runMileage") or "0"),
                            "runTime":str(pt.get("runTime") or "0"),
                            "ts":str(pt.get("ts") or int(time.time())),
                        })
                    meta_s={"crsRunRecordId":rec_id,"schoolId":card.get("schoolId",100),
                            "userName":student,"strides":float(cfg.get("strides",0.8) or 0.8),
                            "speeds":str(meta.get("recodePace") or cfg.get("pace") or 5.5),
                            "cad":int(cfg.get("cadence",170) or 170)}
                    n=len(raw)
                    for i in range(0,n,10):
                        chunk=raw[i:i+10]
                        if len(chunk)<2: continue
                        api.split(chunk,meta_s)
                        wlog(f"REPLAY split {min(i+10,n)}/{n} mile={chunk[-1]['runMileage']}")
                        time.sleep(0.6)
                    # manageList：尽量用原记录的
                    mg=meta.get("manageList") or []
                    if not mg:
                        cps=[]
                        for s0 in (card.get("points") or []):
                            if s0:
                                a=s0.split(","); cps.append((float(a[0]),float(a[1])))
                        ys=[0,1,2,3,5][:max(3,int(cfg.get("marks",5) or 5))]
                        mg=[{"point":f"{c[0]},{c[1]}","marked":"Y" if i in ys else "N",
                             "index":str(i) if i in ys else ""} for i,c in enumerate(cps)]
                    dist=float(meta.get("recordMileage") or cfg.get("dist_km") or 3.0)
                    dur=int(meta.get("duration") or cfg.get("duration_s") or 840)
                    fin=api.finish({
                        "recordMileage":f"{dist:.2f}",
                        "recodeCadence":str(int(cfg.get("cadence",170) or 170)),
                        "recodePace":str(meta.get("recodePace") or cfg.get("pace") or 5.5),
                        "deviceName":cfg.get("devicename","iPhone 16 Pro"),
                        "sysEdition":"26.6","appEdition":"3.6.6",
                        "raIsStartPoint":"Y","raIsEndPoint":"Y",
                        "raRunArea":card.get("raRunArea",""),
                        "recodeDislikes":str(int(cfg.get("marks",5) or 5)),
                        "raId":str(card.get("raId","")),"raType":card.get("raType",""),
                        "id":str(rec_id),"duration":str(dur),
                        "recordStartTime":rec_start,"manageList":mg,"remake":"1"})
                    msg=fin.get("msg") if isinstance(fin,dict) else str(fin)
                    wlog(f"REPLAY DONE record={rec_id} {msg}")
                    state["last"]="DONE"
                except Exception as e:
                    wlog(f"REPLAY FAIL {e}"); state["last"]="FAIL"
                finally:
                    state["running"]=False
            threading.Thread(target=replay_job,daemon=True).start()
            return {"ok":True}

        if path=="/api/news":
            out={}
            for fn,name in [(api.home_list,"home"),(api.news,"news"),
                            (api.popup,"popup"),(api.questions,"survey")]:
                try: out[name]=fn()
                except Exception as e: out[name]=f"ERR {e}"
            return {"ok":True,"data":out}
        # 通用配置写入
        changed=False
        for k in CFG_KEYS:
            if k in b: cfg[k]=b[k]; changed=True
        if changed: save_cfg(cfg)
        return {"ok":True}

    TILE_DIR=HERE/"map_tiles"
    TILE_HOSTS=["https://webrd01.is.autonavi.com","https://webrd02.is.autonavi.com",
                "https://webrd03.is.autonavi.com","https://webrd04.is.autonavi.com"]
    def serve_tile(h,z,x,y):
        f=TILE_DIR/str(z)/str(x)/(str(y)+".png")
        if not f.exists():
            f.parent.mkdir(parents=True,exist_ok=True)
            url=(f"{random.choice(TILE_HOSTS)}/appmaptile?lang=zh_cn&size=1&scale=1"
                 f"&style=8&x={x}&y={y}&z={z}")
            try:
                req=urllib.request.Request(url,headers={
                    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Referer":"https://www.amap.com/"})
                data=urllib.request.urlopen(req,timeout=8).read()
                if data[:4]!=b"\x89PNG": raise ValueError("not png")
                f.write_bytes(data)
            except Exception:
                h.send_response(502)
                h.send_header("Content-Length","0"); h.end_headers(); return
        data=f.read_bytes()
        h.send_response(200)
        h.send_header("Content-Type","image/png")
        h.send_header("Cache-Control","public, max-age=86400")
        h.send_header("Content-Length",str(len(data)))
        h.end_headers(); h.wfile.write(data)

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def _json(self,obj,code=200):
            data=json.dumps(obj,ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(data)))
            self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            u=urllib.parse.urlparse(self.path)
            if u.path.startswith("/tiles/"):
                try:
                    _,_,z,x,yf=u.path.split("/")
                    z,x,y=int(z),int(x),int(yf.split(".")[0])
                    if not (3<=z<=18): raise ValueError
                except Exception:
                    self._json({"error":"bad tile"},400); return
                serve_tile(self,z,x,y); return
            if u.path in ("/","/index.html"):
                data=WEB_HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length",str(len(data)))
                self.end_headers(); self.wfile.write(data)
            elif u.path=="/api/logs":
                qs=urllib.parse.parse_qs(u.query)
                after=int(qs.get("after",[0])[0] or 0)
                with wlog.lock:
                    lines=wlog.buf[after:]; n=len(wlog.buf)
                self._json({"lines":lines,"next":n,"running":state["running"],"last":state["last"]})
            else:
                self._json({"error":"not found"},404)
        def do_POST(self):
            u=urllib.parse.urlparse(self.path)
            try:
                ln=int(self.headers.get("Content-Length") or 0)
                body=json.loads(self.rfile.read(ln) or b"{}")
            except Exception:
                body={}
            try:
                r=_route(u.path,body)
            except Exception as e:
                r={"ok":False,"error":str(e)}
            self._json(r if isinstance(r,dict) else {"ok":True,"data":r})

    httpd=None
    for port in range(17653,17670):
        try:
            httpd=http.server.ThreadingHTTPServer(("127.0.0.1",port),H)
            break
        except OSError:
            continue
    if not httpd:
        print("!! 无可用端口 (17653-17669)"); return
    url=f"http://127.0.0.1:{port}/"
    wlog(f"[BOOT] DEV CONSOLE 启动 @ {url}")
    wlog(f"[BOOT] 学校 {cfg.get('school_name')} · 设备 {cfg.get('devicename')}")
    threading.Timer(0.6,lambda:webbrowser.open(url)).start()
    threading.Thread(target=cron_loop,daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__=="__main__":
    if len(sys.argv)>1:
        cli_main()
    else:
        cfg=load_cfg(); api=API(cfg,print); run_gui(cfg,api)
