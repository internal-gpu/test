"""AI 价值链股票池 - 手动维护的标的知识库"""

from .models import StockMeta, AIChainSegment, Market

S = AIChainSegment

# ============================================================
# AI 价值链股票池
# ai_chain_score: 0-100, AI 营收占比/纯度评分
# ============================================================

UNIVERSE: dict[str, StockMeta] = {}


def _add(ticker, name, name_cn, market, segment, sub_theme, score, notes=""):
    UNIVERSE[ticker] = StockMeta(
        ticker=ticker, name=name, name_cn=name_cn,
        market=market, segment=segment,
        sub_theme=sub_theme, ai_chain_score=score, notes=notes,
    )


# === Models/Cloud 模型与云 ===
_add("GOOGL", "Alphabet", "谷歌", Market.US, S.MODELS_CLOUD,
     "Gemini + GCP AI", 60, "搜索广告仍是主营，但AI投入巨大")
_add("MSFT", "Microsoft", "微软", Market.US, S.MODELS_CLOUD,
     "Azure AI + Copilot", 55, "OpenAI战略合作，Copilot全面铺开")
_add("META", "Meta Platforms", "Meta", Market.US, S.MODELS_CLOUD,
     "LLaMA + AI广告", 50, "开源LLaMA，AI驱动广告推荐")
_add("AMZN", "Amazon", "亚马逊", Market.US, S.MODELS_CLOUD,
     "AWS Bedrock + Anthropic", 45, "AWS云AI平台，Anthropic投资方")
_add("BIDU", "Baidu", "百度", Market.US, S.MODELS_CLOUD,
     "文心一言", 55, "国产大模型领先，但广告营收占比高")
_add("9698.HK", "MiniMax", "MiniMax", Market.HK, S.MODELS_CLOUD,
     "AI大模型", 95, "纯AI大模型公司，海螺AI/星野")
_add("0700.HK", "Tencent", "腾讯", Market.HK, S.MODELS_CLOUD,
     "混元大模型+云", 35, "AI是增长引擎但游戏社交仍是基本盘")
_add("9988.HK", "Alibaba", "阿里巴巴", Market.HK, S.MODELS_CLOUD,
     "通义千问+阿里云", 35, "电商为主，云智能分拆后AI占比提升")
_add("SNOW", "Snowflake", "Snowflake", Market.US, S.MODELS_CLOUD,
     "AI数据云", 65, "Cortex AI平台，数据+AI融合")
_add("PLTR", "Palantir", "Palantir", Market.US, S.MODELS_CLOUD,
     "AI平台AIP", 80, "企业AI平台，国防+商业双轮驱动")
_add("AI", "C3.ai", "C3.ai", Market.US, S.MODELS_CLOUD,
     "企业AI平台", 90, "纯企业AI应用平台")

# === Chips/GPU 芯片 ===
_add("NVDA", "NVIDIA", "英伟达", Market.US, S.CHIPS_GPU,
     "GPU + CUDA", 90, "AI算力绝对垄断，数据中心营收占比超80%")
_add("AMD", "AMD", "AMD", Market.US, S.CHIPS_GPU,
     "MI系列AI GPU", 60, "MI300X追赶NVIDIA，数据中心增长迅猛")
_add("TSM", "TSMC", "台积电", Market.US, S.CHIPS_GPU,
     "AI芯片代工", 65, "全球AI芯片代工垄断，3nm/2nm领先")
_add("AVGO", "Broadcom", "博通", Market.US, S.CHIPS_GPU,
     "定制AI芯片+网络", 70, "Google TPU定制芯片，AI网络交换芯片")
_add("MRVL", "Marvell", "Marvell", Market.US, S.CHIPS_GPU,
     "定制AI芯片", 75, "亚马逊Trainium/微软Maia定制芯片")
_add("ARM", "Arm Holdings", "ARM", Market.US, S.CHIPS_GPU,
     "AI芯片架构", 55, "AI芯片IP授权，CPU架构主导移动和边缘AI")
_add("INTC", "Intel", "英特尔", Market.US, S.CHIPS_GPU,
     "Gaudi AI + 代工", 30, "AI芯片落后，转型代工")
_add("MU", "Micron", "美光", Market.US, S.STORAGE,
     "HBM + AI存储", 70, "HBM3E需求爆发，AI服务器DRAM")
_add("QCOM", "Qualcomm", "高通", Market.US, S.CHIPS_GPU,
     "端侧AI芯片", 40, "骁龙端侧AI，但手机营收仍为主")

# === Optical/Networking 光通信与网络 ===
_add("LITE", "Lumentum", "Lumentum", Market.US, S.OPTICAL_NETWORKING,
     "光模块/激光器", 75, "800G/1.6T光模块核心供应商")
_add("GLW", "Corning", "康宁", Market.US, S.OPTICAL_NETWORKING,
     "光纤+特种玻璃", 50, "AI数据中心光纤需求，但显示玻璃仍占大头")
