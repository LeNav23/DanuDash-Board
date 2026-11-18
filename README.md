# DanuDashboard

Tablero de KPIs de inventario para **DanuStore**, del reto con el socio formador **Danu Analítica** (TI3002C).
Equipo 2 · **Pandalytics**.

## ¿Qué problema resuelve?

DanuStore tiene **exceso de inventario**. Pide a China con base en la temporada pasada y reparte a 7 regiones sin saber bien cuánto vende cada una.

Este tablero muestra:

1. **Descriptivo** — cómo está hoy: ventas, rotación, sobrestock e inventario sin vender, por región, categoría y mes.
2. **Accionable** — qué hacer: pronóstico de ventas, stock ideal y acción por producto y región (comprar, no comprar, mover, promover).

## Datos

Usa `base_final`: 1 fila = producto × región × mes × año (2024 y 2025), 21,840 filas. Se construye en el Colab del equipo.

> Los datos de Danu **no** se suben al repo (es público) hasta que el equipo lo confirme.

## Estado

Ver [`AVANCE_PROYECTO.md`](AVANCE_PROYECTO.md).

## Cómo trabajar

- Rama por tarea: `feat/...`, `fix/...`. PR a `main`.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/), descripción en español: `feat: agrega filtro de región`.
- Stack: **Python + Streamlit**.

## Cómo correrlo

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Carga `Base_final_v2.xlsx` desde **Archivos de datos** en la barra lateral o coloca una copia local en `data/Base_final_v2.xlsx`. También se admite `Base_final.xlsx`. Si ambas versiones están en la carpeta local, se abre la v2 por defecto.

Con la v2, los indicadores de ventas y el pronóstico usan `units_sold_total` como unidades vendidas por producto, región y mes, la misma columna que usa la base para calcular la rotación y el inventario sin vender.
