"""DanuStore · dos tableros Streamlit.

Ejecutar: streamlit run app.py
Instalar: pip install -r requirements.txt

El pronóstico por defecto es una BASE DE REFERENCIA (no un ML entrenado).
Para añadir el ML del equipo, editar ml_adapter.predict_demand o subir CSV
con columnas product_id, region, year, mes_num, forecast_units.
"""
from __future__ import annotations
import calendar
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_utils import (prepare_data,subset,descriptive_kpis,region_rotation,subcategory_rotation,
                        low_rotation_products,compare_year_growth,build_purchase_plan,
                        action_for_product,MONTH_NAMES,next_month,cut_history,REGION_SHORT,REGION_ORDER)

st.set_page_config(page_title='DanuStore · Inventario y compras',page_icon='📦',layout='wide',initial_sidebar_state='expanded')
BASE=Path(__file__).resolve().parent
DEFAULT_BOOKS=('Base_final_v2.xlsx', 'Base_final.xlsx')
BOOK_SNAPSHOT_HASHES={
    'Base_final_v2.xlsx': '75860ab833a29cccc68cf9ed8dc50c4f4f67f6e2ea0d415ef3eb3f5762013853',
    'Base_final.xlsx': '0825dd11fb572fb36a566f2a16343c3d2761017861b44e66260a5fb7751a687a',
}
BLUE='#75A4FF'; INK='#E6EEFA'; MUTED='#A9B7CC'; PURPLE='#BA9AFF'

st.markdown('''<style>
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {border-right:1px solid #2B3B54;}
.block-container {padding:1.1rem 1rem 1.4rem;max-width:100%;}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {gap:.5rem;}
[data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] {gap:.5rem;}
h1 {font-size:2rem !important;font-weight:800 !important;letter-spacing:-0.025em;}
h2 {font-size:1.23rem !important;font-weight:700 !important;}
h3 {font-size:1.05rem !important;font-weight:700 !important;}
[data-testid="stMetric"] {background:#172235;padding:10px 14px;border-radius:9px;border:1px solid #2B3B54;min-height:88px;}
[data-testid="stMetricLabel"] p {font-size:0.74rem;color:#A9B7CC;letter-spacing:0.055em;font-weight:700;text-transform:uppercase;}
[data-testid="stMetricValue"] {font-weight:800;}
[data-testid="stMetricDelta"] {font-size:0.72rem;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:#2B3B54;}
[data-testid="stTabs"] button {font-weight:700;}
.stDownloadButton button {border-radius:8px;}
[data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label {font-size:.75rem;font-weight:700;letter-spacing:.025em;}
[data-testid="stRadio"] label {font-size:.75rem;font-weight:700;}
footer {visibility:hidden;}
.notice{padding:0.55rem .8rem;background:#172235;border:1px solid #2B3B54;border-radius:8px;color:#C5D4EB;font-size:.84rem;}
.sidebrand{font-size:1.1rem;font-weight:800;border-bottom:1px solid #2B3B54;padding:6px 0 15px;margin-bottom:8px;}
.small-caption{font-size:.75rem;color:#A9B7CC;border-bottom:1px;padding-bottom:4px;margin-bottom:8px;}
</style>''',unsafe_allow_html=True)


def compact(num, money=False):
    if pd.isna(num): return '—'
    num=float(num); sign='$' if money else ''
    if abs(num)>=1_000_000_000:return f'{sign}{num/1_000_000_000:,.2f} mil M'
    if abs(num)>=1_000_000:return f'{sign}{num/1_000_000:,.2f} M'
    if abs(num)>=10_000:return f'{sign}{num/1_000:,.1f} mil'
    return f'{sign}{num:,.0f}'

@st.cache_data(show_spinner=False)
def read_book(buf:bytes):
    return prepare_data(pd.read_excel(BytesIO(buf)))

@st.cache_data(show_spinner=False)
def load_default(book_path: Path, book_version: tuple[int, int]):
    workbook = book_path.read_bytes()
    snapshot = book_path.with_suffix('.parquet')
    if snapshot.is_file() and sha256(workbook).hexdigest() == BOOK_SNAPSHOT_HASHES.get(book_path.name):
        return prepare_data(pd.read_parquet(snapshot))
    return read_book(workbook)


def empty_fig(title=None):
    fig=go.Figure()
    fig.add_annotation(text='Sin información para los filtros seleccionados',xref='paper',yref='paper',x=.5,y=.5,showarrow=False,font_color=MUTED)
    fig.update_layout(height=295,xaxis_visible=False,yaxis_visible=False)
    return style_fig(fig)


