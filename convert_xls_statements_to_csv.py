import pandas as pd
import os

def convert_xls_to_csv(xls_folder):
    # Loop over all files in the folder
    for filename in os.listdir(xls_folder):
        if filename.endswith('.xls') or filename.endswith('.xlsx'):
            # Construct full file path
            xls_file = os.path.join(xls_folder, filename)
            
            # Load the XLS file, adjusting the header row if necessary
            df = pd.read_excel(xls_file, sheet_name=0, header=5)

            # Remove footer rows that contain "Printed By" or similar
            df_trimmed = df[~df['Date'].astype(str).str.contains('Printed', na=False)]

            # Convert the 'Date' column to MM/DD/YYYY format
            df_trimmed['Date'] = pd.to_datetime(df_trimmed['Date'], format='%d-%b-%Y').dt.strftime('%m/%d/%Y')
            
            # Convert the 'Value Date' column to MM/DD/YYYY format as well, if needed
            df_trimmed['Value Date'] = pd.to_datetime(df_trimmed['Value Date'], format='%d-%b-%Y').dt.strftime('%m/%d/%Y')

            # Create a new DataFrame with the structure of the CSV format
            df_csv = pd.DataFrame({
                'Date': df_trimmed['Date'],
                'Value Date': df_trimmed['Value Date'],
                'Transaction Details': df_trimmed['Transaction Description 1'].fillna('') + " " + df_trimmed['Transaction Description 2'].fillna(''),
                'Debit': df_trimmed['Debit'],
                'Credit': df_trimmed['Credit']
            })

            # Generate CSV file path with the same name as the XLS file
            csv_file = os.path.join(xls_folder, os.path.splitext(filename)[0] + '.csv')
            
            # Save the trimmed and formatted data to CSV
            df_csv.to_csv(csv_file, index=False)
            print(f"Converted {filename} to {csv_file}")

# Example usage
xls_folder_path = './'  # Path to the folder containing your XLS files
convert_xls_to_csv(xls_folder_path)