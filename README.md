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
- **VRP / generación de rutas**: V2 (188 hubs orgánicos con centroides optimizados)
- **Deduplicación de rutas**: V3 (88 zonas; reduce combinaciones de rutas en un 79%)

---

## Runbook

### Repositorio y rama

```
Repositorio : https://github.com/efrouting/hubs-creation
Rama        : main
Commit evaluado: ver hash en radicación
```

### Python y dependencias

**Versión de Python:** 3.11

Instalar dependencias:
```bash
pip install pandas==2.2.3 numpy==1.26.4 polars==1.4.1 scikit-learn==1.5.1 \
            tqdm==4.66.5 folium==0.17.0 openpyxl==3.1.5
```

### Fuentes de datos externas

Antes de ejecutar el pipeline, colocar los siguientes archivos en las rutas indicadas:

| Archivo | Ruta local | Origen |
|---------|------------|--------|
| `parquetloadsfull.parquet` | `2. cleaning_loads/parquetloadsfull.parquet` | Google Drive — carpeta compartida `datos_cargas/`. Generado por `2. cleaning_loads/3. cleaning_full.ipynb`. |
| CSVs de asignación M1 (4 archivos) | `otros/*.csv` | Google Drive — carpeta compartida `otros/`. Generados por `2. cleaning_loads/4_assign_hubs.ipynb`. |
| `final_results.csv` | `5. merge dbscan/results/final_results.csv` | Generado por `5. merge dbscan/kde+dbscan.ipynb`. Se incluye una copia en `6. results/final_results.csv`. |

> **Nota**: Los archivos `.parquet` están en `.gitignore` por tamaño. `final_results.csv` está en el repositorio en `6. results/`.

### Permisos y credenciales

- Acceso de lectura a la carpeta de Google Drive compartida por el equipo de EF Routing (sin secretos en el código).
- No se requieren credenciales de AWS, bases de datos ni APIs externas para ejecutar este pipeline.

### Orden de ejecución y tiempo estimado

Ejecutar los notebooks en orden desde la carpeta `6. results/` (Jupyter o VS Code):

| Paso | Notebook | Entrada principal | Salida principal | Tiempo estimado |
|------|----------|------------------|-----------------|-----------------|
| 1 | `6. results/1_assign_hubs_m2.ipynb` | `final_results.csv`, `parquetloadsfull.parquet` | `coords_assign_m2.parquet` | ~1 min |
| 2 | `6. results/2.2 optimize_hubs_m2.ipynb` | `../5. merge dbscan/results/final_results.csv`, `coords_assign_m2.parquet`, `parquetloadsfull.parquet` | `final_results_optimized.csv` | ~15 min |
| 3 | `6. results/2.3 assign_hubs_optimized.ipynb` | `final_results_optimized.csv`, `parquetloadsfull.parquet` | `coords_assign_m2.parquet` (sobreescribe) | ~1 min |
| 4 | `6. results/3_comparacion_hubs.ipynb` | `parquetloadsfull.parquet`, `../otros/*.csv`, `coords_assign_m2.parquet` | `loads_assign_m1.parquet`, `loads_assign_m2.parquet` | ~10 min |
| 5 | `6. results/4_metricas_v3_zonas.ipynb` | `loads_assign_m1.parquet`, `hubs_id (5).xlsx` | `coords_assign_v3.parquet`, `loads_assign_v3.parquet`, `tabla_comparativa_v1v2v3.csv` | ~15 min |

**Tiempo total estimado:** ~42 min

### Comando de ejecución

```bash
# Desde la raíz del repositorio
cd "6. results"
jupyter nbconvert --to notebook --execute "1_assign_hubs_m2.ipynb" --inplace
jupyter nbconvert --to notebook --execute "2.2 optimize_hubs_m2.ipynb" --inplace
jupyter nbconvert --to notebook --execute "2.3 assign_hubs_optimized.ipynb" --inplace
jupyter nbconvert --to notebook --execute "3_comparacion_hubs.ipynb" --inplace
jupyter nbconvert --to notebook --execute "4_metricas_v3_zonas.ipynb" --inplace
```

O ejecutar celda por celda en Jupyter/VS Code para inspeccionar resultados intermedios.

### Ejemplo de punta a punta

Resultado esperado al finalizar el paso 5 (`tabla_comparativa_v1v2v3.csv`):