def style_fig(fig,height=285,margins=None):
    fig.update_layout(height=height,margin=margins or dict(l=12,r=10,t=18,b=16),
      template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
      font=dict(family='Arial',color=INK,size=12),
      legend=dict(orientation='h',yanchor='bottom',y=1.01,xanchor='right',x=1,font=dict(size=11)),
      hovermode='closest')
    fig.update_xaxes(showgrid=False,zeroline=False)
    fig.update_yaxes(gridcolor='#2B3B54',zeroline=False)
    return fig


def chart_region(d):
    r=region_rotation(d)
    if r.empty:return empty_fig()
    fig=go.Figure(go.Bar(x=r.region,y=r.rotation,marker_color=BLUE,text=[f'{v:.1f}%' for v in r.rotation],textposition='outside',hovertemplate='%{x}: %{y:.1f}%<extra></extra>'))
    fig.update_yaxes(title='Rotación (%)',range=[0,max(55,r.rotation.max()*1.2)],ticksuffix='%')
    return style_fig(fig,height=275)


def chart_months(d):
    if d.empty:return empty_fig()
    m=d.groupby('mes_num',as_index=False)[['stock','units_sold']].sum()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=m.mes_num,y=m.stock,mode='lines+markers',name='Stock',line=dict(color=BLUE,width=3),marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=m.mes_num,y=m.units_sold,mode='lines+markers',name='Unidades vendidas',line=dict(color=PURPLE,width=3),marker=dict(size=6)))
    fig.update_xaxes(tickvals=list(range(1,13)),ticktext=list(MONTH_NAMES.values()),title=None)
    fig.update_yaxes(title='Unidades',tickformat='~s')
    return style_fig(fig,height=275)


def chart_subcats(d):
    r=subcategory_rotation(d)
    if r.empty:return empty_fig()
    fig=go.Figure(go.Treemap(
        labels=r.subcategory, parents=[''] * len(r), values=r.stock.clip(lower=1),
        marker=dict(colors=r.rotation, colorscale=['#153A71','#275797','#406CB2']),
        customdata=r[['rotation']].to_numpy(),
    ))
    fig.update_traces(texttemplate='%{label}<br>%{customdata[0]:.1f}%',textfont=dict(size=12),
                      hovertemplate='%{label}<br>Rotación: %{customdata[0]:.1f}%<extra></extra>')
    fig.update_layout(coloraxis_showscale=False)
    return style_fig(fig,height=265,margins=dict(l=0,r=0,t=5,b=0))


def title_bar(title,subtitle):
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:flex-end">'
                f'<div><h1 style="margin:0 0 3px">{title}</h1>'
                f'<div class="small-caption">{subtitle}</div></div></div>',unsafe_allow_html=True)


def remember_upload(widget_key, state_key):
    """Guarda el archivo subido en session_state para no volver a pedirlo."""
    f=st.session_state.get(widget_key)
    if f is not None:
        st.session_state[state_key]=(f.name,f.getvalue())


def load_base():
    """Orden: archivo subido en esta sesión > copia local en data/ > pedirlo una sola vez."""
    if 'base_upload' in st.session_state:
        name,buf=st.session_state['base_upload']
        return name,read_book(buf)
    data_dir=BASE/'data'
    book_path=next((data_dir/name for name in DEFAULT_BOOKS if (data_dir/name).is_file()), None)
    if book_path is None:
        return None,None
    book_stat=book_path.stat()
    return book_path.name,load_default(book_path,(book_stat.st_mtime_ns,book_stat.st_size))


try:
    source_name,df=load_base()
except Exception as exc:
    st.error(f'No se pudo cargar la base: {exc}')
    st.session_state.pop('base_upload',None)
    st.stop()

if df is None:
    # Primera vez sin base local: se pide el archivo una sola vez en la pantalla principal.
    _,mid,_=st.columns([1,1.4,1])
    with mid:
        st.markdown('<h2 style="margin-top:12vh">DanuStore</h2>',unsafe_allow_html=True)
        st.file_uploader('Sube la base de ventas e inventario (Base_final_v2.xlsx)',type=['xlsx'],
                         key='base_first',on_change=remember_upload,args=('base_first','base_upload'))
        st.caption('Solo se pide una vez. Después puedes cambiarla desde la barra lateral.')
    st.stop()
if df.empty:
    st.warning('La base de datos no contiene registros válidos.')
    st.stop()

