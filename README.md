<div align="center">

# 👶 Baby Cry Detection

### Offline AI-powered audio analysis for detecting baby cries and distress events.

<br>

<img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/PyTorch-Deep_Learning-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" />
<img src="https://img.shields.io/badge/Hugging_Face-Models-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" />
<img src="https://img.shields.io/badge/Offline-AI_System-10B981?style=for-the-badge" />

<br><br>

**Audio → Transcription → Sound Detection → Alert Analysis → JSON**

</div>

---

# `01` — Overview

**Baby Cry Detection** is an offline AI-powered baby-monitoring prototype that analyzes uploaded audio clips and determines whether the audio contains signals associated with **baby crying or distress**.

The system combines multiple local AI components:

* 🎙️ **Whisper** for audio transcription
* 🔊 **Audio Spectrogram Transformer (AST)** for sound-event classification
* 🧠 **Qwen** for generating a concise contextual explanation
* ⚙️ **Deterministic rules** for deciding whether an alert should trigger
* 🚀 **FastAPI** for exposing the analysis pipeline through an HTTP API

The system is designed around **local model inference**, without requiring a cloud AI service.

---

# `02` — What It Does

```text
                 AUDIO FILE
                      │
                      ▼
              ┌──────────────┐
              │    UPLOAD    │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │     SAVE     │
              │   /uploads   │
              └──────┬───────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    ┌────────────┐       ┌────────────┐
    │  WHISPER   │       │    AST     │
    │TRANSCRIBE  │       │ SOUND AI   │
    └─────┬──────┘       └─────┬──────┘
          │                     │
          │                     ▼
          │              DETECTED SOUNDS
          │                     │
          └──────────┬──────────┘
                     ▼
              ┌──────────────┐
              │ ALERT ENGINE │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │     QWEN     │
              │  EXPLANATION │
              └──────┬───────┘
                     │
                     ▼
                JSON RESULT
```

The result contains the information needed by a client application to understand the audio event and determine whether an alarm should be triggered.

---

# `03` — Core Capabilities

<table>
<tr>
<td width="33%" align="center">

### 🎙️ Transcription

Uses local Whisper inference to generate a transcription from the uploaded audio.

</td>

<td width="33%" align="center">

### 🔊 Sound Detection

Uses an Audio Spectrogram Transformer to identify relevant sound events.

</td>

<td width="33%" align="center">

### 🚨 Alert Analysis

Uses deterministic rules and contextual AI analysis to determine whether an alert should trigger.

</td>
</tr>
</table>

---

# `04` — AI Pipeline

The core processing pipeline consists of several stages.

```text
┌─────────────────────────────────────────────────────────┐
│                    AUDIO INPUT                          │
│                                                         │
│              baby-cry.wav / audio clip                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                     AUDIO LOAD                          │
│                                                         │
│                 librosa · 16 kHz PCM                    │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────┴───────────┐
              ▼                      ▼
┌──────────────────────┐   ┌─────────────────────────────┐
│       WHISPER        │   │             AST             │
│                      │   │                             │
│ Speech Transcription │   │ Audio Event Classification  │
└──────────┬───────────┘   └──────────────┬──────────────┘
           │                              │
           │ transcription                │ sound labels
           └──────────────┬───────────────┘
                          ▼
               ┌─────────────────────┐
               │  ALERT RULE ENGINE  │
               │                     │
               │ baby cry            │
               │ crying              │
               │ sobbing             │
               │ ...                 │
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │        QWEN         │
               │                     │
               │ Contextual summary  │
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │     JSON RESULT     │
               └─────────────────────┘
```

---

# `05` — AI Models

The project currently uses three local Hugging Face models.

| Model                                     | Purpose                        |
| ----------------------------------------- | ------------------------------ |
| `openai/whisper-tiny`                     | Audio transcription            |
| `MIT/ast-finetuned-audioset-10-10-0.4593` | Audio event classification     |
| `Qwen/Qwen2.5-0.5B-Instruct`              | Concise contextual explanation |

### Whisper

Whisper is used to extract a text transcription from the uploaded audio.

