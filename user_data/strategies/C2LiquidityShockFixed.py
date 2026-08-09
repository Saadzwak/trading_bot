"""C2 — Choc de liquidité, sortie fixe (famille C, mean reversion conditionnelle).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
- Entrée identique à C1 (chute <= -3×ATR%(24) pré-choc + volume quote >= 4× MM24h).
- Sorties : take-profit à +1 × ATR%(24) mesuré à l'entrée ; OU timeout 24 bougies ;
  OU stop -2 × ATR%(24) à l'entrée.

Mêmes résolutions d'ambiguïté que C1 (ATR pré-choc via shift(1), volume quote
approximé par volume×close). Le take-profit est un niveau de PRIX
(open_rate × (1 + ATR%)), évalué par custom_exit à la granularité du
--timeframe-detail (5m). Fichier autonome pour auditabilité.
"""

from datetime import timedelta

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, stoploss_from_open


class C2LiquidityShockFixed(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    minimal_roi = {}
    stoploss = -0.25            # plancher catastrophe ; le stop actif est -2×ATR
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    use_custom_stoploss = True

    ATR_LEN = 24
    DROP_MULT = 3.0
    VOL_MULT = 4.0
    STOP_ATR = 2.0
    TP_ATR = 1.0
    TIMEOUT_HOURS = 24

    startup_candle_count = 30

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        atr_abs = ta.ATR(dataframe, timeperiod=self.ATR_LEN)
        dataframe["atr_pct"] = atr_abs.shift(1) / dataframe["close"].shift(1)
        dataframe["candle_ret"] = dataframe["close"] / dataframe["open"] - 1
        dataframe["qvol"] = dataframe["volume"] * dataframe["close"]
        dataframe["qvol_ma24"] = dataframe["qvol"].rolling(24).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["atr_pct"] > 0)
            & (dataframe["candle_ret"] <= -self.DROP_MULT * dataframe["atr_pct"])
            & (dataframe["qvol"] >= self.VOL_MULT * dataframe["qvol_ma24"]),
            "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe  # aucune sortie sur signal : TP / timeout / stop uniquement

    def _entry_atr_pct(self, pair: str, trade: Trade):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        signal_time = (trade.open_date_utc.replace(minute=0, second=0, microsecond=0)
                       - timedelta(hours=1))
        row = df.loc[df["date"] == signal_time]
        if row.empty:
            return None
        val = float(row["atr_pct"].iloc[0])
        return val if np.isfinite(val) and val > 0 else None

    def custom_stoploss(self, pair: str, trade: Trade, current_time,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs):
        atr = self._entry_atr_pct(pair, trade)
        if atr is None:
            return None
        return stoploss_from_open(-self.STOP_ATR * atr, current_profit,
                                  is_short=False, leverage=1.0)

    def custom_exit(self, pair: str, trade: Trade, current_time,
                    current_rate: float, current_profit: float, **kwargs):
        atr = self._entry_atr_pct(pair, trade)
        if atr is not None and current_rate >= trade.open_rate * (1 + self.TP_ATR * atr):
            return "tp_1atr"
        if current_time - trade.open_date_utc >= timedelta(hours=self.TIMEOUT_HOURS):
            return "timeout_24h"
        return None