with st.sidebar:
    st.markdown('<div class="sidebrand">DanuStore</div>',unsafe_allow_html=True)
    page=st.radio('TABLERO',['Ventas e inventario','Ventas esperadas e inventario a pedir'],label_visibility='collapsed')
    st.divider()

    all_years=sorted(df.year.unique().tolist())
    year_options=[str(y) for y in all_years]+['Ambos']
    year_choice=st.segmented_control('AÑO',year_options,default=year_options[-2],key='year') or year_options[-2]
    sel_years=all_years if year_choice=='Ambos' else [int(year_choice)]
    st.caption('Toca para elegir uno o varios. Sin selección = todos.')
    # Chips de selección múltiple; lista vacía = sin filtro.
    region_options=sorted(df.region.unique().tolist(),key=lambda r:REGION_ORDER.index(r) if r in REGION_ORDER else 99)
    sel_regions=st.pills('REGIÓN',region_options,selection_mode='multi',key='region',
                         format_func=lambda r:REGION_SHORT.get(r,r))
    categories=sorted(df.category_es.unique().tolist())
    sel_cats=st.pills('CATEGORÍA',categories,selection_mode='multi',key='cat')
    visible_subcats=sorted(df[df.category_es.isin(sel_cats)].subcategory.unique().tolist() if sel_cats else df.subcategory.unique().tolist())
    # Si se quita una categoría, se limpian sus subcategorías para no dejar filtros escondidos.
    if 'subcat' in st.session_state:
        st.session_state['subcat']=[s for s in st.session_state['subcat'] if s in visible_subcats]
    sel_subcats=st.pills('SUBCATEGORÍA',visible_subcats,selection_mode='multi',key='subcat')
    if page=='Ventas e inventario':
        sel_months=st.pills('MES',list(range(1,13)),selection_mode='multi',key='month_des',
                            format_func=lambda m:MONTH_NAMES[m])
    else:
        # El corte temporal es explícito para no mostrar el futuro al modelo.
        cut_year=max(sel_years)
        max_month=int(df[df.year==cut_year].mes_num.max())
        cutoff_options=[i for i in range(1,max_month+1)]
        default_cut=9 if 9 in cutoff_options else max(cutoff_options)
        current_month=st.selectbox('MES ACTUAL (CORTE)',cutoff_options,format_func=lambda m: calendar.month_name[m],index=cutoff_options.index(default_cut),key='cut')
        service=st.radio('NIVEL DE SERVICIO',[90,95,99],index=1,horizontal=True,format_func=lambda x:f'{x}%',key='service')
        promote_days=st.radio('PROMOVER SI HAY MÁS DE',[60,120,180],index=1,horizontal=True,format_func=lambda x:f'{x} días',key='promote')
    def reset_filters():
        # Se asignan valores vacíos (no se borran) para que los chips también se vean sin seleccionar.
        for k in ('region','cat','subcat','month_des'):
            st.session_state[k]=[]
        st.session_state['year']=year_options[-2]
        for k in ('cut','service','promote'):
            st.session_state.pop(k,None)
    st.button('Quitar filtros',use_container_width=True,on_click=reset_filters)
    st.divider()
    # Carga de archivos escondida en un botón chico al final para no estorbar a los filtros.
    with st.popover('⚙ Cambiar archivos',use_container_width=True):
        st.file_uploader('Base de ventas e inventario (.xlsx)',type=['xlsx'],key='base_new',
                         on_change=remember_upload,args=('base_new','base_upload'))
        st.file_uploader('Forecast de ML (.csv) · opcional',type=['csv'],key='forecast_new',
                         on_change=remember_upload,args=('forecast_new','forecast_upload'))
        st.caption('Forecast: columnas product_id, region, year, mes_num, forecast_units.')
    st.caption(f'Fuente: {source_name}')

forecast_file=st.session_state.get('forecast_upload')

regions=sel_regions or None
cats=sel_cats or None
subs=sel_subcats or None

