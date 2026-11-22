"""DanuStore · dos tableros Streamlit.

Ejecutar: streamlit run app.py
Instalar: pip install -r requirements.txt

El tablero predictivo lee el Excel que genera el notebook del Random Forest
(Plan_RF_oct_dic_2025.xlsx): pronóstico, stock recomendado y acción ya vienen calculados.
"""
from __future__ import annotations
import calendar
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from data_utils import (prepare_data,subset,region_rotation,sold_out_products,
                        low_rotation_products,build_purchase_plan,
                        action_for_product,MONTH_NAMES,next_month,cut_history,REGION_SHORT,REGION_ORDER,
                        kpi_cards,rotation_status,STATUS_LABELS,prepare_plan,plan_kpis,ACTION_ORDER)

st.set_page_config(page_title='DanuStore · Inventario y compras',page_icon='📦',layout='wide',initial_sidebar_state='expanded')
BASE=Path(__file__).resolve().parent
DEFAULT_BOOKS=('Base_final_v2.xlsx', 'Base_final.xlsx')
PLAN_BOOK='Plan_RF_oct_dic_2025.xlsx'
BOOK_SNAPSHOT_HASHES={
    'Base_final_v2.xlsx': '75860ab833a29cccc68cf9ed8dc50c4f4f67f6e2ea0d415ef3eb3f5762013853',
    'Base_final.xlsx': '0825dd11fb572fb36a566f2a16343c3d2761017861b44e66260a5fb7751a687a',
}
BLUE='#6F9CF2'; MUTED='#8A97AB'; PURPLE='#A98BEB'  # se leen bien en tema claro y oscuro
# Colores cálidos y suaves (no chillones) para el semáforo; los mismos tonos que las tarjetas KPI.
STATUS_COLORS={'sobra':'#D9826F','ok':'#7FB38A','corto':'#D4A762'}
# Textos que se repiten en tablas y tarjetas (una sola definición).
UNIT_PCT_UNITS='% unidades'
COL_REGION='Región'
COL_SUBCAT='Subcategoría'
COL_ACTION='Acción'
COL_FORECAST='Forecast de ventas'
COL_IDEAL='Stock ideal'
COL_OVERSTOCK='% Sobrestock'
COL_EXCESS='Excedente estimado'

