import json
import os
import random
import boto3

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")


# Create run in ddb table and write artifact to S3
def create_job(run_id, job_id):
    run_job_id = run_id + "#" + job_id
    table = dynamodb.Table("Jobs")

    # check if job with the same ID already exists in table
    response = table.get_item(Key={"JobID": run_job_id})

    if "Item" not in response:
        # create run item
        item = {
            "JobID": run_job_id,
            "RunID": run_id,
            "JobIDOrig": job_id,
            "Complete": random.choice(
                [True, False]
            ),  # simulate completions and failures
        }

        print(item)
        print("adding item to Jobs table:")
        table.put_item(Item=item)

        print("saving output file to s3")
        key = f"{run_id}/{job_id}.json"
        file_contents = json.dumps(item).encode("UTF-8")
        s3_client.put_object(
            Body=bytes(file_contents),
            Bucket=os.environ["ARTIFACTS_BUCKET_ARN"],
            Key=key,
        )
    else:
        raise ValueError(f"Job with id {run_job_id} already exists in table.")


def lambda_handler(event, context):
    job_id = event["jobID"]
    run_id = event["runID"]
    print(f"received request for job {job_id} in run {run_id}")

    create_job(run_id, job_id)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": f"Worker processed job {job_id}",
            }
        ),
    }
