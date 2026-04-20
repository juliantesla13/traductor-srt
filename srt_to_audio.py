#!/usr/bin/env python3
"""
Script para generar audio a partir de subtítulos .srt usando TTS.
Convierte cada subtítulo en audio y los sincroniza en una línea de tiempo.

Uso:
    python srt_to_audio.py archivo.srt
    python srt_to_audio.py archivo.srt --output mi_audio.mp3
    python srt_to_audio.py archivo.srt --voice es-ES-ElenaNeural
"""

import os
import sys
import argparse
import tempfile
import shutil
import asyncio

try:
    import pysrt
except ImportError:
    print("Error: pysrt no está instalado. Instala con: pip install pysrt")
    sys.exit(1)

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub no está instalado. Instala con: pip install pydub")
    print("Nota: En Windows, instala ffmpeg y agrégalo al PATH.")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("Error: edge-tts no está instalado. Instala con: pip install edge-tts")
    sys.exit(1)


DEFAULT_VOICE = "es-ES-ElenaNeural"
TEMP_DIR = tempfile.mkdtemp()


def time_to_ms(time_obj):
    """Convierte objeto pysrt.Time a milisegundos."""
    return (time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds) * 1000 + time_obj.milliseconds


async def text_to_speech(text, output_file, voice=DEFAULT_VOICE):
    """
    Genera audio TTS para el texto dado usando edge-tts.

    Args:
        text: Texto a convertir en audio
        output_file: Archivo de salida para el audio
        voice: Voz de edge-tts a usar
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)


def sync_audio_subtitles(srt_path, output_path, voice, audio_format):
    """
    Procesa el archivo .srt y genera audio sincronizado.

    Args:
        srt_path: Ruta del archivo .srt
        output_path: Ruta del archivo de audio de salida
        voice: Voz de edge-tts
        audio_format: Formato de salida (mp3 o wav)
    """
    print(f"Leyendo subtítulos: {srt_path}")
    subs = pysrt.open(srt_path)

    if len(subs) == 0:
        print("Error: El archivo SRT está vacío.")
        sys.exit(1)

    last_end_time = subs[-1].end
    total_duration_ms = time_to_ms(last_end_time)
    total_duration_sec = total_duration_ms / 1000
    print(f"Total de subtítulos: {len(subs)}")
    print(f"Duración total: {total_duration_sec:.2f} segundos")
    print(f"Voz: {voice}")
    print("-" * 50)

    base_audio = AudioSegment.silent(duration=total_duration_ms)

    temp_files = []

    for i, sub in enumerate(subs):
        start_ms = time_to_ms(sub.start)
        text = sub.text.strip()

        if not text:
            continue

        print(f"Generando audio {i+1}/{len(subs)}: {sub.start} -> {text[:50]}...")

        temp_file = os.path.join(TEMP_DIR, f"temp_{i}.mp3")
        temp_files.append(temp_file)

        asyncio.run(text_to_speech(text, temp_file, voice))

        try:
            audio_clip = AudioSegment.from_file(temp_file, format="mp3")
        except Exception as e:
            print(f"Error al cargar audio {temp_file}: {e}")
            continue

        clip_duration_ms = len(audio_clip)
        next_start_ms = time_to_ms(sub.end) if i + 1 < len(subs) else total_duration_ms

        if start_ms + clip_duration_ms > next_start_ms:
            pass

        overlay_position = start_ms

        if overlay_position + clip_duration_ms > total_duration_ms:
            clip_duration_ms = total_duration_ms - overlay_position
            audio_clip = audio_clip[:clip_duration_ms]

        base_audio = base_audio.overlay(audio_clip, position=overlay_position)

    print("-" * 50)
    print(f"Guardando audio: {output_path}")

    if audio_format == "wav":
        base_audio.export(output_path, format="wav")
    else:
        base_audio.export(output_path, format="mp3", bitrate="192k")

    print("Audio generado exitosamente!")

    print("Limpiando archivos temporales...")
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("Limpieza completada.")

    print(f"Archivo de salida: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera audio a partir de subtítulos .srt usando TTS."
    )
    parser.add_argument(
        "input_file",
        help="Ruta del archivo .srt de entrada"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Archivo de salida (default: nombre_original.mp3)"
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=DEFAULT_VOICE,
        help=f"Voz de edge-tts (default: {DEFAULT_VOICE})"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["mp3", "wav"],
        default="mp3",
        help="Formato de audio de salida (default: mp3)"
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

    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.{args.format}"

    if os.path.exists(output_file):
        response = input(f"El archivo '{output_file}' ya existe. ¿Sobrescribir? (s/n): ")
        if response.lower() != "s":
            print("Operación cancelada.")
            sys.exit(0)

    try:
        sync_audio_subtitles(input_file, output_file, args.voice, args.format)
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        sys.exit(1)


if __name__ == "__main__":
    main()