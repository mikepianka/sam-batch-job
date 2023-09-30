import json
import os
import boto3

sqs = boto3.resource("sqs")
sns_client = boto3.client("sns")


def lambda_handler(event, context):
    queue = sqs.Queue(url=os.environ["SQS_URL"])

    messages = []

    while True:
        # Retrieve messages from SQS queue until it is empty
        msgs = queue.receive_messages(MaxNumberOfMessages=10)
        if not msgs:
            break
        else:
            messages.extend(msgs)

    # If no messages were returned, exit
    if not messages:
        return {"statusCode": 200, "body": "No messages to process"}

    print(f"Received {len(messages)} messages")

    # Process each message
    for message in messages:
        message_body = json.loads(message.body)
        run_id = message_body.get("runID")
        print(f"Received runID: {run_id}")

        # TODO ~ lookup and analyze info from Jobs and Runs dynamodb tables as needed

        # publish message to SNS topic
        msg = f"Summary for run: {run_id}"
        response = sns_client.publish(TopicArn=os.environ["SNS_TOPIC_ARN"], Message=msg)
        print(f"Message published with ID: {response['MessageId']} and content: {msg}")

        # Delete message from the queue after successful processing
        message.delete()

    return {"statusCode": 200, "body": json.dumps("Messages processed!")}
