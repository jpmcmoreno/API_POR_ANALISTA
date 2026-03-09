# News Crawler API

## Estructura del proyecto

```
api/
├── main.py               # FastAPI app
├── news_crawler.py       # Lógica de crawling
├── requirements.txt
└── analistas/
    ├── JUAN.json         # Endpoints de cada analista
    ├── MARIA.json
    └── ...
```

## Formato del JSON de analista

```json
{
  "NOMBRE_FUENTE": [
    "https://url-seccion-1/",
    "https://url-seccion-2/"
  ],
  "OTRA_FUENTE": [
    "https://url-seccion-3/"
  ]
}
```

## Endpoints

### `GET /`
Lista los analistas disponibles.

### `GET /{analista}?fecha=YYYY-MM-DD`
Ejecuta el crawler para ese analista desde la fecha de corte.

**Parámetros:**
- `analista` — nombre del archivo sin extensión (ej: `JUAN`)
- `fecha` — fecha de corte obligatoria (ej: `2024-06-01`)
- `limite` — artículos por sección, opcional (default: `10`)

**Ejemplo:**
```
GET /JUAN?fecha=2024-06-01
GET /JUAN?fecha=2024-06-01&limite=20
```

**Respuesta:**
```json
[
  { "fuente": "OCCRP", "link": "https://...", "fecha": "2024-07-15" },
  { "fuente": "Ojo_Publico", "link": "https://...", "fecha": null }
]
```

---

## Deploy en Render

1. Sube el proyecto a GitHub
2. En Render → **New Web Service**
3. Conecta el repo
4. Configura:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy ✅
