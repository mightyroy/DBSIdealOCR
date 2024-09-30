This Python script extracts transaction data from a DBS Ideal bank statement PDF and saves it as a CSV file. The fields extracted are: Date,Value Date,Transaction Details,Debit,Credit.

Put pdf file in same folder. run python script (make sure all python modules installed). A csv file will be generated with the same name

If the statement pdf page has grey horizontal stripes, use DBS_Ideal_statement_OCR_stripe_format.py

If the statement pdf page is mostly white with no grey stripes, use DBS_Ideal_statement_OCR_white_format.py

