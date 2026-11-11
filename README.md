# 🐧 Pingüino Delta

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23420389.svg)](https://doi.org/10.5281/zenodo.23420389) [![Pruebas](https://github.com/carrascocisternaf-alt/pinguino-delta/actions/workflows/pruebas.yml/badge.svg)](https://github.com/carrascocisternaf-alt/pinguino-delta/actions/workflows/pruebas.yml)

Calculadora de **programación, rotación y vencimientos de medicamentos** para farmacia de Atención Primaria (APS), desarrollada en CESFAM Limache Viejo — DESAM Limache (Servicio de Salud Viña del Mar–Quillota–Petorca).

**Un solo archivo HTML, sin instalación y sin servidor.** Los Excels se leen en el navegador de quien lo usa; ningún dato sale del computador.

## ▶ Probar ahora

1. Abrir Delta: **[versión web](https://carrascocisternaf-alt.github.io/pinguino-delta/)** o descargar `index.html` y abrirlo con doble clic (funciona sin internet).
2. Presionar **🧪 Cargar datos de prueba** (arriba, en Mi arsenal): carga los 11 Excels ficticios con un clic.

**O manualmente:** descargar la carpeta [`demo/`](demo/) — datos **100 % ficticios** — y cargar los archivos en este orden:

| Paso | Archivo | Dónde se carga |
|---|---|---|
| 1 | `01_Inventario_lotes_DEMO.xlsx` | Mi arsenal → Inventario de lotes |
| 2 | `02_Consumo_promedio_DEMO.xlsx` | Mi arsenal → Consumos promedio |
| 3 | `03_Programacion_vigente_DEMO.xlsx` | Mi arsenal → Programación vigente |
| 4 | `04_Consumo_mes_a_mes_DEMO.xlsx` | Mi arsenal → Consumo mes a mes |
| alt. | `05_Archivo_unico_Consumo_y_Programacion_DEMO.xlsx` | Reemplaza 2–4 en un solo archivo (columna *Origen*: «Consumo 2025», «Consumo SAPU 2026», «CENABAST 2026», «SSVQP 2026») |
| 5 | `06_Despachos_CENABAST_DEMO.xlsx` | 📊 Análisis → 📦 Abastecimiento → Calendario CENABAST |
| 6 | `07_Valor_unitario_DEMO.xlsx` | 📊 Análisis → 💰 Gasto y presupuesto → Gasto y consumo → Valor unitario |
| 7 | `08_Diferencias_inventario_DEMO.xlsx` | 📊 Análisis → 💰 Gasto y presupuesto → Gasto y consumo → Diferencias de inventario |
| 8 | `09_Gasto_consumo_externo_DEMO.xlsx` | 📊 Análisis → 💰 Gasto y presupuesto → Gasto y consumo → Excel externo (opcional) |
| 9 | `10_Bodega_central_SAPU_DEMO.xlsx` | 🚑 Urgencia (SAPU) → 🔁 Reposición SAPU → Stock bodega central |
| 10 | `11_Minimos_maximos_SAPU_DEMO.xlsx` | 🚑 Urgencia (SAPU) → 🔁 Reposición SAPU → Mínimos y máximos SAPU |
| 11 | `12_Consumo_diario_SAPU_DEMO.xlsx` | 🚑 Urgencia (SAPU) → 📈 Consumo real SAPU |
| 12 | `13_Stock_SAPU_AVIS_DEMO.xlsx` | 🚑 Urgencia (SAPU) → 🔁 Reposición SAPU → Stock actual del SAPU (AVIS) |

**Excel tal como sale de AVIS:** Delta busca la fila de títulos en las primeras 30 filas, así que acepta los reportes con título, fecha y funcionario arriba (por ejemplo *Toma de inventario*), números como texto («3.00», «1.234,00») y fechas dd/mm/aaaa. En el stock del SAPU usa la fecha del reporte («Fecha : dd/mm/aaaa»).

**Paquete de bodegas (Pingüino Lotes):** un solo Excel con hojas «Botiquín», «Bodega central» y «SAPU» (columnas de la toma AVIS: Nombre Artículo · Vencimiento · Lote · Stock Sist.) y una hoja opcional «Paquete» con columnas *Bodega* y *Fecha toma AVIS*. El botón «📦 Importar paquete de bodegas» (Mi arsenal y Reposición SAPU) carga las tres a la vez. Todo se procesa en el navegador; nada se sube a internet.

**Versión institucional (Microsoft 365):** la carpeta [`institucional/`](institucional/LEEME.md) permite publicar un link propio (p. ej. en Netlify) donde cada colega entra con su cuenta Microsoft institucional; Delta lee directo de SharePoint el Excel único de consumos/programaciones y el de consumo diario SAPU, comparte los stocks cargados a mano entre todos los PC y funciona sin internet con la última copia. Sin esa configuración (como en este link abierto) no se conecta a nada.

**Resumen (Mi arsenal):** situación actual sin reprogramar — stock esperado al fin del mes evaluado, meses cubiertos, alertas bajo umbral y pedido especial con la programación vigente; filtros por grupo/etiqueta, origen y con/sin programación.

**Órdenes de compra:** seguimiento por línea (✓ OK, sin recepción, informa quiebre) y cierre; en el sitio compartido varias personas editan a la vez con la clave (el servidor aplica cada cambio con su hora y combina por línea).

**Consumo diario sin fechas:** también acepta columnas «Consumo Día 1 (Sábado)», «Día 2 (Domingo)»… Delta deduce la fecha del Día 1 con los días de la semana (el más reciente que calce, sin pasar de hoy) y se puede corregir en pantalla; las columnas de días aún vacías no cuentan como informadas.

`00_Guion_escenarios_DEMO.xlsx` indica qué debe mostrar Delta para cada artículo.

### Qué se observa con los datos demo (40 artículos)
- 🔴 **5 en quiebre** (p. ej. salbutamol inhalador, paracetamol gotas).
- ⚠ **5 con merma por vencimiento próximo** (p. ej. amlodipino 5 mg, fluoxetina).
- 🟡 **6 en sobrestock** (furosemida combina sobrestock + merma).
- ✅ 24 sin alerta.
- Doble programación CENABAST + SSVQP en 3 artículos, estacionalidad invernal en respiratorios y antibióticos.

> Los vencimientos demo están calculados desde el **16-10-2026**; con el paso del tiempo los días restantes disminuyen.

## 🔁 Reposición SAPU
Calcula cuánto reponer al SAPU por **semana o mes**: primero desde la **bodega central** (por lote y vencimiento, FEFO) y lo que falte desde **farmacia**, respetando una reserva para el CESFAM. Lo programado por CENABAST/SSVQP llega a bodega central si el artículo es **exclusivo SAPU** y a farmacia si no. Regla mín/máx con revisión periódica; exporta una guía con el picking por lote.

### 📈 Consumo real del SAPU
Consumo **diario** (Fecha · Artículo · Cantidad, acumulable) y **mensual** (filas «Consumo SAPU AAAA» en el archivo único, que no se suman al botiquín). Muestra el total por día con promedio móvil de 7 días, la tendencia por artículo, la proyección mensual y la comparación con lo estimado. Con ≥ 7 días informados, el consumo real reemplaza al estimado en Reposición SAPU y en Cruce e impacto.

## 🧠 IA local (sin internet)
Todo corre en el navegador; ningún modelo reemplaza un cálculo existente, solo sugiere.

| Módulo | Dónde | Qué hace | Evidencia |
|---|---|---|---|
| Homologación que aprende | Análisis → Configuración → Equivalencias de nombres | Sugiere el artículo AVIS para nombres no reconocidos comparando principio activo, dosis y forma; aprende abreviaturas de los diccionarios y de cada equivalencia confirmada; nunca sugiere una dosis distinta | Validación cruzada (5 partes) sobre 196 pares reales: 95% de acierto vs 90% del método anterior; errores de dosis 7 vs 13 |
| Calidad de datos | Aviso en Mi arsenal · Análisis → Configuración → Calidad de datos | Detecta posibles errores al cargar (cero de más, stock de años, promedio vs real, programación desproporcionada, vencimientos improbables) con mediana y MAD del propio artículo | 0 falsos avisos en los datos demo; detecta errores sembrados |
| Política por artículo | Análisis → Abastecimiento → Política por artículo | Recomienda cobertura mín/máx por artículo minimizando quiebre (ponderado por VEN) + merma + stock, con simulación de escenarios comunes, FEFO y atrasos | La recomendada nunca es peor que la política actual en los mismos escenarios |
| Grupos de comportamiento | Análisis → Clasificación → Grupos de comportamiento | k-means sobre variabilidad, meses sin consumo, tendencia, volumen y cobertura; k elegido por silueta; política sugerida por grupo | Prueba automática |

## 🔒 Datos
- Este repositorio **solo contiene datos ficticios**. `.gitignore` bloquea cualquier otro Excel.
- Nunca subir inventarios, logs de dispensación ni archivos con datos de pacientes.

## ✅ Pruebas automáticas
Cada cambio ejecuta [`tests/test_demo.py`](tests/test_demo.py) en GitHub Actions: abre Delta **sin internet**, carga los 9 Excels (a mano y con el botón de datos de prueba) y exige resultados exactos (40 artículos homologados, 0 no reconocidos, clasificación de rotación 24/5/6/5, sin errores).

```bash
pip install playwright openpyxl && python -m playwright install chromium
python tests/test_demo.py          # pruebas
python tools/generar_demo.py       # regenerar Excels demo (semilla fija, idénticos)
```

## Notas de esta versión
- Pestaña **Log de farmacia** oculta temporalmente (versión demostración).
- SheetJS 0.18.5 y JSZip 3.10.1 embebidos en el HTML (funciona 100 % offline).
- Botón **🧪 Cargar datos de prueba** con los Excels demo embebidos (funciona online y offline).
- Referencia SAPU incluida anonimizada (cantidades y precios ficticios).

## Licencia
CC BY-NC 4.0 — uso y adaptación libres citando la autoría; sin uso comercial. Ver [`LICENSE`](LICENSE).

## Cómo citar
Carrasco Cisterna, F. (2026). *Pingüino Delta: calculadora de programación y rotación de medicamentos para farmacia de Atención Primaria* (v2.0-demo) [Software]. Zenodo. https://doi.org/10.5281/zenodo.23420389

## Autor
Q.F. Felipe Carrasco Cisterna — Ecosistema Pingüino APS. Ver [`CITATION.cff`](CITATION.cff).
