"""
TdxQuant 行情网关。连接时填 用户名=通达信安装目录/PYPlugins/user。
"""
from datetime import datetime
import json
import os
import sys
from typing import Any

from vnpy.event import EventEngine
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.constant import Exchange, Product
from vnpy.trader.object import (
    SubscribeRequest,
    OrderRequest,
    CancelRequest,
    TickData,
    ContractData,
)
from vnpy.trader.utility import ZoneInfo


CHINA_TZ = ZoneInfo("Asia/Shanghai")


EXCHANGE_TDX2VT = {
    "SH": Exchange.SSE,
    "SZ": Exchange.SZSE,
}
EXCHANGE_VT2TDX = {v: k for k, v in EXCHANGE_TDX2VT.items()}

# 沪深 A 股
STOCK_LIST_MARKET_HS_A = "50"


class TdxGateway(BaseGateway):
    """VeighNa 对接 TdxQuant 实时行情的网关。"""

    default_name: str = "TDXQUANT"

    default_setting: dict = {
        "通达信Python插件路径": "C:/new_tdx64/PYPlugins/user",
    }

    exchanges: list = list(EXCHANGE_TDX2VT.values())

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        super().__init__(event_engine, gateway_name)
        self.tq: Any = None
        self.subscribed: set[str] = set()
        self.symbol_map: dict[str, ContractData] = {}

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        if self.tq is not None:
            return

        username: str = setting["通达信Python插件路径"].strip()
        if not username or not os.path.isdir(username):
            self.write_log("TdxQuant接口连接失败：路径不存在")
            return

        if username not in sys.path:
            sys.path.insert(0, username)
        try:
            import tqcenter
            self.tq = tqcenter.tq
        except ImportError as ex:
            self.write_log(f"TdxQuant接口连接失败：{ex}")
            return

        self.tq.initialize(__file__)

        self.query_contract()
        self.write_log("TdxQuant接口连接成功")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        if self.tq is None:
            return

        if req.exchange not in EXCHANGE_VT2TDX:
            self.write_log(f"不支持的交易所：{req.exchange}")
            return

        tdx_symbol: str = f"{req.symbol}.{EXCHANGE_VT2TDX[req.exchange]}"
        self.subscribed.add(tdx_symbol)
        self.tq.subscribe_hq(stock_list=[tdx_symbol], callback=self.handle_msg)

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        return ""

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        pass

    def query_account(self) -> None:
        """查询资金"""
        pass

    def query_position(self) -> None:
        """查询持仓"""
        pass

    def close(self) -> None:
        """关闭接口"""
        if self.tq is not None:
            if self.subscribed:
                self.tq.unsubscribe_hq(stock_list=list(self.subscribed))
            self.tq.close()

    def query_contract(self) -> None:
        """查询合约"""
        raw: list = self.tq.get_stock_list(market=STOCK_LIST_MARKET_HS_A)
        for code in raw:
            if "." not in code:
                continue

            symbol, suffix = code.rsplit(".", 1)
            exchange: Exchange | None = EXCHANGE_TDX2VT.get(suffix.upper())
            if exchange is None:
                continue

            contract: ContractData = ContractData(
                symbol=symbol,
                exchange=exchange,
                name=symbol,
                product=Product.EQUITY,
                size=1,
                pricetick=0.01,
                min_volume=1,
                gateway_name=self.gateway_name,
            )
            self.on_contract(contract)
            self.symbol_map[code] = contract

        self.write_log("合约信息查询成功")

    def handle_msg(self, datas: str) -> None:
        """处理行情推送"""
        obj: dict = json.loads(datas)
        code: str = obj["Code"]

        contract: ContractData | None = self.symbol_map.get(code)
        if contract is None:
            return

        snap: dict = self.tq.get_market_snapshot(stock_code=code)
        if snap.get("ErrorId") != "0":
            return

        buyp: list = snap["Buyp"][:5]
        sellp: list = snap["Sellp"][:5]
        buyv: list = snap["Buyv"][:5]
        sellv: list = snap["Sellv"][:5]
        dt: datetime = datetime.now(CHINA_TZ)
        tick: TickData = TickData(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            datetime=dt,
            open_price=float(snap["Open"]),
            high_price=float(snap["Max"]),
            low_price=float(snap["Min"]),
            pre_close=float(snap["LastClose"]),
            last_price=float(snap["Now"]),
            last_volume=float(snap["NowVol"]),
            volume=float(snap["Volume"]),
            turnover=round(float(snap["Amount"]) * 10000.0, 1),
            bid_price_1=float(buyp[0]),
            bid_price_2=float(buyp[1]),
            bid_price_3=float(buyp[2]),
            bid_price_4=float(buyp[3]),
            bid_price_5=float(buyp[4]),
            ask_price_1=float(sellp[0]),
            ask_price_2=float(sellp[1]),
            ask_price_3=float(sellp[2]),
            ask_price_4=float(sellp[3]),
            ask_price_5=float(sellp[4]),
            bid_volume_1=float(buyv[0]),
            bid_volume_2=float(buyv[1]),
            bid_volume_3=float(buyv[2]),
            bid_volume_4=float(buyv[3]),
            bid_volume_5=float(buyv[4]),
            ask_volume_1=float(sellv[0]),
            ask_volume_2=float(sellv[1]),
            ask_volume_3=float(sellv[2]),
            ask_volume_4=float(sellv[3]),
            ask_volume_5=float(sellv[4]),
            gateway_name=self.gateway_name,
        )
        self.on_tick(tick)
