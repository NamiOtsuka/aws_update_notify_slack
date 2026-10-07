import boto3
from typing import Optional
from utils.config import Config

_translate_client: Optional[object] = None


def _get_translate_client(cfg: Config):
    global _translate_client
    if _translate_client is None:
        _translate_client = boto3.client(
            "translate",
            region_name=cfg.aws_region,
        )
    return _translate_client


def translate_to_ja(cfg: Config, text: str) -> str:
    if not text:
        return ""

    t = " ".join(text.split())
    if len(t) < 2:
        return t
    if len(t) > 3500:
        t = t[:3500] + "…"

    client = _get_translate_client(cfg)
    resp = client.translate_text(
        Text=t,
        SourceLanguageCode="en",
        TargetLanguageCode="ja",
    )
    return resp["TranslatedText"]
