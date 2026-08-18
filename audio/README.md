# Real-time baby-monitoring system.

The most important point is this:

Your AI/rules logic does not need to be redesigned for live streaming. The major architectural change is the audio-ingestion and communication layer.

Below is the project explained end-to-end, including what happens at the microphone, WebSocket layer, FastAPI server, AI pipeline, rules engine, alerting, mobile app, and IoT device.

1. What the project is fundamentally trying to build

You are building an offline real-time audio monitoring and alert system, primarily intended for a nursery.

The system continuously listens to audio from a microphone and determines whether the audio contains something important—for example:

Baby crying
Baby distress
Normal speech
Background noise
Other environmental sounds

When the AI detects a relevant event, your deterministic rules engine decides whether that event is sufficiently strong/consistent to generate an alert.

The final system is essentially:

              ┌─────────────────────┐
              │   Nursery / Room    │
              │                     │
              │   Microphone        │
              └──────────┬──────────┘
                         │
                         │ Continuous audio
                         ▼
              ┌─────────────────────┐
              │   IoT / Mobile      │
              │   Audio Capture     │
              └──────────┬──────────┘
                         │
                         │ 3–5 sec chunks
                         │ WebSocket
                         ▼
              ┌─────────────────────┐
              │   Offline FastAPI   │
              │      Server         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Audio Preprocessing │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ AI Audio Model(s)   │
              │                     │
              │ Whisper / AST / etc │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Deterministic Rules │
              │      Engine         │
              └──────────┬──────────┘
                         │
                  alert_triggered?
                    /           \
                  NO             YES
                  │               │
                  ▼               ▼
             Continue       WebSocket Alert
                                  │
                                  ▼
                         ┌────────────────┐
                         │ Mobile App     │
                         │ Dashboard      │
                         └────────────────┘

2. The fundamental problem: AI models don't listen forever

This is the first concept you need to understand very clearly.

Models such as Whisper or an Audio Spectrogram Transformer (AST) don't normally receive:

microphone → infinite audio stream


and continuously understand it forever.

Instead, they expect a finite piece of audio.

For example:

Audio:
──────────────────────────────────────────────────────────────>

        Chunk 1          Chunk 2          Chunk 3
      0s → 5s          5s → 10s         10s → 15s


Each chunk can independently go through your AI pipeline.

Therefore, you create the illusion of continuous listening by repeatedly creating finite windows.

3. Audio chunking

Suppose the microphone records:

00:00 ─────────────────────────────── 00:15


Instead of sending 15 seconds at once, you divide it into smaller windows.

For example:

Chunk 1: 00:00 → 00:03
Chunk 2: 00:03 → 00:06
Chunk 3: 00:06 → 00:09
Chunk 4: 00:09 → 00:12
Chunk 5: 00:12 → 00:15


This is non-overlapping chunking.

But your description mentions overlapping chunks, which is generally better for event detection.

For example:

Chunk 1: 0.0 ───── 3.0 sec
Chunk 2: 1.5 ───── 4.5 sec
Chunk 3: 3.0 ───── 6.0 sec
Chunk 4: 4.5 ───── 7.5 sec


Now an event occurring around a boundary is less likely to be split badly.

4. Why overlapping chunks matter

Imagine a baby starts crying at:

2.8 seconds


If you use:

Chunk 1: 0 → 3
Chunk 2: 3 → 6


the beginning of the cry is at the very end of Chunk 1 and the rest is in Chunk 2.

That can make classification harder.

With overlap:

Chunk 1: 0.0 → 3.0
Chunk 2: 1.5 → 4.5


the second chunk captures the cry more completely.

Therefore overlapping windows improve robustness.

But there is a trade-off:

More overlap = more AI inference = more CPU/GPU usage.

So the chunk duration and hop size need to be chosen based on your hardware.

5. 3 seconds vs 5 seconds

Your description mentions both 3-second and 5-second chunks.

These should not be treated as contradictory.

You need to establish two separate concepts:

Window length

How much audio the AI receives.

Example:

5 seconds

Hop/step size

How frequently you create a new window.

Example:

3 seconds


That produces:

Window 1: 0 → 5
Window 2: 3 → 8
Window 3: 6 → 11
Window 4: 9 → 14


This gives:

5-second audio window
3-second step
2-second overlap


That may actually be a very useful configuration for your system.

Alternatively:

