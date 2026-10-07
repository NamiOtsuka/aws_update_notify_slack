# utils/rss.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import boto3
import feedparser
from botocore.exceptions import ClientError

from utils.config import Config
from utils.logger import get_logger
from utils.models import NotifyItem
from utils.slack import build_workflow_text, post_slack_text
from utils.translator import translate_to_ja  # cfg受け取る版（前に作った想定）

logger = get_logger(__name__)

# 履歴ファイルのID上限
STATE_MAX_IDS = 3000
# 差分検出の母数
MAX_ENTRIES_DEFAULT = 100
# 通知量の上限
MAX_ITEMS_DEFAULT = 20

_s3_client = None

# S3クライアント
def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client

# 現在時刻のUTC ISO 8601文字列を取得（Z表記）
def now_utc_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# ID をURLリンクの SHA1 ハッシュで生成
def sha1_id(link: str) -> str:
    return hashlib.sha1(link.encode("utf-8")).hexdigest()

# リストの末尾を優先して指定長にトリム
def trim_list_keep_tail(xs: list[str], max_len: int) -> list[str]:
    if len(xs) <= max_len:
        return xs
    return xs[-max_len:]

# RSS設定をS3から読み込み
def load_rss_conf(cfg: Config) -> list[dict]:
    s3 = _get_s3()

    if not cfg.common_s3_bucket:
        raise ValueError("common_s3_bucket is required")
    if not cfg.rss_toml_s3_key:
        raise ValueError("rss_toml_s3_key is required")

    resp = s3.get_object(Bucket=cfg.common_s3_bucket, Key=cfg.rss_toml_s3_key)
    data = resp["Body"].read()

    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore

    conf = tomllib.loads(data.decode("utf-8"))
    return conf.get("rss", [])

# stateをS3から読み込み
def load_state(cfg: Config) -> dict:
    s3 = _get_s3()
    try:
        resp = s3.get_object(Bucket=cfg.common_s3_bucket, Key=cfg.state_s3_key)
        body = resp["Body"].read().decode("utf-8")
        return json.loads(body)
    except ClientError as e:
        code = (e.response.get("Error", {}) or {}).get("Code", "")
        if code in ("NoSuchKey", "NoSuchBucket"):
            logger.info("state not found: s3://%s/%s -> init new state", cfg.common_s3_bucket, cfg.state_s3_key)
            return {"version": 1, "updated_at": "", "feeds": {}}
        raise

# stateをS3へ保存
def save_state(cfg: Config, state: dict) -> None:
    s3 = _get_s3()
    state["updated_at"] = now_utc_z()
    s3.put_object(
        Bucket=cfg.common_s3_bucket,
        Key=cfg.state_s3_key,
        Body=json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        ContentType="application/json",
    )

# feedごとのstateを取得
def get_feed_state(state: dict, feed_name: str) -> dict:
    feeds = state.setdefault("feeds", {})
    fs = feeds.setdefault(feed_name, {})
    fs.setdefault("seen", [])
    fs.setdefault("notified", [])
    return fs

# RSSを取得し、差分を検出してSlackへ通知、stateを更新する。
def run_rss_job(cfg: Config) -> None:
    """
    RSSを取得し、差分を検出してSlackへ通知、stateを更新する。
    """
    state = load_state(cfg)
    state_dirty = False

    rss_list = load_rss_conf(cfg)

    for rss_conf in rss_list:
        if not rss_conf.get("enable", False):
            continue

        feed_name = rss_conf.get("name") or rss_conf.get("title") or rss_conf["url"]
        title_label = rss_conf.get("title", "📢 RSS 更新情報")
        desc = rss_conf.get("desc", "")

        max_entries = int(rss_conf.get("max_entries", MAX_ENTRIES_DEFAULT))
        max_items = int(rss_conf.get("max_items", MAX_ITEMS_DEFAULT))
        do_translate = bool(rss_conf.get("translate", False))

        fs = get_feed_state(state, feed_name)
        seen_set = set(fs["seen"])
        notified_set = set(fs["notified"])

        feed = feedparser.parse(rss_conf["url"])
        entries = list(feed.entries or [])[:max_entries]
        logger.info(f"feed={feed_name} entries_total={len(feed.entries or [])} use={len(entries)} url={rss_conf['url']}")

        new_items: list[NotifyItem] = []

        for e in entries:
            t = getattr(e, "title", "") or ""
            link = getattr(e, "link", "") or ""
            if not t or not link:
                continue

            _id = sha1_id(link)

            if _id in seen_set:
                continue

            fs["seen"].append(_id)
            seen_set.add(_id)
            state_dirty = True

            #
            if _id not in notified_set:
                if do_translate:
                    t = translate_to_ja(cfg, t)
                new_items.append(NotifyItem(title=t, link=link))
                fs["notified"].append(_id)
                notified_set.add(_id)
                state_dirty = True

        fs["seen"] = trim_list_keep_tail(fs["seen"], STATE_MAX_IDS)
        fs["notified"] = trim_list_keep_tail(fs["notified"], STATE_MAX_IDS)

        if new_items:
            new_items = new_items[:max_items]
            date_label = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")

            text = build_workflow_text(
                title=title_label,
                date=date_label,
                desc=desc,
                items=new_items,
            )
            logger.info(f"Generated workflow text:\n{text}")
            post_slack_text(cfg, text)
        else:
            logger.info(f"feed={feed_name} new_items=0 (no updates)")

    if state_dirty:
        save_state(cfg, state)
