"""A2 — TSMOM 90 jours, signe du rendement (famille A, momentum time-series).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
- r90 = close(N)/close(N-2160) - 1, évalué à chaque clôture 1h.
- Long si r90 > 0 (entrée à l'open de N+1), sortie si r90 < 0.
- minimal_roi désactivé, trailing désactivé, stoploss catastrophe -25 %.
"""

from pandas import DataFrame

from freqtrade.strategy import IStrategy


class A2Tsmom90(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    minimal_roi = {}
    stoploss = -0.25
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    LOOKBACK = 2160  # 90 jours en bougies 1h

    startup_candle_count = LOOKBACK + 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["r90"] = dataframe["close"] / dataframe["close"].shift(self.LOOKBACK) - 1
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["r90"] > 0, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["r90"] < 0, "exit_long"] = 1
        return dataframe
