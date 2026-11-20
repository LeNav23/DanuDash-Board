"""Lógica de datos y métricas; independiente de Streamlit para pruebas."""
from __future__ import annotations
import calendar
import numpy as np
import pandas as pd
from ml_adapter import predict_demand, safety_stock_from_history

MONTHS = {m.lower():i for i,m in enumerate(calendar.month_name) if i}
MONTH_NAMES = {i:n for i,n in enumerate(['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']) if i}
CATS_ES = {'Fitness Wear':'Deportiva','Casual Wear':'Casual','Accessories':'Accesorios','Footwear':'Calzado'}
# Nombres cortos para chips y ejes; el orden va de la región más grande a la más chica.
REGION_SHORT = {'Ciudad de México':'CDMX','Zona Metropolitana de Monterrey':'MTY',
                'Zona Metropolitana de Guadalajara':'GDL','Bajío':'Bajío','Noroeste':'Noroeste',
                'Sur':'Sur','Sureste':'Sureste'}
REGION_ORDER = list(REGION_SHORT)


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    if 'units_sold' not in df.columns and 'units_sold_total' in df.columns:
        df = df.rename(columns={'units_sold_total': 'units_sold'})
    required = {'product_id','region','year','units_sold','stock','product_name','category','subcategory','static_price'}
    missing = required-set(df.columns)
    if missing: raise ValueError('La base no contiene estas columnas: '+ ', '.join(sorted(missing)))
    d = df.copy()
    if 'mes_num' not in d:
        if 'month' not in d: raise ValueError('Falta mes_num o month')
        d['mes_num'] = d['month'].astype(str).str.lower().map(MONTHS)
    for c in ('product_id','year','mes_num','units_sold','stock','static_price'):
        d[c] = pd.to_numeric(d[c],errors='coerce')
    d = d.dropna(subset=['product_id','region','year','mes_num','units_sold','stock'])
    d['product_id']=d['product_id'].astype(int)
    d['year']=d['year'].astype(int)
    d['mes_num']=d['mes_num'].astype(int)
    d = d[d['mes_num'].between(1,12)]
    d['date']=pd.to_datetime(dict(year=d.year,month=d.mes_num,day=1))
    d['category_es']=d['category'].replace(CATS_ES)
    return d


def subset(df, years=None, regions=None, categories=None, subcategories=None, months=None):
    d=df
    if years: d=d[d.year.isin(years)]
    if regions: d=d[d.region.isin(regions)]
    if categories: d=d[d.category_es.isin(categories)]
    if subcategories: d=d[d.subcategory.isin(subcategories)]
    if months: d=d[d.mes_num.isin(months)]
    return d.copy()


def descriptive_kpis(d):
    if d.empty: return {'sales':0.,'stock':0.,'rotation':0.,'overstock':0.,'unsold':0.,'unsold_value':0.}
    s=float(d.units_sold.sum()); stock=float(d.stock.sum())
    # El inventario sin vender se valora a precio de lista, no a costo.
    unsold=np.maximum(d.stock.to_numpy()-d.units_sold.to_numpy(),0)
    value=float(np.nansum(unsold*d.static_price.fillna(0).to_numpy()))
    expected = pd.to_numeric(d.get('units_expected',pd.Series(0,index=d.index)),errors='coerce').fillna(0).to_numpy()
    over=float(np.maximum(d.stock.to_numpy()-expected,0).sum())
    return {'sales':s,'stock':stock,'rotation':100*s/stock if stock else 0,
            'overstock':100*over/stock if stock else 0,
            'over_units':over,'unsold':float(unsold.sum()),'unsold_value':value}


def region_rotation(d):
    r=d.groupby('region',as_index=False)[['units_sold','stock']].sum()
    r['rotation']=np.where(r.stock>0,100*r.units_sold/r.stock,0)
    return r.sort_values('rotation',ascending=False)


def subcategory_rotation(d):
    r=d.groupby('subcategory',as_index=False)[['units_sold','stock']].sum()
    r['rotation']=np.where(r.stock>0,100*r.units_sold/r.stock,0)
    return r.sort_values('rotation',ascending=False)


