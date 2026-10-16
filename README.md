# 🐧 Pingüino Delta

Calculadora de **programación, rotación y vencimientos de medicamentos** para farmacia de Atención Primaria (APS), desarrollada en CESFAM Limache Viejo — DESAM Limache (Servicio de Salud Viña del Mar–Quillota–Petorca).

**Un solo archivo HTML, sin instalación y sin servidor.** Los Excels se leen en el navegador de quien lo usa; ningún dato sale del computador.

## ▶ Probar ahora

1. Abrir Delta: **[versión web](https://USUARIO.github.io/pinguino-delta/)** o descargar `index.html` y abrirlo con doble clic (funciona sin internet).
2. Descargar la carpeta [`demo/`](demo/) — datos **100 % ficticios**.
3. Cargar los archivos en este orden:

| Paso | Archivo | Dónde se carga |
|---|---|---|
| 1 | `01_Inventario_lotes_DEMO.xlsx` | Arsenal CESFAM → Inventario de lotes |
| 2 | `02_Consumo_promedio_DEMO.xlsx` | Arsenal CESFAM → Consumos promedio |
| 3 | `03_Programacion_vigente_DEMO.xlsx` | Arsenal CESFAM → Programación vigente |
| 4 | `04_Consumo_mes_a_mes_DEMO.xlsx` | Arsenal CESFAM → Consumo mes a mes |
| alt. | `05_Archivo_unico_Consumo_y_Programacion_DEMO.xlsx` | Reemplaza 2–4 en un solo archivo (columna *Origen*) |
| 5 | `06_Despachos_CENABAST_DEMO.xlsx` | 📊 Análisis → Calendario CENABAST |
| 6 | `07_Valor_unitario_DEMO.xlsx` | 📊 Análisis → Gasto y consumo → Valor unitario |
| 7 | `08_Diferencias_inventario_DEMO.xlsx` | 📊 Análisis → Gasto y consumo → Diferencias de inventario |
| 8 | `09_Gasto_consumo_externo_DEMO.xlsx` | 📊 Análisis → Gasto y consumo → Excel externo (opcional) |

`00_Guion_escenarios_DEMO.xlsx` indica qué debe mostrar Delta para cada artículo.

### Qué se observa con los datos demo (40 artículos)
- 🔴 **5 en quiebre** (p. ej. salbutamol inhalador, paracetamol gotas).
- ⚠ **5 con merma por vencimiento próximo** (p. ej. amlodipino 5 mg, fluoxetina).
- 🟡 **6 en sobrestock** (furosemida combina sobrestock + merma).
- ✅ 24 sin alerta.
- Doble programación CENABAST + SSVQP en 3 artículos, estacionalidad invernal en respiratorios y antibióticos.

> Los vencimientos demo están calculados desde el **16-10-2026**; con el paso del tiempo los días restantes disminuyen.

## 🔒 Datos
- Este repositorio **solo contiene datos ficticios**. `.gitignore` bloquea cualquier otro Excel.
- Nunca subir inventarios, logs de dispensación ni archivos con datos de pacientes.

## ✅ Pruebas automáticas
Cada cambio ejecuta [`tests/test_demo.py`](tests/test_demo.py) en GitHub Actions: abre Delta **sin internet**, carga los 9 Excels y exige resultados exactos (40 artículos homologados, 0 no reconocidos, clasificación de rotación 24/5/6/5, sin errores).

```bash
pip install playwright openpyxl && python -m playwright install chromium
python tests/test_demo.py          # pruebas
python tools/generar_demo.py       # regenerar Excels demo (semilla fija, idénticos)
```

## Notas de esta versión
- Pestaña **Log de farmacia** oculta temporalmente (versión demostración).
- SheetJS 0.18.5 y JSZip 3.10.1 embebidos en el HTML (funciona 100 % offline).
- Referencia SAPU incluida anonimizada (cantidades y precios ficticios).

## Licencia
CC BY-NC 4.0 — uso y adaptación libres citando la autoría; sin uso comercial. Ver [`LICENSE`](LICENSE).

## Autor
Q.F. Felipe Carrasco Cisterna — Ecosistema Pingüino APS. Ver [`CITATION.cff`](CITATION.cff).
