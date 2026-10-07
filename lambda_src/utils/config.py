import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Config:
    stage: str
    aws_region: str
    common_s3_bucket: str
    state_s3_key: str
    rss_toml_s3_key: str
    slack_webhook_url: str
    dry_run: bool

def load_env_for_local() -> None:
    # Lambda 環境では .env を読まない
    if os.environ.get("AWS_EXECUTION_ENV"):
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    dotenv_path = Path(__file__).resolve().parent.parent / ".env.local"
    print("Loading dotenv from", dotenv_path)
    # 例: utils/config.py → lambda_src/.env.local
    load_dotenv(dotenv_path, override=True)

def load_config() -> Config:
    # ローカル実行時だけ dotenv を読む
    load_env_for_local()

    stage = os.environ.get("STAGE", "dev")
    aws_region = os.environ.get("AWS_REGION", "ap-northeast-1")

    common_s3_bucket = os.environ.get("COMMON_S3_BUCKET")
    if not common_s3_bucket:
        raise ValueError("COMMON_S3_BUCKET is required")

    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL is required")

    rss_toml_s3_key = os.environ.get("RSS_TOML_S3_KEY", "def/aws_rss_def.toml")
    state_s3_key = os.environ.get("STATE_S3_KEY", "state/state.json")

    dry_run = os.environ.get("DRY_RUN", "0") == "1"

    return Config(
        stage=stage,
        aws_region=aws_region,
        common_s3_bucket=common_s3_bucket,
        state_s3_key=state_s3_key,
        rss_toml_s3_key=rss_toml_s3_key,
        slack_webhook_url=slack_webhook_url,
        dry_run=dry_run,
    )