st.markdown('''<style>
/* Colores del tema. Oscuro por defecto; el script THEME/SIDE_POPOVER_JS pone html.theme-light
   cuando el fondo de la app es claro (el usuario lo cambia en el menú ⋮ → Light / Dark). */
:root {--card:#172235;--line:#2B3B54;--muted:#A9B7CC;--good:#86BF8F;--bad:#E3836F;}
html.theme-light {--card:#FFFFFF;--line:#D3DBE7;--muted:#5A6880;--good:#3F8A55;--bad:#C0533D;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {border-right:1px solid var(--line);}
.block-container {padding:.35rem 1rem 1.4rem;max-width:100%;}
/* Barra lateral: se quita casi todo el espacio vacío de arriba (franja del botón para cerrarla). */
[data-testid="stSidebarHeader"] {height:2rem;min-height:2rem;padding-top:.3rem;padding-bottom:0;}
[data-testid="stSidebarUserContent"] {padding-top:0;}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {gap:.5rem;}
[data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] {gap:.5rem;}
h1 {font-size:2rem !important;font-weight:800 !important;letter-spacing:-0.025em;}
h2 {font-size:1.23rem !important;font-weight:700 !important;}
h3 {font-size:1.05rem !important;font-weight:700 !important;}
[data-testid="stMetric"] {background:var(--card);padding:10px 14px;border-radius:9px;border:1px solid var(--line);min-height:88px;}
[data-testid="stMetricLabel"] p {font-size:0.74rem;color:var(--muted);letter-spacing:0.055em;font-weight:700;text-transform:uppercase;}
[data-testid="stMetricValue"] {font-weight:800;}
[data-testid="stMetricDelta"] {font-size:0.72rem;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--line);}
[data-testid="stTabs"] button {font-weight:700;}
.stDownloadButton button {border-radius:8px;}
[data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label {font-size:.75rem;font-weight:700;letter-spacing:.025em;}
[data-testid="stRadio"] label {font-size:.75rem;font-weight:700;}
footer {visibility:hidden;}
/* Tarjetas KPI. Colores cálidos y suaves: verde salvia = bueno, terracota = malo. */
.kpi-row {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.5rem;margin-bottom:16px;} /* compensa el -16px que Streamlit le pone al bloque */
.kpi {background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px 14px;}
.kpi-compare,.kpi-note {white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.kpi-label {font-size:.72rem;color:var(--muted);letter-spacing:.055em;font-weight:700;text-transform:uppercase;}
.kpi-unit {display:block;font-weight:500;text-transform:none;letter-spacing:0;opacity:.8;}
.kpi-value {font-size:1.9rem;font-weight:800;line-height:1.25;margin:2px 0;}
.kpi-compare {font-size:.84rem;}
.kpi-note {font-size:.74rem;color:var(--muted);margin-top:2px;}
.kpi-good {color:var(--good);font-weight:700;}
.kpi-bad {color:var(--bad);font-weight:700;}
.kpi-muted {color:var(--muted);}
@media (max-width:900px){.kpi-row{grid-template-columns:repeat(2,minmax(0,1fr));}}
/* Ventanitas de filtros: lista vertical angosta, como un menú, en vez de una fila larga. */
[data-testid="stPopoverBody"]:has([data-testid="stButtonGroup"]) {width:230px !important;min-width:230px !important;max-height:70vh;overflow-y:auto;}
[data-testid="stPopoverBody"] [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]),
[data-testid="stPopoverBody"] [data-testid="stButtonGroup"] {width:100% !important;}
[data-testid="stPopoverBody"] [data-testid="stButtonGroup"] [role="toolbar"] {flex-direction:column;flex-wrap:nowrap;align-items:stretch;gap:4px;width:100%;max-width:none !important;}
/* El script de abajo (SIDE_POPOVER_JS) pone la clase side-pop y la posición junto al botón. */
html.side-pop [data-testid="stPopoverBody"] {transform:translate(var(--pop-x),var(--pop-y)) !important;}
[data-testid="stPopoverBody"] [data-testid="stButtonGroup"] [role="toolbar"] button {width:100%;justify-content:flex-start;min-height:30px;padding:2px 12px;}
.notice{padding:0.55rem .8rem;background:var(--card);border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:.84rem;}
.sidebrand{font-size:1.1rem;font-weight:800;border-bottom:1px solid var(--line);padding:0 0 10px;margin:-1.75rem 2.5rem 8px 0;} /* sube a la fila del botón «« (que está a la derecha) */
.small-caption{font-size:.92rem;color:var(--muted);margin:0 0 18px;}
</style>''',unsafe_allow_html=True)


# Streamlit abre los popovers debajo del botón. Este script (se inyecta una sola vez en la
# página) los mueve a la DERECHA del botón abierto, como menú lateral, para no tapar los
# demás filtros. Si no cabe hacia abajo, lo sube lo necesario para que no se corte.
SIDE_POPOVER_JS='''<script>
const doc = window.parent.document;
if (!doc.getElementById('side-pop-script-v2')) {
  const s = doc.createElement('script');
  s.id = 'side-pop-script-v2';
  s.textContent = `
    (function(){
      const root = document.documentElement;
      // Tema: si el fondo de la app es claro, se pone html.theme-light (el CSS cambia sus colores).
      function detectTheme(){
        const app = document.querySelector('.stApp') || document.body;
        const m = getComputedStyle(app).backgroundColor.match(/[0-9]+/g);
        if (!m) return;
        const lum = (0.299*m[0] + 0.587*m[1] + 0.114*m[2]) / 255;
        root.classList.toggle('theme-light', lum > 0.5);
      }
      detectTheme();
      setInterval(detectTheme, 500);
      function place(){
        const btn = document.querySelector('[data-testid="stPopover"] button[aria-expanded="true"]');
        const body = document.querySelector('[data-testid="stPopoverBody"]');
        if (!btn || !body) { root.classList.remove('side-pop'); return; }
        const r = btn.getBoundingClientRect();
        const h = body.offsetHeight;
        const y = Math.max(8, Math.min(r.top, window.innerHeight - h - 8));
        root.style.setProperty('--pop-x', (r.right + 12) + 'px');
        root.style.setProperty('--pop-y', y + 'px');
        root.classList.add('side-pop');
      }
      new MutationObserver(place).observe(document.body, {subtree:true, childList:true, attributes:true, attributeFilter:['aria-expanded']});
      window.addEventListener('resize', place);
      document.addEventListener('scroll', place, true);
    })();`;
  doc.head.appendChild(s);
}
</script>'''


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