def low_rotation_products(d,n=8):
    r=d.groupby(['product_id','product_name','subcategory'],as_index=False)[['units_sold','stock']].sum()
    r['rotation']=np.where(r.stock>0,100*r.units_sold/r.stock,0)
    r['unsold']=np.maximum(r.stock-r.units_sold,0)
    return r.sort_values(['rotation','unsold'],ascending=[True,False]).head(n)


def compare_year_growth(d, year:int):
    current=d.loc[d.year==year,'units_sold'].sum()
    previous=d.loc[d.year==year-1,'units_sold'].sum()
    return (current/previous-1)*100 if previous>0 else None


def cut_history(df, year, month):
    # Corte inclusive: nunca dejar pasar registros posteriores al pronóstico.
    t=pd.Timestamp(year=year,month=month,day=1)
    return df[df.date<=t].copy()


def next_month(year,month):
    return (year+1,1) if month==12 else (year,month+1)


def _get_current_snapshot(hist):
    keys=['product_id','region']
    return hist.sort_values('date').groupby(keys,as_index=False).tail(1).copy()


def build_purchase_plan(df,year,month,service=95,forecast_override=None,stock_override=None):
    """Pronostica mes posterior al corte, SIN fuga de información del objetivo.

    Los parámetros override son tablas opcionales de predicciones/resultados ML.
    """
    hist=cut_history(df,year,month)
    if hist.empty: return pd.DataFrame(),(year,month)
    target_year,target_month=next_month(year,month)
    snap=_get_current_snapshot(hist)
    requests=snap[['product_id','region','product_name','subcategory','category_es','static_price','stock']].copy()
    requests['year']=target_year
    requests['mes_num']=target_month
    if forecast_override is None:
        pred=predict_demand(hist,requests)
    else:
        pred=forecast_override.copy()
        # Seleccionar únicamente pronósticos del período objetivo.
        pred=pred[(pd.to_numeric(pred.year,errors='coerce')==target_year) & (pd.to_numeric(pred.mes_num,errors='coerce')==target_month)]
    required={'product_id','region','year','mes_num','forecast_units'}
    if not required.issubset(pred.columns):
        raise ValueError('El forecast necesita columnas: '+', '.join(sorted(required)))
    pred=pred[list(required)].drop_duplicates(['product_id','region'])
    requests=requests.merge(pred,on=['product_id','region','year','mes_num'],how='left')
    requests['forecast_units']=pd.to_numeric(requests.forecast_units,errors='coerce')
    requests=requests.dropna(subset=['forecast_units'])
    requests['forecast_units']=requests.forecast_units.clip(lower=0).round().astype(int)
    safety=safety_stock_from_history(hist,requests,service)
    requests=requests.merge(safety,on=['product_id','region'],how='left')
    if stock_override is not None:
        alt=stock_override[['product_id','region','stock_ideal']].copy()
        requests=requests.drop(columns=['stock_ideal']).merge(alt,on=['product_id','region'],how='left')
    requests['stock_ideal']=pd.to_numeric(requests.stock_ideal,errors='coerce').fillna(0).clip(lower=0).round().astype(int)
    requests['stock_actual']=requests.stock.clip(lower=0).round().astype(int)
    requests['excess_units']=(requests.stock_actual-requests.stock_ideal).clip(lower=0)
    requests['overstock_pct']=np.where(requests.stock_actual>0,100*requests.excess_units/requests.stock_actual,0)
    requests['days_inventory']=np.where(requests.forecast_units>0,30*requests.stock_actual/requests.forecast_units,np.nan)
    requests['shortfall']=(requests.stock_ideal-requests.stock_actual).clip(lower=0)
    requests['forecast_date']=pd.Timestamp(year=target_year,month=target_month,day=1)
    return requests,(target_year,target_month)


def action_for_product(row, threshold_days=120):
    """Reglas orientativas editables; no son etiquetas de K-means."""
    if row['shortfall']>0: return 'Reabastecer'
    if np.isfinite(row['days_inventory']) and row['days_inventory']>=threshold_days: return 'Promover'
    if row['overstock_pct']>=20: return 'Revisar envíos'
    return 'Mantener'
