"""B1 — Momentum cross-sectionnel 21j, top 3, rebalancement hebdomadaire (famille B).

Règles exactes pré-enregistrées dans HYPOTHESES.md (commit de gel edbb439) :
- Chaque lundi 00:00 UTC : classement des 10 paires par rendement 21 jours.
- Long équipondéré (1/3 du capital) sur les 3 premières dont le rendement > 0 ;
  part en cash sinon. Tenu jusqu'au lundi suivant.
- minimal_roi désactivé, trailing désactivé, stoploss catastrophe -25 %.
- Lancement : --max-open-trades 3 --stake-amount 3333.

Implémentation du calendrier : le signal est évalué sur la bougie de dimanche 23:00
UTC (qui CLÔTURE lundi 00:00) et exécuté à l'open de la bougie suivante = lundi
00:00 UTC exactement, conformément à la règle. Les rotations sortie/entrée du même
rebalancement sont traitées dans la même bougie (les sorties libèrent le capital
avant les entrées dans le moteur freqtrade).
"""

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class B1XsMomentum21d(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    minimal_roi = {}
    stoploss = -0.25
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    LOOKBACK_DAYS = 21
    TOP_N = 3

    # +25 : marge d'une journée au-delà du lookback pour les bords de fenêtre.
    startup_candle_count = 21 * 24 + 25

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        lb = self.LOOKBACK_DAYS * 24
        closes = {}
        for p in self.dp.current_whitelist():
            pdf = self.dp.get_pair_dataframe(pair=p, timeframe=self.timeframe)
            if pdf is not None and not pdf.empty:
                closes[p] = pdf.set_index("date")["close"]
        panel = pd.DataFrame(closes)
        # Grille horaire COMPLÈTE : le décalage positionnel redevient un décalage
        # temporel exact malgré les trous de maintenance Binance (1-4 bougies).
        # Sans cela, le nombre de trous dépend de la fenêtre chargée et les rangs
        # deviennent non reproductibles — biais détecté par lookahead-analysis le
        # 2026-08-10 (voir JOURNAL.md). ffill(limit=6) ne comble que les
        # maintenances courtes ; les NaN de tête (paire pas encore listée, ex. GRT)
        # sont préservés et excluent la paire du classement.
        grid = pd.date_range(panel.index.min(), panel.index.max(),
                             freq="1h", tz="UTC")
        panel = panel.reindex(grid).ffill(limit=6)
        # Rendement lookback : n'utilise que des closes <= t (aucun look-ahead).
        rets = panel / panel.shift(lb) - 1
        ranks = rets.rank(axis=1, ascending=False, method="min")

        pair = metadata["pair"]
        dataframe["xs_ret"] = rets[pair].reindex(dataframe["date"]).values
        dataframe["xs_rank"] = ranks[pair].reindex(dataframe["date"]).values
        d = dataframe["date"]
        # Bougie dimanche 23:00 UTC -> clôture lundi 00:00, exécution lundi 00:00.
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