@st.cache_data(show_spinner=False)
def read_plan(buf:bytes):
    return prepare_plan(pd.read_excel(BytesIO(buf)))


def load_plan():
    """Orden: archivo subido en esta sesión > copia local en data/ > None (se pide en el tablero)."""
    if 'plan_upload' in st.session_state:
        name,buf=st.session_state['plan_upload']
        return name,read_plan(buf)
    path=BASE/'data'/PLAN_BOOK
    return (path.name,read_plan(path.read_bytes())) if path.is_file() else (None,None)


def empty_fig(title=None):
    fig=go.Figure()
    fig.add_annotation(text='Sin información para los filtros seleccionados',xref='paper',yref='paper',x=.5,y=.5,showarrow=False,font_color=MUTED)
    fig.update_layout(height=295,xaxis_visible=False,yaxis_visible=False)
    return style_fig(fig)


def style_fig(fig,height=285,margins=None):
    # Sin template ni colores de letra/cuadrícula fijos: st.plotly_chart usa theme="streamlit"
    # y los toma del tema claro u oscuro que eligió el usuario.
    fig.update_layout(height=height,margin=margins or dict(l=12,r=10,t=18,b=16),
      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
      font=dict(size=12),
      legend=dict(orientation='h',yanchor='bottom',y=1.01,xanchor='right',x=1,font=dict(size=11)),
      hovermode='closest')
    fig.update_xaxes(showgrid=False,zeroline=False)
    fig.update_yaxes(zeroline=False)
    return fig


def chart_region(d):
    r=region_rotation(d)
    if r.empty:return empty_fig()
    r=r.assign(short=r.region.map(lambda x:REGION_SHORT.get(x,x)),status=r.rotation.map(rotation_status))
    fig=go.Figure()
    # Una serie por color para que la leyenda explique el semáforo.
    for status in ('corto','ok','sobra'):  # mismo orden que las barras (de más a menos rotación)
        s=r[r.status==status]
        fig.add_trace(go.Bar(x=s.short,y=s.rotation,name=STATUS_LABELS[status],marker_color=STATUS_COLORS[status],
            text=[f'{v:.1f}%' for v in s.rotation],textposition='outside',customdata=s.region,
            hovertemplate='%{customdata}: %{y:.1f}% de su stock se vendió<extra></extra>'))
    fig.update_xaxes(categoryorder='array',categoryarray=r.short.tolist())
    fig.update_yaxes(title='Rotación (%)',range=[0,max(55,r.rotation.max()*1.2)],ticksuffix='%')
    fig=style_fig(fig,height=330)
    # Después de style_fig (que pone la leyenda a la derecha): leyenda a la izquierda, en un renglón.
    fig.update_layout(barmode='overlay',legend=dict(font=dict(size=10),x=-0.1,xanchor='left',itemwidth=30,entrywidth=0))
    return fig


