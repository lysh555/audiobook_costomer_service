from __future__ import annotations

from fastapi import FastAPI

from app.api import router


openapi_tags = [
    {
        "name": "系统",
        "description": "服务可用性与基础检查接口。",
    },
    {
        "name": "用户",
        "description": "查询书友相关的听书订单列表和有声书库。",
    },
    {
        "name": "订单",
        "description": "听书订单详情与订单状态查询。",
    },
    {
        "name": "有声书",
        "description": "有声书搜索、详情查询接口。",
    },
    {
        "name": "会员与优惠",
        "description": "VIP 权益查询与优惠码兑换接口。",
    },
]


app = FastAPI(
    title="Atguigu 听书业务服务",
    version="0.1.0",
    description="为 atguigu 客服项目提供听书订单、有声书查询、会员权益与优惠码兑换能力的示例听书业务服务。",
    openapi_tags=openapi_tags,
)

app.include_router(router)