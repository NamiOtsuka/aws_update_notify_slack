import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_update_notify_slack.aws_update_notify_slack_stack import AwsUpdateNotifySlackStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_update_notify_slack/aws_update_notify_slack_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsUpdateNotifySlackStack(app, "aws-update-notify-slack")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
