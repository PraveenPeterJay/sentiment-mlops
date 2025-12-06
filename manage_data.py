import pandas as pd
import sys

def prepare_data(version):
    print(f"Preparing Data Version {version}...")

    # Load the huge original dataset
    df = pd.read_csv('data/full_dataset.csv')

    if version == 1:
        # VERSION 1: TAKE ONLY 10000 ROWS (Small data for initial deploy)
        small_df = df.iloc[:10000]
        small_df.to_csv('data/train.csv', index=False)
        print("Created 'data/train.csv' with 1,0000 rows.")

    elif version == 2:
        # VERSION 2: TAKE ALL DATA (Simulating 'New Data Arrived')
        df.to_csv('data/train.csv', index=False)
        print("Created 'data/train.csv' with ALL rows.")

if __name__ == "__main__":
    # Run this script like: python manage_data.py 1
    if len(sys.argv) > 1:
        prepare_data(int(sys.argv[1]))
    else:
        print("Please provide a version number (1 or 2)")