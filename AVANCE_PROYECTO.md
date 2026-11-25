# Avance del proyecto — DanuDashboard

_Última actualización: 2026-11-25_

## Hecho

- [x] Base `base_final` construida y validada en Colab (21,840 filas, 0 huérfanos).
- [x] Modelos de la Evidencia 2 entregados (K-Means, árbol clasificador, árbol de regresión).
- [x] Diseño de tableros (Etapa 6.1) en Canva con datos dummy: descriptivo + accionable.
- [x] Repo creado con README, `.gitignore` y este archivo.

## Comentarios de la profesora (2026-11-25) — rama `fix/comentarios-maestra`

- [x] Descriptivo: tarjeta «Inventario disponible» (foto del stock del último mes elegido, en unidades).
- [x] Descriptivo: top 10 que vendieron todo, ordenado por unidades vendidas; unidades con coma de miles.
- [x] Descriptivo: top 10 menor rotación ordenado por rotación (menor a mayor, última columna); delta en colores.
- [x] Predictivo: 1.ª tarjeta = forecast vs ventas reales del mes anterior y del mismo mes del año pasado.
- [x] Predictivo: ejes más grandes, eje X por mes, sin Ene 2026, sin ventas reales en los meses pronosticados.
- [x] Predictivo: traslados región → región (destino, piezas, viajes y flete estimado $15–20 mil por viaje, ~10 mil piezas por viaje).
- [x] Todas las tablas con unidades centradas.
- [ ] Verificar con la base real: «Inventario disponible» de dic-2025 debe dar 1,287,220 piezas.
- [ ] Decidir con el equipo la regla de traslado (hoy: se manda solo lo que le falta a la otra región) y si se queda la columna «Vendidas».

## En curso / por decidir

- [x] **Stack del tablero**: Python + Streamlit (decidido 2026-11-12).
- [ ] Dónde se publica la app de Streamlit.
- [ ] **Modelos finales**: el profe cuestionó el árbol clasificador (redundante con K-Means). Propuesta: regresión (pronóstico) + K-Means (colchón por grupo) + fórmula de cuánto pedir. Falta OK del equipo y del profe.
- [ ] ¿Se suben los datos al repo o se cargan aparte? (repo público)

## Por hacer

- [ ] **David**: subir al repo el tablero que tenemos hasta ahorita.
- [ ] Cargar `base_final` y módulo único de KPIs (rotación, cobertura, sobrestock, inventario sin vender, Δ ventas).
- [ ] Vista principal del descriptivo + filtros (mes, región, categoría).
- [ ] Vistas de detalle (región, categoría).
- [ ] Tablero accionable: forecast, stock ideal, acciones por producto×región.
- [ ] Verificar cada KPI contra el notebook.
- [ ] Publicar / preparar demo para Danu.

## Cronograma

- Fechas de entrega: **por confirmar**.