```
        Versión  Nodos  Radio (mi)  % origen cubiert  % destino cubiert  Deadhead Q2 (mi)      Dataset         N
V1 — K-Medoids    194          50              83.7               83.4              32.3 Feb–Ago 2025  57573489
V2 — KDE+DBSCAN   192          50              81.2               83.0              24.7 Feb–Ago 2025  57573489
    V3 — Zonas     88          75              66.3               68.1              49.8 Feb–Ago 2025  57573489
```

---

## Notebooks — descripción detallada

### `6. results/1_assign_hubs_m2.ipynb` — Asignación inicial M2

**Objetivo:** Generar la tabla de coordenadas únicas del dataset con su asignación a los hubs M2 (hubs más cercano y listas de hubs dentro de 50/100/150 mi). Este parquet es el insumo para la optimización de centroides.

| | |
|---|---|
| **Input** | `final_results.csv` (192 hubs M2) |
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` |
| **Output** | `coords_assign_m2.parquet` (738,827 coords únicas) |

---

### `6. results/2.1 analisis cobertura.ipynb` — ¿Faltan hubs M2?

**Objetivo:** Diagnosticar si la brecha de cobertura M1–M2 se debe a posicionamiento (hubs en lugares subóptimos) o a hubs faltantes.

**Conclusión:** 92.1% de las cargas no cubiertas a 50 mi tienen un hub M2 dentro de 100 mi → el problema es de posicionamiento, no de cantidad.

| | |
|---|---|
| **Input** | `loads_assign_m1.parquet`, `loads_assign_m2.parquet` (de `3_comparacion_hubs.ipynb`) |
| **Input** | `final_results.csv` |

---

### `6. results/2.2 optimize_hubs_m2.ipynb` — Optimización de centroides M2

**Objetivo:** Mover cada hub M2 hasta 80 mi para maximizar la cobertura exclusiva (anti-solapamiento). Los 4 hubs imputados (NJ/CT/RI/DE) se excluyen de la optimización.

| | |
|---|---|
| **Input** | `../5. merge dbscan/results/final_results.csv` (192 hubs) |
| **Input** | `coords_assign_m2.parquet` |
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` |
| **Output** | `final_results_optimized.csv` (188 hubs con centroides optimizados y `hub_id` únicos) |

**Nota sobre `hub_id`:** Los IDs numéricos duplicados (misma `id` en dos estados) se desambigúan con sufijo `_{state}`. Los hubs terciarios (sin `new_name`) reciben `hub_id = C{i}`.

---

### `6. results/2.3 assign_hubs_optimized.ipynb` — Asignación M2 con centroides optimizados

**Objetivo:** Regenerar `coords_assign_m2.parquet` con los centroides optimizados del paso anterior. Reemplaza el parquet inicial generado por `1_assign_hubs_m2.ipynb`.