3-second window
1.5-second step


could be used.

The correct choice depends on the models and hardware.

6. The important distinction: recording vs processing

The microphone should not stop recording while the AI is processing.

This is a critical architectural requirement.

Bad architecture:

Record 5 sec
      ↓
STOP microphone
      ↓
Send to server
      ↓
Run AI
      ↓
Finish
      ↓
Record next 5 sec


This creates gaps.

Instead:

Microphone
    │
    │ continuous
    ▼
Audio Buffer
    │
    ├── Chunk 1 ──► Server
    │
    ├── Chunk 2 ──► Server
    │
    ├── Chunk 3 ──► Server
    │
    └── Chunk 4 ──► Server


The microphone continuously captures.

The chunking layer continuously extracts windows.

The network continuously sends those windows.

The backend independently processes them.

7. Why WebSockets are important

Your current architecture apparently has something like:

@router.post(...)


That represents a normal HTTP request.

Conceptually:

Client
  │
  │ POST audio file
  ▼
FastAPI
  │
  │ process
  ▼
Response
  │
  ▼
Client


The connection is associated with an individual request.

For your live system, you want:

Client ═══════════════════════════ Server
       persistent connection


That's where WebSockets become useful.

A WebSocket allows the connection to remain open.

8. The WebSocket becomes your permanent communication channel

After the microphone/device connects:

IoT Device
     │
     │ WebSocket connection
     ▼
FastAPI Server


The connection remains open.

Then the device can repeatedly send:

Audio Chunk 1
Audio Chunk 2
Audio Chunk 3
Audio Chunk 4
...


without establishing a completely new HTTP request for every chunk.

More importantly, the server can send information back over that same connection.

For example:

DEVICE ───────────────► SERVER
       audio chunk

DEVICE ◄─────────────── SERVER
       alert


That's the two-way nature of WebSockets.

9. The real-time pipeline

The complete processing sequence should look approximately like this:

1. Microphone captures audio
             ↓
2. Audio buffer accumulates samples
             ↓
3. Chunk/window becomes available
             ↓
4. Chunk sent through WebSocket
             ↓
5. FastAPI receives binary audio
             ↓
6. Audio decoded
             ↓
7. Resampled / normalized
             ↓
8. AI model inference
             ↓
9. Model produces prediction
             ↓
10. Deterministic rules engine
             ↓
11. alert_triggered = true/false
             ↓
12. If false → continue
             ↓
13. If true → create alert event
             ↓
14. Push alert to mobile/dashboard
             ↓
15. Mobile displays notification


That's the core system.

10. Your AI layer stays conceptually the same

This is probably the most important thing from your previous work.

You already have an AI pipeline that takes an audio segment and produces information.

For example:

audio.wav
   ↓
preprocessing
   ↓
AI model
   ↓
prediction
   ↓
confidence
   ↓
rules engine
   ↓
alert_triggered


Live streaming doesn't fundamentally change this.

Instead of:

uploaded_file.wav


your AI receives:

live_chunk_001
live_chunk_002
live_chunk_003
...


So you're changing:

How audio enters the pipeline

rather than completely changing:

What the AI does with audio.

11. Whisper's role

If you're using Whisper, its primary strength is speech recognition/transcription.

It can take audio and produce text.

Conceptually:

Audio
  ↓
Whisper
  ↓
"baby is crying..."


However, Whisper isn't inherently a dedicated baby-cry classifier.

That distinction is important.

If your project needs to identify:

baby crying


rather than speech, an audio-event classifier may be more appropriate.

12. AST's role

The Audio Spectrogram Transformer works differently.

It is designed for audio classification tasks.

Conceptually:

Audio
  ↓
Spectrogram
  ↓
Transformer
  ↓
Class probabilities


For example:

Baby cry       0.91
Speech         0.04
Background     0.03
Other          0.02


Your exact output depends on the model you're using and how it was trained.

13. Why you may actually use multiple models

Your architecture could eventually become:

                 Audio Chunk
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
        AST                  Whisper
          │                     │
          ▼                     ▼
   Sound classification     Speech/text
          │                     │
          └──────────┬──────────┘
                     ▼
             Decision Layer
                     │
                     ▼
             Rules Engine


This allows different models to answer different questions.

For example:

AST:

"What kind of sound is this?"

Whisper:

"Is someone speaking, and what are they saying?"

