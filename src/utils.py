import numpy as np

try:
    from scipy.stats import median_abs_deviation as scipy_mad

    def mad_robust(x: np.ndarray) -> float:
        arr = np.asarray(x, dtype=float)
        if arr.size == 0:
            return 0.0
        val = float(scipy_mad(arr, scale=1.0, nan_policy="omit"))
        return float(1.4826 * val)
except Exception:
    def mad_robust(x: np.ndarray) -> float:
        arr = np.asarray(x, dtype=float)
        arr = arr[~np.isnan(arr)]
        if arr.size == 0:
            return 0.0
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med)))
        return float(1.4826 * mad)

def robust_z_scores(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.size == 0:
        return np.array([], dtype=float)
    med = float(np.nanmedian(arr))
    denom = mad_robust(arr)
    if denom == 0 or np.isnan(denom):
        return np.zeros_like(arr)
    return (arr - med) / denom