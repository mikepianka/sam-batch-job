import time
import json
import os
import boto3

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


# Fetch jobs from config file in bucket
def fetch_jobs():
    CONFIG_FILE = "jobs.json"

    json_data = s3_client.get_object(
        Bucket=os.environ["CONFIG_BUCKET_ARN"], Key=CONFIG_FILE
    )
    json_content = json_data["Body"].read()
    json_dict = json.loads(json_content.decode("utf-8"))
    return json_dict["jobs"]


# Create run in ddb table
def create_run(run_id, jobs):
    table = dynamodb.Table("Runs")

    # check if run with the same ID already exists in table
    response = table.get_item(Key={"RunID": run_id})

    if "Item" not in response:
        # create run item
        item = {
            "RunID": run_id,
            "TotalJobs": len(jobs),
            "CompletedJobs": 0,
            "JobIDs": [job["id"] for job in jobs],
            "JobsConfig": jobs,
        }

        print("adding item to Runs table:")
        print(item)
        table.put_item(Item=item)
    else:
        raise ValueError(f"Run with id {run_id} already exists in table.")


# Send run completion message to SQS
def send_completion_message(run_id):
    message_body = {"runID": run_id}

    # Send message
    response = sqs_client.send_message(
        QueueUrl=os.environ["SQS_URL"], MessageBody=json.dumps(message_body)
    )

    print(f"Message with ID {response['MessageId']} sent for run {run_id}")


def lambda_handler(event, context):
    jobs = fetch_jobs()
    run_id = str(int(time.time()))

    create_run(run_id, jobs)

    responses = []

    for job in jobs:
        print(f"dispatching job {job['id']}")
        print(job)
        payload = json.dumps({"jobID": job["id"], "runID": run_id})
        response = lambda_client.invoke(
            FunctionName=os.environ["WORKER_LAMBDA_ARN"],
            InvocationType="Event",
            Payload=payload,
        )

        if response["StatusCode"] == 202:
            responses.append(job)
        else:
            print(f"ERROR: failed to dispatch job {job}")

    send_completion_message(run_id)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "runID": run_id,
                "job_count": len(jobs),
                "jobs": responses,
            }
        ),
    }