Then your rules engine combines those outputs.

14. The deterministic rules engine

This part is extremely important because you don't want the AI model alone deciding whether to wake someone up.

The model may say:

cry probability = 0.82


That doesn't necessarily mean:

ALERT!


Instead, your deterministic layer can impose rules.

For example:

IF
    baby_cry_probability > threshold
AND
    cry detected in multiple consecutive windows
AND
    confidence is sufficiently high

THEN
    alert_triggered = true


This prevents one bad AI prediction from generating an unnecessary notification.

15. Temporal reasoning is especially important

This system is fundamentally temporal.

One chunk might produce:

Chunk 1 → cry = 0.87
Chunk 2 → cry = 0.91
Chunk 3 → cry = 0.93


That's much more convincing than:

Chunk 1 → cry = 0.91
Chunk 2 → cry = 0.11
Chunk 3 → cry = 0.07


Therefore, your rules engine can maintain state.

For example:

previous_predictions
        ↓
rolling window
        ↓
threshold logic
        ↓
alert decision


This is where your existing deterministic logic becomes extremely valuable.

16. Alert state

The backend might maintain something conceptually like:

alert_triggered
alert_type
confidence
timestamp
duration


For example:

{
    "alert_triggered": true,
    "alert_type": "baby_cry",
    "confidence": 0.94,
    "timestamp": "...",
    "duration": 6.0
}


The exact schema can be designed later.

The important concept is that AI inference and alert generation are separate layers.

17. Preventing notification spam

This will become one of the biggest practical problems.

Suppose the baby cries for 30 seconds.

You could receive:

Chunk 1 → ALERT
Chunk 2 → ALERT
Chunk 3 → ALERT
Chunk 4 → ALERT
Chunk 5 → ALERT
...


You don't want five or ten notifications.

Instead, your system should distinguish:

EVENT START
EVENT CONTINUING
EVENT END


For example:

21:00:01  Cry detected
21:00:04  Cry continues
21:00:07  Cry continues
21:00:10  Cry continues
21:00:15  Cry ended


The mobile app might receive only:

Baby crying detected


and keep that alert active until the event ends.

18. The IoT device

Now we reach the physical architecture.

You need something that can:

Capture microphone audio
Buffer it
Create chunks
Connect to Wi-Fi
Maintain a WebSocket
Send audio to the server

There are two major approaches you mentioned.

19. Option A — Raspberry Pi

A Raspberry Pi is a very strong choice for a prototype.

Architecture:

Microphone
    ↓
Raspberry Pi
    ↓
Audio capture
    ↓
Chunking
    ↓
WebSocket
    ↓
FastAPI server


Advantages:

Linux environment
Python support
Easy FastAPI integration
Easy audio libraries
Wi-Fi
USB microphone support
Easier debugging
More CPU/RAM than a typical microcontroller
Can potentially run some AI locally

For development, this is probably the easiest hardware platform.

20. Option B — ESP32

ESP32 is much smaller and cheaper.

But it introduces considerably more engineering complexity.

You have:

Microphone
    ↓
ESP32
    ↓
I2S/audio capture
    ↓
Buffer
    ↓
Encoding
    ↓
Wi-Fi
    ↓
WebSocket


The challenge is that you have limited:

RAM
CPU
storage
operating-system functionality

You therefore generally don't want to run your heavy AI pipeline on the ESP32.

The ESP32 should primarily act as:

Audio capture + network streaming device

while the FastAPI server handles:

AI inference + rules + alert logic

21. Option C — Old smartphone

This is actually a very interesting prototype option.

Architecture:

Phone microphone
       ↓
React Native application
       ↓
Audio capture
       ↓
Chunking
       ↓
WebSocket
       ↓
FastAPI server


The smartphone already gives you:

Microphone
Wi-Fi
CPU
Memory
Battery
Screen
Networking
Application runtime

So you don't need to build the low-level microphone hardware yourself.

For a proof of concept, an old Android phone could be considerably easier than designing an ESP32 audio device.

22. But the smartphone has an important problem

Mobile operating systems aggressively manage background applications.

Your application may encounter:

Background execution restrictions
Battery optimization
App suspension
Microphone permissions
Network interruptions
Screen-off behavior
OS-specific audio limitations

So while a smartphone is excellent for prototyping, it isn't necessarily the ideal final dedicated nursery device.

23. A sensible development strategy

