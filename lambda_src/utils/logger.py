import logging
import os
import sys
import boto3

sns = boto3.client("sns")
ERROR_SNS_TOPIC_ARN = os.environ.get("ERROR_SNS_TOPIC_ARN")

def get_logger(name: str) -> logging.Logger:
    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    # root logger を確実に設定（Lambdaはここが未設定だとINFOが出ないことがある）
    root = logging.getLogger()
    root.setLevel(level)

    # ハンドラが無ければ追加（重複追加防止）
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s - %(message)s"
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)

    # モジュール用logger（子logger）を返す
    logger = logging.getLogger(name)
    logger.setLevel(level)

    return logger

def notify_error(subject: str, message: str):
    if not ERROR_SNS_TOPIC_ARN:
        return

    sns.publish(
        TopicArn=ERROR_SNS_TOPIC_ARN,
        subject=subject[:100],
        Message=message,
    )