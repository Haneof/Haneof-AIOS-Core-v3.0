"""Simulated one-day reality feed + PRE-REGISTERED ground truth labels.

Ground truth is authored before any cleaning arm runs, and is never shown to the
AI arm. Each record is labelled:

    KEEP — carries durable fact / commitment / health / relationship / deadline
    DROP — transient filler, ad spam, duplicate-with-no-new-info, test junk

Hard cases are included on purpose: records that mix filler with critical content,
records that look casual but are commitments, and records that look urgent but are
jokes. These are where the two arms should diverge, if they diverge at all.
"""

from __future__ import annotations

from datetime import datetime, timezone

DAY = datetime(2026, 10, 28, tzinfo=timezone.utc)


def at(hour: int, minute: int) -> datetime:
    return DAY.replace(hour=hour, minute=minute, second=0, microsecond=0)


# id, dimension, source_kind, occurred_at, value (text), note
RECORDS: list[dict] = [
    # ---------------- dim:mic_audio  麦克风转写（真实对话 + 大量填充） ----------------
    dict(id="m01", dim="dim:mic_audio", kind="mic", t=at(7, 12),
         text="嗯……啊……那个……", note="起床后无意义发声"),
    dict(id="m02", dim="dim:mic_audio", kind="mic", t=at(7, 15),
         text="今天周二了吧？哦不对，周三。", note="自言自语核对日期"),
    dict(id="m03", dim="dim:mic_audio", kind="mic", t=at(7, 31),
         text="喂，快递放门口就行，谢谢啊。", note="对快递员"),
    dict(id="m04", dim="dim:mic_audio", kind="mic", t=at(8, 2),
         text="跟你说个事，我妈昨天晚上住院了，在市第二人民医院心内科，我下午得过去一趟。",
         note="【重要】家人住院：关系+健康+行程"),
    dict(id="m05", dim="dim:mic_audio", kind="mic", t=at(8, 5),
         text="啊？哦。行。", note="回应，无信息"),
    dict(id="m06", dim="dim:mic_audio", kind="mic", t=at(8, 40),
         text="我跟小李在项目分工上吵了一架，他不愿意接测试那块。",
         note="【重要】同事冲突：关系+工作"),
    dict(id="m07", dim="dim:mic_audio", kind="mic", t=at(9, 3),
         text="好的收到，谢谢，嗯嗯。", note="客套"),
    dict(id="m08", dim="dim:mic_audio", kind="mic", t=at(9, 47),
         text="对了那个，嗯，我答应张总周三之前把合同初稿发过去，别忘了提醒我。",
         note="【重要】承诺 + 截止期，裹在填充词里"),
    dict(id="m09", dim="dim:mic_audio", kind="mic", t=at(10, 15),
         text="哈哈哈笑死我了。", note="无信息"),
    dict(id="m10", dim="dim:mic_audio", kind="mic", t=at(10, 16),
         text="哈哈哈笑死我了。", note="与上一条重复"),
    dict(id="m11", dim="dim:mic_audio", kind="mic", t=at(11, 22),
         text="我这个月目标是把体重减五斤，从今天开始晚上不吃饭。",
         note="【重要】目标 + 计划"),
    dict(id="m12", dim="dim:mic_audio", kind="mic", t=at(12, 30),
         text="午饭吃什么呢……随便吧。", note="无决策"),
    dict(id="m13", dim="dim:mic_audio", kind="mic", t=at(14, 5),
         text="头有点晕，可能是没睡好。", note="【重要】轻度健康信号"),
    dict(id="m14", dim="dim:mic_audio", kind="mic", t=at(15, 41),
         text="头晕得厉害，站都站不稳，我先坐下缓一缓。",
         note="【重要】健康加重，比 m13 严重"),
    dict(id="m15", dim="dim:mic_audio", kind="mic", t=at(16, 2),
         text="明天是世界末日哈哈哈，开玩笑的。", note="玩笑，看似紧急实为噪声"),
    dict(id="m16", dim="dim:mic_audio", kind="mic", t=at(18, 20),
         text="我到二院了，妈这边医生说要做个造影，明天上午出结果。",
         note="【重要】医疗进展 + 次日节点"),
    dict(id="m17", dim="dim:mic_audio", kind="mic", t=at(21, 8),
         text="烦死了，这破系统又卡了。", note="情绪吐槽，无事实"),
    dict(id="m18", dim="dim:mic_audio", kind="mic", t=at(22, 45),
         text="算了不弄了，明天再说吧。", note="无信息"),

    # ---------------- dim:payment / dim:order  支付与订单（结构化） ----------------
    dict(id="p01", dim="dim:payment", kind="pay", t=at(8, 12),
         text="早餐 便利店消费 12.5 元", note="小额日常"),
    dict(id="p02", dim="dim:payment", kind="pay", t=at(13, 5),
         text="医院住院预缴金 12000 元", note="【重要】大额 + 医疗事件佐证"),
    dict(id="p03", dim="dim:payment", kind="pay", t=at(19, 30),
         text="视频会员自动续费 25 元", note="小额订阅"),
    dict(id="o01", dim="dim:order", kind="order", t=at(20, 10),
         text="订单：护颈枕 x1，预计周四送达", note="【重要】有送达时间的行为事实"),

    # ---------------- dim:calendar  日历 ----------------
    dict(id="c01", dim="dim:calendar", kind="cal", t=at(9, 0),
         text="日程：周五 15:00 公司年度体检", note="【重要】未来承诺/节点"),
    dict(id="c02", dim="dim:calendar", kind="cal", t=at(9, 5),
         text="日程：周四 10:00 项目周会", note="例行会议，中等价值"),

    # ---------------- dim:note  便签 ----------------
    dict(id="n01", dim="dim:note", kind="note", t=at(11, 0),
         text="便签：合同要点 —— 交付周期 30 天，违约金 5%，对方联系人张总 138****2210",
         note="【重要】工作事实，含关键条款"),
    dict(id="n02", dim="dim:note", kind="note", t=at(11, 4),
         text="便签：asdfghjkl", note="误触乱码"),
    dict(id="n03", dim="dim:note", kind="note", t=at(17, 55),
         text="便签：记得给妈带医保卡和身份证", note="【重要】待办"),

    # ---------------- dim:camera_visual  摄像头描述 ----------------
    dict(id="v01", dim="dim:camera_visual", kind="cam", t=at(7, 20),
         text="画面：桌面有一台笔记本电脑和一杯水。", note="环境描述，低价值但为事实"),
    dict(id="v02", dim="dim:camera_visual", kind="cam", t=at(12, 10),
         text="画面：餐桌上有两个人和三道菜。", note="环境描述，低价值"),
    dict(id="v03", dim="dim:camera_visual", kind="cam", t=at(15, 45),
         text="画面：一人扶着桌子站立不稳，面色苍白。", note="【重要】与 m14 头晕互为佐证"),

    # ---------------- dim:app_usage  App 行为 / 通知 ----------------
    dict(id="a01", dim="dim:app_usage", kind="app", t=at(8, 55),
         text="【XX商城】限时秒杀！全场3折起，点开领券>>", note="广告推送"),
    dict(id="a02", dim="dim:app_usage", kind="app", t=at(10, 30),
         text="【XX新闻】您关注的球队今日获胜", note="无关推送"),
    dict(id="a03", dim="dim:app_usage", kind="app", t=at(14, 20),
         text="使用 文档编辑 App 47 分钟", note="行为事实，中等价值"),
    dict(id="a04", dim="dim:app_usage", kind="app", t=at(20, 0),
         text="【系统】存储空间不足，建议清理", note="系统通知，低价值"),

    # ---------------- dim:external_chat  外部聊天 ----------------
    dict(id="x01", dim="dim:external_chat", kind="chat", t=at(9, 20),
         text="同事小王：在吗？", note="无信息"),
    dict(id="x02", dim="dim:external_chat", kind="chat", t=at(9, 21),
         text="同事小王：在吗？", note="重复催促"),
    dict(id="x03", dim="dim:external_chat", kind="chat", t=at(9, 25),
         text="同事小王：李总说合同周三必须到，不然就重谈。",
         note="【重要】外部压力 + 截止期，佐证 m08"),
    dict(id="x04", dim="dim:external_chat", kind="chat", t=at(21, 30),
         text="朋友阿强：周末钓鱼去不去？", note="社交邀约，中等价值"),

    # ---------------- 数值流（心率，1000 点压缩为段/变化） ----------------
    dict(id="hr_series", dim="dim:heart_rate", kind="numeric", t=at(0, 0),
         text="心率采样 1000 点（00:00-23:59）", note="数值流，机制侧会机械压缩"),
]

