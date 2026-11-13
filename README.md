# hubs-creation — Pipeline de Generación de Hubs para EF Routing

Genera y valida tres versiones de hubs geográficos para el sistema de ruteo de EF Routing, usando datos de cargas históricas (Feb–Ago 2025, N=57,573,489 registros).

## Versiones de hubs

| Versión | Método | Hubs | Radio | Cobertura origen |
|---------|--------|------|-------|-----------------|
| V1 | K-Medoids | 194 | 50 mi | 83.7% |
| V2 | KDE + DBSCAN | 188 orgánicos + 4 imputados¹ | 50 mi | 81.2% |
| V3 | Zonas (agrupación de hubs V1) | 88 zonas | 75 mi | 66.3% |

¹ Los 4 hubs imputados (NJ, CT, RI, DE) se agregan al pipeline de indicadores (`efdata-indicator-generator`) para garantizar cobertura estatal. No participan en la comparación de métodos.

**Uso recomendado en producción:**
- **VRP**: V2 (192 hubs, misma cobertura que V1 con centroides optimizados)
- **Deduplicación de rutas**: V3 (agrupa hubs geográficamente cercanos en zonas; reduce combinaciones de rutas en un 79%)

---

## Orden de ejecución

```
1. [descarga de datos]       1.1–1.4  parquets_diarios / semanales
2. [limpieza]                2. cleaning_loads/3. cleaning_full.ipynb
                             2. cleaning_loads/4_assign_hubs.ipynb
3. [KDE + DBSCAN]            4. kde/kde_clusters.ipynb
                             5. merge dbscan/kde+dbscan.ipynb
4. [asignación M2 inicial]   6. results/1_assign_hubs_m2.ipynb
5. [análisis cobertura]      6. results/2.1 analisis cobertura.ipynb
6. [optimización centroides] 6. results/2.2 optimize_hubs_m2.ipynb
7. [asignación M2 final]     6. results/2.3 assign_hubs_optimized.ipynb
8. [comparación M1 vs M2]    6. results/3_comparacion_hubs.ipynb
9. [métricas V3]             6. results/4_metricas_v3_zonas.ipynb
```

---

## Notebooks — `6. results/`

### `1_assign_hubs_m2.ipynb` — Asignación inicial M2
Genera una tabla de coordenadas únicas con su asignación a hubs M2 (50 / 100 / 150 mi).

| | |
|---|---|
| **Input** | `final_results.csv` (192 hubs M2) |
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` ⚠️ Drive |
| **Output** | `coords_assign_m2.parquet` (738,827 coords únicas con asignación) |

### `2.1 analisis cobertura.ipynb` — ¿Se necesitan más hubs M2?
Diagnostica si la brecha de cobertura M1–M2 es de posicionamiento o de hubs faltantes.
Conclusión: 92.1% de las cargas no cubiertas a 50mi tienen un hub M2 dentro de 100mi → es de posicionamiento.

| | |
|---|---|
| **Input** | `loads_assign_m1.parquet` (generado por `3_comparacion_hubs.ipynb`) |
| **Input** | `loads_assign_m2.parquet` (generado por `3_comparacion_hubs.ipynb`) |
| **Input** | `final_results.csv` (hubs M2 para cálculo de distancias) |

### `2.2 optimize_hubs_m2.ipynb` — Optimización de centroides M2
Mueve cada hub M2 hasta 80mi para maximizar la cobertura exclusiva (anti-solapamiento). Excluye los 4 hubs imputados (NJ/CT/RI/DE).

| | |
|---|---|
| **Input** | `final_results.csv` (192 hubs → filtra a 188) |
| **Input** | `coords_assign_m2.parquet` |
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` ⚠️ Drive |
| **Output** | `final_results_optimized.csv` (188 hubs con centroides optimizados) |

### `2.3 assign_hubs_optimized.ipynb` — Asignación M2 con centroides optimizados
Regenera `coords_assign_m2.parquet` usando los centroides optimizados.

| | |
|---|---|
| **Input** | `final_results_optimized.csv` (188 hubs) |
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` ⚠️ Drive |
| **Output** | `coords_assign_m2.parquet` (sobreescribe con centroides optimizados) |

### `3_comparacion_hubs.ipynb` — Comparación M1 vs M2
Genera los parquets de asignación de cargas para ambos métodos y calcula cobertura y solapamiento.

| | |
|---|---|
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` ⚠️ Drive |
| **Input** | `../otros/*.csv` (4 CSVs M1 con asignación de coordenadas) ⚠️ Drive |
| **Input** | `coords_assign_m2.parquet` |
| **Output** | `loads_assign_m1.parquet`, `loads_assign_m2.parquet` |

### `4_metricas_v3_zonas.ipynb` — Métricas V3 (Zonas)
Calcula cobertura y deadhead para V3 con radio 75mi, genera la tabla comparativa final V1/V2/V3.

| | |
|---|---|
| **Input** | `loads_assign_m1.parquet` (generado por `3_comparacion_hubs.ipynb`) |
| **Input** | `../utils/hubs_id.xlsx` (sheet 1: centroides V3; sheet 2: mapping hub→zona) |
| **Output** | `coords_assign_v3.parquet`, `loads_assign_v3.parquet`, `tabla_comparativa_v1v2v3.csv` |

---

## Archivos de referencia — `utils/`

| Archivo | Contenido |
|---------|-----------|
| `hubs_id.xlsx` — sheet 0 | 194 centroides V1 (K-Medoids): id, lat, lng, new_name, state |
| `hubs_id.xlsx` — sheet 1 | 88 centroides V3 (zonas): zone_id, Zone_name, lat, lng |
| `hubs_id.xlsx` — sheet 2 | Mapping hub_id → zone_num |
| `zones_v3.csv` | Zonas V3 en formato CSV |
| `states_dictionary.csv` | Diccionario de estados |

## Archivo principal de hubs

| Archivo | Contenido |
|---------|-----------|
| `6. results/final_results.csv` | 192 hubs M2 (188 orgánicos + 4 imputados): id, lat, lng, new_name, state, categoría, cluster |
| `6. results/final_results_optimized.csv` | 188 hubs M2 con centroides optimizados (generado, no en repo) |

---

## Dependencias externas ⚠️

Los archivos grandes no están en el repositorio por tamaño:

| Archivo | Descripción | Dónde obtenerlo |
|---------|-------------|-----------------|
| `../2. cleaning_loads/parquetloadsfull.parquet` | 57.6M cargas Feb–Ago 2025 | Google Drive — carpeta `hubs-creation/datos` |
| `../otros/*.csv` | 4 CSVs con asignación M1 (163,727 coords únicas) | Google Drive — carpeta `hubs-creation/datos` |

> **Nota**: Los archivos `.parquet` están en `.gitignore`. Deben colocarse en las rutas indicadas antes de ejecutar los notebooks.
