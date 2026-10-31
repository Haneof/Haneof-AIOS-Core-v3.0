"""压力测试模拟数据：换一套人设 + 加量，用来压 token 上限与管线扩展性。

设计目标（对应于“更换基础数据，增加模拟数据，看看系统还能行吗”）：
  - 人设更换：从“老王/柔性屏手环”换成“小林/成都自由旅行摄影师”，事件、维度分布都不同，
    验证任务提示词按契约分离后是否对陌生场景不退化（不上绑任何特定叙事）。
  - 加量：单日非数值记录 ~127 条，其中 dim:mic_audio 堆到 80 条（远超原数据 ~18 条），
    用来把 ANNOTATE 的单批次推到 40 / 80 条，实测 3000 token 输出上限在此时是否开始截断。
  - 长文本：麦克风与聊天里混入更长、带填充词的句子，模拟真实 wearable 转写，
    让 SUMMARIZE 的源输入与 ANNOTATE 的 JSON 输出都更“重”。
  - 噪声多样性：广告、钓鱼（“快递丢失理赔”）、重复催促、电视环境声、玩笑夸张（“明天关工作室”）、
    误触乱码，全部预注册 ground truth，AI 臂看不到。

Ground truth 结构沿用 sim_realtime：DAYS[i] = {name, records, labels, checks, keywords, hr}。
hr 字段供 build_hr_samples 生成数值流（机制侧压缩，不进标注）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

DATES = [
    datetime(2026, 11, 3, tzinfo=timezone.utc),  # 单日高负载压力日
]


def at(day_idx: int, hour: int, minute: int) -> datetime:
    return DATES[day_idx].replace(hour=hour, minute=minute, second=0, microsecond=0)


# ============================================================================
# 麦克风高负载流：80 条。前 38 条为手工编排（含重要事实与典型噪声），
# 后 42 条为程序化填充噪声（无意义发声 / 环境声 / 重复），全部 DROP，
# 仅用于把批次体量推上去，逼出 ANNOTATE 输出上限。
# ============================================================================
_MIC_CURATED: list[tuple[str, str, str, str]] = [
    # (id, text, label, note)
    ("m01", "嗯……那个……啊……", "DROP", "起床无意义发声"),
    ("m02", "今天周三了吧，哦不对周四。", "DROP", "自言自语核对日期"),
    ("m03", "喂快递放门口就行谢了啊。", "DROP", "一次性事务"),
    ("m04", "跟你说个事，甲方那个城市宣传片周五得交初剪，我说周三前给一版，"
            "结果拖到现在了，今晚必须肝出来。", "KEEP", "【重要】客户交付+双重截止期(周三版/周五终)"),
    ("m05", "啊行好嘞。", "DROP", "客套回应"),
    ("m06", "我镜头昨天摔了，那个 24-70 的变焦，前组镜片裂了一道，今天得送修，"
            "报价说可能要一千八。", "KEEP", "【重要】设备损毁+金额+待办"),
    ("m07", "嗯嗯好的收到。", "DROP", "客套"),
    ("m08", "对了那个，嗯，我答应张导把大理旅拍的脚本周五前发他，别忘了提醒我。", "KEEP", "【重要】承诺+截止期，裹填充词"),
    ("m09", "哈哈哈笑死。", "DROP", "无信息"),
    ("m10", "哈哈哈笑死。", "DROP", "重复"),
    ("m11", "膝盖又有点疼，昨天爬山拍日出爬狠了，老毛病了，贴个膏药吧。", "KEEP", "【重要】健康信号(递进起点)"),
    ("m12", "午饭吃啥随便。", "DROP", "无决策"),
    ("m13", "膝盖疼得厉害，下楼梯都打软，我坐会儿缓一下。", "KEEP", "【重要】健康加重，比 m11 严重"),
    ("m14", "明天世界末日哈哈哈开玩笑的。", "DROP", "玩笑噪声"),
    ("m15", "我订了后天飞大理的航班，早八的，得早起。", "KEEP", "【重要】未来节点+行程"),
    ("m16", "烦死了这破剪辑软件又卡。", "DROP", "吐槽"),
    ("m17", "签证那个事，我港澳通行证好像月底就到期了，得赶紧续，不然下个月去香港探店拍不了。", "KEEP", "【重要】行政截止期"),
    ("m18", "算了不弄了明天再说。", "DROP", "无信息"),
    ("m19", "我跟剪辑师小周在项目风格上吵了一架，他非要走赛博朋克风，我说客户要清新。", "KEEP", "【重要】同事冲突+工作"),
    ("m20", "晚上吃点清淡的，膝盖别受凉。", "DROP", "无决策(但含健康叮嘱，边界)"),
    ("m21", "朋友阿杰发请柬了，下周六他婚礼，在青城山，得空出一天。", "KEEP", "【重要】社交邀约+未来节点"),
    ("m22", "啊？哦。行。", "DROP", "回应无信息"),
    ("m23", "我这不打算再续那个视频会员了，太贵，一年三百多。", "DROP", "订阅决策(软事实?这里判 DROP，金额小且无硬事实)"),
    ("m24", "那个宣传片客户说预算加到两万了，比之前多五千。", "KEEP", "【重要】金额+工作事实"),
    ("m25", "电视机里放着新闻，听不清说啥。", "DROP", "电视环境噪声"),
    ("m26", "我跟你说我今早跑步心率飙到一百五了，累但爽，练完了。", "KEEP", "晨练真实飙升(非疾病)"),
    ("m27", "嗯那个……那个……", "DROP", "无意义发声"),
    ("m28", "客户王总微信说片子一定要带航拍，大理那边风大注意安全。", "KEEP", "【重要】外部/自述工作事实(航拍要求)"),
    ("m29", "我手机又没电了，烦。", "DROP", "吐槽"),
    ("m30", "明天就把工作室关了不干了哈哈。", "DROP", "玩笑式辞职，假紧急必须 DROP"),
    ("m31", "膝盖今晚好点了，能正常走了，膏药挺管用。", "KEEP", "【重要】健康随访"),
    ("m32", "行李我得 checklist 一下：相机两台、备用镜头、三脚架、无人机、充电宝。", "KEEP", "【重要】待办(出行)"),
    ("m33", "哎我刚发现存储卡只剩两张了，得再买几张大的。", "KEEP", "【重要】待办+设备"),
    ("m34", "哈哈这猫好可爱。", "DROP", "无信息"),
    ("m35", "老板娘打电话来说工作室房租下个月涨三百。", "KEEP", "【重要】金额+行政(房租)"),
    ("m36", "（电视声）……广告……（杂音）", "DROP", "环境噪声无事实"),
    ("m37", "我答应我妈周末回趟老家看看她，别又忘了。", "KEEP", "【重要】承诺+家庭(关系)"),
    ("m38", "睡了明天还得早起赶飞机。", "DROP", "无信息"),
]

# 程序化填充噪声：把麦克风批次体量推到 80 条，全部 DROP（无事实）。
_FILLER_TEXTS = [
    "嗯……那个……啊……", "（环境声）……", "啊行好。", "嗯嗯。", "哈哈哈。",
    "随便吧。", "烦。", "哎。", "那个……", "（电视声）……", "哦对。", "嗯。",
    "好的好的。", "（背景音乐声）……", "啊？", "行吧。", "算了。", "（风声）……",
    "嗯哼。", "哦。", "（键盘声）……", "哈哈。", "这个……", "（鸟叫声）……",
    "好的。", "啊哦。", "（水流声）……", "嗯对。", "（门铃声）……", "哦这样。",
    "哈哈哈哈。", "（空调声）……", "那个啥。", "（狗叫声）……", "嗯啊。", "行。",
    "（锅铲声）……", "啊这。", "（雨声）……", "哦哦。", "嗯好。", "（车流声）……",
]


def _stress_mic_records() -> list[dict]:
    out: list[dict] = []
    # 手工编排部分：从 07:00 起逐条铺开
    t = 7 * 60
    for i, (rid, text, _lab, note) in enumerate(_MIC_CURATED):
        minute = 7 + (i * 17) // 60
        sec = (i * 17) % 60
        out.append(dict(id=rid, dim="dim:mic_audio", kind="mic",
                        t=at(0, minute, sec), text=text, note=note))
    # 填充噪声：从 22:00 起按 7 分钟步长铺开，对当天剩余分钟取模，不跨日
    for j, text in enumerate(_FILLER_TEXTS):
        base_min = 22 * 60
        total = (base_min + j * 7) % 1440  # 越界则绕回当天 00:00 之后
        out.append(dict(id=f"f{j+1:02d}", dim="dim:mic_audio", kind="mic",
                        t=at(0, total // 60, total % 60), text=text,
                        note="填充噪声(压体量)"))
    return out


_STRESS_RECORDS: list[dict] = _stress_mic_records() + [
    # 支付
    dict(id="p01", dim="dim:payment", kind="pay", t=at(0, 8, 12), text="早餐 咖啡 19 元", note="小额日常"),
    dict(id="p02", dim="dim:payment", kind="pay", t=at(0, 13, 5), text="镜头维修预付 1800 元", note="【重要】大额+设备损毁佐证"),
    dict(id="p03", dim="dim:payment", kind="pay", t=at(0, 19, 30), text="视频会员自动续费 28 元", note="小额订阅"),
    dict(id="p04", dim="dim:payment", kind="pay", t=at(0, 21, 0), text="机票 成都-大理 往返 1460 元", note="【重要】大额+行程佐证"),
    dict(id="p05", dim="dim:payment", kind="pay", t=at(0, 11, 0), text="存储卡 x3 高速卡 369 元", note="【重要】设备待办佐证"),
    dict(id="p06", dim="dim:payment", kind="pay", t=at(0, 16, 40), text="工作室房租补缴 300 元", note="【重要】房租上涨佐证"),
    # 订单
    dict(id="o01", dim="dim:order", kind="order", t=at(0, 20, 10), text="订单：无人机桨叶备用 x4，预计周五到", note="【重要】设备待办"),
    dict(id="o02", dim="dim:order", kind="order", t=at(0, 10, 0), text="订单：膏药 x2，预计明日达", note="【重要】健康待办佐证"),
    dict(id="o03", dim="dim:order", kind="order", t=at(0, 9, 30), text="订单：相机清洁套装 x1", note="小额设备"),
    dict(id="o04", dim="dim:order", kind="order", t=at(0, 18, 0), text="订单：青城山婚礼伴手礼 x1，预计周六前到", note="【重要】社交待办"),
    # 日历
    dict(id="c01", dim="dim:calendar", kind="cal", t=at(0, 9, 0), text="日程：周四 交宣传片初剪版给甲方", note="【重要】截止期(佐证 m04)"),
    dict(id="c02", dim="dim:calendar", kind="cal", t=at(0, 9, 5), text="日程：周五 城市宣传片终剪交付 + 发大理脚本给张导", note="【重要】双截止期"),
    dict(id="c03", dim="dim:calendar", kind="cal", t=at(0, 7, 30), text="日程：后天 飞大理旅拍(早八航班)", note="【重要】行程节点"),
    dict(id="c04", dim="dim:calendar", kind="cal", t=at(0, 15, 0), text="日程：月底 港澳通行证续签截止", note="【重要】行政截止期"),
    dict(id="c05", dim="dim:calendar", kind="cal", t=at(0, 18, 30), text="日程：下周六 阿杰婚礼(青城山)", note="【重要】社交节点"),
    # 便签
    dict(id="n01", dim="dim:note", kind="note", t=at(0, 11, 0), text="便签：宣传片要点 —— 时长90秒，清新风，含航拍，交付周五", note="【重要】工作事实+条款"),
    dict(id="n02", dim="dim:note", kind="note", t=at(0, 11, 4), text="便签：asdfghjkl", note="误触乱码"),
    dict(id="n03", dim="dim:note", kind="note", t=at(0, 22, 45), text="便签：记得带港澳通行证+身份证去续签", note="【重要】待办"),
    dict(id="n04", dim="dim:note", kind="note", t=at(0, 21, 30), text="便签：大理行李清单 相机x2 镜头 三脚架 无人机 充电宝 存储卡", note="【重要】待办(佐证 m32)"),
    dict(id="n05", dim="dim:note", kind="note", t=at(0, 17, 55), text="便签：给妈打电话周末回老家", note="【重要】家庭待办"),
    # 摄像头视觉
    dict(id="v01", dim="dim:camera_visual", kind="cam", t=at(0, 7, 20), text="画面：桌上摆着两台相机和一杯水。", note="环境描述低值"),
    dict(id="v02", dim="dim:camera_visual", kind="cam", t=at(0, 12, 10), text="画面：餐桌上两个人三盘菜。", note="环境低值"),
    dict(id="v03", dim="dim:camera_visual", kind="cam", t=at(0, 13, 45), text="画面：一人扶着楼梯扶手，手按膝盖，表情吃痛。", note="【重要】佐证 m13 膝盖"),
    dict(id="v04", dim="dim:camera_visual", kind="cam", t=at(0, 15, 30), text="画面：茶几上放着一张婚礼请柬。", note="【重要】佐证 m21"),
    dict(id="v05", dim="dim:camera_visual", kind="cam", t=at(0, 21, 10), text="画面：行李箱敞开，里面是相机包和无人机盒。", note="【重要】佐证 m32 出行"),
    # App 行为
    dict(id="a01", dim="dim:app_usage", kind="app", t=at(0, 8, 55), text="【XX商城】限时秒杀！3折起点开领券>>", note="广告"),
    dict(id="a02", dim="dim:app_usage", kind="app", t=at(0, 10, 30), text="使用 剪辑App 96 分钟", note="行为事实中等价值"),
    dict(id="a03", dim="dim:app_usage", kind="app", t=at(0, 14, 20), text="【XX新闻】您关注球队今日获胜", note="无关推送"),
    dict(id="a04", dim="dim:app_usage", kind="app", t=at(0, 20, 0), text="【系统】存储空间不足建议清理", note="系统通知低值"),
    dict(id="a05", dim="dim:app_usage", kind="app", t=at(0, 16, 0), text="使用 航拍规划App 21 分钟", note="行为事实(工作相关)"),
    dict(id="a06", dim="dim:app_usage", kind="app", t=at(0, 9, 50), text="【XX旅游】大理机票降价提醒，点击抢>>", note="广告/营销"),
    dict(id="a07", dim="dim:app_usage", kind="app", t=at(0, 19, 20), text="【银行】尾号4321有一笔1460元机票支出", note="【重要】银行通知佐证 p04"),
    dict(id="a08", dim="dim:app_usage", kind="app", t=at(0, 13, 30), text="使用 修图App 54 分钟", note="行为事实中等价值"),
    # 外部聊天
    dict(id="x01", dim="dim:external_chat", kind="chat", t=at(0, 9, 20), text="同事小周：在吗", note="无信息"),
    dict(id="x02", dim="dim:external_chat", kind="chat", t=at(0, 9, 21), text="同事小周：在吗", note="重复催促"),
    dict(id="x03", dim="dim:external_chat", kind="chat", t=at(0, 9, 25), text="同事小周：王总说片子必须带航拍，大理风大注意安全。", note="【重要】外部压力+工作(佐证 m28)"),
    dict(id="x04", dim="dim:external_chat", kind="chat", t=at(0, 21, 30), text="朋友阿杰：周末婚礼去不去，青城山。", note="社交邀约中等价值"),
    dict(id="x05", dim="dim:external_chat", kind="chat", t=at(0, 15, 40), text="【10086】话费礼包待领 t.cn/yy", note="广告形似真通知→DROP"),
    dict(id="x06", dim="dim:external_chat", kind="chat", t=at(0, 17, 50), text="【快递客服】您包裹丢失可理赔，点 t.cn/claim 填写银行卡", note="钓鱼形似真通知→必须 DROP"),
    dict(id="x07", dim="dim:external_chat", kind="chat", t=at(0, 11, 10), text="客户王总：预算加到两万，片子要大气。", note="【重要】外部压力+金额(佐证 m24)"),
    dict(id="x08", dim="dim:external_chat", kind="chat", t=at(0, 18, 0), text="妈妈：周末回来吃饭啊，好久没见了。", note="【重要】家庭关系(佐证 m37)"),
    dict(id="x09", dim="dim:external_chat", kind="chat", t=at(0, 10, 5), text="剪辑群：今晚熬夜肝片子的扣1", note="群聊无指向→DROP(或软事实?判 DROP)"),
    dict(id="x10", dim="dim:external_chat", kind="chat", t=at(0, 12, 0), text="朋友大鹏：周末钓鱼去不去", note="社交邀约中等价值"),
    dict(id="x11", dim="dim:external_chat", kind="chat", t=at(0, 20, 30), text="【安全中心】账户异常已锁定，立即验证 t.cn/lock", note="钓鱼→必须 DROP"),
    dict(id="x12", dim="dim:external_chat", kind="chat", t=at(0, 8, 40), text="张导：大理脚本周五前发我，别拖。", note="【重要】外部压力+截止期(佐证 m08)"),
    dict(id="x13", dim="dim:external_chat", kind="chat", t=at(0, 16, 20), text="房东：房租下月涨三百，谅解。", note="【重要】行政金额(佐证 m35)"),
    dict(id="x14", dim="dim:external_chat", kind="chat", t=at(0, 22, 0), text="阿杰：婚礼记得带相机，帮拍点。", note="【重要】社交+工作交叉(佐证 m21/o04)"),
    # 心率数值流（机制侧压缩，不进标注）
    dict(id="hr", dim="dim:heart_rate", kind="numeric", t=at(0, 0, 0),
         text="心率采样 1000 点（00:00-23:59）", note="数值流"),
]

_STRESS_LABELS: dict[str, tuple[str, str]] = {}
for rid, _t, lab, note in _MIC_CURATED:
    _STRESS_LABELS[rid] = (lab, note)
for j in range(len(_FILLER_TEXTS)):
    _STRESS_LABELS[f"f{j+1:02d}"] = ("DROP", "填充噪声(压体量)")
_STRESS_LABELS.update({
    "p01": ("DROP", "小额"), "p02": ("KEEP", "镜头维修1800"), "p03": ("DROP", "订阅"),
    "p04": ("KEEP", "机票1460"), "p05": ("KEEP", "存储卡369"), "p06": ("KEEP", "房租+300"),
    "o01": ("KEEP", "无人机桨叶"), "o02": ("KEEP", "膏药"), "o03": ("DROP", "小额设备"),
    "o04": ("KEEP", "婚礼伴手礼"),
    "c01": ("KEEP", "初剪截止"), "c02": ("KEEP", "双截止"), "c03": ("KEEP", "大理航班"),
    "c04": ("KEEP", "通行证续签"), "c05": ("KEEP", "婚礼节点"),
    "n01": ("KEEP", "宣传片条款"), "n02": ("DROP", "乱码"), "n03": ("KEEP", "续签待办"),
    "n04": ("KEEP", "行李清单"), "n05": ("KEEP", "回老家居办"),
    "v01": ("DROP", "环境"), "v02": ("DROP", "环境"), "v03": ("KEEP", "膝盖佐证"),
    "v04": ("KEEP", "婚礼佐证"), "v05": ("KEEP", "出行佐证"),
    "a01": ("DROP", "广告"), "a02": ("KEEP", "剪辑行为"), "a03": ("DROP", "推送"),
    "a04": ("DROP", "系统通知"), "a05": ("KEEP", "航拍规划"), "a06": ("DROP", "广告"),
    "a07": ("KEEP", "银行通知"), "a08": ("KEEP", "修图行为"),
    "x01": ("DROP", "无信息"), "x02": ("DROP", "重复"), "x03": ("KEEP", "航拍压力"),
    "x04": ("KEEP", "社交邀约"), "x05": ("DROP", "广告"), "x06": ("DROP", "钓鱼"),
    "x07": ("KEEP", "金额压力"), "x08": ("KEEP", "家庭关系"), "x09": ("DROP", "群聊无指向"),
    "x10": ("KEEP", "社交邀约"), "x11": ("DROP", "钓鱼"), "x12": ("KEEP", "脚本截止"),
    "x13": ("KEEP", "房租金额"), "x14": ("KEEP", "社交+工作"),
    "hr": ("KEEP", "数值流"),
})

_STRESS_CHECKS: list[tuple[str, tuple[str, ...]]] = [
    ("城市宣传片双截止(初剪周四/终剪周五)", ("m04", "c01", "c02", "n01", "x03")),
    ("镜头摔裂维修1800", ("m06", "p02", "o03")),
    ("大理旅拍(航班+脚本+行李)", ("m08", "m15", "c03", "m32", "p04", "o01", "n04", "x12", "v05")),
    ("港澳通行证月底续签", ("m17", "c04", "n03")),
    ("膝盖旧伤递进+缓解", ("m11", "m13", "m31", "v03", "o02")),
    ("阿杰下周六婚礼(青城山)", ("m21", "c05", "o04", "v04", "x04", "x14")),
    ("剪辑师风格冲突", ("m19",)),
    ("宣传片预算加到2万", ("m24", "x07")),
    ("家庭:周末回老家看妈", ("m37", "n05", "x08")),
    ("钓鱼短信/账户锁定(必须DROP)", ("x06", "x11")),
]
_STRESS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "城市宣传片双截止(初剪周四/终剪周五)": ("宣传片", "初剪", "周五", "终剪", "王总", "航拍"),
    "镜头摔裂维修1800": ("镜头", "维修", "1800", "裂"),
    "大理旅拍(航班+脚本+行李)": ("大理", "航班", "脚本", "行李", "无人机", "张导", "机票"),
    "港澳通行证月底续签": ("通行证", "签证", "续签", "港澳", "月底"),
    "膝盖旧伤递进+缓解": ("膝盖", "疼", "膏药", "打软"),
    "阿杰下周六婚礼(青城山)": ("婚礼", "青城山", "阿杰", "请柬"),
    "剪辑师风格冲突": ("剪辑师", "小周", "吵", "风格"),
    "宣传片预算加到2万": ("两万", "预算", "2万"),
    "家庭:周末回老家看妈": ("妈", "老家", "周末"),
    "钓鱼短信/账户锁定(必须DROP)": ("理赔", "锁定", "验证", "t.cn"),
}
_STRESS_HR = dict(baseline=72.0,
                 spikes=[(7 * 60 + 35, 7 * 60 + 50, 150.0), (15 * 60 + 25, 15 * 60 + 45, 96.0)],
                 artifacts=[(9 * 60 + 30, 9 * 60 + 33, 79.0)])

DAYS: list[dict] = [
    dict(name="STRESS_DAY_2026-11-03", records=_STRESS_RECORDS, labels=_STRESS_LABELS,
         checks=_STRESS_CHECKS, keywords=_STRESS_KEYWORDS, hr=_STRESS_HR),
]


def build_hr_samples(day_idx: int, n: int = 1000) -> list:
    """同 sim_realtime.build_hr_samples：生成连续心率数值流。"""
    from aios_core.ingest import NumericSample
    cfg = DAYS[day_idx]["hr"]
    base = DATES[day_idx]
    baseline = cfg["baseline"]
    spikes = {(s, e): v for (s, e, v) in cfg["spikes"]}
    artifacts = {(s, e): v for (s, e, v) in cfg.get("artifacts", [])}
    out = []
    for i in range(n):
        minute = (i * 1440) // n
        second = ((i * 86400) // n) % 60
        t = base + timedelta(minutes=minute, seconds=second)
        value = baseline + ((i % 7) - 3) * 1.2
        for (s, e), v in spikes.items():
            if s <= minute <= e:
                value = v + ((i % 5) - 2) * 2.0
        for (s, e), v in artifacts.items():
            if s <= minute <= e:
                value = v + ((i % 3) - 1) * 1.0
        out.append(NumericSample(
            external_record_id=f"hr-{day_idx}-{i:04d}",
            occurred_at=t, value=round(float(value), 1),
            source_locator=f"sensor://hr/{day_idx}/{i:04d}",
        ))
    return out


if __name__ == "__main__":
    non_numeric = [r for r in DAYS[0]["records"] if r["kind"] != "numeric"]
    mic = [r for r in DAYS[0]["records"] if r["dim"] == "dim:mic_audio"]
    print(f"STRESS day records: total={len(DAYS[0]['records'])} "
          f"non_numeric={len(non_numeric)} mic_audio={len(mic)}")
