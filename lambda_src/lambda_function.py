import os, sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(CURRENT_DIR, "vendor")
if os.path.isdir(VENDOR_DIR) and VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)

from utils.slack import post_slack_text
from utils.logger import get_logger, notify_error
from utils.config import load_config
from utils.rss import run_rss_job

logger = get_logger(__name__)

# # ローカル実行時だけ dotenv を読む
# if os.environ.get("AWS_EXECUTION_ENV") is None:
#     try:
#         from dotenv import load_dotenv
#         load_dotenv(".env.local", override=True)
#         print("dotenv loaded:", os.path.abspath(".env.local"))
#         print("COMMON_S3_BUCKET=", os.environ.get("COMMON_S3_BUCKET"))
#     except ImportError:
#         pass

# try:
#     import tomllib
# except ModuleNotFoundError:  # pragma: no cover
#     import tomli as tomllib  # type: ignore


def handle_health_event(cfg, event: dict) -> None:
    detail = event.get("detail", {}) or {}
    category = detail.get("eventTypeCategory", "")
    service  = detail.get("service", "")
    region   = detail.get("eventRegion", "") or event.get("region", "")
    status   = detail.get("statusCode", "")
    arn      = detail.get("eventArn", "")
    etype    = detail.get("eventTypeCode", "")
    desc = ""
    descs = detail.get("eventDescription", [])
    if descs:
        desc = descs[0].get("latestDescription", "")

    startTime = detail.get("startTime", "")
    endtime = detail.get("endTime", "")
    lastupdatedtime = detail.get("lastUpdatedTime", "")

    text = (
    f"━━━━━━━━━━━━━━━━━━━━\n"
    f" ⚠ CAUTION: 新しい AWS Health event があります\n"
    f"━━━━━━━━━━━━━━━━━━━━\n\n"

    f"サービス： {service}\n"
    f"リージョン：{region}\n"
    f"イベントタイプ： {etype}\n"
    f"イベントカテゴリ： {category}\n"
    f"ステータス： {status}\n"
    f"ARN： {arn}\n"
    f"説明： {desc}\n\n"

    f"StartTime： {startTime}\n"
    f"EndTime： {endtime}\n"
    f"LastUpdatedTime： {lastupdatedtime}\n"
    )
    post_slack_text(cfg, text)


def lambda_handler(event, context):
    cfg = load_config()

    try:
        event = event or {}
        src = event.get("source")
        logger.info(f"Lambda invoked source={src} stage={cfg.stage}")

        if src in ("aws.health", "test.awshealth"):
            handle_health_event(cfg, event)
        else:
            run_rss_job(cfg)

        logger.info("AWS update notify slack Lambda done")

    except Exception as e:
        logger.exception("AWS update notify slack Lambda failed")
        notify_error("AWS update notify slack Lambda failed", str(e))
        raise


if __name__ == "__main__":
    print("### MAIN: calling lambda_handler ###")
    lambda_handler({}, None)
    print("### MAIN: done ###")
