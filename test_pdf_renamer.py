import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import pdf_renamer

def test_parse_arguments():
    test_args = ["pdf_renamer.py", "test_directory"]
    with patch('sys.argv', test_args):
        args = pdf_renamer.parse_arguments()
        assert args.scan_directory == "test_directory"

def test_extract_pdf_text():
    mock_pdf_path = MagicMock(spec=Path)
    mock_pdf_path.open.return_value.__enter__.return_value = MagicMock()
    with patch('PyPDF2.PdfReader') as MockPdfReader:
        mock_reader_instance = MockPdfReader.return_value
        mock_reader_instance.pages = [MagicMock()]
        mock_reader_instance.pages[0].extract_text.return_value = "Sample text"
        text = pdf_renamer.extract_pdf_text(mock_pdf_path)
        assert text == "Sample text"

def test_generate_new_filename():
    sample_text = "Sample PDF content"
    original_file = Path("2023_10_12_13_14_15_sample.pdf")
    mocked_response = {"response": "Sample Name"}
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = mocked_response
        mock_post.return_value.raise_for_status = MagicMock()
        new_filename = pdf_renamer.generate_new_filename(sample_text, original_file)
        assert new_filename == "2023.10.12 - Sample Name.pdf"

def test_process_pdfs(tmp_path):
    # Create a mock PDF file with a date pattern in the filename
    pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")  # Minimal PDF content to simulate a PDF file

    # Mock the extract and generate functions
    with patch('pdf_renamer.extract_pdf_text') as mock_extract_text, \
         patch('pdf_renamer.generate_new_filename') as mock_generate_new_filename:
        mock_extract_text.return_value = "Mocked PDF content"
        mock_generate_new_filename.return_value = "2023.10.12 - Mocked Name.pdf"

        pdf_renamer.process_pdfs(tmp_path)

        # Check that the file has been renamed correctly
        new_file = tmp_path / "2023.10.12 - Mocked Name.pdf"
        assert new_file.exists()
