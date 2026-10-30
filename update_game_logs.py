import io
import json
import os
from datetime import datetime, timezone

import boto3
import pandas as pd
import requests

SEASON = os.getenv("NBA_SEASON", "2026-27")
SOURCE_URL = f"https://huggingface.co/datasets/cbratkovics/nba-game-logs/resolve/main/game_logs/game_logs_{SEASON}.parquet"
BUCKET = "titties-nba-data"
OBJECT_KEY = f"game-logs/{SEASON}.json"


def main():
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()

    df = pd.read_parquet(io.BytesIO(response.content))
    df = df.where(pd.notnull(df), None)

    records = json.loads(df.to_json(orient="records", date_format="iso"))
    payload = {
        "season": SEASON,
        "source": "cbratkovics/nba-game-logs",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "rows": records,
    }

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    s3.put_object(
        Bucket=BUCKET,
        Key=OBJECT_KEY,
        Body=body,
        ContentType="application/json",
    )

    print(f"Uploaded {len(records)} rows to r2://{BUCKET}/{OBJECT_KEY}")


if __name__ == "__main__":
    main()
