import requests
from utils.models import NotifyItem
from utils.logger import get_logger

logger = get_logger(__name__)

# Slack Block Kit形式の通知メッセージを構築する
def build_notify_message_blockkit(
    *,
    title: str,
    date: str,
    desc: str,
    items: list[NotifyItem],
    max_items: int = 20,
) -> dict:

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{title} ({date})",
                "emoji": True
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text":
				{
					"type": "mrkdwn",
					"text": f"*説明:*\n{desc}"
				}
        },
        {"type": "divider"},
    ]

    for item in items[:max_items]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"• <{item.link}|{item.title}>"
            }
        })
        blocks.append({"type": "divider"})

    return {
        "blocks": blocks
    }

def build_workflow_text(title: str, date: str, desc: str, items) -> str:
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📢 {title}（{date}）")
    lines.append("━━━━━━━━━━━━━━━━━━━━\n")
    # if date:
    #     lines.append(f"{date}")
    # if desc:
    #     lines.append(f"{desc}")

    # 空行
    if len(lines) > 0:
        lines.append("")

    for it in items:
        # it.title / it.link を想定
        lines.append(f"🔸 {it.title}\n  {it.link}\n")

    lines.append(f"（全 {len(items)} 件）")
    return "\n".join(lines)


def post_slack_text(cfg, text: str) -> None:
    if cfg.dry_run:
        logger.info(f"[DRY_RUN] would post slack:\n{text}")
        return
    requests.post(cfg.slack_webhook_url, json={"text": text}, timeout=10)