I would separate the project into phases.

Phase 1 — Offline audio

You already have this.

audio file
   ↓
AI
   ↓
rules
   ↓
result

Phase 2 — Simulated live streaming

Before buying hardware, simulate the microphone.

Take a long audio recording:

30-minute recording


and make software behave as if it were live:

0–5 sec → send
3–8 sec → send
6–11 sec → send
9–14 sec → send
...


This lets you test your entire backend without hardware.

This is an extremely important step.

24. Phase 3 — WebSocket backend

Replace:

POST /audio


with something conceptually like:

WebSocket /ws/audio


Then your server can accept:

binary audio chunk
binary audio chunk
binary audio chunk
...


and return events:

{
    "type": "alert",
    "event": "baby_cry",
    ...
}

25. Phase 4 — Desktop microphone

Before IoT hardware, connect a normal computer microphone.

Then:

Laptop microphone
       ↓
chunker
       ↓
WebSocket
       ↓
FastAPI
       ↓
AI
       ↓
rules


This isolates audio-capture problems from hardware problems.

26. Phase 5 — Raspberry Pi

Once the software works:

Raspberry Pi
    +
microphone


becomes your dedicated capture device.

Then you can put it physically in the room.

27. Phase 6 — Mobile dashboard

The phone should become the monitor/control interface, not necessarily the microphone.

For example:

                  ┌───────────────┐
                  │ Nursery Pi    │
                  │ + microphone  │
                  └───────┬───────┘
                          │
                       Wi-Fi
                          │
                          ▼
                  ┌───────────────┐
                  │ Local Server  │
                  │ FastAPI + AI  │
                  └───────┬───────┘
                          │
                       WebSocket
                          │
                          ▼
                  ┌───────────────┐
                  │ Parent Phone  │
                  │ React Native  │
                  └───────────────┘

28. Offline architecture

You specifically described an offline FastAPI server.

That means the system can operate entirely within the local network.

For example:

              HOME Wi-Fi
                  │
       ┌──────────┼──────────┐
       │          │          │
       ▼          ▼          ▼
   Raspberry    Server     Phone
       Pi       + AI


No cloud service is necessarily required.

This has several advantages:

Privacy

Room audio doesn't have to leave the home.

Reliability

Internet failure doesn't necessarily stop monitoring.

Latency

Local network communication can be very fast.

Cost

No continuous cloud inference costs.

29. Local Wi-Fi does not mean "no network"

This distinction is important.

Your architecture can be:

Internet
   X
   │
   │ not required
   │
Home Router
   │
   ├── Raspberry Pi
   ├── FastAPI Server
   └── Mobile Phone


All devices communicate through the local network.

The server could potentially run on:

Desktop PC
Laptop
Raspberry Pi with sufficient hardware
Mini PC
NVIDIA Jetson-class device
Other local compute hardware

depending on the model's computational requirements.

30. Mobile dashboard communication

There are actually two possible WebSocket connections.

Connection 1

Audio device → AI server

Audio Device
      │
      │ audio chunks
      ▼
FastAPI

Connection 2

Mobile app → AI server

FastAPI
   │
   │ alert events
   ▼
Mobile App


This is a cleaner architecture than trying to send everything through the audio device.

31. Example complete event

Imagine the baby starts crying.

Step 1

Microphone captures:

00:00–00:05

Step 2

Device sends:

chunk_001

Step 3

FastAPI receives it.

Step 4

Preprocessing happens.

Step 5

AST produces something like:

cry = 0.91

Step 6

Rules engine checks historical predictions.

Suppose:

previous = 0.89
current = 0.91

Step 7

Rule becomes true:

alert_triggered = true

Step 8

Backend creates:

BABY_CRY_STARTED

Step 9

Mobile WebSocket receives:

{
    "type": "alert",
    "event": "baby_cry",
    "confidence": 0.91
}

Step 10

React Native displays:

⚠️ Baby crying detected


and potentially triggers a local notification.

32. Latency

You should think of the system latency as:

Audio capture
      +
Chunk waiting time
      +
Network transmission
      +
Preprocessing
      +
AI inference
      +
Rules processing
      +
Alert transmission


For example, if you use a 5-second window and only process after the entire window has been captured, there is inherently up to roughly 5 seconds of capture delay.

With overlapping windows and appropriate buffering, you can reduce the perceived response delay.

