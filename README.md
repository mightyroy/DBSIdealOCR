These Python scripts extracts transaction data from a DBS Ideal bank statement PDF and saves it as a CSV file. The fields extracted are: Date,Value Date,Transaction Details,Debit,Credit.

Put pdf file in same folder. Rename target file in the script. Run python script (make sure all python modules installed). A csv file will be generated with the same name

If the statement pdf page has grey horizontal stripes, use DBS_Ideal_statement_OCR_stripe_format.py

If the statement pdf page is mostly white with no grey stripes, use DBS_Ideal_statement_OCR_white_format.py

convert_xls_statements_to_csv.py converts DBS .xls statement files into csv format suitable for importing into quickbooks. DBS Ideal allows download of .xls statement for prior 6 months. If older than 6 months, only pdf statement is available, which the above 2 OCR python files can handle.
