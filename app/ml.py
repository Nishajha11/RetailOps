"""Demand forecasting.

Design for *small, seasonal, growing* retail data (a couple of academic years
of stationery sales with a strong back-to-school spike):

* Sales are aggregated to the requested bucket (weekly / monthly / yearly).
* Three transparent candidates compete on a walk-forward backtest (MAE):
    - ``trend_seasonal`` : a linear trend plus an additive seasonal profile
                           (level + slope*t + season[t mod m]). Unlike a tree
                           model it can *extrapolate* the trend and *repeat the
                           seasonal pattern*, so the forecast is shaped, not flat.
    - ``seasonal_naive`` : last season's same period (e.g. same month last year).
                           A strong, honest baseline a real model must beat.
    - ``persistence``    : repeat the last observed bucket -- the ultimate
                           fallback when there isn't even one full season yet.
* Whichever wins the backtest is used. The system stays honest: it reports its
  error against the seasonal-naive baseline and falls back to it (or to plain
  persistence) when it can't do better.

The forecaster is intentionally dependency-light (numpy/pandas only) so it
deploys anywhere and retrains in milliseconds -- which also keeps billing fast,
since each sale triggers a retrain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from pandas.tseries.frequencies import to_offset

from .config import FORECAST_MODEL_PATH

# bucket rule -> number of buckets in one seasonal cycle
SEASON = {"D": 7, "W": 52, "ME": 12, "QE": 4, "YE": 1}


# --- helpers --------------------------------------------------------------
def _alias(freq: str) -> str:
    return {"D": "D", "W": "W", "M": "ME", "Q": "QE", "Y": "YE",
            "ME": "ME", "QE": "QE", "YE": "YE"}.get(str(freq).upper(), "W")


def _season(rule: str) -> int:
    return SEASON.get(rule, 52)


def _label(d, rule: str) -> str:
    d = pd.Timestamp(d)
    if rule == "YE":
        return d.strftime("%Y")
    if rule == "QE":
        return f"Q{(d.month - 1) // 3 + 1} {d.year}"
    if rule == "ME":
        return d.strftime("%b %Y")
    return d.strftime("%d %b %y")


def _resample(sales: pd.DataFrame, rule: str) -> pd.Series:
    """Aggregate daily sales to the bucket, then trim the tail so the series ends
    at the last bucket with *real* sales:

      * drop a trailing *partial* bucket (its right edge is past the last sale),
        which would otherwise read as an artificially low final period;
      * drop any trailing *zero* buckets -- e.g. quiet recent periods, or the
        empty gap before a single just-entered sale -- so we forecast forward
        from the last real activity instead of treating "no data yet" as 0.

    Interior zero buckets (real no-sale periods between activity) are kept.
    """
    if sales is None or sales.empty:
        return pd.Series(dtype=float)
    s = sales.copy()
    s["date"] = pd.to_datetime(s["date"])
    ts = s.set_index("date").resample(rule)["qty"].sum().astype(float)
    if len(ts) > 1 and s["date"].max() < ts.index[-1]:
        ts = ts.iloc[:-1]                       # trailing partial bucket
    nz = np.nonzero(ts.to_numpy())[0]
    if len(nz):
        ts = ts.iloc[: nz[-1] + 1]              # trim trailing zero buckets
    return ts


def _weekly_series(sales: pd.DataFrame) -> pd.Series:
    return _resample(sales, "W")


# --- the seasonal-trend model --------------------------------------------
def _fit_trend_seasonal(y: np.ndarray, m: int):
    """Return (slope, intercept, seasonal[m] | None). Seasonal indices are only
    estimated when there are at least two full cycles to average over; for
    high-resolution seasonality (e.g. 52 weekly indices) they are circularly
    smoothed so the annual shape is captured without week-to-week noise."""
    n = len(y)
    t = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(t, y, 1)
    seas = None
    if m > 1 and n >= 2 * m:
        detr = y - (intercept + slope * t)
        seas = np.array([detr[k::m].mean() if detr[k::m].size else 0.0
                         for k in range(m)])
        if m >= 13:                        # denoise fine-grained seasonality
            k = max(1, m // 13)
            ext = np.concatenate([seas[-k:], seas, seas[:k]])
            seas = np.convolve(ext, np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
        seas = seas - seas.mean()          # centre so it only redistributes
    return float(slope), float(intercept), seas


def _ts_predict(slope, intercept, seas, m, idx) -> float:
    base = intercept + slope * idx
    if seas is not None:
        base += seas[idx % m]
    return max(float(base), 0.0)


# --- backtest & model selection ------------------------------------------
def _backtest(y: np.ndarray, m: int, h: int = 4) -> dict:
    """Walk-forward *multi-step* MAE for each candidate.

    We score each model the way it is actually used -- forecasting ``h`` buckets
    ahead from each origin -- not just one step. This is what stops flat
    persistence from looking good: it wins one-step on noisy data but blows up
    over a multi-step seasonal horizon, where the shaped models track reality.
    """
    n = len(y)
    start = max(3, m if m > 1 else 3)
    last_origin = n - h                    # need h actuals after the origin
    if last_origin <= start:               # not enough to multi-step backtest
        return {}
    errs = {"trend_seasonal": [], "seasonal_naive": [], "persistence": []}
    for i in range(start, last_origin + 1):
        train, actual = y[:i], y[i:i + h]
        for model in errs:
            pred = np.array(_forecast_values(train, m, h, model))
            errs[model].append(float(np.mean(np.abs(pred - actual))))
    return {k: (float(np.mean(v)) if v else float("inf")) for k, v in errs.items()}


def _choose(maes: dict) -> str:
    order = ["trend_seasonal", "seasonal_naive", "persistence"]
    best, best_mae = "persistence", float("inf")
    for k in order:
        v = maes.get(k, float("inf"))
        if np.isfinite(v) and v < best_mae - 1e-9:
            best, best_mae = k, v
    return best


def _forecast_values(y: np.ndarray, m: int, horizon: int, model: str) -> list[float]:
    if model == "trend_seasonal":
        sl, ic, seas = _fit_trend_seasonal(y, m)
        return [_ts_predict(sl, ic, seas, m, len(y) + h) for h in range(horizon)]
    if model == "seasonal_naive":
        work, out = list(y), []
        for _ in range(horizon):
            idx = len(work)
            v = work[idx - m] if (m > 1 and idx - m >= 0) else work[-1]
            v = max(float(v), 0.0)
            out.append(v); work.append(v)
        return out
    last = max(float(y[-1]), 0.0)
    return [last] * horizon


def _confidence(buckets: int, m: int) -> str:
    if m > 1:
        if buckets >= 2 * m:
            return "ok"
        return "low"               # less than two seasonal cycles
    return "ok" if buckets >= 4 else "low"


# --- artifact -------------------------------------------------------------
@dataclass
class ForecastArtifact:
    kind: str                       # selected model name
    model: object | None            # kept for backwards-compat (unused)
    ts: pd.Series                   # full weekly training series
    backtest_mae: float | None
    naive_mae: float | None
    metrics: dict = field(default_factory=dict)


def train(sales: pd.DataFrame) -> ForecastArtifact:
    """Fit/refresh the weekly forecaster and persist it. Cheap by design."""
    ts = _weekly_series(sales)
    m = _season("W")
    if len(ts) < 3:
        art = ForecastArtifact("persistence", None, ts, None, None,
                               {"selected": "persistence",
                                "note": "insufficient history", "weeks_of_history": int(len(ts))})
        joblib.dump(art, FORECAST_MODEL_PATH)
        return art
    y = ts.to_numpy(dtype=float)
    maes = _backtest(y, m, h=4)
    selected = _choose(maes) if maes else "trend_seasonal"

    def _r(x):
        return round(x, 2) if (x is not None and np.isfinite(x)) else None
    art = ForecastArtifact(
        kind=selected, model=None, ts=ts,
        backtest_mae=_r(maes.get(selected)) if maes else None,
        naive_mae=_r(maes.get("seasonal_naive")) if maes else None,
        metrics={
            "selected": selected,
            "weeks_of_history": int(len(ts)),
            "model_mae": _r(maes.get(selected)) if maes else None,
            "seasonal_naive_mae": _r(maes.get("seasonal_naive")) if maes else None,
            "persistence_mae": _r(maes.get("persistence")) if maes else None,
            "confidence": _confidence(len(ts), m),
        },
    )
    joblib.dump(art, FORECAST_MODEL_PATH)
    return art


def load() -> Optional[ForecastArtifact]:
    if FORECAST_MODEL_PATH.exists():
        return joblib.load(FORECAST_MODEL_PATH)
    return None


def forecast_series(sales: pd.DataFrame, freq: str = "W", horizon: int = 4) -> dict:
    """Period-aware forecast at the requested granularity (weekly/monthly/yearly).

    Picks the model that wins a walk-forward backtest, then emits the historical
    buckets plus ``horizon`` future buckets. The horizon is clamped so we never
    forecast further ahead than we have history -- e.g. only a couple of yearly
    points means only a couple of yearly predictions.
    """
    rule = _alias(freq)
    m = _season(rule)
    base = {"freq": str(freq).upper(), "season": m}

    ts = _resample(sales, rule)
    if len(ts) == 0:
        return {"metrics": {"selected": "persistence", "note": "no sales yet", **base}, "series": []}

    series = [{"period": pd.Timestamp(d).date().isoformat(), "label": _label(d, rule),
               "predicted_units": round(float(v), 1), "kind": "history"}
              for d, v in ts.items()]

    if len(ts) < 2:
        return {"metrics": {"selected": "persistence", "buckets": int(len(ts)),
                            "confidence": "low", "model_mae": None,
                            "seasonal_naive_mae": None, "persistence_mae": None,
                            **base}, "series": series}

    y = ts.to_numpy(dtype=float)
    maes = _backtest(y, m, h=int(horizon))
    if maes:
        selected = _choose(maes)
    else:                                   # too short to backtest -> shaped line
        selected = "trend_seasonal"

    eff_h = max(1, min(int(horizon), len(ts)))     # honesty clamp
    preds = _forecast_values(y, m, eff_h, selected)

    off = to_offset(rule)
    nxt = ts.index[-1]
    for v in preds:
        nxt = nxt + off
        series.append({"period": pd.Timestamp(nxt).date().isoformat(),
                       "label": _label(nxt, rule),
                       "predicted_units": round(float(v), 1), "kind": "forecast"})

    def _r(x):
        return round(x, 2) if (x is not None and np.isfinite(x)) else None
    return {
        "metrics": {
            "selected": selected,
            "buckets": int(len(ts)),
            "horizon": eff_h,
            "model_mae": _r(maes.get(selected)) if maes else None,
            "seasonal_naive_mae": _r(maes.get("seasonal_naive")) if maes else None,
            "persistence_mae": _r(maes.get("persistence")) if maes else None,
            "confidence": _confidence(len(ts), m),
            **base,
        },
        "series": series,
    }


def forecast(art: ForecastArtifact, horizon: int = 4) -> list[dict]:
    """Weekly forecast from a persisted artifact (kept for API compatibility)."""
    ts = art.ts
    if ts is None or len(ts) == 0:
        return []
    history = [{"period": pd.Timestamp(d).date().isoformat(),
                "predicted_units": round(float(v), 1), "kind": "history"}
               for d, v in ts.items()]
    if len(ts) < 3:
        return history
    y = ts.to_numpy(dtype=float)
    m = _season("W")
    eff_h = max(1, min(int(horizon), len(ts)))
    preds = _forecast_values(y, m, eff_h, art.kind)
    off = to_offset("W")
    nxt = ts.index[-1]
    out = []
    for v in preds:
        nxt = nxt + off
        out.append({"period": pd.Timestamp(nxt).date().isoformat(),
                    "predicted_units": round(float(v), 1), "kind": "forecast"})
    return history + out