This is why "real-time" does not necessarily mean zero latency.

It means:

The system continuously processes new audio with bounded, predictable delay.

33. One major architectural issue: sequential vs concurrent processing

Suppose your chunks arrive:

Chunk 1
Chunk 2
Chunk 3
Chunk 4


and AI inference takes 2 seconds.

If chunks arrive every 1 second, you can end up with:

Chunk 1 → processing
Chunk 2 → waiting
Chunk 3 → waiting
Chunk 4 → waiting


Eventually the backend falls behind.

Therefore you need to design the processing pipeline carefully.

Possible architecture:

WebSocket receiver
       ↓
   async queue
       ↓
  worker(s)
       ↓
 AI inference
       ↓
 rules engine


The WebSocket receiver should not necessarily perform all heavy inference directly.

34. Queue architecture

A robust design could look like:

                 WebSocket
                     │
                     ▼
              Audio Receiver
                     │
                     ▼
                Audio Queue
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
       Worker 1            Worker 2
           │                   │
           └─────────┬─────────┘
                     ▼
                 AI Model
                     │
                     ▼
              Rules Engine
                     │
                     ▼
               Event Queue
                     │
                     ▼
             Mobile WebSocket


This gives you separation between:

Network I/O
Audio processing
AI inference
Alert delivery
35. Don't let the queue grow indefinitely

This is another critical real-time design issue.

If the AI becomes slower than the audio arrival rate:

Incoming:
████████████████████

Processing:
███


the queue grows.

Eventually you have:

10 sec behind
20 sec behind
30 sec behind
...


A baby monitor that tells you about crying 60 seconds after it happened is useless.

Therefore, a real-time system should prioritize freshness.

You may need policies such as:

If queue is too old:
    drop stale audio
    process newest audio


rather than blindly processing every chunk forever.

36. Audio format

You also need to standardize the audio format between device and server.

Things you need to define include:

Sample rate
Channels
Bit depth
Encoding
Chunk duration
Byte format


For example, you might choose:

16 kHz
mono
16-bit PCM


depending on the model requirements.

The exact format should be determined by the model's expected input and the capabilities of your capture device.

37. Why PCM is attractive

Raw PCM is straightforward.

Conceptually:

Microphone
   ↓
PCM samples
   ↓
WebSocket binary frame
   ↓
FastAPI


The downside is bandwidth.

Compressed formats reduce network usage but add encoding/decoding complexity and potentially additional latency.

Since your system is intended for local Wi-Fi, raw/low-complexity audio may be perfectly reasonable depending on your chosen sample rate.

38. WebSocket messages shouldn't be only "audio"

You should think of your WebSocket protocol as an actual application protocol.

For example, there can be message types:

connection
audio
heartbeat
configuration
status
alert
error


Conceptually:

{
    "type": "audio",
    "timestamp": "...",
    "sequence": 1024
}


followed by binary audio data.

This makes debugging and synchronization much easier.

39. Sequence numbers are extremely useful

Each chunk should ideally have a sequence number.

For example:

chunk 001
chunk 002
chunk 003
chunk 004


If the server receives:

001
002
004


you immediately know:

003 was lost


This becomes extremely useful for debugging network issues.

40. Timestamps are also important

Each chunk should have a timestamp associated with when the audio was captured.

This allows you to distinguish:

audio happened at 21:43:10


from:

server processed it at 21:43:14


That distinction is extremely important when measuring latency.

41. Device identity

If you eventually have multiple rooms/devices, you need device IDs.

For example:

nursery-mic-01
bedroom-mic-01
livingroom-mic-01


Then the backend knows which microphone generated the event.

Architecture:

Device A ──┐
Device B ──┼──► FastAPI ──► Rules
Device C ──┘

42. Connection lifecycle

The system also needs to handle:

connect
disconnect
reconnect
heartbeat
timeout


For example:

Device
  │
  ├── CONNECT
  │
  ├── AUDIO
  │
  ├── AUDIO
  │
  ├── AUDIO
  │
  ├── HEARTBEAT
  │
  ├── AUDIO
  │
  X── Wi-Fi interruption
  │
  ├── RECONNECT
  │
  └── AUDIO


This is essential for a real physical product.

43. The mobile application

Your React Native application can have several responsibilities.

Dashboard

Show:

System status
Microphone status
AI status
Current event
Last detected event
Connection status

