# Test log

| When (IST) | Build | Scenario | Result | Latency | Notes |
|---|---|---|---|---|---|
| Sun 8 Nov 15:10 | feat/tm-awaaz | Live voice clone: embedding from a 5.4 s synthetic Timbre clip (Hindi), then `vachana-vc-v1` REST in Hindi and Tamil, with and without `language` | Works | Embedding 0.9 s; ~2 s sentence in ~1.8 s | `language` field accepted. Shape [1, 768] bfloat16. Clone audio re-transcribed by Prisma word for word in Hindi and Tamil (cross-language speech works). (TM) |
| Sun 8 Nov 15:30 | feat/tm-awaaz | Live API run, real Gnani + Groq: profile → clip check → consented enrol → speak (hi, ta, romanised hi) → SOS (hi + ta) → `/ws/listen` with a synthetic nurse | All steps work | Enrol 0.68 s; speak 1.2–1.65 s; captions + 3 suggestions within ~1 s of each sentence | Reference = 12.4 s synthetic Hindi "voice note" (Timbre Prakash): 10.1 s speech, SNR 47 dB. Enrol without consent → 400. Tamil spoken in the Hindi speaker's cloned voice. "mujhe dawai chahiye" → spoken as मुझे दवा चाहिए. Suggestions fit each nurse question. (TM) |
