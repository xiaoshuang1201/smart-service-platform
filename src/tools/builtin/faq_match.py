# FAQ 精确匹配工具 — 高频问题零延迟响应，无需调用 LLM

from __future__ import annotations
import re
from typing import Any

# FAQ 库 — 生产环境可迁移到 Redis
FAQ_DATABASE: list[dict[str, Any]] = [
    {"keywords": ["退货", "退款", "退钱"], "question": "如何申请退货退款？",
     "answer": "您可以在订单详情页点击「申请售后」，选择退货退款。审核通过后，请在3天内将商品寄回。退款将在收到商品后1-3个工作日原路返回。"
             "退货地址将以短信形式发送到您下单手机号。"},
    {"keywords": ["换货", "换一个"], "question": "如何换货？",
     "answer": "在订单详情页点击「申请售后」→「换货」，选择需要更换的商品和原因，审核通过后我们将先寄出新商品，您收到后再寄回旧商品。"},
    {"keywords": ["发货", "什么时候发", "发货时间", "几天发货", "还没发货"],
     "question": "订单什么时候发货？",
     "answer": "一般商品下单后48小时内发货，预售商品以页面标注时间为准。大促期间发货可能延迟至72小时。"},
    {"keywords": ["物流", "快递", "到哪了", "运单", "查物流"],
     "question": "如何查询物流信息？",
     "answer": "在订单详情页可以查看实时物流轨迹。如果没有显示，请提供订单号我帮您查询。"},
    {"keywords": ["客服电话", "联系电话", "人工客服"],
     "question": "客服电话是多少？",
     "answer": "客服热线 400-800-8888，服务时间：周一至周日 9:00-21:00。"},
    {"keywords": ["会员", "积分", "等级", "VIP"],
     "question": "会员等级和积分有什么权益？",
     "answer": "金牌会员享9折优惠+免运费，银牌会员享95折。积分可在积分商城兑换优惠券和礼品。您可以说出手机号我帮您查询。"},
    {"keywords": ["优惠券", "优惠", "折扣", "满减", "领券"],
     "question": "在哪里领取优惠券？",
     "answer": "您可以在App首页「领券中心」或商品详情页领取优惠券。新人首单可领取满99减20专享券。"},
]

class FAQMatchTool:
    name = "faq_match"
    description = "高精度FAQ匹配，无需LLM，毫秒级响应"
    params_schema = {"query": {"type": "string", "required": True, "description": "用户问题文本"}}

    # FIXME: threshold 设太低容易误匹配(比如只命中一个无关关键词),
    # 设太高又召回不够。0.4 是试了20条测试问题后折中的，后面用 Ragas 系统评估一下
    async def execute(self, query: str, threshold: float = 0.4, **kwargs) -> str | None:
        """关键词匹配 FAQ"""
        query_lower = query.lower()
        best_score = 0.0
        best_answer = None

        for faq in FAQ_DATABASE:
            score = 0.0
            for kw in faq["keywords"]:
                if kw.lower() in query_lower:
                    score += 1.0 / len(faq["keywords"])  # 归一化
            if score > best_score:
                best_score = score
                best_answer = faq["answer"]

        if best_score >= threshold and best_answer:
            return best_answer
        return None
