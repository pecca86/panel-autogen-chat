# filename: plot_weight_horsepower.py
import pandas as pd
import matplotlib.pyplot as plt

# URL of the dataset
url = "https://raw.githubusercontent.com/uwdata/draco/master/data/cars.csv"

# Download the dataset
try:
    data = pd.read_csv(url)
except Exception as e:
    print(f"An error occurred while downloading the data: {e}")
    exit()

# Plotting the relationship between weight and horsepower
plt.figure(figsize=(10, 6))
plt.scatter(data['Weight'], data['Horsepower(HP)'], alpha=0.5)
plt.title('Relationship between Weight and Horsepower')
plt.xlabel('Weight')
plt.ylabel('Horsepower (HP)')
plt.grid(True)

# Save the plot to a file
plt.savefig('weight_vs_horsepower.png')
print("The plot has been saved as 'weight_vs_horsepower.png'")