if page=='Ventas e inventario':
    months=sorted(sel_months) or None
    data=subset(df,sel_years,regions,cats,subs,months)
    title_bar('Ventas e inventario','Análisis descriptivo de ventas, inventario y rotación por región y producto')
    if data.empty:st.warning('No hay registros para los filtros seleccionados.');st.stop()
    k=descriptive_kpis(data)
    growth=compare_year_growth(subset(df,[max(sel_years),max(sel_years)-1],regions,cats,subs,months),max(sel_years)) if year_choice!='Ambos' else None
    c1,c2,c3,c4=st.columns(4)
    with c1:st.metric('Δ VENTAS VS AÑO PREVIO',f'{growth:+.1f}%' if growth is not None else '—',help='Variación de unidades vendidas respecto al período equivalente del año anterior.')
    with c2:st.metric('ROTACIÓN DE INVENTARIO',f'{k["rotation"]:.1f}%',help='Unidades vendidas / stock registrado de los períodos seleccionados.')
    with c3:st.metric('SOBRESTOCK',f'{k["overstock"]:.1f}%',help='Máximo(stock - unidades esperadas, 0), dividido por el stock registrado. Es un indicador orientativo.')
    with c4:st.metric('INVENTARIO SIN VENDER',compact(k['unsold_value'],True),help='Valor a precio de lista de máx(stock - unidades vendidas, 0); NO es costo de inventario.')
    a,b=st.columns([1,1.05],gap='small')
    with a:
        with st.container(border=True):
            st.subheader('Rotación por región')
            st.plotly_chart(chart_region(data),use_container_width=True,config={'displayModeBar':False})
    with b:
        with st.container(border=True):
            st.subheader('Comparación ventas contra stock por mes')
            st.plotly_chart(chart_months(data),use_container_width=True,config={'displayModeBar':False})
    a,b=st.columns([.85,1.4],gap='small')
    with a:
        with st.container(border=True):
            st.subheader('Rotación por subcategoría')
            st.plotly_chart(chart_subcats(data),use_container_width=True,config={'displayModeBar':False})
    with b:
        with st.container(border=True):
            st.subheader('Productos con menor rotación')
            low=low_rotation_products(data)
            low=low.rename(columns={'product_name':'Producto','subcategory':'Subcategoría','rotation':'% de rotación','unsold':'Sin vender'})
            st.dataframe(low[['Producto','Subcategoría','% de rotación','Sin vender']],hide_index=True,use_container_width=True,height=365,
                column_config={'% de rotación':st.column_config.ProgressColumn('% de rotación',min_value=0,max_value=100,format='%.1f%%'),
                               'Sin vender':st.column_config.NumberColumn('Sin vender',format='%d')})
    st.caption('Nota: el stock se registra cada mes. Al seleccionar varios meses, los totales corresponden a la suma de observaciones mensuales, no a un inventario físico único.')
