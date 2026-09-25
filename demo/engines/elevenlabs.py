"""ElevenLabs speech integrations for Rasa Pro's voice channel.

ElevenLabs is not among Rasa's built-in speech engines (ASR: azure,
deepgram; TTS: azure, cartesia, deepgram, deepgram_flux, rime), so this
module implements the two engine interfaces directly against the
ElevenLabs realtime APIs:

- STT: Scribe v2 Realtime, ``wss://api.elevenlabs.io/v1/speech-to-text/realtime``
  (https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime)
- TTS: stream-input, ``wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input``
  (https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input)

Both engines read ``ELEVENLABS_API_KEY`` from the environment and are
referenced from ``credentials.yml`` by module path, e.g.::

    inspector:
      asr:
        name: engines.elevenlabs.ElevenLabsASR
      tts:
        name: engines.elevenlabs.ElevenLabsTTS
        voice_id: 21m00Tcm4TlvDq8ikWAM
"""

from __future__ import annotations

import base64
import os
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import quote, urlencode

import aiohttp
import orjson
import structlog
from aiohttp import ClientTimeout, ClientWSTimeout, WSMsgType

from rasa.core.channels.voice_stream.asr.asr_engine import (
    ASREngine,
    ASREngineConfig,
    ASRLanguageMapEntry,
)
from rasa.core.channels.voice_stream.asr.asr_event import (
    ASREvent,
    NewTranscript,
    UserIsSpeaking,
)
from rasa.core.channels.voice_stream.audio_bytes import (
    L16_16KHZ,
    L16_24KHZ,
    L16_48KHZ,
    MULAW_8KHZ,
    AudioFormat,
    RasaAudioBytes,
)
from rasa.core.channels.voice_stream.tts._client_session import (
    create_ssl_client_session,
)
from rasa.core.channels.voice_stream.tts.tts_engine import (
    TTSEngine,
    TTSEngineConfig,
    TTSError,
    TTSLanguageMapEntry,
)
from rasa.shared.exceptions import ConnectionException
from rasa.tracing import voice as voice_tracing

structlogger = structlog.get_logger()

ELEVENLABS_API_KEY_ENV_VAR = "ELEVENLABS_API_KEY"

# Rasa's audio formats map 1:1 onto ElevenLabs encodings, on both APIs.
ASR_AUDIO_FORMATS = {
    MULAW_8KHZ: "ulaw_8000",
    L16_16KHZ: "pcm_16000",
    L16_24KHZ: "pcm_24000",
    L16_48KHZ: "pcm_48000",
}

# Scribe error message types that mean the session cannot continue.
_FATAL_STT_ERRORS = {
    "auth_error",
    "quota_exceeded",
    "unaccepted_terms",
    "invalid_request",
    "input_error",
    "session_time_limit_exceeded",
    "insufficient_audio_activity",
    "transcriber_error",
    "queue_overflow",
    "resource_exhausted",
}


def _api_key() -> str:
    return os.environ[ELEVENLABS_API_KEY_ENV_VAR]


class ElevenLabsASRConfig(ASREngineConfig):
    model_id: str = "scribe_v2_realtime"
    endpoint: str = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
    # 'vad' lets Scribe segment utterances itself (silence-based auto-commit);
    # 'manual' would require us to send commit=True on every chunk.
    commit_strategy: str = "vad"
    keyterms: Optional[List[str]] = None