| | |
|---|---|
| **Input** | `final_results_optimized.csv` (188 hubs) |
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` |
| **Output** | `coords_assign_m2.parquet` (sobreescribe; 738,827 coords con hub_ids optimizados) |

---

### `6. results/3_comparacion_hubs.ipynb` — Comparación M1 vs M2

**Objetivo:** Generar los parquets de asignación de cargas para M1 y M2, calcular cobertura a 50 mi, solapamiento entre hubs, y similitud geométrica de centroides (BallTree haversine).

| | |
|---|---|
| **Input** | `../2. cleaning_loads/parquetloadsfull.parquet` (57,573,489 cargas) |
| **Input** | `../otros/*.csv` (4 CSVs con asignación de coords a hubs M1) |
| **Input** | `coords_assign_m2.parquet` |
| **Input** | `../utils/hubs_id.xlsx` (sheet 0: hubs V1) |
| **Output** | `loads_assign_m1.parquet` — cargas con asignación M1 (near_hub, hubs_50/100/150m) |
| **Output** | `loads_assign_m2.parquet` — cargas con asignación M2 |

**Resultados clave:**
- M1 cobertura origen: 83.7% | M2 cobertura origen: 81.2% (% sobre total cargas)
- Mediana distancia M2→M1 nearest hub: 34.7 mi | M1→M2: 34.8 mi
- 188 hubs M2 con carga asignada (100%)

---

### `6. results/4_metricas_v3_zonas.ipynb` — Métricas V3 (Zonas)

**Objetivo:** Calcular cobertura y deadhead para V3 (88 zonas, radio 75 mi) con la misma métrica de M1/M2, y generar la tabla comparativa final V1/V2/V3 para el criterio 1.2 del convenio.

| | |
|---|---|
| **Input** | `loads_assign_m1.parquet` (de `3_comparacion_hubs.ipynb`) |
| **Input** | `hubs_id (5).xlsx` — sheet 0: hubs V1; sheet 1 (`zones id`): 88 centroides V3; sheet 2 (`zones hub`): mapping hub→zona |
| **Output** | `coords_assign_v3.parquet` (750,433 coords con near_zone, dist_mi, zones_75m) |
| **Output** | `loads_assign_v3.parquet` (57,573,489 cargas con asignación V3) |
| **Output** | `tabla_comparativa_v1v2v3.csv` — tabla resumen V1/V2/V3 |
| **Output** | `mapa_v1_v2_v3.html` — mapa Folium V1+V2+V3 (capas togglables) |

---

## Archivos de referencia — `utils/`

| Archivo | Contenido |
|---------|-----------|
| `hubs_id.xlsx` — sheet 0 | 194 centroides V1 (K-Medoids): id, lat, lng, new_name, state |
| `zones_v3.csv` | 88 zonas V3: zone_id, Zone_name, lat, lng, dhd_q1/q2/q3 |
| `states_dictionary.csv` | Diccionario de estados |

---

## Diccionario de columnas — archivos de salida principales

### `final_results_optimized.csv` (188 hubs M2)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `hub_id` | str | Identificador único del hub. Hubs con nombre: `str(id)` o `{id}_{state}` si hay duplicado. Hubs terciarios: `C{i}`. |
| `new_name` | str | Nombre del hub (nulo para hubs terciarios sin nombre asignado) |
| `state` | str | Código de estado (2 letras) |
| `lat` | float | Latitud del centroide optimizado |
| `lng` | float | Longitud del centroide optimizado |
| `categoría` | str | Categoría del hub (principal / secundario / terciario) |

### `coords_assign_m2.parquet` (738,827 coords únicas)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `lat` | float64 | Latitud de la coordenada (redondeada a 6 decimales) |
| `lng` | float64 | Longitud de la coordenada |
| `near_hub_m2` | str | `hub_id` del hub M2 más cercano |
| `hubs_50m_m2` | list[str] | Lista de `hub_id` dentro de 50 mi |
| `hubs_100m_m2` | list[str] | Lista de `hub_id` dentro de 100 mi |
| `hubs_150m_m2` | list[str] | Lista de `hub_id` dentro de 150 mi |

### `tabla_comparativa_v1v2v3.csv`

| Columna | Descripción |
|---------|-------------|
| `Versión` | Método (V1, V2, V3) |
| `Nodos` | Número de hubs/zonas |
| `Radio (mi)` | Radio de cobertura usado |
| `% origen cubiert` | % cargas con origen dentro del radio |
| `% destino cubiert` | % cargas con destino dentro del radio |
| `Deadhead Q2 (mi)` | Mediana de distancia al hub/zona más cercano (cargas cubiertas) |
| `Dataset` | Ventana de fechas |
| `N` | Total de registros evaluados |

---

## Archivos intermedios (generados, no en repo)

Los archivos `.parquet` están en `.gitignore` por tamaño. Se generan ejecutando el pipeline en orden:

| Archivo | Generado por |
|---------|-------------|
| `2. cleaning_loads/parquetloadsfull.parquet` | `2. cleaning_loads/3. cleaning_full.ipynb` |
| `otros/*.csv` (4 CSVs M1) | `2. cleaning_loads/4_assign_hubs.ipynb` |
| `6. results/coords_assign_m2.parquet` | `6. results/1_assign_hubs_m2.ipynb` → sobreescrito por `2.3` |
| `6. results/final_results_optimized.csv` | `6. results/2.2 optimize_hubs_m2.ipynb` |
| `6. results/loads_assign_m1.parquet` | `6. results/3_comparacion_hubs.ipynb` |
| `6. results/loads_assign_m2.parquet` | `6. results/3_comparacion_hubs.ipynb` |
| `6. results/coords_assign_v3.parquet` | `6. results/4_metricas_v3_zonas.ipynb` |
| `6. results/loads_assign_v3.parquet` | `6. results/4_metricas_v3_zonas.ipynb` |
