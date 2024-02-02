# filename: print_dataset_fields.py
import pandas as pd

# URL of the dataset
url = "https://raw.githubusercontent.com/uwdata/draco/master/data/cars.csv"

# Download the dataset
try:
    data = pd.read_csv(url)
    # Print the fields in the dataset
    print("Fields in the dataset:", data.columns.tolist())
except Exception as e:
    print(f"An error occurred while downloading or printing the data: {e}")