Alerts

Display:

Baby crying detected

History

Potentially:

21:43 Baby crying
21:31 Baby crying
20:54 Environmental noise

Configuration

Potentially allow:

Sensitivity
Alert threshold
Monitoring on/off
Device selection

44. Important distinction: dashboard vs notification

The mobile app doesn't necessarily need to stay open.

There are two different concepts:

Live dashboard

Requires an active connection:

App open
   ↓
WebSocket
   ↓
Server

Background notification

The operating system needs to wake/display something even when your app isn't actively visible.

This is much more platform-dependent.

For a fully offline local-network system, background notification behavior requires careful mobile architecture.

So don't assume:

WebSocket → phone screen automatically wakes


is universally guaranteed.

The WebSocket can deliver an event to an active app, but true background/system notification behavior is a separate concern.

45. The project should therefore have clear layers

I would organize your architecture into these layers:

┌─────────────────────────────────────────┐
│              PHYSICAL LAYER             │
│ Microphone / Raspberry Pi / ESP32       │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│            AUDIO INGESTION              │
│ Capture / buffer / chunk / timestamp    │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│             TRANSPORT LAYER             │
│             WebSocket                   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│          AUDIO PROCESSING               │
│ Decode / resample / normalize           │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│              AI LAYER                   │
│ AST / Whisper / other models            │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│          DECISION LAYER                 │
│ Deterministic rules / temporal logic    │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│             EVENT LAYER                 │
│ Alert creation / deduplication          │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│          MOBILE COMMUNICATION            │
│ WebSocket / notifications / dashboard   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│             UI LAYER                    │
│ React Native mobile dashboard           │
└─────────────────────────────────────────┘


This separation will make your project much easier to maintain.

46. What changes from your current project

Your current system is approximately:

Audio File
    ↓
FastAPI POST
    ↓
Preprocessing
    ↓
AI
    ↓
Rules
    ↓
Response


The new system becomes:

Continuous Microphone
       ↓
Audio Buffer
       ↓
Chunk Generator
       ↓
WebSocket
       ↓
Audio Receiver
       ↓
Processing Queue
       ↓
AI
       ↓
Rules
       ↓
Event Manager
       ↓
WebSocket
       ↓
Mobile App


So the AI and rules engine can remain largely reusable.

47. The biggest engineering challenges

The difficult parts of the project aren't necessarily the WebSocket itself.

The major challenges will be:

1. Audio capture reliability

The microphone must continuously produce valid audio.

2. Chunk timing

You need consistent windows and overlap.

3. AI inference speed

The backend must process audio fast enough to keep up.

4. Latency

You need alerts quickly enough to be useful.

5. Temporal decision-making

One prediction shouldn't necessarily trigger an alert.

6. Alert deduplication

One crying episode should not produce dozens of notifications.

7. Connection reliability

Wi-Fi interruptions must be handled.

8. Device recovery

If the IoT device crashes, the system should recover.

9. Mobile background behavior

Notifications must work appropriately when the app isn't foregrounded.

10. Resource management

Memory, CPU, GPU and queue sizes must remain controlled.

48. The architecture I would recommend for your project

For the first serious live prototype, I'd recommend:

                ┌──────────────────────┐
                │   USB / I2S Mic      │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   Raspberry Pi       │
                │                      │
                │ Audio Capture        │
                │ Buffer               │
                │ Chunk Generator      │
                │ WebSocket Client     │
                └──────────┬───────────┘
                           │
                       Local Wi-Fi
                           │
                           ▼
                ┌──────────────────────┐
                │   AI Server          │
                │                      │
                │ FastAPI              │
                │ WebSocket             │
                │ Audio Queue          │
                │ Preprocessing        │
                │ AST / Whisper        │
                │ Rules Engine         │
                │ Event Manager        │
                └──────────┬───────────┘
                           │
                       WebSocket
                           │
                           ▼
                ┌──────────────────────┐
                │ React Native Phone   │
                │                      │
                │ Dashboard            │
                │ Alerts               │
                │ History              │
                └──────────────────────┘


That gives you a clean separation between capture, AI, and user interface.

49. Where the AI server should run

This depends on your models.

If the models are computationally heavy:

Raspberry Pi
     ↓
audio only
     ↓
powerful local computer
     ↓
AI


is preferable.

For example:

Pi = capture device
PC = inference server
Phone = UI


