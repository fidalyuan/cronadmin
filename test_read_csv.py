#!/usr/bin/env python3
import unittest
from unittest.mock import patch
import io
import os
import sys
import tempfile

# Import the read_csv function from read_csv.py
from read_csv import read_csv

class TestReadCSV(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        # Clean up temporary directory
        self.test_dir.cleanup()

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_read_valid_csv(self, mock_stdout):
        # Create a valid temporary CSV file
        csv_path = os.path.join(self.test_dir.name, 'valid.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("id,name,age\n1,Alice,30\n2,Bob,25\n")
            
        read_csv(csv_path)
        output = mock_stdout.getvalue()
        
        # Verify headers and data rows exist in the output
        self.assertIn("id", output)
        self.assertIn("name", output)
        self.assertIn("age", output)
        self.assertIn("Alice", output)
        self.assertIn("Bob", output)
        self.assertIn("Successfully read 2 rows", output)

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_nonexistent_file(self, mock_stderr):
        non_existent_path = os.path.join(self.test_dir.name, 'missing.csv')
        
        # Expect the function to call sys.exit(1)
        with self.assertRaises(SystemExit) as cm:
            read_csv(non_existent_path)
            
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: The file", mock_stderr.getvalue())
        self.assertIn("does not exist", mock_stderr.getvalue())

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_empty_file(self, mock_stderr):
        empty_path = os.path.join(self.test_dir.name, 'empty.csv')
        with open(empty_path, 'w', encoding='utf-8') as f:
            pass  # Create an empty file
            
        read_csv(empty_path)
        self.assertIn("Warning: The file", mock_stderr.getvalue())
        self.assertIn("empty or has no headers", mock_stderr.getvalue())

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_headers_no_data(self, mock_stdout):
        headers_path = os.path.join(self.test_dir.name, 'headers_only.csv')
        with open(headers_path, 'w', encoding='utf-8') as f:
            f.write("id,name,age\n")
            
        read_csv(headers_path)
        output = mock_stdout.getvalue()
        self.assertIn("contains headers but no data rows", output)
        self.assertIn("Headers: id, name, age", output)

if __name__ == '__main__':
    unittest.main()
