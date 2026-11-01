# Local Whisper transcription and timestamp estimates

Read for requested local Whisper speech recognition, transcription, subtitle drafts or timestamp analysis. This workflow invokes `whisper-cli` from whisper.cpp separately from LocalAIHub's Qwen3-ASR `ai transcribe`. It does not establish support in the native Local AI Studio app. Keep audio local and preserve source media and existing subtitles. Follow user-selected tools and models.

## Discover runtime and model

- Resolve the user's executable, otherwise `command -v whisper-cli`; `/opt/homebrew/bin/whisper-cli` is only a reference Mac candidate. Read that executable's `--version` and `--help`. The observed runtime on 2026-10-30 was whisper.cpp 1.9.5. Confirm current flags instead of assuming compatibility.
- Resolve an explicit model path first, then a task-known model receipt or the selected model storage directory. Reuse an existing verified model read-only; do not move/delete weights or redownload by default. Do not scan unrelated project trees. A missing configured volume is a blocker, not a reason to change storage roots.
- For the multilingual, unquantized `ggml-large-v3-turbo.bin`, the verified reference artifact has **1,624,555,275 bytes**, SHA-256 `1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69`, and SHA-1 `4af2b29d7ec73d781377bfd1758ca957a807e941`. Verify the selected file's identity before adopting this receipt. Other models or quantizations need their own provenance and checksums.
- When a requested Whisper task needs a missing runtime/model, inspect the [official runtime instructions](https://github.com/ggml-org/whisper.cpp#quick-start) and [model catalog](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md). Install only those prerequisites in the selected locations; the LocalAIHub `audio` group is not required. Check available space and active jobs before starting. Do not change a global installation as part of a skill documentation update.
- The reference weights are available at this [revision-pinned download](https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-large-v3-turbo.bin). For an authorized missing-model download, write a new staging file, retain transport errors, and verify size/checksum before use. Do not disable TLS verification after a network failure. Download duration is environment-dependent.

Keep model weights, transcripts, audio, private task paths and logs outside the skill repository. Existing project model locations belong in task context, not product defaults.

## Prepare input and run

Use a fresh output directory and absolute paths. Prepare a mono 16 kHz PCM WAV from the selected audio or video without overwriting the original. Inspect the selected audio stream and record the conversion arguments. For a bounded crop, record its start in the original media timeline and its measured duration. Keep that offset separate from Whisper's internal `-ot` option; do not apply an offset twice. If the crop process does not establish its origin reliably, report that uncertainty.

The following Python example assumes `whisper`, `model`, `wav` and `prefix` are already resolved absolute paths. `prefix` is a fresh output stem **without an extension**. It shows the invocation contract, not a batch to run during setup:

```python
from pathlib import Path
import json
import subprocess

argv = [str(whisper), "-m", str(model), "-f", str(wav),
        "-l", "auto", "-t", "4", "-ojf", "-otxt", "-osrt",
        "-of", str(prefix)]
# Keep the exact argument vector, including paths with spaces, without a shell.
Path(str(prefix) + ".argv.json").write_text(
    json.dumps(argv, ensure_ascii=False, indent=2), encoding="utf-8")
with Path(str(prefix) + ".stdout.log").open("wb") as stdout, \
     Path(str(prefix) + ".stderr.log").open("wb") as stderr:
    result = subprocess.run(argv, stdout=stdout, stderr=stderr, check=False)
# Record result.returncode even on failure; inspect artifacts before delivery.
```

Use `auto` for language detection, or the supported language code chosen for the task (`ko`/`en` in the observed run). Do not assume mixed-language singing is recognized correctly. Four threads is a reference setting, not a requirement. Optional independent overlapping crops used `-mc 0 -nf` to remove carried text context and temperature fallback. These settings do not make outputs independent ground truth.

For an unbiased recognition pass, do not inject existing lyrics through `--prompt` or grammar. If the task calls for prompted recognition, record the supplied text and label the result accordingly. Prompted ASR is not verified forced alignment. `--translate` translates speech into English; it is not the English→Korean text translation workflow.

Record runtime version/path, exact arguments, model/input/crop hashes, crop origin and duration, exit code, full stdout/stderr, output paths/hashes and uncertainty. Distinguish original media from prepared WAV provenance. A zero exit code still requires new, nonempty, decodable output files: `.json`, `.txt`, `.srt` for this example. Parse UTF-8 JSON/subtitles and inspect cue ordering, bounds and text. Preserve valid empty/silence results as observations rather than inventing speech or claiming a completed transcript.

## Interpret timestamps

For the inspected [1.9.5 JSON writer](https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/examples/cli/cli.cpp), retain these distinct types:

| Value | Meaning and conversion to original seconds |
| --- | --- |
| `transcription[].offsets.from/to` | Coarse segment interval in milliseconds: `crop_origin_seconds + value / 1000` |
| `tokens[].offsets.from/to`, when present | Ordinary token interval in milliseconds; same conversion, separate from the segment interval |
| `tokens[].t_dtw`, when valid | Experimental DTW token point in 10 ms units: `crop_origin_seconds + value / 100` |

These conversions assume a prepared WAV starting at local zero and no additional Whisper time offset. Negative `t_dtw` is invalid, not a negative onset to clamp to zero. Missing token intervals are unknown. Ignore special/control tokens when matching words; preserve raw tokens and their text order because tokens can contain partial words or merged UTF-8 fragments. SRT cues describe estimated segment intervals, not verified word or sung boundaries. Cropped SRT times are local; convert only when the requested deliverable uses the original timeline, and retain the raw version.

DTW is optional and experimental. In the inspected runtime, the matching preset was `-dtw large.v3.turbo -nfa`; the preset is **not** a model filename. Flash attention otherwise disabled that DTW path. Recheck the current runtime and selected model before enabling it. Ordinary transcription is the default when DTW was not requested or needed.

Reject DTW points as alignment evidence when they are negative, nonmonotonic, collapsed/repeated across lexical tokens, outside the corresponding coarse segment/crop, or attached to incorrect/missing words. Check repeated-phrase mapping and uncertain backing vocals. Retain rejected raw values with reasons; do not silently repair them. A token point locates a token estimate; the last point is not a sung end. Stable points across same-model crops can disagree with ordinary token intervals and do not justify an automatic subtitle correction.

## Failures and quality limits

In an observed 1.9.5 run, a 130–160 s crop with DTW aborted with `SIGABRT` (Python subprocess return code `-6`) and `WHISPER_ASSERT src/whisper.cpp:9136: filter_width < a->ne[2]`. This is one retained failure, not proof that every crop of that duration fails. Preserve the command and complete logs, stop unchanged retries, and do not patch/reinstall the runtime automatically. If ordinary transcription still serves the request, run a separately named pass without DTW and label the missing DTW evidence. Otherwise report the blocker. Do not use partial output from the aborted pass as a completed result.

Successful full-song passes have hallucinated generic closing text and repeated chorus text. Korean/English sung words can be wrong even at high reported token probabilities. Compare lexical content and timing against available listening evidence; overlapping same-model crops are consistency checks only. Do not claim listening occurred from waveform inspection, a probability, or a successful process.

Report process completion, transcript structure, estimated timestamps, observed listening/content review and applied corrections separately. When the words or onset/end remain uncertain, deliver a draft or analysis with that uncertainty and preserve existing timing. Creating a transcript does not authorize replacing a lyric timeline or rendering a successor video.
