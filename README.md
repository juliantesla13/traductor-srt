# Traductor de Subtítulos + Generador de Audio

Script batch para traducir archivos `.srt` a español y generar audio sincronizado.

## Tabla de Contenidos

- [Descripción](#descripción)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Scripts Disponibles](#scripts-disponibles)
- [Variables de Configuración](#variables-de-configuración)
- [Formato de Salida](#formato-de-salida)
- [Solución de Problemas](#solución-de-problemas)

---

## Descripción

Este proyecto contiene un conjunto de scripts Python que:

1. **Traduce** archivos de subtítulos `.srt` del inglés al español usando OpenAI
2. **Genera audio** mp3/wav a partir de los subtítulos traducidos
3. **Procesa recursivamente** carpetas manteniendo la estructura original

### Características

- Uso de librería oficial `openai` (v1.0.0+)
- Preserva timing y números de secuencia de subtítulos
- Procesamiento en lotes (batching) para evitar límites de tokens
- Soporte para OpenRouter
- Logs visuales en consola
- Manejo de errores continuo

---

## Instalación

### 1. Instalar Dependencias Python

```bash
pip install pysrt openai python-dotenv edge-tts pydub
```

### 2. Instalar FFmpeg (necesario para pydub)

#### Windows

1. Descarga de https://ffmpeg.org/download.html
2. extrae el archivo `.zip`
3. Agrega la carpeta `bin` al PATH de Windows

O usando winget:
```powershell
winget install ffmpeg
```

#### Verificar instalación

```bash
ffmpeg -version
```

---

## Configuración

### 1. Obtener API Key

#### OpenRouter (Recomendado - modelo gratuito)

1. Ve a https://openrouter.ai/
2. Crea una cuenta
3. Genera tu API key

#### OpenAI (Oficial)

1. Ve a https://platform.openai.com/
2. Crea una cuenta
3. Genera tu API key en https://platform.openai.com/account/api-keys

### 2. Configurar Variable de Entorno

```powershell
# PowerShell
$env:OPENAI_API_KEY="tu-api-key-aquí"

# CMD
set OPENAI_API_KEY=tu-api-key-aquí
```

Para永久设置 (PowerShell):
```powershell
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "tu-api-key", "User")
```

---

## Uso

### Script Completo (Traducción + Audio)

Procesa todos los `.srt` de una carpeta y genera audio:

```bash
python batch_srt_to_audio.py
```

### Solo Traducir

Traduce subtítulos sin generar audio:

```bash
python batch_translate.py
```

### Solo Generar Audio

Genera audio a partir de un archivo `.srt` existente:

```bash
python srt_to_audio.py "curso.srt" --voice es-ES-XimenaNeural
```

### Traducir un Solo Archivo

```bash
python translate_srt.py "archivo.srt" --openrouter --model "openai/gpt-oss-120b"
```

---

## Scripts Disponibles

| Script | Función |
|--------|---------|
| `batch_srt_to_audio.py` | Traduce + genera audio (todo en uno) |
| `batch_translate.py` | Solo traduce subtítulos |
| `srt_to_audio.py` | Solo genera audio |
| `translate_srt.py` | Traduce un archivo individual |

---

## Variables de Configuración

### batch_srt_to_audio.py

Abre el archivo y modifica las variables al inicio:

```python
CARPETA_RAIZ = r"D:\mis_cursos"     # Ruta de la carpeta a procesar

BATCH_SIZE = 50                  # Subtítulos por lote (50-100 recomendado)
MODEL = "gpt-4o-mini"           # Modelo OpenAI (default)
USE_OPENROUTER = True           # Usar OpenRouter
OPENROUTER_MODEL = "openai/gpt-oss-120b"  # Modelo OpenRouter

VOICE = "es-ES-XimenaNeural"     # Voz edge-tts
AUDIO_FORMAT = "mp3"           # Formato de salida (mp3 o wav)
```

### srt_to_audio.py

Uso desde línea de comandos:

```bash
python srt_to_audio.py "archivo.srt" [opciones]
```

| Opción | Descripción | Default |
|--------|------------|----------|
| `--output` | Archivo de salida | `nombre.mp3` |
| `--voice` | Voz edge-tts | `es-ES-XimenaNeural` |
| `--format` | Formato mp3/wav | `mp3` |

---

## Voces Disponibles

### Español España

- `es-ES-XimenaNeural` (femenino)
- `es-ES-AlvaroNeural` (masculino)
- `es-ES-ElviraNeural` (femenino)

### Español México

- `es-MX-DaliaNeural` (femenino)
- `es-MX-JorgeNeural` (masculino)

### Español Argentina

- `es-AR-ElenaNeural` (femenino)
- `es-AR-TomasNeural` (masculino)

Ver todas las voces:
```bash
python -c "import asyncio, edge_tts; vo = asyncio.run(edge_tts.list_voices()); print([v['ShortName'] for v in vo if 'es-' in v['Locale']])"
```

---

## Formato de Salida

### Estructura de Carpetas

```
D:\mis_cursos\
├── curso_01\
│   ├── 01 - Introduccion.srt      (original)
│   ├── 01 - Introduccion_es.srt   (traducido)
│   ├── 01 - Introduccion_es.mp3  (audio)
│   └── 02 - Conceptos.srt
│       ├── 02 - Conceptos_es.srt
│       └── 02 - Conceptos_es.mp3
├── curso_02\
│   └── ...
```

### Nomenclatura de Archivos

- Subtítulo traducido: `[nombre]_es.srt`
- Audio: `[nombre]_es.mp3` (o `.wav`)

---

## Solución de Problemas

### Error: "API key incorrecta"

```powershell
# Verifica que la variable esté configurada
$env:OPENAI_API_KEY
```

### Error: " pysrt no está instalado"

```bash
pip install pysrt
```

### Error: "pydub no puede cargar audio"

Instala ffmpeg y agrégalo al PATH:
```powershell
winget install ffmpeg
```

### Error: "Invalid voice"

Usa una voz válida. Ejemplo:
```bash
--voice es-ES-XimenaNeural
```

### Error: "Rate limit"

El script incluye reintentos automáticos. Si persiste, aumenta el tiempo de espera en el código.

### Archivos con espacios en blanco

En Windows PowerShell, usa comillas:
```bash
python translate_srt.py "01 - What is FastAPI.srt"
```

---

## Ejemplo Completo

```powershell
# 1. Configurar API key
$env:OPENAI_API_KEY="sk-or-v1-..."

# 2. Editar CARPETA_RAIZ en batch_srt_to_audio.py

# 3. Ejecutar
python batch_srt_to_audio.py
```

Salida esperada:

```
============================================================
Traductor + Generador de Audio
============================================================
Carpeta raíz: D:\mis_cursos
Archivos .srt encontrados: 25
Modelo: openai/gpt-oss-120b
Voz: es-ES-XimenaNeural
============================================================

[1/25]
  Carpeta: fastapi\curso_01
  Original: 01 - Introduccion.srt
  Traduciendo...
    -> SRT: 01 - Introduccion_es.srt
  Generando audio...
    -> Audio: 01 - Introduccion_es.mp3
...
============================================================
RESUMEN FINAL
============================================================
Total procesado: 20
Total saltados:  3
Errores traducción: 2
Errores audio:     0
============================================================
```

---

## Notas

- El script verifica si el archivo ya termina en `_es.srt` para evitar re-procesamiento
- Si el archivo de audio ya existe, se salta el procesamiento
- Los errores no detienen el proceso, continue con el siguiente archivo