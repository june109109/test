"""Offline model/factory/AnyIO/S3 contract checks; no real AWS requests."""

from dataclasses import dataclass
import uuid
import anyio
import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache
from moto import mock_aws
from polyfactory.factories.dataclass_factory import DataclassFactory
import pytest


@dataclass(frozen=True)
class Document:
    key: str
    payload: bytes


class DocumentFactory(DataclassFactory[Document]):
    __model__ = Document


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def s3():
    # Explicit fictional credentials: do not discover host credentials/metadata.
    with mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        bucket = "study-" + uuid.uuid4().hex
        client.create_bucket(Bucket=bucket)
        try:
            yield client, bucket
        finally:
            client.close()  # mock context discards all in-memory service state


def read_bytes(client, bucket, key):
    response = client.get_object(Bucket=bucket, Key=key)
    try:
        return response["Body"].read()
    finally:
        response["Body"].close()


@pytest.mark.anyio
@pytest.mark.parametrize("payload", [b"", b"hello", bytes(range(256))])
async def test_s3_round_trip(s3, payload):
    client, bucket = s3
    # Explicit boundaries; random default generation is not the oracle.
    doc = DocumentFactory.build(key="fixed-key", payload=payload)
    await anyio.to_thread.run_sync(
        lambda: client.put_object(Bucket=bucket, Key=doc.key, Body=doc.payload)
    )
    received = await anyio.to_thread.run_sync(read_bytes, client, bucket, doc.key)
    assert received == payload


def test_missing_object_contract(s3):
    client, bucket = s3
    with pytest.raises(ClientError) as exc:
        read_bytes(client, bucket, "missing")
    assert exc.value.response["Error"]["Code"] == "NoSuchKey"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


def test_factories_produce_independent_instances():
    a = DocumentFactory.build(key="one", payload=b"a")
    b = DocumentFactory.build(key="two", payload=b"b")
    assert a is not b and a.key != b.key and a.payload == b"a"


def test_ttl_with_injected_clock():
    now = [0.0]
    cache = TTLCache(maxsize=2, ttl=10, timer=lambda: now[0])
    cache["tenant-A:settings"] = "v1"
    now[0] = 9.999
    assert cache["tenant-A:settings"] == "v1"
    now[0] = 10.0
    assert "tenant-A:settings" not in cache
