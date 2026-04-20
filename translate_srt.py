#!/usr/bin/env python3
"""
Script para traducir archivos de subtítulos .srt del inglés al español.
Utiliza la API de OpenAI (gpt-4o-mini) preservando el formato original.

Uso:
    python translate_srt.py archivo.srt
    python translate_srt.py archivo.srt --model gpt-4o  (usar otro modelo)
    python translate_srt.py archivo.srt --batch-size 100 (tamaño de lote)
"""

import os
import sys
import argparse
import time

try:
    import pysrt
except ImportError:
    print("Error: pysrt no está instalado. Instala con: pip install pysrt")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai no está instalado. Instala con: pip install openai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv no está instalado. Instala con: pip install python-dotenv")
    sys.exit(1)


BATCH_SIZE_DEFAULT = 50
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def load_openai_client(use_openrouter=False):
    """Carga el cliente de OpenAI usando la API key del entorno."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Error: La variable de entorno OPENAI_API_KEY no está configurada.")
        print("Establece la variable de entorno antes de ejecutar:")
        print("  Windows (PowerShell): $env:OPENAI_API_KEY='tu-api-key'")
        print("  Windows (CMD): set OPENAI_API_KEY=tu-api-key")
        print("  Linux/Mac: export OPENAI_API_KEY='tu-api-key'")
        sys.exit(1)

    if use_openrouter:
        return OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )

    return OpenAI(api_key=api_key)


def translate_batch(client, texts, model="gpt-4o-mini", target_lang="español"):
    """
    Traduce un lote de subtítulos al idioma objetivo.
    Mantiene el tono, contexto y no agrega texto adicional.

    Args:
        client: Cliente de OpenAI
        texts: Lista de textos a traducir
        model: Modelo de OpenAI a usar
        target_lang: Idioma objetivo

    Returns:
        Lista de textos traducidos
    """
    if not texts:
        return []

    combined = "\n\n".join([f"[{i+1}] {text}" for i, text in enumerate(texts)])

    prompt = f"""Traduce los siguientes subtítulos al {target_lang}.
INSTRUCCIONES IMPORTANTES:
- Devuelve ÚNICAMENTE la traducción, sin comillas, notas o texto adicional.
- Mantén el tono y contexto original de cada subtítulo.
- Preserva los números de línea [1], [2], etc. en la respuesta.
- Cada subtítulo traduce el texto después del número.

Subtítulos a traducir:
{combined}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Eres un traductor profesional de subtítulos."},
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
        print(f"Error durante la traducción: {e}")
        raise


def process_subtitles(input_path, output_path, batch_size, model, use_openrouter=False):
    """
    Procesa el archivo .srt traduciéndolo por lotes.

    Args:
        input_path: Ruta del archivo .srt de entrada
        output_path: Ruta del archivo .srt de salida
        batch_size: Número de subtítulos por lote
        model: Modelo de OpenAI a usar
        use_openrouter: Usar OpenRouter en lugar de OpenAI
    """
    client = load_openai_client(use_openrouter)

    print(f"Leyendo archivo: {input_path}")
    subs = pysrt.open(input_path)

    total_subs = len(subs)
    print(f"Total de subtítulos a traducir: {total_subs}")
    print(f"Tamaño de lote: {batch_size}")
    print(f"Modelo: {model}")
    print("-" * 50)

    for i in range(0, total_subs, batch_size):
        batch_end = min(i + batch_size, total_subs)
        batch = subs[i:batch_end]

        texts = [sub.text for sub in batch]

        print(f"Traduciendo subtítulos {i+1} a {batch_end} de {total_subs}...")

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                translations = translate_batch(client, texts, model)
                for j, sub in enumerate(batch):
                    sub.text = translations[j] if j < len(translations) else texts[j]
                break

            except Exception as e:
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Error: {e}. Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    print(f"Error definitivo después de {max_attempts} intentos: {e}")
                    raise

        if batch_end < total_subs:
            time.sleep(0.5)

    print("-" * 50)
    print(f"Guardando archivo traducido: {output_path}")
    subs.save(output_path, encoding="utf-8")
    print("¡Traducción completada exitosamente!")
    print(f"Archivo de salida: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Traduce archivos de subtítulos .srt al español usando OpenAI."
    )
    parser.add_argument(
        "input_file",
        help="Ruta del archivo .srt a traducir"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE_DEFAULT,
        help=f"Número de subtítulos por lote (default: {BATCH_SIZE_DEFAULT})"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Modelo de OpenAI a usar (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--openrouter",
        action="store_true",
        help="Usar OpenRouter en lugar de OpenAI"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    input_file = args.input_file
    if not os.path.exists(input_file):
        print(f"Error: El archivo '{input_file}' no existe.")
        sys.exit(1)

    if not input_file.lower().endswith(".srt"):
        print("Error: El archivo debe tener extensión .srt")
        sys.exit(1)

    base_name = input_file[:-4]
    output_file = f"{base_name}_es.srt"

    if os.path.exists(output_file):
        response = input(f"El archivo '{output_file}' ya existe. ¿Sobrescribir? (s/n): ")
        if response.lower() != "s":
            print("Operación cancelada.")
            sys.exit(0)

    try:
        process_subtitles(input_file, output_file, args.batch_size, args.model, args.openrouter)
    except Exception as e:
        print(f"Error durante el proceso: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()