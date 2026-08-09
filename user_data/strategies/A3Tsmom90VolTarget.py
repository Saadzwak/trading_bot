"""A3 — TSMOM 90j + ciblage de volatilité (famille A, momentum time-series).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
- Signal identique à A2 (signe du rendement 90 jours).
- Taille de position : (capital/10) × min(1, σ_cible/σ_réalisée),
  σ_cible = 40 % annualisée, σ_réalisée = écart-type des rendements QUOTIDIENS sur
  30 jours, annualisé √365. Calculée à l'entrée uniquement.

Résolutions d'ambiguïté fixées AVANT tout backtest (journalisées) :
- La vol quotidienne du jour J n'est connue qu'à la clôture de J → la série est
  décalée d'un jour (shift(1)) avant projection sur les bougies 1h (anti-look-ahead).
- Si σ indisponible (début de série) : facteur 1 (comportement identique à A2).
"""

from datetime import timedelta

import numpy as np
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class A3Tsmom90VolTarget(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    minimal_roi = {}
    stoploss = -0.25
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    LOOKBACK = 2160        # 90 jours en bougies 1h
    TARGET_VOL = 0.40      # annualisée
    VOL_WINDOW_DAYS = 30

    startup_candle_count = LOOKBACK + 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["r90"] = dataframe["close"] / dataframe["close"].shift(self.LOOKBACK) - 1

        daily_close = dataframe.set_index("date")["close"].resample("1D").last()
        vol_ann = (daily_close.pct_change()
                   .rolling(self.VOL_WINDOW_DAYS).std() * np.sqrt(365))
        # shift(1) : la vol du jour J n'est utilisable qu'à partir de J+1.
        vol_ann = vol_ann.shift(1)
        dataframe["vol30d_ann"] = vol_ann.reindex(
            dataframe["date"], method="ffill").values
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["r90"] > 0, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["r90"] < 0, "exit_long"] = 1
        return dataframe

    def custom_stake_amount(self, pair: str, current_time, current_rate,
                            proposed_stake: float, min_stake, max_stake,
                            leverage: float, entry_tag, side: str,
                            **kwargs) -> float:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        signal_time = (current_time.replace(minute=0, second=0, microsecond=0)
                       - timedelta(hours=1))
        row = df.loc[df["date"] == signal_time]
        vol = float(row["vol30d_ann"].iloc[0]) if len(row) else float("nan")
        if not np.isfinite(vol) or vol <= 0:
            factor = 1.0
        else:
            factor = min(1.0, self.TARGET_VOL / vol)
        return proposed_stake * factor
