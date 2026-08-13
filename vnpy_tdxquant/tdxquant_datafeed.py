"""
TdxQuant 数据服务接口。
需先启动通达信客户端并登录；全局配置 datafeed.name=tdxquant，datafeed.username=通达信安装目录/PYPlugins/user。
"""
from datetime import timedelta
from collections.abc import Callable
import os
import sys
from typing import Any

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest, TickData
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.utility import ZoneInfo
from vnpy.trader.setting import SETTINGS

CHINA_TZ = ZoneInfo("Asia/Shanghai")

INTERVAL_VT2TDX: dict[Interval, str] = {
    Interval.MINUTE: "1m",
    Interval.DAILY: "1d",
}

# 通达信 K 线时间为结束时点，转为 VeighNa 开始时点
INTERVAL_ADJUSTMENT: dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.DAILY: timedelta(),
}

STOCK_EXCHANGES: set[Exchange] = {Exchange.SSE, Exchange.SZSE}

EXCHANGE_SUFFIX: dict[Exchange, str] = {
    Exchange.SSE: "SH",
    Exchange.SZSE: "SZ",
}


class TdxDatafeed(BaseDatafeed):
    """通达信 TdxQuant 数据服务接口"""

    def __init__(self) -> None:
        """"""
        self.path: str = SETTINGS["datafeed.username"]
        self.tq: Any = None
        self.inited: bool = False

    def init(self, output: Callable = print) -> bool:
        """初始化"""
        if self.inited:
            return True

        if not self.path or not os.path.isdir(self.path):
            output("TdxQuant数据服务初始化失败：datafeed.username 路径无效或不存在")
            return False

        if self.path not in sys.path:
            sys.path.insert(0, self.path)
        try:
            from tqcenter import tq as _tq_loaded
            self.tq = _tq_loaded
        except ImportError:
            pass
        if self.tq is None:
            output("TdxQuant数据服务初始化失败：未找到 tqcenter")
            return False

        try:
            self.tq.initialize(__file__)
            self.inited = True
            return True
        except Exception as ex:
            output(f"TdxQuant数据服务初始化失败：{ex}")
            return False

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> list[BarData]:
        """查询K线数据"""
        if not self.inited:
            n: bool = self.init(output)
            if not n:
                return []

        # 仅支持 A 股
        if req.exchange not in STOCK_EXCHANGES:
            output(f"TdxQuant查询K线数据失败：仅支持 A 股 {req.vt_symbol}")
            return []

        # 周期映射
        tdx_period: str | None = None
        if req.interval is not None:
            tdx_period = INTERVAL_VT2TDX.get(req.interval)
        if not tdx_period:
            output(f"TdxQuant查询K线数据失败：仅支持周期 1m/1d {req.interval}")
            return []

        # 通达信合约代码与时间范围
        tdx_symbol: str = f"{req.symbol}.{EXCHANGE_SUFFIX[req.exchange]}"

        # 请求前先刷新 K 线缓存
        try:
            self.tq.refresh_kline(stock_list=[tdx_symbol], period=tdx_period)
            raw = self.tq.get_market_data(
                field_list=["Open", "High", "Low", "Close", "Volume", "Amount"],
                stock_list=[tdx_symbol],
                start_time=req.start.strftime("%Y%m%d%H%M%S"),
                end_time=req.end.strftime("%Y%m%d%H%M%S"),  # type: ignore[union-attr]
                count=-1,
                dividend_type="front",
                period=tdx_period,
                fill_data=False,
            )
        except Exception as ex:
            output(f"TdxQuant查询K线数据失败：{ex}")
            return []

        if "Open" not in raw:
            output(f"TdxQuant查询K线数据失败：未返回K线 {req.vt_symbol}")
            return []

        open_df = raw["Open"]
        adjustment: timedelta = INTERVAL_ADJUSTMENT[req.interval]    # type: ignore[index]
        data: list[BarData] = []
        for i in range(len(open_df)):
            dt = open_df.index[i].to_pydatetime().replace(tzinfo=CHINA_TZ) - adjustment
            bar = BarData(
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                datetime=dt,
                open_price=float(raw["Open"].iloc[i][tdx_symbol]),
                high_price=float(raw["High"].iloc[i][tdx_symbol]),
                low_price=float(raw["Low"].iloc[i][tdx_symbol]),
                close_price=float(raw["Close"].iloc[i][tdx_symbol]),
                volume=float(raw["Volume"].iloc[i][tdx_symbol]),
                turnover=round(float(raw["Amount"].iloc[i][tdx_symbol]) * 10000.0, 1),
                open_interest=0,
                gateway_name="TDX",
            )
            data.append(bar)

        return data

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> list[TickData]:
        """查询Tick数据（仅有当前快照，无历史 tick）"""
        return []
