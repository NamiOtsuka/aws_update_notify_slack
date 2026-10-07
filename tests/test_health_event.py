# tests/test_health_event.py
import lambda_src.lambda_function as lf

def test_handle_health_event_posts_expected_text(monkeypatch):
    sent = {}

    def fake_post(text: str):
        sent["text"] = text

    monkeypatch.setattr(lf, "post_slack_text", fake_post)

    event = {
        "detail": {
            "eventTypeCategory": "issue",
            "service": "EC2",
            "eventRegion": "ap-northeast-1",
            "statusCode": "open",
            "eventArn": "arn:aws:health:...",
            "eventTypeCode": "AWS_EC2_ISSUE",
        },
        "region": "us-east-1"
    }

    lf.handle_health_event(event)

    assert sent["text"] == (
        "[AWS Health] category=issue service=EC2 region=ap-northeast-1 "
        "status=open type=AWS_EC2_ISSUE arn=arn:aws:health:..."
    )