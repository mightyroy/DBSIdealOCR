import pdfplumber
import pandas as pd
import re
from datetime import datetime
import os

pdf_path = '08-AUG.pdf'  # Replace with your actual PDF file path

# Generate the CSV file name by replacing the '.pdf' extension with '.csv'
csv_filename = os.path.splitext(pdf_path)[0] + '.csv'

transactions = []

# Manually set the x-coordinate boundaries for each column
column_boundaries = {
    'Date': (30, 110),
    'Value Date': (110, 190),
    'Transaction Details': (190, 350),
    'Debit': (350, 430),
    'Credit': (430, 497),
    'Running Balance': (497, 550),
}

header_texts = ["Date", "Value Date", "Transaction Details", "Debit", "Credit", "Running Balance"]
date_pattern = r'\d{2}-[A-Za-z]{3}-\d{4}'  # Adjust if your date format is different

def parse_amount(amount_str):
    amount_str = amount_str.replace(',', '').replace('$', '').strip()
    # Check if the string is a valid number
    if re.match(r'^-?\d+(\.\d+)?$', amount_str):
        return float(amount_str)
    else:
        return ''

total_debit_transactions = 0
total_credit_transactions = 0
total_debit_amount = 0.0
total_credit_amount = 0.0

with pdfplumber.open(pdf_path) as pdf:
    num_pages = len(pdf.pages)
    for page_num, page in enumerate(pdf.pages):
        print(f"\nProcessing page {page_num + 1}...")
        words = page.extract_words(use_text_flow=True)

        # Identify the header line and the footer line
        header_found = False
        footer_y = None
        header_y = None
        additional_footer_y = None  # For 'Total Debit Count :'

        for word in words:
            if word['text'] == 'Printed' and footer_y is None:
                footer_y = word['top']
            if (page_num == num_pages - 1) and ('Total' in word['text'] and 'Debit' in word['text'] and 'Count' in word['text']):
                # Found the additional footer on the last page
                additional_footer_y = word['top']
            if word['text'] in header_texts and not header_found:
                header_y = word['top']
                header_found = True

        if not header_found:
            print(f"Header not found on page {page_num + 1}. Skipping page.")
            continue

        if footer_y is None:
            # If 'Printed' is not found, set footer_y to the bottom of the page
            footer_y = page.height

        if additional_footer_y is not None:
            # On the last page, set footer_y to the minimum of existing footer_y and additional_footer_y
            footer_y = min(footer_y, additional_footer_y)
            print(f"Additional footer detected at Y-coordinate: {additional_footer_y}")

        print(f"Page {page_num + 1}: Header Y-coordinate: {header_y}")
        print(f"Page {page_num + 1}: Footer Y-coordinate: {footer_y}")

        # Filter words between the header and footer lines
        content_words = [w for w in words if header_y < w['top'] < footer_y]
        print(f"Page {page_num + 1}: Number of content words: {len(content_words)}")

        # Group words into lines based on their y-coordinate
        lines = {}
        for word in content_words:
            line_key = round(word['top'], 1)
            if line_key in lines:
                lines[line_key].append(word)
            else:
                lines[line_key] = [word]

        # Sort lines by their y-coordinate
        sorted_line_keys = sorted(lines.keys())

        # Group lines into transactions
        transactions_data = []
        current_transaction = []
        for line_key in sorted_line_keys:
            line_words = lines[line_key]
            # Check if the line starts with a date
            line_text = ' '.join([w['text'] for w in line_words])
            date_match = re.match(date_pattern, line_text.strip())

            if date_match:
                # Start of a new transaction
                if current_transaction:
                    transactions_data.append(current_transaction)
                current_transaction = [line_words]
            else:
                # Continuation of the current transaction
                if current_transaction:
                    current_transaction.append(line_words)
                else:
                    # Lines before the first transaction are ignored
                    continue

        # Append the last transaction
        if current_transaction:
            transactions_data.append(current_transaction)

        print(f"Page {page_num + 1}: Number of transactions detected: {len(transactions_data)}")

        # Extract data from transactions
        for trans in transactions_data:
            # Initialize fields
            date = ''
            value_date = ''
            transaction_details = ''
            debit = ''
            credit = ''

            # Process the first line separately
            first_line = trans[0]
            columns_data = {name: '' for name in column_boundaries.keys()}
            for word in first_line:
                # Assign word to the appropriate column based on x0
                assigned_column = None
                for name, (col_start, col_end) in column_boundaries.items():
                    if col_start <= word['x0'] < col_end:
                        assigned_column = name
                        break
                if assigned_column:
                    columns_data[assigned_column] += word['text'] + ' '

            # Extract Date and Value Date
            date_text = columns_data.get('Date', '').strip()
            value_date_text = columns_data.get('Value Date', '').strip()

            print(f"Extracted Date text: '{date_text}'")
            print(f"Extracted Value Date text: '{value_date_text}'")

            # Parse and reformat dates
            for date_field, date_str in [('Date', date_text), ('Value Date', value_date_text)]:
                try:
                    parsed_date = datetime.strptime(date_str, '%d-%b-%Y')  # Adjust format if needed
                    formatted_date = parsed_date.strftime('%m/%d/%Y')
                    if date_field == 'Date':
                        date = formatted_date
                    else:
                        value_date = formatted_date
                except ValueError as e:
                    print(f"Failed to parse {date_field} '{date_str}': {e}")
                    pass  # Handle invalid dates if necessary

            # Extract Debit and Credit amounts
            debit_text = columns_data.get('Debit', '').strip()
            credit_text = columns_data.get('Credit', '').strip()

            # Clean and convert amounts
            debit = parse_amount(debit_text)
            credit = parse_amount(credit_text)

            # Ensure debit and credit are strings for empty values
            debit_str = str(debit) if debit != '' else ''
            credit_str = str(credit) if credit != '' else ''

            # Update totals
            if debit != '':
                total_debit_transactions += 1
                total_debit_amount += debit
            if credit != '':
                total_credit_transactions += 1
                total_credit_amount += credit

            # Extract 'Transaction Details' from the first line
            first_line_transaction_details = columns_data.get('Transaction Details', '').strip()
            transaction_details_lines = []
            if first_line_transaction_details:
                transaction_details_lines.append(first_line_transaction_details)

            # Extract 'Transaction Details' from the rest of the lines except the last line
            lines_to_include = trans[1:-1] if len(trans) > 2 else trans[1:]  # Exclude last line if more than two lines

            for line in lines_to_include:
                # Get words in the 'Transaction Details' column
                line_transaction_details = ''
                for word in line:
                    assigned_column = None
                    for name, (col_start, col_end) in column_boundaries.items():
                        if col_start <= word['x0'] < col_end:
                            assigned_column = name
                            break
                    if assigned_column == 'Transaction Details':
                        line_transaction_details += word['text'] + ' '
                if line_transaction_details.strip():  # Only add if there's content
                    transaction_details_lines.append(line_transaction_details.strip())

            # Combine all transaction details lines
            transaction_details = ' '.join(transaction_details_lines)

            # Append to transactions list if Date is present
            if date:
                transaction_record = {
                    'Date': date if date != '' else '',
                    'Value Date': value_date if value_date != '' else '',
                    'Transaction Details': transaction_details if transaction_details != '' else '',
                    'Debit': debit_str,
                    'Credit': credit_str
                }
                transactions.append(transaction_record)
                print(f"Appended transaction: {transaction_record}")
            else:
                print("Transaction skipped due to missing date.")

# Check if transactions list is not empty
if transactions:
    # Export to CSV
    df = pd.DataFrame(transactions)
    # Ensure empty fields are represented as empty strings
    df.fillna('', inplace=True)
    df.to_csv(csv_filename, index=False)
    print(f"\nTransactions have been successfully extracted and saved to '{csv_filename}'.")
else:
    print("\nNo transactions were extracted. Please check the debug output for issues.")

# Print summary
print("\nSummary:")
print(f"Total number of debit transactions: {total_debit_transactions}")
print(f"Total number of credit transactions: {total_credit_transactions}")
print(f"Total debit amount: {total_debit_amount}")
print(f"Total credit amount: {total_credit_amount}")