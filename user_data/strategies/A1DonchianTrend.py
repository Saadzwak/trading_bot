"""A1 — Donchian 30j/15j (famille A, momentum time-series).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
- Entrée long à l'open de N+1 si close(N) > max(high) des 720 bougies 1h précédentes
  (bougie courante exclue).
- Sortie à l'open de N+1 si close(N) < min(low) des 360 bougies précédentes.
- minimal_roi désactivé, trailing désactivé, stoploss catastrophe -25 %.
Aucun paramètre ne peut être modifié après les backtests (protocole).
"""

from pandas import DataFrame

from freqtrade.strategy import IStrategy


class A1DonchianTrend(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    minimal_roi = {}
    stoploss = -0.25
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    ENTRY_WINDOW = 720  # 30 jours en bougies 1h
    EXIT_WINDOW = 360   # 15 jours

    startup_candle_count = ENTRY_WINDOW + 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # shift(1) : la bougie courante est exclue de la fenêtre (règle pré-enregistrée).
        dataframe["don_high"] = (
            dataframe["high"].shift(1).rolling(self.ENTRY_WINDOW).max())
        dataframe["don_low"] = (
            dataframe["low"].shift(1).rolling(self.EXIT_WINDOW).min())
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["close"] > dataframe["don_high"], "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["close"] < dataframe["don_low"], "exit_long"] = 1
        return dataframe