```text
Audio
  ↓
Whisper
  ↓
Transcription
```

### Audio Spectrogram Transformer

AST is used to classify sound events in the audio.

```text
Audio
  ↓
16 kHz processing
  ↓
AST
  ↓
Detected sound labels
```

### Qwen

Qwen is used after transcription and sound classification to generate a concise explanation of the detected context.

```text
Transcription
       +
Detected Sounds
       ↓
     Qwen
       ↓
Contextual Explanation
```

---

# `06` — Alert Decision System

The alert decision is intentionally not delegated entirely to the language model.

A deterministic rule-based layer checks detected sound labels for terms associated with crying or distress.

Examples include:

```text
baby cry
crying
sobbing
...
```

The simplified flow is:

```text
Detected Sounds
      │
      ▼
┌───────────────────────┐
│ Deterministic Rules   │
└───────────┬───────────┘
            │
       Match found?
        /        \
      YES         NO
       │           │
       ▼           ▼
    ALERT       NO ALERT
    TRUE          FALSE
```

This gives the system a predictable alert decision while allowing the language model to provide contextual reasoning.

---

# `07` — API

The application exposes a FastAPI endpoint for audio analysis.

### Endpoint

```http
POST /analyze-audio/
```

### Request

The endpoint accepts an uploaded audio file using multipart form data.

```bash
curl -X POST "http://localhost:8000/analyze-audio/" \
  -F "file=@/path/to/baby-cry.wav"
```

### Response

The API returns a JSON payload containing:

```json
{
  "event_id": "...",
  "timestamp": "...",
  "transcription": "...",
  "detected_sounds": [],
  "alert_analysis": "...",
  "alert_triggered": true
}
```

The exact values depend on the audio being analyzed.

---

# `08` — Request Lifecycle

```text
CLIENT
  │
  │ POST /analyze-audio/
  │
  ▼
FastAPI Router
  │
  ▼
Save Uploaded File
  │
  ▼
AI Service
  │
  ├──► transcribe()
  │
  ├──► detect_sounds()
  │
  └──► analyze_context()
  │
  ▼
JSON Response
  │
  ▼
CLIENT
```

---

# `09` — Project Architecture

The current repository keeps the API layer and AI processing layer separated.

```text
baby_cry_detection/
│
├── .gitignore
│
└── audio/
    │
    ├── README.md
    │
    ├── main.py
    ├── requirements.txt
    │
    ├── routers/
    │   └── audio_router.py
    │
    └── services/
        └── ai_service.py
```

### Runtime directory

The upload directory is created when required:

```text
audio/
└── uploads/
```

Uploaded audio files are processed from this runtime location.

---

# `10` — Component Responsibilities

## `main.py`

Responsible for:

* FastAPI application startup
* Uvicorn execution
* Application lifespan
* AI service initialization
* Model preloading

The application preloads the AI service during startup so the models remain available in memory while the service is running.

---

## `audio_router.py`

Responsible for:

* Receiving uploaded audio
* Saving the file
* Calling the AI service
* Building the API response

The router calls:

```python
ai.transcribe(file_path)
ai.detect_sounds(file_path)
ai.analyze_context(raw_transcription, sounds)
```

---

## `ai_service.py`

Contains the core AI processing logic.

Responsibilities include:

* Device selection
* Model loading
* Audio processing
* Whisper transcription
* AST sound classification
* Alert rule evaluation
* Qwen contextual analysis

The service checks whether CUDA is available:

```python
torch.cuda.is_available()
```

and uses GPU or CPU accordingly.

---

# `11` — Processing Environment

Audio processing is performed with:

```text
librosa
   │
   ▼
16 kHz PCM Audio
   │
   ▼
AI Models
```

The system is designed to process audio locally after the required models have been downloaded.

---

# `12` — Technology Stack

<div align="center">

### CORE

<img src="https://skillicons.dev/icons?i=python,fastapi" />

<br><br>

### AI / ML

<img src="https://skillicons.dev/icons?i=pytorch,huggingface" />

</div>

### Stack

