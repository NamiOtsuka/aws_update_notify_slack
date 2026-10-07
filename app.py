#!/usr/bin/env python3
import os

import aws_cdk as cdk

from aws_update_notify_slack.aws_update_notify_slack_stack import AwsUpdateNotifySlackStack


app = cdk.App()

stage = app.node.try_get_context("stage") or "dev"
conf_all = app.node.try_get_context("aws_update_notify")
cfg = conf_all[stage]

AwsUpdateNotifySlackStack(
    app, 
    "AwsUpdateNotifySlackTokyo",
    stage=stage,
    env=cdk.Environment(
            account=cdk.Aws.ACCOUNT_ID,
            region="ap-northeast-1",  # RSS & Tokyo Health
        ),
    cfg=cfg,
    enable_rss_schedule=True,
)


# グローバルHealth用（Virginia）
AwsUpdateNotifySlackStack(
    app, 
    "AwsUpdateNotifySlackVirginia",
    stage=stage,
    env=cdk.Environment(
            account=cdk.Aws.ACCOUNT_ID,
            region="us-east-1",  # Global Health
        ),
    cfg=cfg,
    enable_rss_schedule=False,
)


app.synth()