def chart_months(d):
    if d.empty:return empty_fig()
    m=d.groupby('mes_num',as_index=False)[['stock','units_sold']].sum()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=m.mes_num,y=m.stock,mode='lines+markers',name='Stock',line=dict(color=BLUE,width=3),marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=m.mes_num,y=m.units_sold,mode='lines+markers',name='Unidades vendidas',line=dict(color=PURPLE,width=3),marker=dict(size=6)))
    fig.update_xaxes(tickvals=list(range(1,13)),ticktext=list(MONTH_NAMES.values()),title=None)
    fig.update_yaxes(title='Unidades',tickformat='~s')
    return style_fig(fig,height=330)



def delta_html(value, unit='%', good_when_up=True, suffix=''):
    """Flecha + número con color: verde si es bueno para el negocio, rojo si es malo."""
    if value is None: return f'<span class="kpi-muted">Sin dato para comparar</span>'
    if abs(value)<0.05: return f'<span class="kpi-muted">● Sin cambio {suffix}</span>'
    up=value>0
    cls='kpi-good' if up==good_when_up else 'kpi-bad'
    arrow='▲' if up else '▼'
    return f'<span class="{cls}">{arrow} {abs(value):.1f}{unit}</span> <span class="kpi-muted">{suffix}</span>'


def big_delta(v, good_when_up=True):
    """Número grande de cambio con flecha y color (verde = bueno para el negocio)."""
    if v is None: return '<span class="kpi-muted">—</span>'
    cls='kpi-good' if (v>0)==good_when_up else 'kpi-bad'
    return f'<span class="{cls}">{"▲" if v>0 else "▼"} {abs(v):.1f}%</span>'


def kpi_card(label, unit, value_html, compare_html, note, tip):
    return (f'<div class="kpi" title="{tip}"><div class="kpi-label">{label}<span class="kpi-unit">{unit}</span></div>'
            f'<div class="kpi-value">{value_html}</div><div class="kpi-compare">{compare_html}</div></div>')


def render_kpi_cards(k):
    """4 tarjetas. En cada una: valor, comparación con color y una frase corta para ventas."""
    if k is None:
        st.warning('No hay datos para el año y los meses elegidos.'); return
    y,last=k['year'],k['last']
    mlast,mprev=MONTH_NAMES[last],MONTH_NAMES[k['prev_m']]
    period='todo el año' if len(k['months'])==12 else ', '.join(MONTH_NAMES[m] for m in k['months']) if len(k['months'])<=3 else f'{len(k["months"])} meses'

    def uds(n):  # menos de 1 millón con comas; arriba de eso abreviado para que quepa
        return f'{n/1e6:.2f} M' if n>=1e6 else f'{n:,.0f}'

    cards=[
        kpi_card('Ventas vs año anterior',UNIT_PCT_UNITS,big_delta(k['yoy']),
                 f'{uds(k["sales"])} vs {uds(k["sales_ly"])} uds ({y-1})' if k['sales_ly'] else f'{uds(k["sales"])} uds',
                 period.capitalize() if k['yoy'] is not None else f'Sin datos de {y-1}',
                 'Unidades vendidas del periodo contra los mismos meses del año anterior. Verde = vendimos más.'),
        kpi_card('Ventas vs mes anterior',UNIT_PCT_UNITS,big_delta(k['mom']),
                 f'{mlast}: {uds(k["sales_last"])} vs {mprev}: {uds(k["sales_prev_month"])} uds' if k['sales_prev_month'] else f'{mlast}: {uds(k["sales_last"])} uds',
                 f'{mlast} {y} vs {mprev} {k["prev_y"]}' if k['mom'] is not None else 'Sin mes anterior en la base',
                 'Unidades vendidas del último mes elegido contra el mes inmediato anterior. Verde = vendimos más.'),
        kpi_card('Rotación de inventario','% vendido',f'{k["rotation"]:.1f}%',
                 delta_html(k['rotation_delta'],' pts',True,f'vs {y-1}'),
                 f'De cada 100 piezas se vendieron {k["rotation"]:.0f}',
                 'Unidades vendidas ÷ stock del periodo. Más alto = el inventario se mueve más rápido.'),
        kpi_card('Inventario sin vender','$ precio de lista',compact(k['unsold'],True),
                 delta_html(k['unsold_change'],'%',False,f'vs {mlast} {y-1}'),
                 f'Foto de {mlast} {y}',
                 'Foto del último mes elegido: (stock − vendidas) × precio de lista. No es costo. Más alto = peor (rojo si sube).'),
    ]
    st.markdown('<div class="kpi-row">'+''.join(cards)+'</div>',unsafe_allow_html=True)


