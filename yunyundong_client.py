#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云运动 / LePao 3.6.6 全功能 API 客户端（覆盖主程序接口表）.

加密（E13 已实测合格成绩）：
  content = base64(SM4-ECB-PKCS7(json))，空串=无载荷
  cipherKey = 固定 SM2 密文（仓库默认，服务端不校验来源）
  splitPointCheating / splitPointBreakpoint: 先 gzip(json) 再 SM4
  响应 = gzip → JSON字符串(b64) → SM4 解密 →（个别 gunzip）→ dict
sign = md5("platform=ios&utc=..&uuid=..&appsecret=0h1UIfMDSc7piesRINRXXfkE")  # E16 来自 IPA
"""
from __future__ import annotations

import base64, gzip, hashlib, json, random, time, uuid as uuidlib, urllib.request, urllib.error
from typing import Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sm4_std import ecb_encrypt, ecb_decrypt

# ===== 常量（IPA / 仓库实测）=====
SM4_KEY = base64.b64decode("JXhWGZjmhhXN+nt8nLpNxA==")
CIPHER_KEY = (
    "BGfbsG9EkXz5KeCva8E0MisBeS6bhBEDId3VXeIuBoiBMZU0Mosv7PqKsvqxZ3PjkUlsjzh09Se629SWW45XP4TIUeXoLpYzgk5fAMbg0VNVnXuLH9xVzdHAeM+1qJrgvwwkwio85/DnrP1aArvVQrw3N4xd5tugqQ=="
)
APPSECRET = "0h1UIfMDSc7piesRINRXXfkE"          # E16 IPA 格式串
MD5KEY_REPO = "pie0hDSfMRINRXc7s1UIXfkE"          # 仓库 3.4.7，备用
BASE = "http://192.0.2.10:8000/m-api"
SPORTS_BASE = "https://sports.aiyyd.com:9011/api/app"
DEVICE_ID = "00000000-0000-0000-0000-000000000000"
DEVICE_NAME = "iPhone 16 Pro"
UA = "LePao/3.6.6 (iPhone; iOS 26.6; Scale/3.00)"
SYS_EDITION = "26.6"
APP_EDITION = "3.6.6"
PLATFORM = "ios"
TOKEN = "00000000-0000-0000-0000-000000000000"
SCHOOL_ID = "100"
USER_NAME = "20230000001"


def getsign(utc: str, u: str, appsecret: str = APPSECRET) -> str:
    sb = f"platform={PLATFORM}&utc={utc}&uuid={u}&appsecret={appsecret}"
    return hashlib.md5(sb.encode()).hexdigest()


def _enc(data: str | bytes | dict | None, gz: bool = False) -> str:
    if data is None or data == "":
        return ""
    if isinstance(data, dict):
        data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    if not raw:
        return ""
    if gz:
        raw = gzip.compress(raw)
    return base64.b64encode(ecb_encrypt(SM4_KEY, raw)).decode()


def _dec(raw: bytes) -> Any:
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
    pt = ecb_decrypt(SM4_KEY, base64.b64decode(b64))
    try:
        return json.loads(pt.decode("utf-8"))
    except Exception:
        try:
            return json.loads(gzip.decompress(pt).decode("utf-8"))
        except Exception:
            try:
                return pt.decode("utf-8")
            except Exception:
                return pt[:200]


class YunAPI:
    def __init__(self, token: str = TOKEN, base: str = BASE, school_id: str = SCHOOL_ID):
        self.token = token
        self.base = base
        self.school_id = school_id
        self.student_id = USER_NAME

    # ---- 底层 ----
    def call(self, path: str, payload: Any = "", gz: bool = False,
             host: Optional[str] = None, timeout: int = 30) -> Any:
        body = {"cipherKey": CIPHER_KEY, "content": _enc(payload, gz=gz)}
        u = str(uuidlib.uuid4()).upper()
        utc = str(int(time.time()))
        url = (host or self.base) + (path if path.startswith("/") else "/" + path)
        headers = {
            "deviceid": DEVICE_ID, "user-agent": UA, "sysversion": SYS_EDITION,
            "content-type": "application/json", "version": APP_EDITION, "isapp": "app",
            "token": self.token, "accept-encoding": "gzip, deflate", "accept": "*/*",
            "devicename": DEVICE_NAME, "platform": PLATFORM, "uuid": u,
            "sign": getsign(utc, u), "utc": utc,
        }
        req = urllib.request.Request(
            url, data=json.dumps(body, separators=(",", ":")).encode(),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _dec(resp.read())
        except urllib.error.HTTPError as e:
            return _dec(e.read()) if e.fp else {"code": e.code, "msg": str(e)}

    def _p(self, prefix: str, name: str, payload: Any = "", **kw) -> Any:
        return self.call(f"/{prefix}/{name}", payload, **kw)

    # ================= 登录 / 用户 =================
    def app_login(self, username: str, password: str, school_id: Optional[str] = None):
        """login/appLogin — 账号密码登录，返回 token（登录后替换 self.token）."""
        r = self._p("login", "appLogin", {
            "username": username, "password": password,
            "schoolId": school_id or self.school_id,
        })
        if isinstance(r, dict) and r.get("code") == 200 and isinstance(r.get("data"), dict):
            tok = r["data"].get("token")
            if tok:
                self.token = tok
        return r

    def get_student_info(self):
        return self._p("login", "getStudentInfo")

    def update_user(self, **fields):
        return self._p("login", "updateUser", fields)

    def perfect_info(self, **fields):
        return self._p("login", "perfectInfo", fields)

    def sign_out(self):
        return self._p("login", "signOut")

    def get_ver_code(self, phone: str = ""):
        return self._p("login", "getVerCode", {"phone": phone})

    def get_ver_phone_code(self, phone: str = ""):
        return self._p("login", "getVerPhoneCode", {"phone": phone})

    def ver_password(self, **fields):
        return self._p("login", "verPassword", fields)

    def user_check(self, **fields):
        return self._p("login", "userCheck", fields)

    def third_party_login(self, sname: str, open_id: str, icon: str = "",
                          typ: str = "wechat", gender: str = "1"):
        return self._p("login", "thirdPartyLogin", {
            "sname": sname, "openId": open_id, "icon": icon, "type": typ, "gender": gender,
        })

    def gesture_login(self, pwd: str = ""):
        return self._p("login", "gestureLogin", {"gesturePassword": pwd})

    def gesture_switch(self, enable: bool = True):
        return self._p("login", "gestureSwitch", {"status": "Y" if enable else "N"})

    def get_list_camp_tree(self):
        """校区树 / 学校列表."""
        return self._p("login", "getListCampTree")

    def get_gd_map(self):
        return self._p("login", "getGDMap")

    def get_stu_qr_code(self):
        return self._p("login", "getStuQrCodeInfo")

    def apply_auth(self, **fields):
        return self._p("login", "applyAuth", fields)

    # ================= 跑步 =================
    def get_home_run_info(self):
        return self._p("run", "getHomeRunInfo")

    def run_start(self, ra_run_area: str, ra_type: str, ra_id):
        r = self._p("run", "start", {
            "raRunArea": ra_run_area, "raType": ra_type, "raId": ra_id,
        })
        return r

    def split_point_cheating(self, points: list, meta: dict):
        """10 点一组；内部 gzip."""
        body = {
            "StepNumber": int(float(points[-1]["runMileage"]) - float(points[0]["runMileage"])) / meta.get("strides", 0.8),
            "a": 0, "b": None, "c": None,
            "mileage": float(points[-1]["runMileage"]) - float(points[0]["runMileage"]),
            "orientationNum": 0,
            "runSteps": random.uniform(meta.get("cadence_min", 160), meta.get("cadence_max", 180)),
            "cardPointList": points,
            "simulateNum": 0,
            "time": float(points[-1]["runTime"]) - float(points[0]["runTime"]),
            "crsRunRecordId": meta["crsRunRecordId"],
            "speeds": meta.get("speeds", "5.50"),
            "schoolId": meta.get("schoolId", self.school_id),
            "strides": meta.get("strides", 0.8),
            "userName": meta.get("userName", self.student_id),
        }
        return self._p("run", "splitPointCheating", body, gz=True)

    def split_point_breakpoint(self, body: dict):
        """断点续传分段（同样 gzip）."""
        return self._p("run", "splitPointBreakpoint", body, gz=True)

    def run_finish(self, payload: dict):
        return self._p("run", "finish", payload)

    def is_standard(self, payload: dict):
        return self._p("run", "isStandard", payload)

    def goon_after_standard(self, payload: dict = ""):
        return self._p("run", "goonAfterStandard", payload)

    def pause_or_goon(self, status: str = "pause"):
        return self._p("run", "pauseOrGoon", {"status": status})

    def get_run_start_remake(self, task_id: str = ""):
        return self._p("run", "getRunStartRemake", {"taskId": task_id} if task_id else {})

    def get_is_point_breakpoint(self):
        return self._p("run", "getIsPointBreakpoint")

    def refresh_time(self):
        return self._p("run", "refreshTime")

    def get_rank(self, **fields):
        return self._p("run", "getRank", fields)

    def rank(self, **fields):
        return self._p("run", "rank", fields)

    def get_rank_name_list(self):
        return self._p("run", "getRankNameList")

    def get_rl_status(self):
        return self._p("run", "getRlStatus")

    def runscore(self):
        return self._p("run", "runscore")

    def run_score_list_by_code(self, code: str = ""):
        return self._p("run", "runScoreListByCode", {"code": code})

    def crs_reocord_info_list(self, table_name: str = f"crs_run_record{SCHOOL_ID}"):
        return self._p("run", "crsReocordInfoList", {"tableName": table_name})

    def crs_reocord_info(self, rid: str, table_name: str = f"crs_run_record{SCHOOL_ID}"):
        return self._p("run", "crsReocordInfo", {"id": rid, "tableName": table_name})

    def list_xn_year_xq(self):
        return self._p("run", "listXnYearXqByStudentId")

    def my_info_crs_run_info(self):
        return self._p("run", "myInfoCrsRunInfo")

    def crs_is_moring_reocord_info(self):
        return self._p("run", "crsIsMoringReocordInfo")

    def run_task(self):
        return self._p("run", "task")

    def delete_crs_run_record(self, rid: str):
        return self._p("run", "deleteCrsRunRecordById", {"id": rid})

    def add_record_appeal(self, **fields):
        return self._p("run", "addRecordAppeal", fields)

    def record_appeal_list(self):
        return self._p("run", "recordAppealList")

    def run_face_info(self, **fields):
        return self._p("run", "appFace/runFaceInfo", fields)

    def run_face_info_comparison(self, **fields):
        return self._p("run", "appFace/runFaceInfoComparison", fields)

    # ================= 跑步免跑 / 教师 =================
    def avoid_info(self):
        return self._p("runAvoid", "avoidInfo")

    def crs_run_avoid_list(self):
        return self._p("runAvoid", "crsRunAvoidList")

    def crs_run_avoid_save(self, **fields):
        return self._p("runAvoid", "crsRunAvoidSave", fields)

    def audit_run_avoid(self, **fields):
        return self._p("runAvoid", "auditRunAvoid", fields)

    def teacher_run_avoid_list(self):
        return self._p("runAvoid", "teacherRunAvoidList")

    def run_teacher_stud_run_info_list(self, **fields):
        return self._p("runTeacher", "studRunInfoList", fields)

    def run_teacher_record(self, **fields):
        return self._p("runTeacher", "crsReocordInfo", fields)

    # ================= 成绩 / 学业 =================
    def score_list(self, **fields):
        return self._p("score", "list", fields)

    def my_score_info_list(self):
        return self._p("achievementApi", "myScoreInfoList")

    def achievement_manager(self):
        return self._p("achievementApi", "achievementManager")

    def achievement_stud_list(self, **fields):
        return self._p("achievementApi", "achievementStudList", fields)

    def xn_list(self):
        return self._p("achievementApi", "xnList")

    def sjfx(self, **fields):
        return self._p("achievementApi", "sjfx", fields)

    # ================= 首页 / 资讯 / 消息 =================
    def home_page_list(self):
        return self._p("homePageApi", "list")

    def home_page_detail(self, **fields):
        return self._p("homePageApi", "getDetail", fields)

    def home_msg_list(self):
        return self._p("homePageApi", "msg/list")

    def home_msg_popup(self):
        return self._p("homePageApi", "msg/isPopupList")

    def home_teacher_list(self):
        return self._p("homePageApi", "teacherList")

    def app_news_list(self):
        return self._p("appNewsApi", "list")

    def get_have_read_num(self):
        return self._p("AppSysMsgApi", "getHaveReadNum")

    # ================= 问卷 =================
    def question_list(self):
        return self._p("questionNaire", "getQuestionList")

    def question_detail(self, **fields):
        return self._p("questionNaire", "questionDetail", fields)

    def question_insert(self, answers: list):
        return self._p("questionNaire", "questionInsertList", answers)

    # ================= AI 体测 =================
    def ai_list_task(self):
        return self._p("aiSport/student", "listTask")

    def ai_task_info(self, **fields):
        return self._p("aiSport/student", "taskInfo", fields)

    def ai_task_start_preview(self, **fields):
        return self._p("aiSport/student", "taskStartPreview", fields)

    def ai_task_start(self, **fields):
        return self._p("aiSport/student", "taskStart", fields)

    def ai_task_finish(self, **fields):
        return self._p("aiSport/student", "taskFinish", fields)

    def ai_task_img_upload(self, img_b64: str, **fields):
        return self._p("aiSport/student", "taskImgUpload", {"img": img_b64, **fields})

    def ai_list_record(self):
        return self._p("aiSport/student", "listRecord")

    def ai_list_record_ranking(self, **fields):
        return self._p("aiSport/student", "listRecordRanking", fields)

    # ================= 课程 / 选课 =================
    def course_stud_my_list(self):
        return self._p("course", "studMyCourseListDateList")

    def course_get_by_id(self, cid: str):
        return self._p("course", "getById", {"id": cid})

    def course_sort_list(self):
        return self._p("course", "courseSortList")

    def course_save_my(self, cid: str):
        return self._p("course", "saveMyCourse", {"courseId": cid})

    def course_del_my(self, cid: str):
        return self._p("course", "delMyCourse", {"courseId": cid})

    def sel_course_list(self):
        return self._p("selCourse", "selectCourseList/v2")

    def sel_course_submit(self, **fields):
        return self._p("selCourse", "submitSelectCourseInfo/v2", fields)

    def sel_course_sign_in(self, **fields):
        return self._p("selCourse", "clickSignInStud", fields)

    # ================= 体测预约 / 场馆 =================
    def venue_home(self):
        return self._p("venue", "venueHomPage")

    def venue_info_list(self):
        return self._p("venue", "getVenueInfoList")

    def venue_field(self, **fields):
        return self._p("venue", "getVenueField", fields)

    def venue_time_list(self, venue_id: str, day: str = ""):
        return self._p("venue", "getTimeListByVenueId", {"venueId": venue_id, "date": day})

    def venue_submit_appointment(self, **fields):
        return self._p("venue", "submitAppointment", fields)

    def venue_my_appointment(self):
        return self._p("venue", "myAppointmentList")

    def venue_appointment_cancel(self, aid: str):
        return self._p("venue", "appointmentCancel", {"id": aid})

    def venue_sign_submit(self, **fields):
        return self._p("venue", "VenueSignSubmit", fields)

    def pt_plan_list(self):
        return self._p("pt/Reservation", "planListReservation")

    def pt_save_plan(self, **fields):
        return self._p("pt/Reservation", "savePlanByStu", fields)

    def pt_my_score(self):
        return self._p("pt", "myScoreInfo")

    def pt_my_score_list(self):
        return self._p("pt", "myScoreList")

    # ================= 社团 =================
    def club_list(self):
        return self._p("studClub", "clubList")

    def club_info(self, cid: str):
        return self._p("studClub", "clubInfoById", {"id": cid})

    def club_apply(self, cid: str, **fields):
        return self._p("studClub", "applyQuestionsByClubId", {"clubId": cid, **fields})

    def my_apply_club(self):
        return self._p("studClub", "myApplyClubList")

    def club_sign_in(self, **fields):
        return self._p("studClub", "clickSignInStud", fields)

    # ================= 考试 =================
    def exam_list(self):
        return self._p("studExam", "examList")

    def exam_questions(self, eid: str):
        return self._p("studExam", "examQuestionsList", {"examId": eid})

    def exam_commit(self, eid: str, answers: list):
        return self._p("studExam", "examCommit", {"examId": eid, "answers": answers})

    def exam_score(self, eid: str):
        return self._p("studExam", "examStudentScore", {"examId": eid})

    # ================= 社区 / 评论 =================
    def community_list(self, **fields):
        return self._p("community", "AppList", fields)

    def community_add(self, **fields):
        return self._p("community", "add", fields)

    def community_like(self, cid: str):
        return self._p("community", "likeAdd", {"id": cid})

    def community_comment(self, cid: str, content: str):
        return self._p("community", "commentAdd", {"id": cid, "content": content})

    def yunzhi_comment_list(self, **fields):
        return self._p("yunzhiComment", "list", fields)

    def yunzhi_comment_save(self, **fields):
        return self._p("yunzhiComment", "save", fields)

    # ================= 签到 =================
    def yunzhi_sign_list(self):
        return self._p("yunzhiSign", "list")

    def yunzhi_sign_save(self, **fields):
        return self._p("yunzhiSign", "saveOrUpdate", fields)

    def yunzhi_clock_area(self):
        return self._p("yunzhiClockArea", "list")

    # ================= 意见反馈 =================
    def feedback_save(self, content: str, typ: str = "1"):
        return self._p("feedback", "save", {"content": content, "type": typ})

    def feedback_complaint_add(self, **fields):
        return self._p("feedback/complaint", "add", fields)

    def feedback_complaint_list(self):
        return self._p("feedback/complaint", "list")

    # ================= 赛事 =================
    def match_list(self):
        return self._p("appMatchApi", "list")

    def match_detail(self, mid: str):
        return self._p("appMatchApi", "matchById", {"id": mid})

    def match_enroll(self, mid: str, **fields):
        return self._p("appMatchApi", "saveMatchsEnroll", {"matchId": mid, **fields})

    # ================= 资源 / 文件 =================
    def dfs_upload_pub(self, file_b64: str, name: str = "a.jpg"):
        return self._p("dfs", "uploadPub", {"file": file_b64, "fileName": name})


# ================= 合格跑步（E15 复用） =================
CHECKPOINTS = [
    (117.596597, 31.608729), (117.596941, 31.608327),
    (117.597305, 31.607937), (117.596005, 31.608317),
    (117.596259, 31.608032), (117.596523, 31.607543),
]
MARK_Y = [0, 1, 2, 3, 5]


def synth_points(n=50, dist_km=3.0, duration_s=840, origin=(117.5966, 31.6083)):
    pts, ts0 = [], int(time.time()) - duration_s
    for i in range(n):
        t = i / (n - 1)
        lon = origin[0] + 0.002 * t * (dist_km / 2.2) * (1 if i % 2 == 0 else -1) * 0.3 + 0.0008 * t
        lat = origin[1] + 0.0015 * t * (dist_km / 2.2) * (1 if i % 3 == 0 else -1) * 0.3 + 0.0005 * t
        mile = dist_km * 1000 * (i + 1) / n
        sec = int(duration_s * (i + 1) / n)
        pts.append({
            "point": f"{lon:.8f},{lat:.8f}", "runStatus": "1",
            "speed": f"{random.uniform(4.6, 5.2):.2f}", "isFence": "Y", "isMock": False,
            "runMileage": f"{mile:.4f}", "runTime": f"{sec}", "ts": str(ts0 + sec),
        })
    return pts


def run_qualified(api: YunAPI, dist_km=3.0, duration_s=840, n_pts=50):
    home = api.get_home_run_info()
    info = home["data"]["cralist"][0]
    start = api.run_start(info["raRunArea"], info["raType"], info["id"])
    if start.get("code") != 200:
        return {"stage": "start", "resp": start}
    rec_id = start["data"]["id"]
    rec_start = start["data"].get("recordStartTime", "")
    student = start["data"].get("studentId", "")
    meta = {"crsRunRecordId": rec_id, "schoolId": info.get("schoolId", 100),
            "userName": student, "strides": 0.8, "speeds": "5.50",
            "cadence_min": 170, "cadence_max": 175}
    pts = synth_points(n_pts, dist_km, duration_s)
    splits = []
    for i in range(0, len(pts), 10):
        chunk = pts[i:i + 10]
        if len(chunk) >= 2:
            splits.append(api.split_point_cheating(chunk, meta))
            time.sleep(1.2)
    pace = round(duration_s / 60 / dist_km, 2)
    mg = [{"point": f"{lon},{lat}", "marked": "Y" if i in MARK_Y else "N",
           "index": str(i if i in MARK_Y else "")}
          for i, (lon, lat) in enumerate(CHECKPOINTS)]
    fin = api.run_finish({
        "recordMileage": f"{dist_km:.2f}", "recodeCadence": "170",
        "recodePace": f"{pace:.2f}", "deviceName": DEVICE_NAME,
        "sysEdition": SYS_EDITION, "appEdition": APP_EDITION,
        "raIsStartPoint": "Y", "raIsEndPoint": "Y",
        "raRunArea": info["raRunArea"], "recodeDislikes": str(len(MARK_Y)),
        "raId": str(info["id"]), "raType": info["raType"], "id": str(rec_id),
        "duration": str(duration_s), "recordStartTime": rec_start,
        "manageList": mg, "remake": "1",
    })
    return {"recordId": rec_id, "finish": fin, "splits": splits, "student": student}


if __name__ == "__main__":
    api = YunAPI()
    print("== student ==")
    print(json.dumps(api.get_student_info(), ensure_ascii=False)[:240])
    print("\n== home run ==")
    home = api.get_home_run_info()
    print(json.dumps(home, ensure_ascii=False)[:240])
    print("\n== score ==")
    print(json.dumps(api.score_list(), ensure_ascii=False)[:200])
    print("\n== news ==")
    print(json.dumps(api.app_news_list(), ensure_ascii=False)[:200])
    print("\n== history ==")
    print(json.dumps(api.crs_reocord_info_list(), ensure_ascii=False)[:240])
    print("\n== rank ==")
    print(json.dumps(api.get_rank(), ensure_ascii=False)[:200])
    print("\n== runscore ==")
    print(json.dumps(api.runscore(), ensure_ascii=False)[:200])
