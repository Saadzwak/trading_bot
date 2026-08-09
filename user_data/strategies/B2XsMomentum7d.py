"""B2 — Momentum cross-sectionnel 7j, top 3, rebalancement hebdomadaire (famille B).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
identiques à B1 avec lookback 7 jours. Fichier autonome (pas d'héritage) pour que
chaque candidate soit auditable isolément contre son enregistrement.
"""

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class B2XsMomentum7d(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    minimal_roi = {}
    stoploss = -0.25
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    LOOKBACK_DAYS = 7
    TOP_N = 3

    startup_candle_count = 7 * 24 + 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        lb = self.LOOKBACK_DAYS * 24
        closes = {}
        for p in self.dp.current_whitelist():
            pdf = self.dp.get_pair_dataframe(pair=p, timeframe=self.timeframe)
            if pdf is not None and not pdf.empty:
                closes[p] = pdf.set_index("date")["close"]
        panel = pd.DataFrame(closes)
        rets = panel / panel.shift(lb) - 1
        ranks = rets.rank(axis=1, ascending=False, method="min")

        pair = metadata["pair"]
        dataframe["xs_ret"] = rets[pair].reindex(dataframe["date"]).values
        dataframe["xs_rank"] = ranks[pair].reindex(dataframe["date"]).values
        d = dataframe["date"]
        dataframe["rebalance"] = (
            (d.dt.dayofweek == 6) & (d.dt.hour == 23)).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rebalance"] == 1)
            & (dataframe["xs_rank"] <= self.TOP_N)
            & (dataframe["xs_ret"] > 0),
            "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rebalance"] == 1)
            & ((dataframe["xs_rank"] > self.TOP_N) | (dataframe["xs_ret"] <= 0)),
            "exit_long"] = 1
        return dataframe