def title_bar(title,subtitle):
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:flex-end">'
                f'<div><h1 style="margin:0;padding:0;line-height:1.15">{title}</h1>'
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

try:
    plan_name,plan_df=load_plan()
except Exception as exc:
    st.error(f'No se pudo cargar el plan: {exc}')
    st.session_state.pop('plan_upload',None)
    plan_name,plan_df=None,None

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
    page=st.radio('TABLERO',['Ventas e inventario','Plan de inventario por región'],label_visibility='collapsed')
    st.divider()

    # Cada filtro es un botón que abre una ventanita (popover) con chips; así todos
    # los filtros caben en la barra sin scroll. El botón muestra lo que está elegido.
    def picked(key, fmt=str, todos='Todas'):
        sel=st.session_state.get(key) or []
        if not sel: return todos
        if len(sel)<=2: return ', '.join(fmt(s) for s in sel)
        return f'{len(sel)} elegidas'

    def multi_filter(title, options, key, fmt=str, todos='Todas'):
        # Chips de selección múltiple; lista vacía = sin filtro.
        with st.popover(f'{title}: {picked(key,fmt,todos)}',use_container_width=True):
            return st.pills(title,options,selection_mode='multi',key=key,format_func=fmt,label_visibility='collapsed')

    def single_filter(title, options, key, default, fmt=str):
        # Ventanita con chips de UNA opción. Si se desmarca, se usa el valor por defecto.
        if st.session_state.get(key) not in options: st.session_state[key]=default
        with st.popover(f'{title}: {fmt(st.session_state[key])}',use_container_width=True):
            value=st.pills(title,options,selection_mode='single',key=key,format_func=fmt,label_visibility='collapsed')
        return default if value is None else value

    all_years=sorted(df.year.unique().tolist())
    year_options=[str(y) for y in all_years]+['Ambos']
    st.session_state.setdefault('year',year_options[-2])
    if page=='Ventas e inventario':
        with st.popover(f'Año: {st.session_state["year"] or year_options[-2]}',use_container_width=True):
            year_choice=st.segmented_control('Año',year_options,key='year',label_visibility='collapsed') or year_options[-2]
    else:
        year_choice=year_options[-2]  # el plan es de un solo año; no hay filtro de año
    sel_years=all_years if year_choice=='Ambos' else [int(year_choice)]
    region_options=sorted(df.region.unique().tolist(),key=lambda r:REGION_ORDER.index(r) if r in REGION_ORDER else 99)
    sel_regions=multi_filter(COL_REGION,region_options,'region',fmt=lambda r:REGION_SHORT.get(r,r))
    categories=sorted(df.category_es.unique().tolist())
    sel_cats=multi_filter('Categoría',categories,'cat')
    visible_subcats=sorted(df[df.category_es.isin(sel_cats)].subcategory.unique().tolist() if sel_cats else df.subcategory.unique().tolist())
    # Si se quita una categoría, se limpian sus subcategorías para no dejar filtros escondidos.
    if 'subcat' in st.session_state:
        st.session_state['subcat']=[s for s in st.session_state['subcat'] if s in visible_subcats]
    sel_subcats=multi_filter(COL_SUBCAT,visible_subcats,'subcat')
    if page=='Ventas e inventario':
        sel_months=multi_filter('Mes',list(range(1,13)),'month_des',fmt=lambda m:MONTH_NAMES[m],todos='Todos')
    else:
        # El plan trae solo los meses que predijo el modelo (oct–dic 2025).
        plan_months=sorted(plan_df.mes_num.unique().astype(int).tolist()) if plan_df is not None else [10,11,12]
        plan_month=single_filter('Mes del plan',plan_months,'plan_month',plan_months[0],fmt=lambda m:MONTH_NAMES[m])
        sel_actions=multi_filter(COL_ACTION,ACTION_ORDER,'act',todos='Todas')
    def reset_filters():
        # Se asignan valores vacíos (no se borran) para que los chips también se vean sin seleccionar.
        for k in ('region','cat','subcat','month_des','act'):
            st.session_state[k]=[]
        st.session_state['year']=year_options[-2]
        for k in ('plan_month',):
            st.session_state.pop(k,None)
    st.button('Quitar filtros',use_container_width=True,on_click=reset_filters)
    st.divider()
    # Carga de archivos escondida en un botón chico al final para no estorbar a los filtros.
    with st.popover('⚙ Cambiar archivos',use_container_width=True):
        st.file_uploader('Base de ventas e inventario (.xlsx)',type=['xlsx'],key='base_new',
                         on_change=remember_upload,args=('base_new','base_upload'))
        st.file_uploader('Plan del modelo (.xlsx)',type=['xlsx'],key='plan_new',
                         on_change=remember_upload,args=('plan_new','plan_upload'))
    st.caption(f'Fuente: {source_name}'+(f' · {plan_name}' if page!='Ventas e inventario' and plan_name else ''))
    components.html(SIDE_POPOVER_JS,height=0)