_add("ANET", "Arista Networks", "Arista", Market.US, S.OPTICAL_NETWORKING,
     "AI数据中心交换机", 75, "AI集群网络首选，400G/800G交换机")
_add("COHR", "Coherent", "Coherent", Market.US, S.OPTICAL_NETWORKING,
     "光模块/激光器", 70, "800G光模块，数据中心互连")
_add("CIEN", "Ciena", "Ciena", Market.US, S.OPTICAL_NETWORKING,
     "光网络设备", 55, "WaveLogic 6 AI优化光网络")
_add("INFN", "Infinera", "Infinera", Market.US, S.OPTICAL_NETWORKING,
     "光传输", 60, "已被诺基亚收购，ICE-7光引擎")
_add("AAOI", "Applied Optoelectronics", "应用光电", Market.US, S.OPTICAL_NETWORKING,
     "光模块", 70, "数据中心光模块，400G/800G")

# === Storage 存储 ===
_add("WDC", "Western Digital", "西部数据", Market.US, S.STORAGE,
     "AI存储HDD/SSD", 40, "数据中心存储需求增长")
_add("STX", "Seagate", "希捷", Market.US, S.STORAGE,
     "AI数据存储", 35, "大容量HDD for AI数据湖")
_add("PSTG", "Pure Storage", "Pure Storage", Market.US, S.STORAGE,
     "AI闪存阵列", 65, "全闪存阵列，AI训练数据加速")
_add("NTAP", "NetApp", "NetApp", Market.US, S.STORAGE,
     "AI数据管理", 50, "混合云AI数据基础设施")

# === HPC/Infrastructure 基础设施 ===
_add("VRT", "Vertiv", "维谛技术", Market.US, S.HPC_INFRA,
     "数据中心散热/电力", 80, "AI数据中心液冷+配电，受益于算力密度提升")
_add("SMCI", "Super Micro", "超微电脑", Market.US, S.HPC_INFRA,
     "AI服务器", 85, "AI服务器龙头，GPU服务器整机")
_add("DELL", "Dell Technologies", "戴尔", Market.US, S.HPC_INFRA,
     "AI服务器+存储", 45, "PowerEdge AI服务器，但PC/企业IT仍为主")
_add("EQIX", "Equinix", "Equinix", Market.US, S.HPC_INFRA,
     "AI数据中心REITs", 40, "全球数据中心，AI租户增长")
_add("DLR", "Digital Realty", "Digital Realty", Market.US, S.HPC_INFRA,
     "AI数据中心REITs", 40, "大型AI数据中心租赁")
_add("CRWV", "CoreWeave", "CoreWeave", Market.US, S.HPC_INFRA,
     "GPU云计算", 95, "纯GPU云计算平台，NVIDIA紧密合作")

# === Mining-to-HPC 矿转HPC ===
_add("CLSK", "CleanSpark", "CleanSpark", Market.US, S.MINING_TO_HPC,
     "比特币挖矿→HPC", 55, "矿机转型HPC/AI算力")
_add("WGMI", "Valkyrie Bitcoin Miners ETF", "矿股ETF", Market.US, S.MINING_TO_HPC,
     "矿股ETF", 40, "一篮子矿股，部分公司转型HPC")
_add("IREN", "Iris Energy", "Iris Energy", Market.US, S.MINING_TO_HPC,
     "矿→HPC/AI", 65, "积极转型AI/HPC，与NVDA合作GPU云")
_add("CIFR", "Cipher Mining", "Cipher Mining", Market.US, S.MINING_TO_HPC,
     "矿→HPC", 55, "低成本电力+HPC转型")
_add("CORZ", "Core Scientific", "Core Scientific", Market.US, S.MINING_TO_HPC,
     "矿→HPC", 70, "与CoreWeave签大单，全面转型HPC托管")
_add("BTBT", "Bit Digital", "Bit Digital", Market.US, S.MINING_TO_HPC,
     "矿→HPC/AI", 60, "GPU云服务+挖矿双线并行")
_add("HUT", "Hut 8 Corp", "Hut 8", Market.US, S.MINING_TO_HPC,
     "矿→HPC", 60, "数据中心+挖矿，AI基础设施")
_add("MARA", "Marathon Digital", "Marathon", Market.US, S.MINING_TO_HPC,
     "比特币矿→AI", 35, "主要仍是矿，HPC转型较慢")


def get_stock_meta(ticker: str) -> StockMeta | None:
    """查询股票元数据"""
    return UNIVERSE.get(ticker)


def get_all_by_segment(segment: AIChainSegment) -> list[StockMeta]:
    """按板块获取股票列表"""
    return [s for s in UNIVERSE.values() if s.segment == segment]


def get_all_segments() -> list[AIChainSegment]:
    """获取所有板块"""
    return list(AIChainSegment)


def search_universe(query: str) -> list[StockMeta]:
    """搜索股票池（模糊匹配ticker/name）"""
    q = query.upper()
    results = []
    for s in UNIVERSE.values():
        if q in s.ticker.upper() or q in s.name.upper() or q in s.name_cn:
            results.append(s)
    return results