This is a very practical architecture.

You don't need to force the Raspberry Pi to run the entire AI stack.

50. What I would NOT do initially

I would not start with:

ESP32
+
complex audio compression
+
WebSocket
+
AI
+
mobile notifications
+
multiple devices


all at once.

That gives you too many possible failure points.

Instead:

Stage 1:
Existing audio file → AI


then:

Stage 2:
Simulated chunks → WebSocket → AI


then:

Stage 3:
Computer microphone → WebSocket → AI


then:

Stage 4:
Raspberry Pi → WebSocket → AI


then:

Stage 5:
AI → mobile WebSocket


then:

Stage 6:
Background notifications


This gives you a controlled development path.

51. Your project in one sentence

If I had to describe your complete project technically:

An offline, low-latency, continuous audio-monitoring system in which an IoT microphone captures nursery audio, divides it into overlapping finite windows, streams those windows over a persistent WebSocket connection to a FastAPI inference server, applies AI-based audio analysis followed by a deterministic temporal rules engine, and delivers deduplicated real-time alert events to a React Native mobile dashboard.

That's the actual system you are building.

52. The most important conceptual model

Keep this mental model throughout development:

             CONTINUOUS WORLD
                    │
                    ▼
              MICROPHONE
                    │
                    ▼
            INFINITE AUDIO STREAM
                    │
             ┌──────┴──────┐
             │             │
             ▼             ▼
          WINDOW 1      WINDOW 2
          0–5 sec       3–8 sec
             │             │
             └──────┬──────┘
                    ▼
                 AI MODEL
                    │
                    ▼
             RAW PREDICTIONS
                    │
                    ▼
             TEMPORAL STATE
                    │
                    ▼
             RULES ENGINE
                    │
             ┌──────┴──────┐
             │             │
            FALSE         TRUE
             │             │
             ▼             ▼
          Continue       EVENT
                           │
                           ▼
                     MOBILE ALERT


The microphone is continuous.

The AI input is finite.

The WebSocket is continuous.

The predictions are sequential.

The rules engine provides temporal intelligence.

The alert is an event, not merely an individual model prediction.

53. And the physical-device decision

Between the three choices you mentioned:

Device	Prototype difficulty	Audio capability	AI capability	Best use
Old smartphone	Low	Excellent	High	Fast proof-of-concept
Raspberry Pi	Medium	Excellent with suitable mic	Good	Best dedicated prototype
ESP32	High	Good with suitable I2S mic	Limited	Later embedded product
My recommendation

For your project, I'd use:

Raspberry Pi + microphone → WebSocket → FastAPI AI server → React Native phone

for the first real hardware implementation.

If you want to validate the concept as quickly and cheaply as possible, use an old Android phone as the temporary microphone device first.

I would leave ESP32 until the audio protocol, chunking, WebSocket protocol, inference latency, rules engine, and alert architecture are already proven.

Final architecture

So the mature version of your project should ultimately look like:

                         NURSERY
                            │
                     ┌──────▼──────┐
                     │ Microphone  │
                     └──────┬──────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ Raspberry Pi      │
                  │                   │
                  │ Capture           │
                  │ Buffer            │
                  │ Chunk              │
                  │ Timestamp         │
                  │ WebSocket Client  │
                  └─────────┬─────────┘
                            │
                       LOCAL WI-FI
                            │
                            ▼
             ┌─────────────────────────────┐
             │       OFFLINE SERVER        │
             │                             │
             │ FastAPI                     │
             │      ↓                      │
             │ WebSocket Receiver          │
             │      ↓                      │
             │ Audio Queue                  │
             │      ↓                      │
             │ Preprocessing               │
             │      ↓                      │
             │ AI Models                   │
             │      ↓                      │
             │ Temporal State              │
             │      ↓                      │
             │ Deterministic Rules         │
             │      ↓                      │
             │ Event Manager               │
             └──────────────┬──────────────┘
                            │
                       ALERT EVENT
                            │
                            ▼
                  ┌──────────────────┐
                  │ React Native App │
                  │                  │
                  │ Dashboard        │
                  │ Alert            │
                  │ History          │
                  │ Status           │
                  └──────────────────┘


In short: your existing AI project is the brain. The new work is building the nervous system around it—continuous audio capture, chunking, WebSocket transport, buffering/queueing, temporal event handling, and real-time mobile delivery.