regions=sel_regions or None
cats=sel_cats or None
subs=sel_subcats or None

if page=='Ventas e inventario':
    months=sorted(sel_months) or None
    data=subset(df,sel_years,regions,cats,subs,months)
    title_bar('Ventas e inventario','Análisis descriptivo de ventas, inventario y rotación por región y producto')
    if data.empty:st.warning('No hay registros para los filtros seleccionados.');st.stop()
    k=kpi_cards(subset(df,None,regions,cats,subs),max(sel_years),months)
    render_kpi_cards(k)
    a,b=st.columns([1,1.05],gap='small')
    with a:
        with st.container(border=True):
            st.subheader('Rotación por región')
            st.plotly_chart(chart_region(data),use_container_width=True,config={'displayModeBar':False})
    with b:
        with st.container(border=True):
            st.subheader('Comparación ventas contra stock por mes')
            st.plotly_chart(chart_months(data),use_container_width=True,config={'displayModeBar':False})
    a,b=st.columns(2,gap='small')
    with a:
        with st.container(border=True):
            st.subheader('Top 10 que vendieron todo su stock')
            sold=sold_out_products(data)
            n_months=int(data.groupby(['year','mes_num']).ngroups)
            n_all=int((sold.months_sold_out==n_months).sum())
            st.caption(f'{n_all:,} producto-región vendieron todo su stock en los {n_months} meses elegidos' if n_months>1
                       else f'{len(sold):,} producto-región vendieron todo su stock en el mes elegido')
            sold=sold.head(10)  # top 10; el total va en la nota de arriba
            sold=sold.assign(Región=sold.region.map(lambda r:REGION_SHORT.get(r,r)))
            sold=sold.rename(columns={'product_name':'Producto','months_sold_out':'Meses con todo vendido','units_sold':'Vendidas'})
            st.dataframe(sold[['Producto',COL_REGION,'Vendidas']],hide_index=True,use_container_width=True,height=388,
                column_config={'Producto':st.column_config.TextColumn('Producto',width=150),
                               COL_REGION:st.column_config.TextColumn(COL_REGION,width=72),
                               'Vendidas':st.column_config.NumberColumn('Vendidas (uds)',format='localized',width=95)})
    with b:
        with st.container(border=True):
            st.subheader('Top 10 menor rotación y bajas ventas')
            low=low_rotation_products(data,n=10,base=subset(df,sel_years,regions,cats,subs))
            last_d=data.date.max()
            prev_lbl=MONTH_NAMES[last_d.month-1] if last_d.month>1 else None
            st.caption(f'De los 20 que menos rotan, los 10 que menos venden. Cambio = {MONTH_NAMES[last_d.month]} vs {prev_lbl} {last_d.year}' if prev_lbl
                       else 'De los 20 que menos rotan, los 10 que menos venden. Enero no tiene mes anterior en el mismo año.')
            low=low.rename(columns={'product_name':'Producto','subcategory':COL_SUBCAT,'rotation':'% de rotación','delta':'Cambio (pts)'})
            st.dataframe(low[['Producto',COL_SUBCAT,'% de rotación','Cambio (pts)']],hide_index=True,use_container_width=True,height=388,
                column_config={'Producto':st.column_config.TextColumn('Producto',width=150),
                               COL_SUBCAT:st.column_config.TextColumn('Subcat.',width=72),
                               '% de rotación':st.column_config.ProgressColumn('Rotación',min_value=0,max_value=100,format='%.0f%%',width=80),
                               'Cambio (pts)':st.column_config.NumberColumn('Delta mes ant.',format='%+.1f pts',width=96,help='Puntos de rotación del último mes contra el mes anterior del mismo año')})
    st.caption('Nota: el stock se registra cada mes. Al seleccionar varios meses, los totales corresponden a la suma de observaciones mensuales, no a un inventario físico único.')
