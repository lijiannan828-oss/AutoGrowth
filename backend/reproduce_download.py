from google.cloud import storage
import time

def test_download():
    client = storage.Client()
    bucket_name = "vigloo_processed"
    blob_name = "KR051P07S01_김대표의 엽기적인 부인/ar_translated/ep000.mp4"
    
    print(f"Checking {blob_name}...")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    if not blob.exists():
        print("Blob does not exist!")
        return

    print(f"Blob exists. Size: {blob.size} bytes")
    
    start = time.time()
    print("Starting download...")
    blob.download_to_filename("/tmp/test_download.mp4")
    end = time.time()
    
    print(f"Download complete in {end - start:.2f} seconds")

if __name__ == "__main__":
    test_download()