class ElevenLabsASR(ASREngine[ElevenLabsASRConfig]):
    """Streaming STT via Scribe v2 Realtime.

    Partial transcripts surface as ``UserIsSpeaking`` (barge-in), committed
    transcripts as ``NewTranscript`` (the user message), mirroring how the
    built-in Deepgram engine maps its events.
    """

    required_env_vars = (ELEVENLABS_API_KEY_ENV_VAR,)
    ws: Optional[aiohttp.ClientWebSocketResponse] = None
    session: Optional[aiohttp.ClientSession] = None

    @classmethod
    def name(cls) -> str:
        return "elevenlabs"

    def get_websocket_url(self, config: ElevenLabsASRConfig) -> str:
        audio_format = ASR_AUDIO_FORMATS.get(self.audio_format)
        if audio_format is None:
            raise ConnectionException(
                f"Audio format {self.audio_format} is not supported by ElevenLabs ASR."
            )
        params: Dict[str, object] = {
            "model_id": config.model_id,
            "audio_format": audio_format,
            "commit_strategy": config.commit_strategy,
        }
        language = self.current_language_config.engine_language_key
        if language:
            params["language_code"] = language
        if config.keyterms:
            params["keyterms"] = config.keyterms
        return f"{config.endpoint}?{urlencode(params, doseq=True)}"

    @voice_tracing.traced_asr_connect
    async def connect(self) -> None:
        if self.session is None or self.session.closed:
            # total=None: the connection spans a whole call, not one request.
            self.session = create_ssl_client_session(
                ClientTimeout(total=None, sock_connect=10)
            )
        self.ws = await self.session.ws_connect(
            self.get_websocket_url(self.config),
            headers={"xi-api-key": _api_key()},
            timeout=ClientWSTimeout(ws_close=30.0),
        )

    @voice_tracing.traced_asr_disconnect
    async def close_connection(self) -> None:
        if self.ws and not self.ws.closed:
            await self.ws.close()
        self.ws = None
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    def rasa_audio_bytes_to_engine_bytes(self, chunk: RasaAudioBytes) -> bytes:
        return chunk.data

    async def send_audio_chunks(self, chunk: RasaAudioBytes) -> None:
        if not self.ws or self.ws.closed:
            raise ConnectionException("ASR websocket not connected.")
        await self.ws.send_json(
            {
                "message_type": "input_audio_chunk",
                "audio_base_64": base64.b64encode(
                    self.rasa_audio_bytes_to_engine_bytes(chunk)
                ).decode(),
                "sample_rate": self.audio_format.sample_rate,
                "commit": False,
            }
        )

    async def signal_audio_done(self) -> None:
        """Commit whatever Scribe has buffered when the user stops sending audio."""
        if self.ws and not self.ws.closed:
            await self.ws.send_json(
                {
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "sample_rate": self.audio_format.sample_rate,
                    "commit": True,
                }
            )

    async def stream_asr_events(self) -> AsyncIterator[ASREvent]:
        if not self.ws or self.ws.closed:
            raise ConnectionException("ASR websocket not connected.")
        async for msg in self.ws:
            if msg.type == WSMsgType.TEXT:
                event = self._parse_message(orjson.loads(msg.data))
                if event is not None:
                    yield event
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
                structlogger.debug("elevenlabs.asr.ws_closed")
                break
            elif msg.type == WSMsgType.ERROR:
                raise ConnectionException(f"ElevenLabs ASR websocket error: {msg.data}")

    def _parse_message(self, data: Dict) -> Optional[ASREvent]:
        message_type = data.get("message_type")
        if message_type == "partial_transcript":
            return UserIsSpeaking(text=data.get("text", ""))
        if message_type in (
            "committed_transcript",
            "committed_transcript_with_timestamps",
        ):
            return NewTranscript(text=data.get("text", ""))
        if message_type in ("session_started",):
            structlogger.debug("elevenlabs.asr.session_started")
            return None
        if message_type == "warning":
            structlogger.warning("elevenlabs.asr.warning", warning=data.get("warning"))
            return None
        if message_type in _FATAL_STT_ERRORS:
            raise ConnectionException(
                f"ElevenLabs ASR error ({message_type}): {data.get('error')}"
            )
        if message_type in ("commit_throttled", "rate_limited"):
            structlogger.warning(
                "elevenlabs.asr.throttled", error=data.get("error")
            )
            return None
        structlogger.debug("elevenlabs.asr.unknown_message", message_type=message_type)
        return None

    @staticmethod
    def get_default_config(rasa_language: str) -> ElevenLabsASRConfig:
        return ElevenLabsASRConfig(
            language_map={
                rasa_language: ASRLanguageMapEntry(language=rasa_language),
            }
        )

    @classmethod
    def from_config_dict(
        cls,
        config: Dict,
        format: AudioFormat,
        rasa_language: str,
        additional_languages: Optional[List[str]] = None,
    ) -> "ElevenLabsASR":
        return cls(
            rasa_language=rasa_language,
            format=format,
            config=ElevenLabsASRConfig.model_validate(config),
            additional_languages=additional_languages,
        )


class ElevenLabsTTSConfig(TTSEngineConfig):
    # Rachel, a stock ElevenLabs voice, so the demo works unconfigured.
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    model_id: str = "eleven_multilingual_v2"
    endpoint: str = "wss://api.elevenlabs.io"
    # ElevenLabs buffers text before generating; the default schedule
    # ([120, 160, 250, 290]) is tuned for long documents and would add
    # seconds of latency to a two-sentence bot reply. Smaller is faster,
    # floor is 50 characters.
    chunk_length_schedule: Optional[List[int]] = None


