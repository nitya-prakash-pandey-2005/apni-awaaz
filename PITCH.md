# Apni Awaaz · अपनी आवाज़: your own voice, back

**Live demo:** *[live demo link]* · **Video:** *[video link]* · **Code:** [github.com/nitya-prakash-pandey-2005/apni-awaaz](https://github.com/nitya-prakash-pandey-2005/apni-awaaz) · Built on Gnani AI

## The problem
Nearly half of the world's oral cancer is in India. GLOBOCAN 2024 estimates 2,05,878 new lip and oral cavity cancer cases in India, about 45.5% of the world's 4,52,205 (our calculation), and it is the most common cancer in Indian men ([IARC India sheet](https://gco.iarc.who.int/media/globocan/factsheets/populations/356-india-fact-sheet.pdf), [IARC world sheet](https://gco.iarc.who.int/media/globocan/factsheets/cancers/1-lip-oral-cavity-fact-sheet.pdf)). There are 35,169 new cases a year of cancer of the voice box, and about 12.9 lakh new strokes in a year ([ThePrint, Lancet study](https://theprint.in/health/india-recorded-13-lakh-stroke-cases-in-2019-highest-in-southeast-asia-finds-lancet-study/1798324)). Many of these people lose their speech. What they get is an electrolarynx buzz, a notebook, or an app that speaks in a stranger's voice. Shrenik Shah wrote on paper for three months after his voice box was removed ([Cancerworld](https://cancerworld.net/shrenik-shah-the-voice-that-transcends-sound/)).

## The product
Apni Awaaz rebuilds a person's **own** voice from the WhatsApp voice notes they already have, then speaks for them in that voice:

- **My voice:** consent first, then a quality check on each note (speech length, clipping, noise, and a Prisma v3.0 transcript), then Gnani zero-shot voice cloning.
- **Speak:** type in any of 10 Indian languages, or romanised ("mujhe paani chahiye"), or tap a quick phrase. It is spoken through `vachana-vc-v1`, and a badge always says whose voice you heard.
- **Converse:** live captions of the other person (Prisma v3.0 streaming) and three suggested replies; one tap speaks a reply in your voice.
- **Banked messages, switch scanning** for stroke and ALS users, and **SOS** that still speaks, in the phone's voice, when the server is down.

## Proof (live Gnani runs, synthetic voices)

- The voice was built in 0.67 s. Sentences were spoken in the cloned voice in 1.5–2.2 s. Tamil was spoken in the cloned voice of a Hindi speaker.
- All 7 cloned clips were transcribed back by Prisma word for word, in Hindi and Tamil.
- Two simultaneous Speak presses were both spoken in the cloned voice, with no rate-limit error.
- Delete my voice removed the embedding, the consent record and every cloned clip.
- 92 automated tests pass. Details: [docs/test-log.md](docs/test-log.md).

## How it is different
Cloning a voice from old WhatsApp notes is **not new**: ElevenLabs' free Impact Program already does it, in [14 Indian languages](https://cxotoday.com/media-coverage/elevenlabs-charts-next-phase-of-india-growth-at-first-summit-in-bengaluru/), for people who apply ([MIT Technology Review](https://www.technologyreview.com/2025/02/13/1111882/motor-neuron-diseases-took-their-voices-ai-bringing-them-back/)). Apple Personal Voice needs a fresh recording made while you can still speak, and supports no Indian language ([Apple](https://www.apple.com/ios/feature-availability/)). Avaz and Jellow are Indian AAC apps, but they do not clone your voice. To our knowledge, no free, India-first phone app combines all three: your own voice from notes you already have, 10 Indian languages with code-mix, and a conversation mode with captions and suggested replies.

## Honesty note
Every voice in our demos is synthetic (Gnani Timbre). We never cloned a real person. The live demo replays a real recorded session and has no backend. Consent is enforced by the API, and deletion is real.

## Team
Team: Nitya Prakash Pandey · Dilavesh Kanz Nidooli.

One Gnani voice engine, three products: [Dadi vs Scammers](https://github.com/nitya-prakash-pandey-2005/dadi-vs-scammers), [Pukaar](https://github.com/nitya-prakash-pandey-2005/pukaar) and Apni Awaaz. Combined pitch: [Dadi's PITCH.md](https://github.com/nitya-prakash-pandey-2005/dadi-vs-scammers/blob/main/PITCH.md). #GnaniAI #GreatIndianAIInternshipChallenge