else:
    title_bar('Plan de inventario por región','Qué hacer con el inventario de cada producto en cada región, según el pronóstico del Random Forest')
    if plan_df is None:
        _,mid,_=st.columns([1,1.4,1])
        with mid:
            st.file_uploader('Sube el plan del modelo (Plan_RF_oct_dic_2025.xlsx)',type=['xlsx'],key='plan_first',
                             on_change=remember_upload,args=('plan_first','plan_upload'))
            st.caption('Es el Excel que genera el notebook del Random Forest. Solo se pide una vez.')
        st.stop()
    p=plan_df[plan_df.mes_num==plan_month]
    if regions: p=p[p.region.isin(regions)]
    if cats: p=p[p.category_es.isin(cats)]
    if subs: p=p[p.subcategory.isin(subs)]
    if p.empty:
        st.warning('No hay registros para los filtros seleccionados.');st.stop()
    k=plan_kpis(p)
    mname=f'{MONTH_NAMES[plan_month]} {int(p.year.iloc[0])}'
    cards=[
        kpi_card('Acciones para reducir sobrestock','producto-región',f'{k["reducen"]["n"]:,}',
                 f'{k["Trasladar a otra región"]["n"]:,} trasladar · {k["Descuento"]["n"]:,} descuento',
                 '','Producto-región con sobrestock en '+mname+' que se pueden resolver trasladando o con descuento.'),
        kpi_card('Trasladar a otra región','producto-región',f'{k["Trasladar a otra región"]["n"]:,}',
                 f'{compact(k["Trasladar a otra región"]["valor"],True)} inmovilizados',
                 '','Sobra stock aquí y el mismo producto está en riesgo de agotado en otra región. Valor a precio de lista.'),
        kpi_card('Descuento','producto-región',f'{k["Descuento"]["n"]:,}',
                 f'{compact(k["Descuento"]["valor"],True)} inmovilizados',
                 '','Sobra stock y ninguna otra región lo necesita: promover o dar descuento para recuperar el dinero. Valor a precio de lista.'),
        kpi_card('Reabastecer','producto-región',f'{k["Reabastecer"]["n"]:,}',
                 'Riesgo de agotado',
                 '','Producto-región con stock por debajo de lo recomendado.'),
    ]
    st.markdown('<div class="kpi-row">'+''.join(cards)+'</div>',unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader('Comparación ventas contra forecast por mes')
        # Ventas reales de toda la historia (base final) contra el pronóstico del modelo (oct–dic 2025), con los mismos filtros.
        hist=subset(df,None,regions,cats,subs).groupby('date',as_index=False)['units_sold'].sum().sort_values('date')
        pf=plan_df
        if regions: pf=pf[pf.region.isin(regions)]
        if cats: pf=pf[pf.category_es.isin(cats)]
        if subs: pf=pf[pf.subcategory.isin(subs)]
        fc=pf.groupby(['year','mes_num'],as_index=False)['ventas_esperadas'].sum()
        fc['date']=pd.to_datetime(dict(year=fc.year.astype(int),month=fc.mes_num.astype(int),day=1))
        fc=fc.sort_values('date')
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=hist.date,y=hist.units_sold,mode='lines+markers',name='Unidades vendidas',line=dict(color=BLUE,width=3)))
        fig.add_trace(go.Scatter(x=fc.date,y=fc.ventas_esperadas,mode='lines+markers+text',name='Forecast del modelo',
            line=dict(color=PURPLE,width=3,dash='dot'),marker=dict(color=PURPLE,size=11,symbol='diamond'),
            text=[compact(v) for v in fc.ventas_esperadas],textposition='top center'))
        if len(fc):
            # La línea roja marca dónde termina el entrenamiento: desde ahí es pronóstico.
            fig.add_vline(x=(fc.date.min()-pd.DateOffset(days=15)).timestamp()*1000,line_color='#F16363',line_dash='dash',line_width=1.6)
        top=max(hist.units_sold.max(),fc.ventas_esperadas.max() if len(fc) else 0)
        fig.update_yaxes(title='Unidades',tickformat='~s',range=[hist.units_sold.min()*0.93,top*1.07])  # espacio para las etiquetas
        st.plotly_chart(style_fig(fig,height=280),use_container_width=True,config={'displayModeBar':False})

    shown=p if not sel_actions else p[p.accion.isin(sel_actions)]
    shown=shown.sort_values(['accion','valor_inmovilizado'],ascending=[True,False])
    shown=shown.assign(Región=shown.region.map(lambda r:REGION_SHORT.get(r,r)))
    shown=shown.rename(columns={'product_name':'Producto','stock':'Stock actual','ventas_esperadas':'Ventas esperadas',
                                'stock_recomendado':'Stock recomendado','diferencia':'Sobra (+) / Falta (−)','accion':COL_ACTION})
    cols=['Producto',COL_REGION,'Stock actual','Ventas esperadas','Stock recomendado','Sobra (+) / Falta (−)',COL_ACTION]
    with st.container(border=True):
        coltitle,download=st.columns([3,1],vertical_alignment='center')
        with coltitle:st.subheader('Plan de acciones por producto y región')
        with download:
            st.download_button('Descargar plan CSV',data=shown[cols].to_csv(index=False).encode('utf-8-sig'),
                               file_name=f'DanuStore_plan_{int(p.year.iloc[0])}_{plan_month:02d}.csv',mime='text/csv',use_container_width=True)
        st.dataframe(shown[cols],hide_index=True,use_container_width=True,height=520,
            column_config={'Producto':st.column_config.TextColumn('Producto',width=150),
                           COL_REGION:st.column_config.TextColumn(COL_REGION,width=72),
                           'Stock actual':st.column_config.NumberColumn('Stock actual',format='localized',width=90),
                           'Ventas esperadas':st.column_config.NumberColumn('Ventas esperadas',format='localized',width=105),
                           'Stock recomendado':st.column_config.NumberColumn('Stock recomendado',format='localized',width=115),
                           'Sobra (+) / Falta (−)':st.column_config.NumberColumn('Sobra (+) / Falta (−)',format='%+d',width=130),
                           COL_ACTION:st.column_config.TextColumn(COL_ACTION,width=160)})
    st.caption('Valores a precio de lista. El pronóstico y el stock recomendado vienen del modelo Random Forest (stock recomendado = ventas esperadas + colchón de seguridad).')
