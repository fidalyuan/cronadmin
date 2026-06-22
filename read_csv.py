#!/usr/bin/env python3
import argparse
import csv
import os
import sys

def read_csv(file_path):
    """
    Reads a CSV file and prints its content in a formatted table.
    
    Args:
        file_path (str): The path to the CSV file.
    """
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
            # Using DictReader to handle header mapping automatically
            # utf-8-sig handles BOM if present (common in Excel exported CSVs)
            reader = csv.DictReader(csv_file)
            
            # Retrieve fieldnames (headers)
            headers = reader.fieldnames
            if not headers:
                print(f"Warning: The file '{file_path}' appears to be empty or has no headers.", file=sys.stderr)
                return

            # Read all rows
            rows = list(reader)
            if not rows:
                print(f"The file '{file_path}' contains headers but no data rows.")
                print(f"Headers: {', '.join(headers)}")
                return

            # Calculate column widths for nice formatting
            col_widths = {header: len(header) for header in headers}
            for row in rows:
                for header in headers:
                    val = str(row.get(header, ''))
                    if len(val) > col_widths[header]:
                        col_widths[header] = len(val)

            # Print header row
            header_format = " | ".join(f"{{:<{col_widths[h]}}}" for h in headers)
            separator = "-+-".join("-" * col_widths[h] for h in headers)
            
            print(header_format.format(*headers))
            print(separator)
            
            # Print data rows
            for row in rows:
                row_values = [str(row.get(h, '')) for h in headers]
                print(header_format.format(*row_values))
                
            print(f"\nSuccessfully read {len(rows)} rows from '{file_path}'.")

    except PermissionError:
        print(f"Error: Permission denied when trying to read '{file_path}'.", file=sys.stderr)
        sys.exit(1)
    except csv.Error as e:
        print(f"Error parsing CSV: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Read and print the contents of a CSV file.")
    parser.add_argument(
        "file_path", 
        nargs="?", 
        default="sample.csv",
        help="Path to the CSV file to read (default: sample.csv)"
    )
    
    args = parser.parse_args()
    read_csv(args.file_path)

if __name__ == "__main__":
    main()
