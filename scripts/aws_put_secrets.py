"""Copy the out-of-band secrets from the local .env into AWS Secrets Manager.

Values are read from .env and sent with boto3: never printed, never placed on a command line, never logged.
Usage:  uv run python -m scripts.aws_put_secrets   (needs AWS credentials for the target account)
"""

import re
from pathlib import Path

import boto3

REGION = "us-west-2"
MAP = {"OPENAI_API_KEY": "munshi/openai-api-key", "GMAIL_APP_PASSWORD": "munshi/gmail-app-password",
       "GOOGLE_CLIENT_SECRET": "munshi/google-client-secret", "GOOGLE_REFRESH_TOKEN": "munshi/google-refresh-token",
       "SERPAPI_API_KEY": "munshi/serpapi-api-key", "LANGSMITH_API_KEY": "munshi/langsmith-api-key"}


def main() -> None:
    env = {}
    for line in Path(".env").read_text().splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line)
        if m:
            env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    sm = boto3.client("secretsmanager", region_name=REGION)
    for key, secret_id in MAP.items():
        value = env.get(key, "")
        if not value:
            print(f"{secret_id}: skipped ({key} is empty in .env)")
            continue
        sm.put_secret_value(SecretId=secret_id, SecretString=value)
        print(f"{secret_id}: updated ({len(value)} characters)")


if __name__ == "__main__":
    main()
