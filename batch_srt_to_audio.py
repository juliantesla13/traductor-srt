#!/usr/bin/env python3
"""
Script combinado: traduce archivos .srt a español Y genera audio.
Procesa recursivamente manteniendo la estructura de carpetas.

Uso:
    python batch_srt_to_audio.py
"""

import os
import sys
import time
import asyncio
import tempfile
import shutil
from pathlib import Path

CARPETA_RAIZ = r"D:\mis_cursos"

BATCH_SIZE = 50
MODEL = "gpt-4o-mini"
USE_OPENROUTER = True
OPENROUTER_MODEL = "openai/gpt-oss-120b"

VOICE = "es-ES-XimenaNeural"
AUDIO_FORMAT = "mp3"

try:
    import pysrt
except ImportError:
    print("Error: pip install pysrt")
    sys.exit(1)

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pip install pydub")
    print("Nota: Instala ffmpeg y agrégalo al PATH")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("Error: pip install edge-tts")
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


async def text_to_speech(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)


def generar_audio(srt_path, audio_path, voice, audio_format):
    temp_dir = tempfile.mkdtemp()
    temp_files = []

    try:
        subs = pysrt.open(srt_path)

        if len(subs) == 0:
            raise Exception("Archivo SRT vacío")

        last_end_time = subs[-1].end
        total_duration_ms = time_to_ms(last_end_time)

        base_audio = AudioSegment.silent(duration=total_duration_ms)

        for i, sub in enumerate(subs):
            start_ms = time_to_ms(sub.start)
            text = sub.text.strip()

            if not text:
                continue

            temp_file = os.path.join(temp_dir, f"temp_{i}.mp3")
            temp_files.append(temp_file)

            asyncio.run(text_to_speech(text, temp_file, voice))

            try:
                audio_clip = AudioSegment.from_file(temp_file, format="mp3")
            except Exception as e:
                print(f"    Warning: Error al cargar audio {i}: {e}")
                continue

            clip_duration_ms = len(audio_clip)
            next_start_ms = time_to_ms(sub.end) if i + 1 < len(subs) else total_duration_ms

            overlay_position = start_ms

            if start_ms + clip_duration_ms > next_start_ms:
                pass

            if overlay_position + clip_duration_ms > total_duration_ms:
                clip_duration_ms = total_duration_ms - overlay_position
                audio_clip = audio_clip[:clip_duration_ms]

            base_audio = base_audio.overlay(audio_clip, position=overlay_position)

        if audio_format == "wav":
            base_audio.export(audio_path, format="wav")
        else:
            base_audio.export(audio_path, format="mp3", bitrate="192k")

    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    raiz = Path(CARPETA_RAIZ)

    if not raiz.exists():
        print(f"Error: La carpeta '{raiz}' no existe.")
        sys.exit(1)

    client = load_client()

    archivos_srt = list(raiz.rglob("*.srt"))
    archivos_srt = [f for f in archivos_srt if not f.name.endswith("_es.srt")]

    print(f"{'='*60}")
    print(f"Traductor + Generador de Audio")
    print(f"{'='*60}")
    print(f"Carpeta raíz: {raiz}")
    print(f"Archivos .srt encontrados: {len(archivos_srt)}")
    print(f"Modelo: {OPENROUTER_MODEL if USE_OPENROUTER else MODEL}")
    print(f"Voz: {VOICE}")
    print(f"{'='*60}\n")

    if not archivos_srt:
        print("No se encontraron archivos .srt para procesar.")
        sys.exit(0)

    traducidos = 0
    saltados = 0
    errores_traduccion = 0
    errores_audio = 0

    for idx, archivo in enumerate(archivos_srt):
        carpeta = archivo.parent
        nombre = archivo.stem
        extension = archivo.suffix

        srt_output = carpeta / f"{nombre}_es{extension}"
        audio_output = carpeta / f"{nombre}_es.{AUDIO_FORMAT}"

        print(f"[{idx + 1}/{len(archivos_srt)}]")
        print(f"  Carpeta: {carpeta.relative_to(raiz)}")
        print(f"  Original: {archivo.name}")

        if srt_output.exists() and audio_output.exists():
            print(f"  Estado: YA PROCESADO -> Saltado\n")
            saltados += 1
            continue

        model_to_use = OPENROUTER_MODEL if USE_OPENROUTER else MODEL

        try:
            print(f"  Traduciendo...")
            subs = traducir_archivo(client, archivo, MODEL)
            subs.save(srt_output, encoding="utf-8")
            print(f"    -> SRT: {srt_output.name}")
            traducidos += 1
        except Exception as e:
            print(f"    -> ERROR traducción: {e}\n")
            errores_traduccion += 1
            continue

        try:
            print(f"  Generando audio...")
            generar_audio(srt_output, audio_output, VOICE, AUDIO_FORMAT)
            print(f"    -> Audio: {audio_output.name}")
        except Exception as e:
            print(f"    -> ERROR audio: {e}\n")
            errores_audio += 1

        print()

    print(f"{'='*60}")
    print(f"RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"Total procesado: {traducidos}")
    print(f"Total saltados:  {saltados}")
    print(f"Errores traducción: {errores_traduccion}")
    print(f"Errores audio:     {errores_audio}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()