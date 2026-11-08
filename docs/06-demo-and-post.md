# Demo video, posts and submission kit (Apni Awaaz)

Replace every `[…]` with real numbers from your recording. The rules forbid misleading demos: every number must be true.

## 1. Recording setup
1. **Consent first.** Clone only your own voice, or a teammate's or relative's with their clear permission, on camera if possible. Never a stranger's or a celebrity's voice.
2. The "old voice notes": 2–3 WhatsApp voice notes of the same person, 10–30 s each, quiet room. The app checks quality (≥ 5 s speech, SNR ≥ 15 dB) and picks the best.
3. `bash run_backend.sh` (port 8767), then the frontend (`cd frontend && npm ci && npm run build` is served by the backend; or `npm run dev` → http://localhost:5193). Use Chrome; phone width looks best for the video.
4. Second person (the "nurse" or "daughter") speaks Hindi or Tamil near the laptop for the live-captions part. Earphones off for this part only if the echo guard holds; test once.
5. Record 2–3 takes. Cutting for length is fine (caption "edited for length"); changing what happened is not.

## 2. The 60-second cut
| Time | Picture | Sound / caption |
|---|---|---|
| 0–5 s | Black, white text: "After throat cancer surgery, many people never hear their own voice again." | Silence |
| 5–12 s | A WhatsApp voice note plays (the person's real old voice). Upload it; the quality check turns green; the consent box is ticked | Old voice note audio |
| 12–20 s | "Clone": the test phrase plays in the cloned voice | "नमस्ते, ये मेरी आवाज़ है।" (in their own voice) |
| 20–35 s | Converse: the nurse asks "आज दर्द कैसा है?" → live caption → 3 suggested replies → one tap → the answer in their own voice | Real audio; English subtitles |
| 35–45 s | Type a Tamil sentence → spoken in the same cloned voice | Caption: "Same voice, 10 Indian languages" |
| 45–52 s | SOS button → emergency message in two languages, in their voice | — |
| 52–60 s | End card: "Apni Awaaz: your own voice, back." · "Built on Gnani AI voice cloning, Timbre and Prisma" · #GnaniAI #GreatIndianAIInternshipChallenge | — |

## 3. LinkedIn post (native video; tag `@Gnani AI`)
```
What if you lost your voice, but not the way it sounded?

Thousands of Indians lose their voice every year to throat and oral cancer surgery, stroke or ALS. Most get a robotic electrolarynx, a notebook, or silence.

Apni Awaaz (अपनी आवाज़, "your own voice") rebuilds your voice from a few old WhatsApp voice notes. Then you type, tap a phrase or pick a suggested reply, and speak again: in your own voice, in Hindi, Tamil or any of 10 Indian languages.

🎙️ Voice cloning from ~30 s of old voice notes, with consent built in
👂 Live captions of the person you're talking to, with one-tap reply suggestions
🗣️ Same voice across languages: a Hindi speaker's voice also speaks Tamil
🆘 One-tap SOS in your language and the local language

Built on @Gnani AI's voice stack: zero-shot voice cloning (vachana-vc-v1), Timbre v3.0 and Prisma v3.0.

(The voice in the video is cloned with [name]'s permission.)

#GnaniAI #GreatIndianAIInternshipChallenge #Accessibility #AAC #VoiceAI #MadeInIndia
```

## 4. X post (≤ 280 characters; attach the video)
```
Lost your voice to surgery or stroke? Apni Awaaz rebuilds it from old WhatsApp voice notes, so you can speak again, in your own voice, in 10 Indian languages. Live captions + one-tap replies.
Built on @GnaniAi voice cloning + Timbre + Prisma.
#GnaniAI #GreatIndianAIInternshipChallenge
```

## 5. Measured so far (live, Sun 8 Nov; see `docs/test-log.md`)
- Voice enrolment 0.68 s; speaking a sentence in the cloned voice 1.2–1.65 s.
- Cloned Hindi and Tamil audio re-transcribed by Prisma word for word.
- Live captions plus 3 suggested replies within about 1 s of each sentence.
