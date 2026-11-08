# Apni Awaaz: design

*Apni Awaaz (अपनी आवाज़) = "your own voice".*

## 1. One line
A phone app for Indians who have lost, or are losing, their voice (throat or oral cancer surgery, stroke, ALS/MND, Parkinson's). It rebuilds **their own voice** from 30 seconds of old WhatsApp voice notes using Gnani's zero-shot voice cloning. They then **type, tap or pick a suggested reply** and speak in that voice, in any of 10 Indian languages, with **live captions** of the person they're talking to.

## 2. Why, without sugarcoating
- India carries a very large share of the world's head-and-neck and oral cancers. Many survivors lose their larynx or tongue function. Today they mostly get an electrolarynx (a robotic buzz), a notebook, or silence. Stroke and ALS add more people who cannot speak. Census 2011 counted about 20 lakh people with a speech disability.
- **Prior art exists:** Apple Personal Voice (few languages, Apple devices only), ElevenLabs' impact programme for ALS, CereVoice Me, Acapela My Own Voice, and **Avaz** (Chennai), a strong AAC app for autism that uses generic voices.
- **Our honest difference:**
  1. **Your own voice in Indian languages and code-mixed speech**, from voice notes you already have (no studio recording; works even after you have lost your voice).
  2. **Conversation mode:** Prisma captions what the other person says, and the LLM suggests three replies in your language and style. One tap speaks. This closes the "rate gap": typing-based communication runs at about 10–15 words a minute, speech at about 150.
  3. **Speak languages you never spoke, in your own voice.** A Tamil patient in a Delhi hospital can answer the Hindi-speaking nurse in Hindi, in their own voice (Gnani's zero-shot cloning works across 12 Indic languages).
  4. **SOS** in your own voice.
  5. **Privacy first:** the voice embedding stays on your device or server, with explicit consent and one-tap delete.
- **Risk we accept:** the cloned voice quality depends on the input notes and on Gnani's beta model. If cloning fails, we fall back to a chosen Timbre voice and say so clearly in the UI.

## 3. Users
The patient (often older, slow typist, weak hands); family (sets it up, records phrases); doctor, nurse or speech therapist (the conversation partner).

## 4. Goals, non-goals, anti-goals
**P0:** voice bank (upload or record → quality check → embedding → test phrase); Speak board (type in any script plus a quick-phrase grid → speak in own voice in the chosen language); conversation mode (captions plus 3 suggested replies).
**P1:** cross-language speaking; SOS; phrase learning (frequent phrases float up).
**P2:** emotion controls; offline phrase cache.
**Non-goals:** medical diagnosis; real-time voice conversion of the user's own residual speech.
**Anti-goals:**
- Cloning anyone's voice without consent. The **consent checkbox is mandatory**, and the API rejects an enrolment without `consent=true`.
- Storing voices in third-party clouds beyond the Gnani API call itself.
- Faking the demo: the demo uses the team member's own voice, and the video says so.

## 5. How it works
```
Voice notes (.opus/.ogg/.mp3/.wav) ──browser decode (decodeToPcm16, 16 kHz)──► POST /api/voice/enroll (wav, consent)
   quality check (5–30 s speech, clipping < 1%, SNR estimate ≥ 15 dB, single speaker by Prisma transcript sanity)
   → Prisma REST (what was heard + detected language) → Gnani create_voice_embedding → saved in SQLite (profile)
   → test phrase via tts_clone_rest ("नमस्ते, ये मेरी आवाज़ है।")
Speak: text (any script) + output language → if output language ≠ input → LLM translation → tts_clone_rest (cached) → play
Converse: mic → VoiceAgentSession-like listener (Prisma stream, no agent speech) → captions → LLM: 3 replies (≤ 8 words each) in the user's language, using the profile (name, family names, condition) and the last 6 turns → tap → speak
```
Audio rate for synthesis: **16 kHz** (speakerphone quality matters here, unlike Dadi's telephony).

## 6. Screens (mobile-first, 390 px; PWA installable)
1. **Welcome + consent** → **Voice bank** wizard: add 1–5 clips → per-clip quality badges → "Build my voice" → play the test phrase → "Sounds like me" or "Try other clips".
2. **Speak:** large text box (romanised Hinglish OK), language chips (10), the quick-phrase grid (12 tiles per language: water, pain, toilet, yes, no, thank you, call my son/daughter, I'm tired…), a big **Speak** button, history.
3. **Converse:** live captions (partner bubbles), 3 suggestion chips, "type instead", a mic on/off toggle; the echo guard ignores the app's own speech.
4. **SOS:** full-screen card; speaks the emergency message in own voice in the user's language and the selected local language alternately; shows the text in large type.
5. **Profile:** name, family names (sent as Prisma `keyterms` and `speaker_names`), condition, preferred language, delete my voice.

## 7. Calls made (by the designer)
- One profile per device in the demo (multi-profile later).
- Suggestions use `LLM(purpose="dialogue")` for speed.
- If `tts_clone_rest` rejects a language, fall back to the closest supported language and show a toast.
