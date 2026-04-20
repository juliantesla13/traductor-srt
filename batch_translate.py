#!/usr/bin/env python3
"""
Script para traducir recursivamente archivos .srt a español.
Procesa todos los archivos en subcarpetas manteniendo la estructura.

Uso:
    python batch_translate.py
"""

import os
import sys
import time
from pathlib import Path

CARPETA_RAIZ = r"D:\mis_cursos"

BATCH_SIZE = 50
MODEL = "gpt-4o-mini"
USE_OPENROUTER = True
OPENROUTER_MODEL = "openai/gpt-oss-120b"

try:
    import pysrt
except ImportError:
    print("Error: pip install pysrt")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Error: pip install openai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: pip install python-dotenv")
    sys.exit(1)


def load_client():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Define OPENAI_API_KEY en variables de entorno")
        sys.exit(1)

    if USE_OPENROUTER:
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    return OpenAI(api_key=api_key)


def time_to_ms(time_obj):
    return (time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds) * 1000 + time_obj.milliseconds


def translate_batch(client, texts, model):
    if not texts:
        return []

    combined = "\n\n".join([f"[{i+1}] {text}" for i, text in enumerate(texts)])

    prompt = f"""Traduce los siguientes subtítulos al español.
INSTRUCCIONES:
- Devuelve ÚNICAMENTE la traducción, sin comillas ni notas.
- Mantén el tono y contexto original.
- Preserva los números [1], [2], etc. en la respuesta.

{combined}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Eres un traductor profesional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )

        result = response.choices[0].message.content.strip()
        translations = []

        for line in result.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and "] " in line:
                parts = line.split("] ", 1)
                if len(parts) == 2:
                    translations.append(parts[1].strip())

        while len(translations) < len(texts):
            translations.append(texts[len(translations) - len(texts)])

        return translations[:len(texts)]

    except Exception as e:
        raise Exception(f"Error API: {e}")


def traducir_archivo(client, archivo_path, model):
    try:
        subs = pysrt.open(archivo_path)
    except Exception as e:
        raise Exception(f"Error al leer SRT: {e}")

    total_subs = len(subs)
    if total_subs == 0:
        raise Exception("Archivo SRT vacío")

    model_to_use = OPENROUTER_MODEL if USE_OPENROUTER else MODEL

    for i in range(0, total_subs, BATCH_SIZE):
        batch_end = min(i + BATCH_SIZE, total_subs)
        batch = subs[i:batch_end]
        texts = [sub.text for sub in batch]

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                translations = translate_batch(client, texts, model_to_use)
                for j, sub in enumerate(batch):
                    sub.text = translations[j] if j < len(translations) else texts[j]
                break
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep((attempt + 1) * 2)
                else:
                    raise Exception(f"Error traducción después de 3 intentos: {e}")

        if batch_end < total_subs:
            time.sleep(0.3)

    return subs


def main():
    raiz = Path(CARPETA_RAIZ)

    if not raiz.exists():
        print(f"Error: La carpeta '{raiz}' no existe.")
        sys.exit(1)

    client = load_client()

    archivos_srt = list(raiz.rglob("*.srt"))
    archivos_srt = [f for f in archivos_srt if not f.name.endswith("_es.srt")]

    print(f"{'='*60}")
    print(f"Traductor de Subtítulos - Batch Processing")
    print(f"{'='*60}")
    print(f"Carpeta raíz: {raiz}")
    print(f"Archivos .srt encontrados (sin _es): {len(archivos_srt)}")
    print(f"Modelo: {OPENROUTER_MODEL if USE_OPENROUTER else MODEL}")
    print(f"{'='*60}\n")

    if not archivos_srt:
        print("No se encontraron archivos .srt para procesar.")
        sys.exit(0)

    procesados = 0
    saltados = 0
    errores = 0

    for archivo in archivos_srt:
        carpeta = archivo.parent
        nombre = archivo.stem
        extension = archivo.suffix

        output_path = carpeta / f"{nombre}_es{extension}"

        print(f"[{procesados + saltados + errores + 1}/{len(archivos_srt)}]")
        print(f"  Carpeta: {carpeta.relative_to(raiz)}")
        print(f"  Archivo: {archivo.name}")

        if output_path.exists():
            print(f"  Estado: YA EXISTE -> Saltado\n")
            saltados += 1
            continue

        try:
            subs = traducir_archivo(client, archivo, MODEL)
            subs.save(output_path, encoding="utf-8")
            print(f"  Estado: OK -> {output_path.name}\n")
            procesados += 1
        except Exception as e:
            print(f"  Estado: ERROR -> {e}\n")
            errores += 1
            continue

    print(f"{'='*60}")
    print(f"RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"Total procesados: {procesados}")
    print(f"Total saltados:   {saltados}")
    print(f"Total errores:    {errores}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()