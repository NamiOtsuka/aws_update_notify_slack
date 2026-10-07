from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_sns as sns,
    aws_s3 as s3,
)
from constructs import Construct
import os


class AwsUpdateNotifySlackStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        cfg: dict,
        *,
        enable_rss_schedule: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda
        fn = _lambda.Function(
            self,
            "NotifyLambda",
            function_name=f"AwsUpdateNotifySlack-{self.account}",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join(os.getcwd(), "lambda_src")
            ),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "STAGE": stage,
                "SLACK_WEBHOOK_URL": cfg["slack_webhook_url"],
                "COMMON_S3_BUCKET": cfg["common_s3_bucket"],
                "STATE_S3_KEY": cfg["state_s3_key"],
                "RSS_TOML_S3_KEY": cfg["rss_toml_s3_key"],
                "DRY_RUN": "1" if cfg.get("dry_run", False) else "0",
                "LOG_LEVEL": cfg.get("log_level", "INFO"),
            },
        )


        # AWS Translate 権限
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["translate:TranslateText"],
                resources=["*"],
            )
        )

        # S3 読み書き権限
        bucket = s3.Bucket.from_bucket_name(
            self,
            "AWSUpdateNotifyCommonBucket",
            cfg["common_s3_bucket"],
        )
        bucket.grant_read_write(fn)

        # =====================
        # RSS 定期実行（平日のみ）
        # =====================
        if enable_rss_schedule:
            rss_rule = events.Rule(
                self,
                "RssScheduleRule",
                rule_name=f"AwsRssNotifyScheduleRule-{self.account}",
                schedule=events.Schedule.cron(
                    minute="0",
                    hour="0",  # 日本時間 午前9時
                    week_day="MON-FRI",  # 土日除外
                ),
            )
            rss_rule.add_target(targets.LambdaFunction(fn))

        # =====================
        # AWS Health イベント
        # =====================
        health_rule = events.Rule(
            self,
            "HealthEventRule",
            rule_name=f"AwsHealthEventRule-{self.account}",
            event_pattern=events.EventPattern(
                source=["aws.health", "test.awshealth"],
                detail_type=["AWS Health Event"],
                detail={
                    "eventTypeCategory": [
                        "issue"
                    ]
                },
            ),
        )
        health_rule.add_target(targets.LambdaFunction(fn))

        # エラー通知用 SNS
        error_topic = sns.Topic(
            self,
            "AWSUpdateNotifySlackLambdaErrorTopic",
            topic_name=f"aws-update-notify-slack-{self.account}",
        )
        error_topic.grant_publish(fn)
        fn.add_environment(
            "ERROR_SNS_TOPIC_ARN",
            error_topic.topic_arn
        )
