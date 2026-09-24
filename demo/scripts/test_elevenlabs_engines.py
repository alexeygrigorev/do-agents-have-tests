"""Live roundtrip: ElevenLabs TTS -> PCM -> ElevenLabs ASR -> transcript."""

import asyncio
import os
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for line in Path("/home/alexey/tmp/rasa/.env").read_text().splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from engines.elevenlabs import ElevenLabsASR, ElevenLabsTTS  # noqa: E402
from rasa.core.channels.voice_stream.asr.asr_event import (  # noqa: E402
    NewTranscript,
    UserIsSpeaking,
)
from rasa.core.channels.voice_stream.audio_bytes import (  # noqa: E402
    L16_24KHZ,
    RasaAudioBytes,
)

QUESTION = "Who is hiring for AI engineers right now?"
PCM_PATH = "/tmp/el_roundtrip.pcm"


async def tts_phase() -> bytes:
    tts = ElevenLabsTTS.from_config_dict(
        config={"chunk_length_schedule": [50, 80, 120]},
        format=L16_24KHZ,
        rasa_language="en",
    )
    await tts.connect()
    chunks = []
    first_byte = None
    import time

    start = time.monotonic()
    async for audio in tts.synthesize(QUESTION):
        if first_byte is None:
            first_byte = time.monotonic() - start
        chunks.append(audio.data)
    await tts.close_connection()
    pcm = b"".join(chunks)
    print(f"TTS: {len(chunks)} chunks, {len(pcm)} bytes, "
          f"first-byte {first_byte:.2f}s, ~{len(pcm) / 48000:.1f}s audio")
    return pcm


async def asr_phase(pcm: bytes) -> str:
    asr = ElevenLabsASR(rasa_language="en", format=L16_24KHZ)
    await asr.connect()

    committed: list[str] = []
    partials = 0

    async def read_events():
        nonlocal partials
        async for event in asr.stream_asr_events():
            if isinstance(event, UserIsSpeaking):
                partials += 1
            elif isinstance(event, NewTranscript):
                committed.append(event.text)
                print(f"  committed: {event.text!r}")

    reader = asyncio.create_task(read_events())
    chunk_size = 4800  # 100ms of 24kHz 16-bit mono
    for i in range(0, len(pcm), chunk_size):
        await asr.send_audio_chunks(RasaAudioBytes(pcm[i:i + chunk_size], format=L16_24KHZ))
        await asyncio.sleep(0.04)  # pace like a live mic
    await asr.signal_audio_done()
    try:
        await asyncio.wait_for(reader, timeout=20)
    except asyncio.TimeoutError:
        print("  (timeout waiting for events)")
    await asr.close_connection()
    print(f"ASR: {partials} partials, {len(committed)} committed transcripts")
    return " ".join(committed)


async def main() -> int:
    pcm = await tts_phase()
    Path(PCM_PATH).write_bytes(pcm)
    transcript = await asr_phase(pcm)
    print(f"TRANSCRIPT: {transcript!r}")
    key_words = {"hiring", "engineers"} & set(transcript.lower().split())
    ok = bool(key_words) and len(pcm) > 20000
    print("ROUNDTRIP:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
