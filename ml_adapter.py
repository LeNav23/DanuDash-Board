"""Punto único para integrar el modelo de Machine Learning del equipo.

CONTRATO:
    predict_demand(history, requests) -> DataFrame con columnas
    product_id, region, year, mes_num, forecast_units

- history: registros disponibles HASTA el mes de corte (inclusive).
- requests: combinaciones producto x región para el MES SIGUIENTE.
- NO usar ventas, stock, rotación o variables derivadas del mes objetivo.

Cuando recibas el código de ML:
    1) Copia su lógica de inferencia a predict_demand() (o importa aquí su módulo).
    2) Conserva el esquema de salida indicado.
    3) Quita el modo provisional desde la interfaz si el modelo ya funciona.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def predict_demand(history: pd.DataFrame, requests: pd.DataFrame) -> pd.DataFrame:
    """Pronóstico PROVISIONAL estacional; reemplazar por el ML entrenado.

    Busca ventas del mismo mes del año previo. Si no existen, toma
    promedio de hasta 3 meses recientes disponibles por producto-región.
    Este método es una referencia simple, NO una predicción ML.
    """
    key = ['product_id', 'region']
    target = requests[key + ['year', 'mes_num']].drop_duplicates().copy()
    monthly = history.groupby(key + ['year', 'mes_num'], as_index=False)['units_sold'].sum()
    reference = monthly.rename(columns={'year':'ref_year','units_sold':'previous_year_units'})
    target['ref_year'] = target['year'] - 1
    target = target.merge(reference, on=key+['ref_year','mes_num'], how='left')
    recent = monthly.copy()
    recent['date'] = pd.to_datetime(dict(year=recent.year, month=recent.mes_num, day=1))
    recent = recent.sort_values('date').groupby(key, group_keys=False).tail(3)
    fallback = recent.groupby(key, as_index=False)['units_sold'].mean().rename(columns={'units_sold':'recent_average'})
    target = target.merge(fallback, on=key, how='left')
    target['forecast_units'] = (target['previous_year_units']
        .fillna(target['recent_average']).fillna(0).clip(lower=0).round().astype(int))
    return target[key + ['year','mes_num','forecast_units']]


def safety_stock_from_history(history: pd.DataFrame, requests: pd.DataFrame, service_level: int = 95) -> pd.DataFrame:
    """Reserva orientativa: z * RMSE regional de un pronóstico ingenuo.

    Solo usa información disponible antes o durante el mes de corte.
    Cuando la muestra es insuficiente, usa un porcentaje conservador del
    pronóstico como reserva ilustrativa, debidamente señalada en la UI.
    """
    from statistics import NormalDist
    z = NormalDist().inv_cdf(service_level / 100)
    hist = history.copy()
    hist = hist.sort_values(['product_id','region','year','mes_num'])
    hist['prev_units'] = hist.groupby(['product_id','region'])['units_sold'].shift(1)
    hist['sq_err'] = (hist['units_sold'] - hist['prev_units']) ** 2
    region_err = hist.groupby('region',as_index=False)['sq_err'].mean()
    region_err['rmse_region'] = np.sqrt(region_err['sq_err'])
    out = requests[['product_id','region','forecast_units']].copy()
    out = out.merge(region_err[['region','rmse_region']],on='region',how='left')
    out['safety_stock'] = (z * out['rmse_region'].fillna(out['forecast_units'] * 0.15)).clip(lower=0).round().astype(int)
    out['stock_ideal'] = out['forecast_units'] + out['safety_stock']
    return out[['product_id','region','safety_stock','stock_ideal']]