| Layer                | Technology                    |
| -------------------- | ----------------------------- |
| Language             | Python                        |
| API Framework        | FastAPI                       |
| Runtime              | Uvicorn                       |
| Deep Learning        | PyTorch                       |
| Model Ecosystem      | Hugging Face Transformers     |
| Speech Recognition   | Whisper                       |
| Audio Classification | Audio Spectrogram Transformer |
| Audio Processing     | librosa                       |
| API Uploads          | python-multipart              |
| Local LLM            | Qwen                          |

---

# `13` — Installation

Clone the repository and enter the audio application directory.

```bash
cd baby_cry_detection/audio
```

Create a virtual environment:

```bash
python -m venv .venv
```

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# `14` — Run the Application

Start the FastAPI application:

```bash
python main.py
```

The service runs on:

```text
http://localhost:8000
```

The API endpoint is:

```text
POST /analyze-audio/
```

---

# `15` — Test the API

Using `curl`:

```bash
curl -X POST "http://localhost:8000/analyze-audio/" \
  -F "file=@/path/to/baby-cry.wav"
```

Replace:

```text
/path/to/baby-cry.wav
```

with the path to an audio file available on your machine.

---

# `16` — First Run

The first execution requires the Hugging Face models to be downloaded.

The current models include:

```text
Whisper
   +
AST
   +
Qwen
```

Depending on the machine and network connection, the initial setup can take several minutes.

After the models are downloaded, inference is performed locally.

### Important

The repository does **not** currently define:

* Database credentials
* Cloud API credentials
* Required application environment variables

The intended inference architecture is local model execution.

---

# `17` — Offline Architecture

The project is designed around local AI inference rather than a cloud inference API.

```text
                 ┌──────────────────────┐
                 │      AUDIO FILE       │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │     FASTAPI APP      │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    LOCAL AI MODELS   │
                 │                      │
                 │       Whisper        │
                 │        AST           │
                 │       Qwen           │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   ALERT PROCESSING   │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │      JSON API        │
                 └──────────────────────┘
```

There is no cloud inference service in the current implementation.

---

# `18` — Why the Architecture Uses Rules + AI

The project combines model-based analysis with deterministic alert logic.

```text
              AI MODELS
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
 Transcription          Sound Detection
       │                     │
       └──────────┬──────────┘
                  ▼
          Deterministic Rules
                  │
                  ▼
             Alert Decision
                  │
                  ▼
          LLM Explanation
```

This separation allows the system to use AI for **understanding the audio** while retaining a deterministic mechanism for the actual alert trigger.

---

# `19` — Current Scope

The current codebase implements the **core backend audio-analysis pipeline**.

### Implemented

* [x] Audio file upload
* [x] Audio persistence during processing
* [x] Local Whisper transcription
* [x] Local AST sound classification
* [x] Deterministic cry/distress detection rules
* [x] Qwen contextual explanation
* [x] FastAPI endpoint
* [x] JSON response
* [x] CPU/GPU device detection
* [x] Model preloading

### Not currently implemented

* [ ] Continuous microphone capture
* [ ] Real-time audio streaming
* [ ] WebSocket audio pipeline
* [ ] Mobile monitoring application
* [ ] Persistent alert history
* [ ] Database-backed monitoring
* [ ] Production deployment infrastructure

---

# `20` — From Prototype to Real-Time System

The project documentation describes a larger future monitoring architecture.

```text
              ┌───────────────────┐
              │     MICROPHONE     │
              └─────────┬─────────┘
                        │
                        ▼
               Continuous Audio
                        │
                        ▼
              ┌───────────────────┐
              │     WebSocket     │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │    FastAPI AI     │
              │      Backend      │
              └─────────┬─────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
          Whisper                AST
              │                   │
              └─────────┬─────────┘
                        ▼
                 Alert Rule Engine
                        │
                        ▼
                 Context Analysis
                        │
                        ▼
              ┌───────────────────┐
              │   Mobile / Web    │
              │     Dashboard     │
              └───────────────────┘
```

The current repository represents the **AI analysis backend portion** of this larger architecture.

---

# `21` — Future Development

Possible extensions described by the project's architecture include:

