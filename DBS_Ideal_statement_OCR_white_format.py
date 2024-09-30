import pdfplumber
import pandas as pd
import re
from datetime import datetime
import os

# Short description of the program
# This Python script extracts transaction data from a bank statement PDF and saves it as a CSV file with the same name, accurately parsing and formatting the data while handling specific layout nuances.

pdf_path = '06-JUN.pdf'  # Replace with your actual PDF file path

# Generate the CSV file name by replacing the '.pdf' extension with '.csv'
csv_filename = os.path.splitext(pdf_path)[0] + '.csv'

transactions = []

# Initialize totals for summary
total_debit_transactions = 0
total_credit_transactions = 0
total_debit_amount = 0.0
total_credit_amount = 0.0

# Function to parse amounts
def parse_amount(amount_str):
    amount_str = amount_str.replace(',', '').replace('$', '').strip()
    # Check if the string is a valid number
    if re.match(r'^-?\d+(\.\d+)?$', amount_str):
        return float(amount_str)
    else:
        return ''

# Regular expression pattern for dates with two-digit years (e.g., '31-Oct-23')
date_pattern = r'\d{2}-[A-Za-z]{3}-\d{2}'

# Manually set the x-coordinate boundaries for each column
column_boundaries = {
    'Transaction Date': (45, 109),      # Replace with your x-coordinate ranges
    'Value Date': (109, 165),
    'Transaction Details': (165, 355),
    'Withdrawal': (355, 440),
    'Deposit': (440, 505),
    'Balance': (505, 590),
}