# ---------------- PRE-REGISTERED GROUND TRUTH ----------------
# 在任何清洗跑起来之前就写死。AI 侧永远看不到这张表。
LABELS: dict[str, tuple[str, str]] = {
    "m01": ("DROP", "无意义发声"),
    "m02": ("DROP", "自言自语核对日期，无长期价值"),
    "m03": ("DROP", "一次性事务，已完结"),
    "m04": ("KEEP", "家人住院：关系+健康+行程"),
    "m05": ("DROP", "回应无信息"),
    "m06": ("KEEP", "同事冲突：关系+工作"),
    "m07": ("DROP", "客套"),
    "m08": ("KEEP", "承诺+截止期（裹在填充词里）"),
    "m09": ("DROP", "无信息"),
    "m10": ("DROP", "与上一条重复"),
    "m11": ("KEEP", "目标+计划"),
    "m12": ("DROP", "无决策"),
    "m13": ("KEEP", "轻度健康信号"),
    "m14": ("KEEP", "健康加重，比 m13 严重"),
    "m15": ("DROP", "玩笑，看似紧急实为噪声"),
    "m16": ("KEEP", "医疗进展+次日节点"),
    "m17": ("DROP", "情绪吐槽，无事实"),
    "m18": ("DROP", "无信息"),
    "p01": ("DROP", "小额日常消费"),
    "p02": ("KEEP", "大额住院预缴，医疗事件佐证"),
    "p03": ("DROP", "小额订阅"),
    "o01": ("KEEP", "有送达时间的行为事实"),
    "c01": ("KEEP", "未来节点：体检"),
    "c02": ("KEEP", "例行会议，中等价值"),
    "n01": ("KEEP", "工作事实，含关键条款"),
    "n02": ("DROP", "误触乱码"),
    "n03": ("KEEP", "待办"),
    "v01": ("DROP", "环境描述，低价值"),
    "v02": ("DROP", "环境描述，低价值"),
    "v03": ("KEEP", "与 m14 头晕互为佐证"),
    "a01": ("DROP", "广告推送"),
    "a02": ("DROP", "无关推送"),
    "a03": ("KEEP", "行为事实，中等价值"),
    "a04": ("DROP", "系统通知，低价值"),
    "x01": ("DROP", "无信息"),
    "x02": ("DROP", "重复催促"),
    "x03": ("KEEP", "外部压力+截止期，佐证 m08"),
    "x04": ("KEEP", "社交邀约，中等价值"),
    "hr_series": ("KEEP", "数值流（压缩后应保留段与变化）"),
}

# 事后认知验收点：清理后的数据若喂给总结/认知，能否还原这些结论
COGNITION_CHECKS: list[tuple[str, tuple[str, ...]]] = [
    ("母亲住院（市二院心内科）", ("m04", "m16", "p02")),
    ("承诺周三前给张总合同", ("m08", "x03", "n01")),
    ("头晕加重（两次递进）", ("m13", "m14", "v03")),
    ("与小李的工作冲突", ("m06",)),
    ("减重五斤目标", ("m11",)),
    ("周五体检 / 周四周会", ("c01", "c02")),
    ("需带医保卡身份证", ("n03",)),
]