```text
CURRENT
   │
   ▼
Uploaded Audio Analysis
   │
   ▼
────────────────────────
   │
   ▼
LIVE MICROPHONE INPUT
   │
   ▼
WEBSOCKET STREAMING
   │
   ▼
REAL-TIME AI INFERENCE
   │
   ▼
ALERT MANAGEMENT
   │
   ▼
MOBILE / DASHBOARD CLIENT
```

Potential engineering directions include:

* Live microphone streaming
* WebSocket-based audio ingestion
* Custom baby-cry classification
* Alert cooldowns
* Persistent alert state
* Episode-based detection
* Mobile notifications
* Monitoring dashboard
* Long-running monitoring sessions

---

# `22` — Custom Model Direction

The current system uses general-purpose pretrained models.

A future version could replace or supplement the AST model with a specialized baby-cry classifier.

```text
Current

Audio
  ↓
General Audio Classification
  ↓
Sound Labels
  ↓
Alert Rules


Potential Future

Audio
  ↓
Baby Cry Classifier
  ↓
Cry / Distress / Other
  ↓
Confidence
  ↓
Alert Engine
```

This would allow the project to experiment with models specifically trained for infant vocalizations and distress events.

---

# `23` — Alert Cooldown Concept

A production monitoring system would also need to avoid repeatedly triggering alerts during one continuous crying episode.

A possible future flow:

```text
CRY DETECTED
      │
      ▼
ALERT TRIGGERED
      │
      ▼
COOLDOWN ACTIVE
      │
      ▼
Additional Cry Events
      │
      └──────► Do Not Repeat Alert
      │
      ▼
Episode Ends
      │
      ▼
Cooldown Reset
```

This is currently a future architectural direction rather than an implemented feature.

---

# `24` — Project Intent

This project is primarily a **proof-of-concept and architecture exploration** for an offline nursery monitoring system.

The goal is to investigate how local AI models can be combined into an audio intelligence pipeline capable of:

```text
LISTEN
  ↓
UNDERSTAND
  ↓
CLASSIFY
  ↓
REASON
  ↓
ALERT
```

The current implementation focuses specifically on the **audio-analysis backend**.

---

# `25` — Project Structure at a Glance

```text
baby_cry_detection/
│
├── .gitignore
│
└── audio/
    │
    ├── README.md
    │
    ├── main.py
    │
    ├── requirements.txt
    │
    ├── routers/
    │   └── audio_router.py
    │
    ├── services/
    │   └── ai_service.py
    │
    └── uploads/
        └── runtime audio files
```

### Responsibilities

```text
main.py
    ↓
Application + Model Startup

audio_router.py
    ↓
HTTP / Audio Upload

ai_service.py
    ↓
AI Inference + Alert Analysis

uploads/
    ↓
Runtime Audio Files
```

---

# `26` — Questions to Explore

This project can be extended in several directions.

### 🎙️ Real-Time Audio

> How can the upload-based API be converted into a live WebSocket stream from a microphone?

### 🧠 Custom Classification

> Can the default AST model be replaced with a custom baby-cry classifier?

### 🚨 Alert Management

> How can alert cooldowns and episode persistence prevent repeated alarms during a single crying event?

### 📱 Monitoring Client

> How could a mobile application consume the analysis API and display live alerts?

---

# `27` — Final Architecture

```text
                         👶
                  BABY MONITORING
                         │
                         ▼
                  🎙️ AUDIO INPUT
                         │
                         ▼
                 ┌───────────────┐
                 │    FASTAPI    │
                 └───────┬───────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
         WHISPER        AST          QWEN
            │            │            │
            ▼            ▼            │
      TRANSCRIPTION   SOUNDS          │
            │            │            │
            └──────┬─────┘            │
                   ▼                  │
             ALERT RULES             │
                   │                  │
                   └────────┬─────────┘
                            ▼
                     🚨 ALERT RESULT
                            │
                            ▼
                       JSON RESPONSE
```

---

<div align="center">

# 👶 Baby Cry Detection

### Listen. Analyze. Understand. Alert.

<br>

**Offline AI • FastAPI • Whisper • AST • Qwen**

<br>

<img src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer&color=gradient" />

</div>