class ElevenLabsTTS(TTSEngine[ElevenLabsTTSConfig]):
    """Streaming TTS via the stream-input websocket.

    One websocket is reused across responses: each response sends text
    chunks, a flush, and reads audio until the server reports ``isFinal``.
    Interruptions have no server-side clear, so ``signal_interrupt`` drops
    the socket and the next response reconnects lazily.
    """

    required_env_vars = (ELEVENLABS_API_KEY_ENV_VAR,)
    streaming_input = True
    ws: Optional[aiohttp.ClientWebSocketResponse] = None
    session: Optional[aiohttp.ClientSession] = None

    @classmethod
    def name(cls) -> str:
        return "elevenlabs"

    def __init__(
        self,
        rasa_language: str,
        format: AudioFormat,
        config: Optional[ElevenLabsTTSConfig] = None,
        additional_languages: Optional[List[str]] = None,
    ):
        super().__init__(rasa_language, format, config, additional_languages)
        self._initialized = False

    def get_websocket_url(self, config: ElevenLabsTTSConfig) -> str:
        output_format = ASR_AUDIO_FORMATS.get(self.audio_format)
        if output_format is None:
            raise TTSError(
                f"Audio format {self.audio_format} is not supported by ElevenLabs TTS."
            )
        params: Dict[str, object] = {
            "output_format": output_format,
            "model_id": self.current_language_config.model or config.model_id,
            "inactivity_timeout": 60,
        }
        language = self.current_language_config.engine_language_key
        if language:
            params["language_code"] = language
        path = f"/v1/text-to-speech/{quote(config.voice_id)}/stream-input"
        return f"{config.endpoint}{path}?{urlencode(params)}"

    @voice_tracing.traced_tts_connect
    async def connect(self, config: Optional[ElevenLabsTTSConfig] = None) -> None:
        if self.session is None or self.session.closed:
            self.session = create_ssl_client_session(
                ClientTimeout(total=None, sock_connect=10)
            )
        self.ws = await self.session.ws_connect(
            self.get_websocket_url(config or self.config),
            headers={"xi-api-key": _api_key()},
            timeout=ClientWSTimeout(ws_close=30.0),
        )
        # First message must be a blank space; it carries per-connection settings.
        init: Dict[str, object] = {"text": " "}
        schedule = (config or self.config).chunk_length_schedule
        if schedule:
            init["generation_config"] = {"chunk_length_schedule": schedule}
        await self.ws.send_json(init)
        self._initialized = True

    @voice_tracing.traced_tts_disconnect
    async def close_connection(self) -> None:
        if self.ws and not self.ws.closed:
            await self.ws.close()
        self.ws = None
        self._initialized = False

    async def _ensure_connected(self) -> aiohttp.ClientWebSocketResponse:
        if self.ws is None or self.ws.closed:
            await self.connect()
        assert self.ws is not None
        return self.ws

    async def send_text_chunk(self, text: str) -> None:
        if not text:
            return
        ws = await self._ensure_connected()
        await ws.send_json(
            {"text": text if text.endswith(" ") else text + " "}
        )

    async def signal_text_done(self) -> None:
        """Flush buffered text; the connection stays open for the next response."""
        ws = await self._ensure_connected()
        await ws.send_json({"text": "", "flush": True})

    async def signal_interrupt(self) -> None:
        # No server-side clear: dropping the socket is the interrupt. The
        # reader in stream_audio() ends when the socket closes, and the next
        # response reconnects lazily.
        await self.close_connection()
        structlogger.debug("elevenlabs.tts.interrupted")

    async def stream_audio(self) -> AsyncIterator[RasaAudioBytes]:
        ws = await self._ensure_connected()
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = orjson.loads(msg.data)
                if data.get("isFinal"):
                    structlogger.debug("elevenlabs.tts.final")
                    break
                audio = data.get("audio")
                if audio:
                    yield RasaAudioBytes(
                        base64.b64decode(audio), format=self.audio_format
                    )
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
                structlogger.debug("elevenlabs.tts.ws_closed")
                break
            elif msg.type == WSMsgType.ERROR:
                raise TTSError(f"ElevenLabs TTS websocket error: {msg.data}")

    async def synthesize(
        self, text: str, config: Optional[ElevenLabsTTSConfig] = None
    ) -> AsyncIterator[RasaAudioBytes]:
        await self.send_text_chunk(text)
        await self.signal_text_done()
        async for audio_chunk in self.stream_audio():
            yield audio_chunk

    def engine_bytes_to_rasa_audio_bytes(self, chunk: bytes) -> RasaAudioBytes:
        return RasaAudioBytes(chunk, format=self.audio_format)

    @staticmethod
    def get_default_config(rasa_language: str) -> ElevenLabsTTSConfig:
        return ElevenLabsTTSConfig(
            language_map={
                rasa_language: TTSLanguageMapEntry(language=rasa_language),
            },
        )

    @classmethod
    def from_config_dict(
        cls,
        config: Dict,
        format: AudioFormat,
        rasa_language: str,
        additional_languages: Optional[List[str]] = None,
    ) -> "ElevenLabsTTS":
        return cls(
            rasa_language=rasa_language,
            format=format,
            config=ElevenLabsTTSConfig.model_validate(config),
            additional_languages=additional_languages,
        )

    async def set_language(self, rasa_language: str) -> bool:
        if not await super().set_language(rasa_language):
            return False
        await self._reconnect_with_lock()
        return True
