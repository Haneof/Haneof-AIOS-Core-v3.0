"""多日实时模拟日志 + 预注册 ground truth（A/B 实测 v2，n=3）。

每个 DAY 是一天从各来源采集进来的原始记录，外加一条连续心率数值流。
Ground truth（LABELS / COGNITION_CHECKS / CHECK_KEYWORDS）在任何清洗跑起来之前
就写死，AI 臂永远看不到。

刻意让 3 天埋**不同类型**的硬骨头，以测试泛化，而不是同一题做 3 遍：
  Day1 母亲住院 / 合同截止 / 头晕递进 / 与小李冲突（控制日，沿用 v1 叙事）
  Day2 海鲜过敏起疹+服药 / 个税截止 / 玩笑式辞职 / 钓鱼短信 / 运动心率飙升(非疾病)
  Day3 错过火车改签 / 夜间低血氧 / 老板"周一谈谈" / 孩子话剧 / 钓鱼锁定账户

数据来源取自宪法《数据获取》：麦克风、支付、订单、日历、便签、摄像头、App 行为、
外部聊天、可穿戴心率。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

DATES = [
    datetime(2026, 10, 28, tzinfo=timezone.utc),
    datetime(2026, 10, 29, tzinfo=timezone.utc),
    datetime(2026, 10, 30, tzinfo=timezone.utc),
]


def at(day_idx: int, hour: int, minute: int) -> datetime:
    return DATES[day_idx].replace(hour=hour, minute=minute, second=0, microsecond=0)


# ============================================================================
# DAY 0  —— 2026-10-28（控制日，沿用 v1 叙事）
# ============================================================================
DAY0_RECORDS: list[dict] = [
    dict(id="m01", dim="dim:mic_audio", kind="mic", t=at(0, 7, 12), text="嗯……啊……那个……", note="起床后无意义发声"),
    dict(id="m02", dim="dim:mic_audio", kind="mic", t=at(0, 7, 15), text="今天周二了吧？哦不对，周三。", note="自言自语核对日期"),
    dict(id="m03", dim="dim:mic_audio", kind="mic", t=at(0, 7, 31), text="喂，快递放门口就行，谢谢啊。", note="对快递员"),
    dict(id="m04", dim="dim:mic_audio", kind="mic", t=at(0, 8, 2), text="跟你说个事，我妈昨天晚上住院了，在市第二人民医院心内科，我下午得过去一趟。", note="【重要】家人住院：关系+健康+行程"),
    dict(id="m05", dim="dim:mic_audio", kind="mic", t=at(0, 8, 5), text="啊？哦。行。", note="回应，无信息"),
    dict(id="m06", dim="dim:mic_audio", kind="mic", t=at(0, 8, 40), text="我跟小李在项目分工上吵了一架，他不愿意接测试那块。", note="【重要】同事冲突：关系+工作"),
    dict(id="m07", dim="dim:mic_audio", kind="mic", t=at(0, 9, 3), text="好的收到，谢谢，嗯嗯。", note="客套"),
    dict(id="m08", dim="dim:mic_audio", kind="mic", t=at(0, 9, 47), text="对了那个，嗯，我答应张总周三之前把合同初稿发过去，别忘了提醒我。", note="【重要】承诺+截止期，裹在填充词里"),
    dict(id="m09", dim="dim:mic_audio", kind="mic", t=at(0, 10, 15), text="哈哈哈笑死我了。", note="无信息"),
    dict(id="m10", dim="dim:mic_audio", kind="mic", t=at(0, 10, 16), text="哈哈哈笑死我了。", note="与上一条重复"),
    dict(id="m11", dim="dim:mic_audio", kind="mic", t=at(0, 11, 22), text="我这个月目标是把体重减五斤，从今天开始晚上不吃饭。", note="【重要】目标+计划"),
    dict(id="m12", dim="dim:mic_audio", kind="mic", t=at(0, 12, 30), text="午饭吃什么呢……随便吧。", note="无决策"),
    dict(id="m13", dim="dim:mic_audio", kind="mic", t=at(0, 14, 5), text="头有点晕，可能是没睡好。", note="【重要】轻度健康信号"),
    dict(id="m14", dim="dim:mic_audio", kind="mic", t=at(0, 15, 41), text="头晕得厉害，站都站不稳，我先坐下缓一缓。", note="【重要】健康加重，比 m13 严重"),
    dict(id="m15", dim="dim:mic_audio", kind="mic", t=at(0, 16, 2), text="明天是世界末日哈哈哈，开玩笑的。", note="玩笑，看似紧急实为噪声"),
    dict(id="m16", dim="dim:mic_audio", kind="mic", t=at(0, 18, 20), text="我到二院了，妈这边医生说要做个造影，明天上午出结果。", note="【重要】医疗进展+次日节点"),
    dict(id="m17", dim="dim:mic_audio", kind="mic", t=at(0, 21, 8), text="烦死了，这破系统又卡了。", note="情绪吐槽，无事实"),
    dict(id="m18", dim="dim:mic_audio", kind="mic", t=at(0, 22, 45), text="算了不弄了，明天再说吧。", note="无信息"),
    dict(id="p01", dim="dim:payment", kind="pay", t=at(0, 8, 12), text="早餐 便利店消费 12.5 元", note="小额日常"),
    dict(id="p02", dim="dim:payment", kind="pay", t=at(0, 13, 5), text="医院住院预缴金 12000 元", note="【重要】大额+医疗事件佐证"),
    dict(id="p03", dim="dim:payment", kind="pay", t=at(0, 19, 30), text="视频会员自动续费 25 元", note="小额订阅"),
    dict(id="o01", dim="dim:order", kind="order", t=at(0, 20, 10), text="订单：护颈枕 x1，预计周四送达", note="【重要】有送达时间的行为事实"),
    dict(id="c01", dim="dim:calendar", kind="cal", t=at(0, 9, 0), text="日程：周五 15:00 公司年度体检", note="【重要】未来节点：体检"),
    dict(id="c02", dim="dim:calendar", kind="cal", t=at(0, 9, 5), text="日程：周四 10:00 项目周会", note="例行会议，中等价值"),
    dict(id="n01", dim="dim:note", kind="note", t=at(0, 11, 0), text="便签：合同要点 —— 交付周期 30 天，违约金 5%，对方联系人张总 138****2210", note="【重要】工作事实，含关键条款"),
    dict(id="n02", dim="dim:note", kind="note", t=at(0, 11, 4), text="便签：asdfghjkl", note="误触乱码"),
    dict(id="n03", dim="dim:note", kind="note", t=at(0, 17, 55), text="便签：记得给妈带医保卡和身份证", note="【重要】待办"),
    dict(id="v01", dim="dim:camera_visual", kind="cam", t=at(0, 7, 20), text="画面：桌面有一台笔记本电脑和一杯水。", note="环境描述，低价值但为事实"),
    dict(id="v02", dim="dim:camera_visual", kind="cam", t=at(0, 12, 10), text="画面：餐桌上有两个人和三道菜。", note="环境描述，低价值"),
    dict(id="v03", dim="dim:camera_visual", kind="cam", t=at(0, 15, 45), text="画面：一人扶着桌子站立不稳，面色苍白。", note="【重要】与 m14 头晕互为佐证"),
    dict(id="a01", dim="dim:app_usage", kind="app", t=at(0, 8, 55), text="【XX商城】限时秒杀！全场3折起，点开领券>>", note="广告推送"),
    dict(id="a02", dim="dim:app_usage", kind="app", t=at(0, 10, 30), text="【XX新闻】您关注的球队今日获胜", note="无关推送"),
    dict(id="a03", dim="dim:app_usage", kind="app", t=at(0, 14, 20), text="使用 文档编辑 App 47 分钟", note="行为事实，中等价值"),
    dict(id="a04", dim="dim:app_usage", kind="app", t=at(0, 20, 0), text="【系统】存储空间不足，建议清理", note="系统通知，低价值"),
    dict(id="x01", dim="dim:external_chat", kind="chat", t=at(0, 9, 20), text="同事小王：在吗？", note="无信息"),
    dict(id="x02", dim="dim:external_chat", kind="chat", t=at(0, 9, 21), text="同事小王：在吗？", note="重复催促"),
    dict(id="x03", dim="dim:external_chat", kind="chat", t=at(0, 9, 25), text="同事小王：李总说合同周三必须到，不然就重谈。", note="【重要】外部压力+截止期，佐证 m08"),
    dict(id="x04", dim="dim:external_chat", kind="chat", t=at(0, 21, 30), text="朋友阿强：周末钓鱼去不去？", note="社交邀约，中等价值"),
    dict(id="hr", dim="dim:heart_rate", kind="numeric", t=at(0, 0, 0), text="心率采样 1000 点（00:00-23:59）", note="数值流，机制侧机械压缩"),
]
DAY0_LABELS: dict[str, tuple[str, str]] = {
    "m01": ("DROP", "无意义发声"), "m02": ("DROP", "自言自语核对日期"), "m03": ("DROP", "一次性事务"),
    "m04": ("KEEP", "家人住院"), "m05": ("DROP", "回应无信息"), "m06": ("KEEP", "同事冲突"),
    "m07": ("DROP", "客套"), "m08": ("KEEP", "承诺+截止期"), "m09": ("DROP", "无信息"),
    "m10": ("DROP", "重复"), "m11": ("KEEP", "目标+计划"), "m12": ("DROP", "无决策"),
    "m13": ("KEEP", "轻度健康"), "m14": ("KEEP", "健康加重"), "m15": ("DROP", "玩笑噪声"),
    "m16": ("KEEP", "医疗进展"), "m17": ("DROP", "吐槽"), "m18": ("DROP", "无信息"),
    "p01": ("DROP", "小额日常"), "p02": ("KEEP", "大额住院"), "p03": ("DROP", "小额订阅"),
    "o01": ("KEEP", "送达时间"), "c01": ("KEEP", "体检节点"), "c02": ("KEEP", "周会"),
    "n01": ("KEEP", "工作条款"), "n02": ("DROP", "乱码"), "n03": ("KEEP", "待办"),
    "v01": ("DROP", "环境低值"), "v02": ("DROP", "环境低值"), "v03": ("KEEP", "佐证头晕"),
    "a01": ("DROP", "广告"), "a02": ("DROP", "无关推送"), "a03": ("KEEP", "行为事实"),
    "a04": ("DROP", "系统通知"), "x01": ("DROP", "无信息"), "x02": ("DROP", "重复"),
    "x03": ("KEEP", "外部压力"), "x04": ("KEEP", "社交邀约"), "hr": ("KEEP", "数值流"),
}
DAY0_CHECKS: list[tuple[str, tuple[str, ...]]] = [
    ("母亲住院（市二院心内科）", ("m04", "m16", "p02")),
    ("承诺周三前给张总合同", ("m08", "x03", "n01")),
    ("头晕加重（两次递进）", ("m13", "m14", "v03")),
    ("与小李的工作冲突", ("m06",)),
    ("减重五斤目标", ("m11",)),
    ("周五体检 / 周四周会", ("c01", "c02")),
    ("需带医保卡身份证", ("n03",)),
]
DAY0_KEYWORDS: dict[str, tuple[str, ...]] = {
    "母亲住院（市二院心内科）": ("妈", "母亲", "住院", "二院", "第二人民"),
    "承诺周三前给张总合同": ("合同", "张总", "周三"),
    "头晕加重（两次递进）": ("头晕", "晕"),
    "与小李的工作冲突": ("小李", "吵", "冲突"),
    "减重五斤目标": ("减", "体重", "斤"),
    "周五体检 / 周四周会": ("体检", "周会", "周五", "周四"),
    "需带医保卡身份证": ("医保卡", "身份证", "带"),
}
DAY0_HR = dict(baseline=70.0, spikes=[(15 * 60 + 35, 15 * 60 + 50, 128.0)], artifacts=[(9 * 60 + 30, 9 * 60 + 33, 78.0)])

# ============================================================================
# DAY 1  —— 2026-10-29（海鲜过敏 / 个税 / 玩笑辞职 / 钓鱼 / 运动心率）
# ============================================================================
DAY1_RECORDS: list[dict] = [
    dict(id="m01", dim="dim:mic_audio", kind="mic", t=at(1, 7, 5), text="额……那个……那个……", note="无意义发声"),
    dict(id="m02", dim="dim:mic_audio", kind="mic", t=at(1, 7, 40), text="今天周六对吧……不对周日。", note="自言自语核对日期"),
    dict(id="m03", dim="dim:mic_audio", kind="mic", t=at(1, 8, 10), text="喂快递放驿站了啊谢谢。", note="一次性事务"),
    dict(id="m04", dim="dim:mic_audio", kind="mic", t=at(1, 8, 30), text="我跟你说我今早跑步心率飙到150了，累死，不过练完了爽。", note="晨练真实飙升(非疾病)，保留健身事实"),
    dict(id="m05", dim="dim:mic_audio", kind="mic", t=at(1, 9, 15), text="我后天得把个税汇算清缴交了，不然要滞纳金。", note="【重要】个税截止"),
    dict(id="m06", dim="dim:mic_audio", kind="mic", t=at(1, 9, 40), text="哈哈哈我明天就辞职不干了哈哈。", note="玩笑式辞职，假紧急 → 必须 DROP"),
    dict(id="m07", dim="dim:mic_audio", kind="mic", t=at(1, 10, 20), text="啊行嗯好的。", note="客套"),
    dict(id="m08", dim="dim:mic_audio", kind="mic", t=at(1, 11, 30), text="下午胳膊起了一片疹子，痒得不行，可能是上午吃的那海鲜。", note="【重要】过敏健康事件"),
    dict(id="m09", dim="dim:mic_audio", kind="mic", t=at(1, 11, 32), text="我刚吃了颗氯雷他定。", note="【重要】服药，佐证过敏"),
    dict(id="m10", dim="dim:mic_audio", kind="mic", t=at(1, 12, 0), text="午饭随便吃点吧。", note="无决策"),
    dict(id="m11", dim="dim:mic_audio", kind="mic", t=at(1, 13, 10), text="疹子好多了，不怎么痒了。", note="【重要】健康随访"),
    dict(id="m12", dim="dim:mic_audio", kind="mic", t=at(1, 14, 0), text="气死我了，我老婆说我又不陪孩子，吵了一架。", note="【重要】夫妻冲突"),
    dict(id="m13", dim="dim:mic_audio", kind="mic", t=at(1, 15, 20), text="算了不说了。", note="无信息"),
    dict(id="m14", dim="dim:mic_audio", kind="mic", t=at(1, 16, 40), text="我定了明天带娃去动物园的票。", note="【重要】未来计划/承诺"),
    dict(id="m15", dim="dim:mic_audio", kind="mic", t=at(1, 18, 30), text="晚上吃啥呢随便。", note="无决策"),
    dict(id="m16", dim="dim:mic_audio", kind="mic", t=at(1, 20, 10), text="那个过敏的急诊挂号费我刷了卡，八百多。", note="【重要】急诊花费，佐证过敏"),
    dict(id="m17", dim="dim:mic_audio", kind="mic", t=at(1, 21, 50), text="烦这破输入法又卡。", note="吐槽"),
    dict(id="m18", dim="dim:mic_audio", kind="mic", t=at(1, 22, 30), text="睡了。", note="无信息"),
    dict(id="p01", dim="dim:payment", kind="pay", t=at(1, 8, 5), text="早餐 咖啡 18 元", note="小额日常"),
    dict(id="p02", dim="dim:payment", kind="pay", t=at(1, 16, 45), text="过敏急诊挂号 860 元", note="【重要】大额，佐证过敏"),
    dict(id="p03", dim="dim:payment", kind="pay", t=at(1, 21, 0), text="视频会员续费 25 元", note="小额订阅"),
    dict(id="o01", dim="dim:order", kind="order", t=at(1, 14, 30), text="订单：动物园门票 x2，预计明日使用", note="【重要】未来计划，佐证 m14"),
    dict(id="c01", dim="dim:calendar", kind="cal", t=at(1, 9, 0), text="日程：10-31 个税汇算清缴截止", note="【重要】截止期，佐证 m05"),
    dict(id="c02", dim="dim:calendar", kind="cal", t=at(1, 19, 0), text="日程：明晚家庭聚餐", note="中等价值"),
    dict(id="n01", dim="dim:note", kind="note", t=at(1, 11, 35), text="便签：氯雷他定 1片/日 吃3天", note="【重要】用药计划"),
    dict(id="n02", dim="dim:note", kind="note", t=at(1, 12, 50), text="便签：qwertyuiop", note="误触乱码"),
    dict(id="n03", dim="dim:note", kind="note", t=at(1, 20, 30), text="便签：记得带娃的水杯和帽子明天", note="【重要】待办"),
    dict(id="v01", dim="dim:camera_visual", kind="cam", t=at(1, 7, 25), text="画面：床头柜上有手机和眼镜。", note="环境低值"),
    dict(id="v02", dim="dim:camera_visual", kind="cam", t=at(1, 12, 15), text="画面：餐桌两人三菜。", note="环境低值"),
    dict(id="v03", dim="dim:camera_visual", kind="cam", t=at(1, 11, 35), text="画面：手臂可见一片红色皮疹。", note="【重要】佐证过敏 m08"),
    dict(id="a01", dim="dim:app_usage", kind="app", t=at(1, 9, 50), text="【XX商城】限时秒杀3折，点领券>>", note="广告"),
    dict(id="a02", dim="dim:app_usage", kind="app", t=at(1, 13, 40), text="使用 阅读App 32 分钟", note="行为事实，中等价值"),
    dict(id="a03", dim="dim:app_usage", kind="app", t=at(1, 17, 0), text="【系统】存储不足建议清理", note="系统通知"),
    dict(id="a04", dim="dim:app_usage", kind="app", t=at(1, 19, 20), text="【银行】您尾号1234支行有一笔860元支出", note="【重要】银行通知，佐证 p02"),
    dict(id="x01", dim="dim:external_chat", kind="chat", t=at(1, 10, 0), text="同事老赵：在吗", note="无信息"),
    dict(id="x02", dim="dim:external_chat", kind="chat", t=at(1, 10, 1), text="同事老赵：在吗", note="重复催促"),
    dict(id="x03", dim="dim:external_chat", kind="chat", t=at(1, 10, 5), text="同事老赵：领导说税的事周五前必须交。", note="【重要】外部压力，佐证 m05/c01"),
    dict(id="x04", dim="dim:external_chat", kind="chat", t=at(1, 18, 0), text="朋友小美：周末喝咖啡去不去", note="社交邀约，中等价值"),
    dict(id="x05", dim="dim:external_chat", kind="chat", t=at(1, 15, 30), text="【10086】尊敬的客户，您的话费礼包待领取，点击 t.cn/xxx", note="广告/垃圾，形似真通知 → 必须 DROP"),
    dict(id="x06", dim="dim:external_chat", kind="chat", t=at(1, 20, 50), text="【安全中心】您的账户已被锁定，立即验证 t.cn/lock", note="钓鱼，形似真通知 → 必须 DROP"),
    dict(id="hr", dim="dim:heart_rate", kind="numeric", t=at(1, 0, 0), text="心率采样 1000 点（00:00-23:59）", note="数值流"),
]
DAY1_LABELS: dict[str, tuple[str, str]] = {
    "m01": ("DROP", "发声"), "m02": ("DROP", "日期"), "m03": ("DROP", "一次性"),
    "m04": ("KEEP", "晨练事实"), "m05": ("KEEP", "个税截止"), "m06": ("DROP", "玩笑辞职"),
    "m07": ("DROP", "客套"), "m08": ("KEEP", "过敏"), "m09": ("KEEP", "服药"),
    "m10": ("DROP", "无决策"), "m11": ("KEEP", "健康随访"), "m12": ("KEEP", "夫妻冲突"),
    "m13": ("DROP", "无信息"), "m14": ("KEEP", "动物园计划"), "m15": ("DROP", "无决策"),
    "m16": ("KEEP", "急诊花费"), "m17": ("DROP", "吐槽"), "m18": ("DROP", "无信息"),
    "p01": ("DROP", "小额"), "p02": ("KEEP", "急诊860"), "p03": ("DROP", "订阅"),
    "o01": ("KEEP", "动物园票"), "c01": ("KEEP", "个税节点"), "c02": ("KEEP", "家庭聚餐"),
    "n01": ("KEEP", "用药计划"), "n02": ("DROP", "乱码"), "n03": ("KEEP", "待办"),
    "v01": ("DROP", "环境"), "v02": ("DROP", "环境"), "v03": ("KEEP", "皮疹佐证"),
    "a01": ("DROP", "广告"), "a02": ("KEEP", "阅读行为"), "a03": ("DROP", "系统通知"),
    "a04": ("KEEP", "银行通知"), "x01": ("DROP", "无信息"), "x02": ("DROP", "重复"),
    "x03": ("KEEP", "税务压力"), "x04": ("KEEP", "社交邀约"), "x05": ("DROP", "垃圾短信"),
    "x06": ("DROP", "钓鱼"), "hr": ("KEEP", "数值流"),
}
DAY1_CHECKS: list[tuple[str, tuple[str, ...]]] = [
    ("海鲜过敏起疹+服药", ("m08", "m09", "v03", "n01")),
    ("个税汇算清缴截止10-31", ("m05", "c01", "x03")),
    ("与妻子因陪孩子吵架", ("m12",)),
    ("明带娃去动物园", ("m14", "o01")),
    ("过敏急诊花费860", ("p02", "a04")),
    ("明晚家庭聚餐", ("c02",)),
    ("记得带娃水杯帽子", ("n03",)),
]
DAY1_KEYWORDS: dict[str, tuple[str, ...]] = {
    "海鲜过敏起疹+服药": ("过敏", "疹", "氯雷他定", "皮疹"),
    "个税汇算清缴截止10-31": ("税", "汇算", "滞纳金", "个税"),
    "与妻子因陪孩子吵架": ("老婆", "吵", "孩子", "娃"),
    "明带娃去动物园": ("动物园", "娃"),
    "过敏急诊花费860": ("860", "急诊", "挂号"),
    "明晚家庭聚餐": ("聚餐",),
    "记得带娃水杯帽子": ("水杯", "帽子", "带"),
}
DAY1_HR = dict(baseline=68.0,
               spikes=[(8 * 60, 8 * 60 + 20, 150.0), (11 * 60 + 25, 11 * 60 + 45, 95.0)],
               artifacts=[(10 * 60, 10 * 60 + 2, 76.0)])

# ============================================================================
# DAY 2  —— 2026-10-30（错过火车 / 夜间低血氧 / 老板周一谈 / 孩子话剧 / 钓鱼锁定）
# ============================================================================
DAY2_RECORDS: list[dict] = [
    dict(id="m01", dim="dim:mic_audio", kind="mic", t=at(2, 6, 50), text="呃……那个……", note="无意义发声"),
    dict(id="m02", dim="dim:mic_audio", kind="mic", t=at(2, 7, 10), text="今天周一？对周一。", note="自言自语核对日期"),
    dict(id="m03", dim="dim:mic_audio", kind="mic", t=at(2, 7, 40), text="糟了我刚看手机火车晚点了……不对是我就没赶上，7:20那班走了。", note="【重要】错过火车"),
    dict(id="m04", dim="dim:mic_audio", kind="mic", t=at(2, 7, 45), text="我改签了9点的，贵了八十块。", note="【重要】改签花费"),
    dict(id="m05", dim="dim:mic_audio", kind="mic", t=at(2, 8, 30), text="昨晚没睡好，血氧仪显示夜里最低91%，有点低。", note="【重要】夜间低血氧信号"),
    dict(id="m06", dim="dim:mic_audio", kind="mic", t=at(2, 9, 20), text="啊行好。", note="客套"),
    dict(id="m07", dim="dim:mic_audio", kind="mic", t=at(2, 10, 15), text="老板刚发微信说周一找我谈谈。", note="【重要】模糊工作/关系信号(边界项，设计保留)"),
    dict(id="m08", dim="dim:mic_audio", kind="mic", t=at(2, 11, 0), text="孩子学校下周三有话剧表演，得去。", note="【重要】未来节点"),
    dict(id="m09", dim="dim:mic_audio", kind="mic", t=at(2, 12, 10), text="中午吃啥随便。", note="无决策"),
    dict(id="m10", dim="dim:mic_audio", kind="mic", t=at(2, 13, 30), text="电视里放着新闻，听不清说了啥。", note="电视环境噪声，无事实 → DROP"),
    dict(id="m11", dim="dim:mic_audio", kind="mic", t=at(2, 14, 20), text="对了那个，嗯，我答应周爸把项目月报周五前发他。", note="【重要】承诺+截止期，裹在填充词里"),
    dict(id="m12", dim="dim:mic_audio", kind="mic", t=at(2, 15, 0), text="烦死了又卡。", note="吐槽"),
    dict(id="m13", dim="dim:mic_audio", kind="mic", t=at(2, 16, 30), text="血氧今天白天正常97%，还行。", note="【重要】健康随访"),
    dict(id="m14", dim="dim:mic_audio", kind="mic", t=at(2, 18, 0), text="晚上吃点清淡的。", note="无决策"),
    dict(id="m15", dim="dim:mic_audio", kind="mic", t=at(2, 19, 40), text="那个月报的模板在电脑D盘。", note="【重要】工作事实，佐证 m11"),
    dict(id="m16", dim="dim:mic_audio", kind="mic", t=at(2, 21, 10), text="睡了明天还得早起。", note="无信息"),
    dict(id="m17", dim="dim:mic_audio", kind="mic", t=at(2, 22, 0), text="（电视声）……广告……（杂音）", note="环境噪声无事实 → DROP"),
    dict(id="p01", dim="dim:payment", kind="pay", t=at(2, 7, 50), text="火车改签补差 80 元", note="【重要】佐证 m04"),
    dict(id="p02", dim="dim:payment", kind="pay", t=at(2, 12, 0), text="午餐 35 元", note="小额日常"),
    dict(id="p03", dim="dim:payment", kind="pay", t=at(2, 20, 0), text="会员续费 30 元", note="小额订阅"),
    dict(id="o01", dim="dim:order", kind="order", t=at(2, 8, 0), text="订单：血氧仪耗材 x1 预计周三到", note="【重要】健康相关"),
    dict(id="c01", dim="dim:calendar", kind="cal", t=at(2, 9, 0), text="日程：下周三 孩子学校话剧", note="【重要】佐证 m08"),
    dict(id="c02", dim="dim:calendar", kind="cal", t=at(2, 10, 30), text="日程：周一 与老板一对一面谈", note="【重要】佐证 m07"),
    dict(id="n01", dim="dim:note", kind="note", t=at(2, 11, 5), text="便签：项目月报 — 模板在D盘，含Q3数据", note="【重要】工作事实"),
    dict(id="n02", dim="dim:note", kind="note", t=at(2, 13, 20), text="便签：zxcvbnm", note="误触乱码"),
    dict(id="n03", dim="dim:note", kind="note", t=at(2, 19, 30), text="便签：给孩子带话剧演出的衣服", note="【重要】待办"),
    dict(id="v01", dim="dim:camera_visual", kind="cam", t=at(2, 7, 15), text="画面：玄关地上有行李箱和鞋。", note="环境低值"),
    dict(id="v02", dim="dim:camera_visual", kind="cam", t=at(2, 12, 20), text="画面：餐桌一人一菜。", note="环境低值"),
    dict(id="v03", dim="dim:camera_visual", kind="cam", t=at(2, 8, 35), text="画面：床边放着血氧仪，屏幕显示91%。", note="【重要】佐证 m05"),
    dict(id="a01", dim="dim:app_usage", kind="app", t=at(2, 9, 40), text="【XX新闻】您关注球队获胜", note="无关推送"),
    dict(id="a02", dim="dim:app_usage", kind="app", t=at(2, 13, 50), text="使用 邮件App 40 分钟", note="行为事实，中等价值"),
    dict(id="a03", dim="dim:app_usage", kind="app", t=at(2, 17, 0), text="【系统】电量低", note="系统通知"),
    dict(id="a04", dim="dim:app_usage", kind="app", t=at(2, 20, 30), text="【安全】账户异常已被锁定，点击 t.cn/xx 验证", note="钓鱼，形似真通知 → 必须 DROP"),
    dict(id="x01", dim="dim:external_chat", kind="chat", t=at(2, 9, 10), text="同事大刘：在吗", note="无信息"),
    dict(id="x02", dim="dim:external_chat", kind="chat", t=at(2, 9, 11), text="同事大刘：在吗", note="重复催促"),
    dict(id="x03", dim="dim:external_chat", kind="chat", t=at(2, 10, 20), text="老板：周一详谈，别紧张。", note="【重要】佐证 m07/c02"),
    dict(id="x04", dim="dim:external_chat", kind="chat", t=at(2, 18, 30), text="朋友阿强：周末钓鱼去不去", note="社交邀约，中等价值"),
    dict(id="x05", dim="dim:external_chat", kind="chat", t=at(2, 15, 40), text="【10086】话费礼包待领 t.cn/yy", note="广告，形似真通知 → 必须 DROP"),
    dict(id="hr", dim="dim:heart_rate", kind="numeric", t=at(2, 0, 0), text="心率采样 1000 点（00:00-23:59）", note="数值流"),
]
DAY2_LABELS: dict[str, tuple[str, str]] = {
    "m01": ("DROP", "发声"), "m02": ("DROP", "日期"), "m03": ("KEEP", "错过火车"),
    "m04": ("KEEP", "改签花费"), "m05": ("KEEP", "低血氧"), "m06": ("DROP", "客套"),
    "m07": ("KEEP", "老板面谈"), "m08": ("KEEP", "孩子话剧"), "m09": ("DROP", "无决策"),
    "m10": ("DROP", "电视噪声"), "m11": ("KEEP", "月报承诺"), "m12": ("DROP", "吐槽"),
    "m13": ("KEEP", "白天血氧"), "m14": ("DROP", "无决策"), "m15": ("KEEP", "月报模板"),
    "m16": ("DROP", "无信息"), "m17": ("DROP", "电视噪声"),
    "p01": ("KEEP", "改签80"), "p02": ("DROP", "小额"), "p03": ("DROP", "订阅"),
    "o01": ("KEEP", "血氧耗材"), "c01": ("KEEP", "话剧节点"), "c02": ("KEEP", "面谈节点"),
    "n01": ("KEEP", "月报事实"), "n02": ("DROP", "乱码"), "n03": ("KEEP", "待办"),
    "v01": ("DROP", "环境"), "v02": ("DROP", "环境"), "v03": ("KEEP", "血氧佐证"),
    "a01": ("DROP", "推送"), "a02": ("KEEP", "邮件行为"), "a03": ("DROP", "系统通知"),
    "a04": ("DROP", "钓鱼"), "x01": ("DROP", "无信息"), "x02": ("DROP", "重复"),
    "x03": ("KEEP", "老板证实"), "x04": ("KEEP", "社交邀约"), "x05": ("DROP", "广告"),
    "hr": ("KEEP", "数值流"),
}
DAY2_CHECKS: list[tuple[str, tuple[str, ...]]] = [
    ("错过7:20火车并改签", ("m03", "m04", "p01")),
    ("夜间低血氧91%", ("m05", "v03")),
    ("老板周一面谈", ("m07", "c02", "x03")),
    ("孩子下周三话剧", ("m08", "c01")),
    ("周五前交项目月报给周爸", ("m11", "n01", "m15")),
    ("白天血氧正常97%", ("m13",)),
    ("给孩子带话剧衣服", ("n03",)),
]
DAY2_KEYWORDS: dict[str, tuple[str, ...]] = {
    "错过7:20火车并改签": ("火车", "改签", "赶上"),
    "夜间低血氧91%": ("血氧", "91", "低"),
    "老板周一面谈": ("老板", "面谈", "谈", "周一"),
    "孩子下周三话剧": ("话剧", "表演"),
    "周五前交项目月报给周爸": ("月报", "周爸", "周五", "D盘"),
    "白天血氧正常97%": ("97", "血氧", "正常"),
    "给孩子带话剧衣服": ("衣服", "带"),
}
DAY2_HR = dict(baseline=66.0,
               spikes=[(7 * 60 + 35, 7 * 60 + 55, 110.0)],
               artifacts=[(14 * 60 + 30, 14 * 60 + 32, 73.0)])


# ============================================================================
# 汇总
# ============================================================================
DAYS: list[dict] = [
    dict(name="DAY1_2026-10-28", records=DAY0_RECORDS, labels=DAY0_LABELS,
         checks=DAY0_CHECKS, keywords=DAY0_KEYWORDS, hr=DAY0_HR),
    dict(name="DAY2_2026-10-29", records=DAY1_RECORDS, labels=DAY1_LABELS,
         checks=DAY1_CHECKS, keywords=DAY1_KEYWORDS, hr=DAY1_HR),
    dict(name="DAY3_2026-10-30", records=DAY2_RECORDS, labels=DAY2_LABELS,
         checks=DAY2_CHECKS, keywords=DAY2_KEYWORDS, hr=DAY2_HR),
]


def build_hr_samples(day_idx: int, n: int = 1000) -> list:
    """生成连续心率数值流：基线 + 真实飙升段(机制应捕获) + 运动/佩戴伪影小凸起(低于阈值，机制应忽略)。"""
    from aios_core.ingest import NumericSample
    cfg = DAYS[day_idx]["hr"]
    base = DATES[day_idx]
    baseline = cfg["baseline"]
    spikes = { (s, e): v for (s, e, v) in cfg["spikes"] }
    artifacts = { (s, e): v for (s, e, v) in cfg.get("artifacts", []) }
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
