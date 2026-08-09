"""C1 — Choc de liquidité, sortie mean-revert (famille C, mean reversion conditionnelle).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
- Entrée à l'open de N+1 si, à la clôture de N :
  (a) close/open - 1 <= -3 × ATR%(24) ; ET
  (b) volume quote >= 4 × moyenne mobile 24h du volume quote.
- Sorties (première atteinte) : close >= EMA(12) 1h ; OU timeout 48 bougies ;
  OU stop à -2 × ATR%(24) mesuré à l'entrée.

Résolutions d'ambiguïté fixées AVANT tout backtest (journalisées) :
- ATR%(24) mesuré sur les 24 bougies se terminant à N-1 (shift(1)) : le choc est
  comparé à la volatilité PRÉ-choc, pas à une fenêtre contaminée par le choc lui-même.
- Volume quote approximé par volume_base × close (le feather ne stocke que le volume
  base) ; le ratio à sa moyenne mobile est quasi identique.
- Le stop -2×ATR est fixe pendant le trade (custom_stoploss, converti via
  stoploss_from_open).
"""

from datetime import timedelta

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, stoploss_from_open


class C1LiquidityShockRevert(IStrategy):
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
    TIMEOUT_HOURS = 48
    EMA_LEN = 12

    startup_candle_count = 30

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        atr_abs = ta.ATR(dataframe, timeperiod=self.ATR_LEN)
        # Volatilité PRÉ-choc : fenêtre terminant à la bougie précédente.
        dataframe["atr_pct"] = atr_abs.shift(1) / dataframe["close"].shift(1)
        dataframe["candle_ret"] = dataframe["close"] / dataframe["open"] - 1
        dataframe["qvol"] = dataframe["volume"] * dataframe["close"]
        dataframe["qvol_ma24"] = dataframe["qvol"].rolling(24).mean()
        dataframe["ema12"] = ta.EMA(dataframe, timeperiod=self.EMA_LEN)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["atr_pct"] > 0)
            & (dataframe["candle_ret"] <= -self.DROP_MULT * dataframe["atr_pct"])
            & (dataframe["qvol"] >= self.VOL_MULT * dataframe["qvol_ma24"]),
            "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] >= dataframe["ema12"], "exit_long"] = 1
        return dataframe

    def _entry_atr_pct(self, pair: str, trade: Trade):
        """ATR% de la bougie de signal (celle qui précède l'ouverture du trade)."""
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
            return None  # conserve le plancher catastrophe -25 %
        return stoploss_from_open(-self.STOP_ATR * atr, current_profit,
                                  is_short=False, leverage=1.0)

    def custom_exit(self, pair: str, trade: Trade, current_time,
                    current_rate: float, current_profit: float, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(hours=self.TIMEOUT_HOURS):
            return "timeout_48h"
        return None
