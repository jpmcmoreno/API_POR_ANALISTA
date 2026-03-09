"""
main.py — API de crawling de noticias
Render: uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import json
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from news_crawler import extract_news_links, enrich_dates

app = FastAPI(title="News Crawler API", version="1.0.0")

ANALISTAS_DIR = Path(__file__).parent / "analistas"


def cargar_analista(nombre: str) -> dict:
    """Carga el JSON del analista. Lanza 404 si no existe."""
    path = ANALISTAS_DIR / f"{nombre}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Analista '{nombre}' no encontrado. Archivo esperado: analistas/{nombre}.json"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
def health():
    analistas = [p.stem for p in ANALISTAS_DIR.glob("*.json")]
    return {"status": "ok", "analistas_disponibles": analistas}


@app.get("/{analista}")
def crawl(
    analista: str,
    fecha: str = Query(..., description="Fecha de corte formato YYYY-MM-DD"),
    limite: int = Query(10, description="Máximo de artículos por sección"),
):
    """
    Ejecuta el crawler para el analista indicado desde la fecha de corte.

    Ejemplo: /JUAN?fecha=2024-06-01
    """
    # Validar fecha
    try:
        fecha_corte = date.fromisoformat(fecha)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de fecha inválido: '{fecha}'. Usa YYYY-MM-DD"
        )

    # Cargar endpoints del analista
    endpoints = cargar_analista(analista)

    # Crawl
    resultados = []
    for fuente_nombre, urls in endpoints.items():
        for url in urls:
            resultados.extend(
                extract_news_links(
                    url,
                    limit=limite,
                    fecha_corte=fecha_corte,
                    fuente_nombre=fuente_nombre,
                )
            )

    # Enriquecer fechas null
    resultados = enrich_dates(resultados)

    # Deduplicar por link
    vistos = set()
    unicos = []
    for item in resultados:
        if item["link"] not in vistos:
            vistos.add(item["link"])
            unicos.append(item)

    return JSONResponse(content=unicos)
