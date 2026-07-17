import os
import zipfile

import httpx

from smart_replenishment.config import Config


def download_and_extract(config=None):
    if config is None:
        config = Config()

    os.makedirs(config.raw_dir, exist_ok=True)

    zip_path = os.path.join(os.path.dirname(config.raw_dir), "m5-forecasting-accuracy.zip")

    # 1. Download if not already present
    if not os.path.exists(zip_path):
        print(f"Downloading M5 dataset from {config.zenodo_zip_url}...")
        with httpx.stream("GET", config.zenodo_zip_url, timeout=60.0) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Failed to download M5 dataset, status code: {response.status_code}")

            with open(zip_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        print("Download complete.")
    else:
        print("M5 zip file already exists locally.")

    # 2. Extract files
    expected_files = ["calendar.csv", "sell_prices.csv", "sales_train_validation.csv"]
    missing_files = [f for f in expected_files if not os.path.exists(os.path.join(config.raw_dir, f))]

    if missing_files:
        print(f"Extracting M5 dataset to {config.raw_dir}...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # The zip file might contain files inside a nested directory or directly.
            # Let's extract everything.
            zip_ref.extractall(config.raw_dir)
        print("Extraction complete.")
    else:
        print("M5 CSV files already exist in the target directory.")

if __name__ == "__main__":
    download_and_extract()
