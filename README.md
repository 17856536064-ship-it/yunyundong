# 云运动 · yunyundong

云运动 / LePao **3.6.6** 协议完整复现 + 自动跑步客户端。

> 仅供学习交流。使用者自负一切责任。

## 功能

- **协议完整复现**：SM4-ECB + SM2 包 SM4（cipherKey）+ MD5 sign
- **一键跑步**：打表 / 快速 / 真实 GPS 轨迹 + 漂移
- **历史轨迹复现**：选一次历史跑步，按原轨迹点完整重放
- **多账户批量**：批量账号管理，一键批量跑
- **任务卡**：里程/时段/配速/晨跑规则/今日进度
- **学校切换**：90+ 学校列表 / 随机切校
- **设备指纹**：12 种机型随机
- **定时挂机**：每日定时 / 批量 config
- **GUI + CLI**：桌面工作台（内置 Web DEV CONSOLE）+ 命令行

## 快速开始

```bash
pip install -r requirements.txt   # 仅 gmssl 可选，纯 stdlib 也能跑
python yunyundong_full.py          # 启动 Web 工作台
```

或直接用 `云运动全功能.exe`（独立运行，无需 Python）。

填账号：

```bash
cp yunyundong_config.example.json yunyundong_config.json
# 编辑 username / password / school_id
python yunyundong_full.py login --user 学号 --pass 密码
```

## 配置

`yunyundong_config.json`：

```json
{
  "username": "学号",
  "password": "密码",
  "school_id": "169",
  "dist_km": 3.0,
  "duration_s": 840,
  "n_points": 50,
  "marks": 5,
  "route": "loop",
  "timer_on": true,
  "timer_hh": 7,
  "timer_mm": 30
}
```

**注意**：`yunyundong_config.json` 含账号密码，**不要提交到 git**（已在 `.gitignore`）。

## 协议要点

| 项 | 值 |
|----|-----|
| 加密 | content = `Base64(SM4-ECB-PKCS7(json))` |
| 密钥 | cipherKey = SM2(sm4_key)，固定 SM2 密文 |
| split | 先 `gzip(json)` 再 SM4 |
| 响应 | gzip → JSON字符串(b64) → SM4 解密 |
| sign | `MD5(platform & utc & uuid & appsecret)` |
| appsecret | `0h1UIfMDSc7piesRINRXXfkE` |
| version | `3.6.6`（3.5.10 会被拒） |
| 登录 | `{"userName","password","schoolId","type":"1"}` |

## API 一览

```
POST /m-api/login/appLogin              登录
POST /m-api/login/getStudentInfo        学籍
POST /m-api/run/getHomeRunInfo          任务卡
POST /m-api/run/start                   开始
POST /m-api/run/splitPointCheating      轨迹分段 (gzip)
POST /m-api/run/finish                  结束
POST /m-api/run/crsReocordInfoList      历史
POST /m-api/run/crsReocordInfo          历史详情 (pointsList)
POST /m-api/run/addRecordAppeal         申诉
POST /m-api/runAvoid/crsRunAvoidSave    免跑
+ 课程/场馆/社团/考试/公告/问卷/AI 体测/成绩 ...
```

完整列表见 `云运动协议分析.md`。

## 合格配方

- 里程 2.6–10 km（默认 3.0）
- 配速 3–10 min/km（840s/3km ≈ 4.67）
- 打卡 ≥3（默认 5），`manageList` 坐标对
- 轨迹过打卡点（cardRange 20m）
- 时段 06:00–23:00

实测：3.0km / 840s / 50 点 / 踩 5 点 →「恭喜你当前跑步成绩合格」

## 文件说明

| 文件 | 用途 |
|------|------|
| `yunyundong_full.py` | 主程序（Web 工作台 + CLI） |
| `yunyundong_client.py` | 全接口客户端 |
| `sm4_std.py` | 标准 SM4（过国标测试向量） |
| `run_qualified.py` | 合格跑步脚本 |
| `云运动工作站.html` | 网页版工作台 |
| `云运动协议分析.md` | 协议细节 |
| `使用教程.md` | 图文教程 |
| `本地代理.py` | 网页版跨域代理 |

## 技术栈

- 纯 Python stdlib（tkinter / http.server / hashlib）
- SM4-ECB-PKCS7（GB/T 32907）
- SM2 包 SM4（gmssl 可选）
- 本地 Web 工作台（127.0.0.1:17653-17669）
- 高德瓦片离线地图

## 免责声明

本项目仅供学习交流，禁止用于违规用途。使用者应遵守所在学校/地区法律法规，一切后果自负。

## License

MIT