else:
    cut_year=max(sel_years)
    if forecast_file is not None:
        try: forecast_external=pd.read_csv(BytesIO(forecast_file[1]))
        except Exception as exc:
            st.error(f'Error en el CSV de forecast: {exc}');st.stop()
        source_tag='Pronóstico importado · archivo del equipo'
    else:
        forecast_external=None
        source_tag='Referencia provisional · mismo mes del año anterior (NO ML)'
    # Filtro a toda la historia hasta corte; se conservan años previos para los lags.
    universe=subset(df,None,regions,cats,subs)
    try:
        plan,(fy,fm)=build_purchase_plan(universe,cut_year,current_month,service,forecast_external)
    except Exception as exc:
        st.error(f'No se pudo calcular el plan: {exc}');st.stop()
    title_bar('Ventas esperadas e inventario a pedir',f'Plan de abastecimiento para {calendar.month_name[fm]} {fy} · {source_tag}')
    if plan.empty:
        st.warning('No hay registros con pronóstico para ese período y filtros.');st.stop()
    plan['Acción']=plan.apply(lambda r:action_for_product(r,promote_days),axis=1)
    # El mes del corte puede ser un mes histórico, NO se usa el objetivo como entrada.
    sales_current=float(universe[(universe.year==cut_year)&(universe.mes_num==current_month)].units_sold.sum())
    sales_prev=float(universe[(universe.year==cut_year-1)&(universe.mes_num==current_month)].units_sold.sum())
    growth=(sales_current/sales_prev-1)*100 if sales_prev else None
    k1,k2,k3=st.columns([1,1,1.05])
    with k1:st.metric('Δ VENTAS PERÍODO VS AÑO PREVIO',f'{growth:+.1f}%' if growth is not None else '—')
    with k2:st.metric('VENTAS ESPERADAS',compact(plan.forecast_units.sum()),help='Pronóstico de ventas en unidades para el mes siguiente al corte.')
    with k3:
        over=100*plan.excess_units.sum()/plan.stock_actual.sum() if plan.stock_actual.sum() else 0
        st.metric('SOBRESTOCK ESTIMADO',f'{over:.1f}%',help='Unidades por encima del stock ideal / stock registrado en el último mes disponible por producto y región.')
    st.markdown(f'<div class="notice">{source_tag}. El stock ideal utiliza un margen de seguridad aproximado al nivel de servicio elegido; requiere validar lead times, pedidos en tránsito y ventas perdidas.</div>',unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader('Comparación ventas contra forecast por mes')
        # Para comparar meses observados, se genera una referencia estacional desde 2024.
        hist=cut_history(universe,cut_year,current_month)
        monthly=hist.groupby(['year','mes_num'],as_index=False)['units_sold'].sum()
        monthly['date']=pd.to_datetime(dict(year=monthly.year,month=monthly.mes_num,day=1))
        monthly=monthly.sort_values('date')
        annual=monthly.copy()
        annual['date']=annual.date+pd.DateOffset(years=1)
        annual=annual.rename(columns={'units_sold':'reference_units'})
        historic=monthly.merge(annual[['date','reference_units']],on='date',how='left')
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=historic.date,y=historic.units_sold,mode='lines+markers',name='Unidades vendidas',line=dict(color=BLUE,width=3)))
        past_ref=historic.dropna(subset=['reference_units'])
        if not past_ref.empty:
            fig.add_trace(go.Scatter(x=past_ref.date,y=past_ref.reference_units,mode='lines',name='Referencia histórica',line=dict(color=PURPLE,width=2,dash='dot')))
        next_date=pd.Timestamp(year=fy,month=fm,day=1)
        fig.add_trace(go.Scatter(x=[next_date],y=[plan.forecast_units.sum()],mode='markers+text',name='Forecast siguiente mes',
            marker=dict(color=PURPLE,size=12,symbol='diamond'),text=[compact(plan.forecast_units.sum())],textposition='top center'))
        fig.add_vline(x=hist.date.max().timestamp()*1000,line_color='#F16363',line_dash='dash',line_width=1.6)
        fig.update_yaxes(title='Unidades',tickformat='~s')
        st.plotly_chart(style_fig(fig,height=280),use_container_width=True,config={'displayModeBar':False})
        st.caption('La línea punteada muestra una referencia basada en el año anterior; el punto del mes siguiente muestra el pronóstico seleccionado. No son ventas futuras observadas.')
    with st.container(border=True):
        coltitle,download=st.columns([3,1],vertical_alignment='center')
        with coltitle:st.subheader('Plan por producto y región')
        shown=plan.rename(columns={'product_name':'Producto','region':'Región','subcategory':'Subcategoría','forecast_units':'Forecast de ventas',
                                   'stock_ideal':'Stock ideal','stock_actual':'Stock actual','overstock_pct':'% Sobrestock',
                                   'days_inventory':'Días de inventario','shortfall':'Unidades a comprar','excess_units':'Excedente estimado'})
        cols=['Producto','Región','Subcategoría','Forecast de ventas','Stock ideal','Stock actual','% Sobrestock','Días de inventario','Unidades a comprar','Excedente estimado','Acción']
        with download:
            st.download_button('Descargar plan CSV',data=shown[cols].to_csv(index=False).encode('utf-8-sig'),
                               file_name=f'DanuStore_plan_{fy}_{fm:02d}.csv',mime='text/csv',use_container_width=True)
        st.dataframe(shown[cols].sort_values(['Excedente estimado','% Sobrestock'],ascending=False),hide_index=True,use_container_width=True,height=560,
          column_config={'% Sobrestock':st.column_config.ProgressColumn('% Sobrestock',format='%.1f%%',min_value=0,max_value=100),
                         'Días de inventario':st.column_config.NumberColumn('Días de inventario',format='%.0f')})
    st.caption('Acciones provisionales basadas en reglas editables: Reabastecer si falta stock ideal; Promover si días de inventario exceden el umbral; Revisar envíos si hay exceso > 20%; en otro caso Mantener. No son etiquetas del clasificador K-means.')
    with st.expander('Cómo integrar los modelos ML cuando los recibamos'):
        st.markdown('''**Opción A (recomendada):** sustituir `predict_demand` dentro de `ml_adapter.py` por la inferencia del árbol/XGBoost de su equipo.

**Opción B:** subir un `.csv` de predicciones con `product_id, region, year, mes_num, forecast_units`. El sistema seleccionará únicamente el mes posterior al corte.

Las variables disponibles para los modelos deben existir **antes del mes objetivo**. No usar `units_sold`, `stock` o métricas construidas con ventas del mes a pronosticar. Para integrar el clasificador de grupos, añadir sus etiquetas por `product_id + region` antes de calcular las recomendaciones.''')
