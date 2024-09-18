import pandas as pd

# Step 1: Read the CSV file
csv_file_path = 'Email_Sent_List1.csv'  # Update this path with the actual path to your CSV file
df = pd.read_csv(csv_file_path, encoding="latin1")

# Step 2: Show the number of rows before removing duplicates
initial_row_count = len(df)

# Remove duplicates based on the email column, keeping only the first occurrence
df_cleaned = df.drop_duplicates(subset=['email'], keep='first', inplace=False)

# Save the cleaned DataFrame to a new CSV file
cleaned_csv_file_path = 'Email_Sent_List_Cleaned.csv'
df_cleaned.to_csv(cleaned_csv_file_path, index=False)

# Show the number of rows after removing duplicates
final_row_count = len(df_cleaned)
duplicates_removed = initial_row_count - final_row_count
print(f"Initial row count: {initial_row_count}")
print(f"Final row count: {final_row_count}")
print(f"Duplicates removed: {duplicates_removed}")

print(f"Cleaned data saved to: {cleaned_csv_file_path}")
