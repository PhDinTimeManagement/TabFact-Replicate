import os
import csv
import json

import json
import os

# # Function to combine two JSON files
# def combine_json_files(file1, file2, output_file):
#     combined_data = {}
#
#     # Load the first JSON file
#     with open(file1, 'r', encoding='utf-8') as f1:
#         data1 = json.load(f1)
#
#     # Load the second JSON file
#     with open(file2, 'r', encoding='utf-8') as f2:
#         data2 = json.load(f2)
#
#     # Merge the data from both files
#     # If keys are unique, they will simply be added
#     # If keys overlap, the second file's data will overwrite the first file's data
#     combined_data.update(data1)
#     combined_data.update(data2)
#
#     # Save the combined data to a new file
#     with open(output_file, 'w', encoding='utf-8') as fout:
#         json.dump(combined_data, fout, indent=2, ensure_ascii=False)
#
#     print(f"Combined JSON file saved to: {output_file}")


def calculate_data_size(csv_directory):
    total_instances = 0  # Represents m * d
    for file_name in os.listdir(csv_directory):
        if file_name.endswith(".csv"):
            file_path = os.path.join(csv_directory, file_name)
            with open(file_path, 'r', encoding='utf-8') as csv_file:
                header = csv_file.readline().strip()
                num_columns = len(header.split('#'))  # Count the number of columns based on '#'

                num_rows = sum(1 for _ in csv_file)  # Count rows excluding the header

                table_size = num_columns * num_rows # Calculate m * d
                total_instances += table_size

                print(f"{file_name}: {num_rows} rows, {num_columns} columns -> {table_size} instances")
    return total_instances

# Paths to access the data
csv_directory = "../data/all_csv"

# Calculate the data size (m * d)
print("Calculating data size (m * d) from CSV files...")
total_csv_data_size = calculate_data_size(csv_directory)

# Results
print()
print(f"Total data size (m * d) from CSV files: {total_csv_data_size}")
