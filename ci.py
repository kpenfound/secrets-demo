import sys
import os
import anyio
import dagger
import hvac


async def pipeline():
    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        lambda_file = client.host().directory(".", exclude=["ci.py", "env/"])

        test = (
            client.container()
            .from_("python:3-slim-bullseye")
            .with_directory("/src", lambda_file)
            .with_workdir("/src")
            .with_exec(["python", "-c", "'import lambda_function; print (lambda_function.lambda_handler(\"\",\"\"))'"])
        )

        build = (
            client.container()
            .from_("alpine:3")
            .with_exec(["apk", "add", "zip"])
            .with_directory("/src", test.directory("/src"))
            .with_workdir("/src")
            .with_exec(["zip", "function.zip", "lambda_function.py"])
        )

        deploy = (
            get_aws_container(client)
            .with_file("/aws/function.zip", build.file("/src/function.zip"))
            .with_exec(["lambda", "update-function-code", "--function-name", "timeFunc", "--zip-file", "fileb://function.zip", "--region", "us-east-1"])
        )

        await deploy.exit_code()

def get_aws_container(dagger_client):
    host = os.getenv("VAULT_HOST")
    token = os.getenv("VAULT_TOKEN")
    vault = hvac.Client(
        url=host,
        token=token,
    )

    aws_key_id = get_vault_value(vault, 'aws-creds', 'key')
    secret_key = dagger_client.set_secret('aws_key', aws_key_id)

    aws_secret = get_vault_value(vault, 'aws-creds', 'secret')
    secret_secret = dagger_client.set_secret('aws_secret', aws_secret)

    return (
        dagger_client.container()
        .from_("amazon/aws-cli:2.11.3")
        .with_secret_variable("AWS_ACCESS_KEY_ID", secret_key)
        .with_secret_variable("AWS_SECRET_ACCESS_KEY", secret_secret)
    )

def get_vault_value(client, secret, key):
    read_response = client.secrets.kv.read_secret(path=secret)
    return read_response['data']['data'][key]

if __name__ == "__main__":
    anyio.run(pipeline)
