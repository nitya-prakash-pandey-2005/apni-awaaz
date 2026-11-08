# Test log

| When (IST) | Build | Scenario | Result | Latency | Notes |
|---|---|---|---|---|---|
| Sun 8 Nov 15:10 | feat/tm-awaaz | Live voice clone: embedding from a 5.4 s synthetic Timbre clip (Hindi), then `vachana-vc-v1` REST in Hindi and Tamil, with and without `language` | Works | Embedding 0.9 s; ~2 s sentence in ~1.8 s | `language` field accepted. Shape [1, 768] bfloat16. Clone audio re-transcribed by Prisma word for word in Hindi and Tamil (cross-language speech works). (TM) |