with pdfplumber.open(pdf_path) as pdf:
    num_pages = len(pdf.pages)
    for page_num, page in enumerate(pdf.pages):
        print(f"\nProcessing page {page_num + 1}...")
        words = page.extract_words(use_text_flow=True)

        # Identify the footer lines
        footer_y = None
        header_y = None  # To be set when 'Transaction Date' is found

        for idx, word in enumerate(words):
            if word['text'] == 'Printed' and footer_y is None:
                footer_y = word['top']
                print(f"'Printed' found. Setting footer_y to {footer_y}")
            if page_num == num_pages - 1:
                # Check for 'Total' as a standalone word on the last page
                if word['text'] == 'Total' and footer_y is None:
                    # Check if 'Total' is the only word on the line
                    line_key = round(word['top'], 1)
                    line_words = [w for w in words if round(w['top'], 1) == line_key]
                    line_text = ' '.join([w['text'] for w in line_words])
                    if line_text.strip() == 'Total':
                        footer_y = word['top']
                        print(f"'Total' detected as standalone word on last page. Setting footer_y to {footer_y}")
            if word['text'] == 'Transaction' and header_y is None:
                # Check if the next word is 'Date'
                if idx + 1 < len(words) and words[idx + 1]['text'] == 'Date':
                    header_y = word['top']
                    print(f"Header found at Y-coordinate: {header_y}")

        if header_y is None:
            print(f"Header not found on page {page_num + 1}. Skipping page.")
            continue

        if footer_y is None:
            # If footer not detected, set footer_y to the bottom of the page
            footer_y = page.height
            print(f"No footer detected. Setting footer_y to page height: {footer_y}")

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

        # Group lines into transactions based on the presence of a value in the 'Transaction Date' column
        transactions_data = []
        current_transaction = []
        for line_key in sorted_line_keys:
            line_words = lines[line_key]
            # Assign words to columns based on x-coordinates
            line_columns_data = {name: '' for name in column_boundaries.keys()}
            for word in line_words:
                assigned_column = None
                for name, (col_start, col_end) in column_boundaries.items():
                    if col_start <= word['x0'] < col_end:
                        assigned_column = name
                        break
                if assigned_column:
                    line_columns_data[assigned_column] += word['text'] + ' '
            # Debug: Print line_columns_data
            print(f"Line at y={line_key}: {line_columns_data}")

            transaction_date_text = line_columns_data.get('Transaction Date', '').strip()
            if transaction_date_text:
                date_match = re.match(date_pattern, transaction_date_text)
                if date_match:
                    # Start of a new transaction
                    if current_transaction:
                        transactions_data.append(current_transaction)
                    current_transaction = [line_words]
                else:
                    print(f"Transaction Date '{transaction_date_text}' does not match date pattern. Skipping line.")
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
        for idx, trans in enumerate(transactions_data):
            print(f"\nProcessing transaction {idx + 1} on page {page_num + 1}")
            # Initialize fields
            date = ''
            value_date = ''
            transaction_details = ''
            debit = ''
            credit = ''

            # Process the transaction lines
            transaction_lines = trans
            transaction_details_lines = []

            for line in transaction_lines:
                line_columns_data = {name: '' for name in column_boundaries.keys()}
                for word in line:
                    # Assign word to the appropriate column based on x0
                    assigned_column = None
                    for name, (col_start, col_end) in column_boundaries.items():
                        if col_start <= word['x0'] < col_end:
                            assigned_column = name
                            break
                    if assigned_column:
                        line_columns_data[assigned_column] += word['text'] + ' '
                # Debug: Print line_columns_data
                print(f"Line data: {line_columns_data}")

                transaction_date_present = False

                # Check if the 'Transaction Date' is present in this line
                date_text = line_columns_data.get('Transaction Date', '').strip()
                if date_text:
                    date_match = re.match(date_pattern, date_text)
                    if date_match:
                        transaction_date_present = True
                        if not date:
                            try:
                                parsed_date = datetime.strptime(date_text, '%d-%b-%y')  # Adjusted format for two-digit year
                                date = parsed_date.strftime('%m/%d/%Y')
                            except ValueError as e:
                                print(f"Failed to parse Transaction Date '{date_text}': {e}")
                                pass  # Handle invalid dates if necessary
                    else:
                        print(f"Transaction Date '{date_text}' does not match date pattern.")

                # If the 'Value Date' is present and not already set, extract it
                if transaction_date_present and not value_date:
                    value_date_text = line_columns_data.get('Value Date', '').strip()
                    if value_date_text:
                        try:
                            parsed_date = datetime.strptime(value_date_text, '%d-%b-%y')  # Adjusted format for two-digit year
                            value_date = parsed_date.strftime('%m/%d/%Y')
                        except ValueError as e:
                            print(f"Failed to parse Value Date '{value_date_text}': {e}")
                            pass  # Handle invalid dates if necessary

                # Only extract 'Withdrawal' and 'Deposit' if 'Transaction Date' is present in this line
                if transaction_date_present:
                    # Extract 'Withdrawal' and 'Deposit' amounts from this line
                    debit_text = line_columns_data.get('Withdrawal', '').strip()
                    if debit_text:
                        debit = parse_amount(debit_text)
                    credit_text = line_columns_data.get('Deposit', '').strip()
                    if credit_text:
                        credit = parse_amount(credit_text)
                else:
                    # Do not extract 'Withdrawal' or 'Deposit' from lines without 'Transaction Date'
                    pass

                # Collect 'Transaction Details' from each line
                details_text = line_columns_data.get('Transaction Details', '').strip()
                if details_text:
                    transaction_details_lines.append(details_text)

            # Ensure debit and credit are strings for empty values
            debit_str = str(debit) if debit != '' else ''
            credit_str = str(credit) if credit != '' else ''

            # Update totals only if amounts are valid
            if debit != '':
                total_debit_transactions += 1
                total_debit_amount += debit
            if credit != '':
                total_credit_transactions += 1
                total_credit_amount += credit

            # Combine all transaction details lines
            transaction_details = ' '.join(transaction_details_lines).strip()
            print(f"Transaction Details collected: '{transaction_details}'")

            # Append to transactions list
            transaction_record = {
                'Transaction Date': date if date else '',
                'Value Date': value_date if value_date else '',
                'Transaction Details': transaction_details if transaction_details else '',
                'Withdrawal': debit_str,
                'Deposit': credit_str
            }
            transactions.append(transaction_record)
            print(f"Appended transaction: {transaction_record}")

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