# Working with S3 Buckets
Amazon S3 provides object storage for files and datasets that do not need to reside on the Nexus persistent file system. Unlike EFS storage, S3 objects are accessed using S3 tools and APIs rather than through a regular directory under `/teams/`.

Team S3 buckets must be requested through the [Roman Help Desk](https://romanhelp.stsci.edu). For information about storage options and credit consumption, see the [Roman Research Nexus Storage Resources documentation](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/storage-resources).

This guide describes how to write, read, and list objects in an S3 bucket from a Roman Research Nexus session. It also covers efficient transfers of large files. The examples use Python's [`s3fs`](https://s3fs.readthedocs.io/) and [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html), along with the AWS command-line interface (CLI).
## Setup
Replace `your-team-bucket` with the name of your team's provisioned S3 bucket. Use the same bucket name throughout the examples. Nexus sessions provide credentials through the environment, so you do not need to include AWS keys in your code.

```python
import boto3
import s3fs
from boto3.s3.transfer import TransferConfig

BUCKET = "your-team-bucket"
fs = s3fs.S3FileSystem()
s3_client = boto3.client("s3")
```

Check that you can access the bucket:

```python
fs.ls(BUCKET)
```

An empty result is expected for a new, empty bucket.
## Writing to a Bucket
### Write a Small Text File
```python
key = f"{BUCKET}/scratch/hello.txt"
with fs.open(key, "w") as f:
    f.write("Hello from the Roman Research Nexus!")

print(f"Wrote to s3://{key}")
```
### Upload a Local File
To upload an existing file from disk, use `boto3`:

```python
local_path = "example_output.csv"  # Replace with an existing local file
s3_key = "catalogs/example_output.csv"

s3_client.upload_file(local_path, BUCKET, s3_key)
print(f"Uploaded {local_path} to s3://{BUCKET}/{s3_key}")
```
### Write Binary Data from Memory
For small binary objects, you can write directly to S3 without creating a local file:

```python
import io

buffer = io.BytesIO(b"Example binary content")
key = f"{BUCKET}/scratch/example.bin"

with fs.open(key, "wb") as f:
    f.write(buffer.getvalue())
```

For large files, use the transfer methods in [Working with Large Files](#working-with-large-files) instead of buffering the entire file in memory.
## Reading from a Bucket
### Read a Text File
```python
key = f"{BUCKET}/scratch/hello.txt"
with fs.open(key, "r") as f:
    contents = f.read()

print(contents)
```
### Read Binary Data Without Saving a Local Copy
```python
key = f"{BUCKET}/scratch/example.bin"
with fs.open(key, "rb") as f:
    contents = f.read()
```

This avoids creating a second copy on the Nexus file system. For large objects, use a library that supports streaming or read the file in chunks rather than loading it entirely into memory.
### Download an Object to Disk
Use this approach when an application requires a local file:

```python
s3_key = "catalogs/example_output.csv"
local_path = "downloaded_example_output.csv"

s3_client.download_file(BUCKET, s3_key, local_path)
```
## Listing Bucket Contents
List objects at the top level:

```python
fs.ls(BUCKET)
```

List a particular prefix, which is the S3 equivalent of a folder:

```python
fs.ls(f"{BUCKET}/scratch/")
```

Recursively list all objects:

```python
fs.find(BUCKET)
```

This operation may be slow for large buckets.

Show object metadata, including sizes and modification times:

```python
details = fs.ls(f"{BUCKET}/scratch/", detail=True)
for item in details:
    print(item["name"], item.get("size"), item.get("LastModified"))
```

For very large inventories, use `boto3` pagination rather than collecting the entire listing at once:

```python
paginator = s3_client.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=BUCKET, Prefix="calibrated/"):
    for obj in page.get("Contents", []):
        print(obj["Key"], obj["Size"])
```
## Working with Large Files
For large files, such as files hundreds of megabytes or larger, prefer managed transfers that support multipart uploads. Avoid loading an entire file into an `io.BytesIO` buffer. Also consider your Nexus session's memory, CPU resources, and credit allocation when planning bulk transfers.
### AWS CLI
The AWS CLI is convenient for one-off transfers and directories:

```bash
# Upload one file
aws s3 cp large_output.fits s3://your-team-bucket/calibrated/large_output.fits

# Synchronize a directory by copying new or changed files
aws s3 sync ./local_output_dir/ s3://your-team-bucket/calibrated/
```

Check the source and destination before running `sync`, particularly when adding options that delete remote objects.
### Managed Multipart Uploads with boto3
`boto3` handles multipart uploads and retries. You can customize the threshold, chunk size, and concurrency:

```python
config = TransferConfig(
    multipart_threshold=64 * 1024 * 1024,
    multipart_chunksize=64 * 1024 * 1024,
    max_concurrency=10,
    use_threads=True,
)

local_path = "large_output.fits"  # Existing local file
s3_key = "calibrated/large_output.fits"

s3_client.upload_file(local_path, BUCKET, s3_key, Config=config)
```
### Track Upload Progress
To display progress, pass a callback to `upload_file`:

```python
import os
import sys
import threading


class ProgressPercentage:
    def __init__(self, filename):
        self.filename = filename
        self.size = float(os.path.getsize(filename))
        self.transferred = 0
        self.lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self.lock:
            self.transferred += bytes_amount
            percent = 100 * self.transferred / self.size
            sys.stdout.write(f"\r{self.filename}: {percent:.1f}%")
            sys.stdout.flush()


s3_client.upload_file(
    local_path,
    BUCKET,
    s3_key,
    Config=config,
    Callback=ProgressPercentage(local_path),
)
print()
```

For large files that you only need to inspect, prefer streaming reads where supported instead of downloading a second copy to local disk.
## Clean Up Example Objects
If you created the sample objects above, you can remove them:

```python
for key in [
    f"{BUCKET}/scratch/hello.txt",
    f"{BUCKET}/scratch/example.bin",
    f"{BUCKET}/catalogs/example_output.csv",
    f"{BUCKET}/calibrated/large_output.fits",
]:
    if fs.exists(key):
        fs.rm(key)
        print(f"Removed s3://{key}")
```

**Object versioning and backups:** S3 buckets on the Roman Research Nexus have versioning enabled automatically, and backups are retained for six months. This provides protection against accidental deletion or overwriting of objects. Previous versions and backups may continue to consume storage.
## Notes and Best Practices
- **Credentials:** Use the credentials provided through the Nexus environment. Do not embed AWS keys in scripts or notebooks.
- **Streaming:** Use `fs.open(..., "rb")` when a library supports reading directly from S3 and a local copy is unnecessary.
- **Listing:** Limit listings to relevant prefixes when possible. For large inventories, use a `boto3` paginator.
- **Prefixes:** S3 uses object keys, not true directories. A prefix such as `calibrated/` appears when objects exist under it or when a placeholder object is created.
- **Storage and credits:** Refer to the [Storage Resources documentation](https://roman-docs.stsci.edu/data-handbook/roman-research-nexus/storage-resources) for Nexus-specific storage guidance.
- **Bucket requests:** Request team S3 buckets through the [Roman Help Desk](https://romanhelp.stsci.edu).

---
*Last updated: November 2026*
