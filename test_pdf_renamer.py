import pytest
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
import requests
import PyPDF2
import pdf_renamer

class TestParseArguments:
    def test_valid_directory(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['pdf_renamer.py', 'test_directory'])
        args = pdf_renamer.parse_arguments()
        assert args.scan_directory == "test_directory"

    def test_missing_directory(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['pdf_renamer.py'])
        with pytest.raises(SystemExit):
            pdf_renamer.parse_arguments()

class TestExtractPdfText:
    def test_valid_pdf(self):
        mock_pdf_path = MagicMock(spec=Path)
        mock_pdf_path.open.return_value.__enter__.return_value = MagicMock()
        with patch('PyPDF2.PdfReader') as MockPdfReader:
            mock_reader_instance = MockPdfReader.return_value
            mock_reader_instance.pages = [MagicMock(), MagicMock()]
            mock_reader_instance.pages[0].extract_text.return_value = "Page 1"
            mock_reader_instance.pages[1].extract_text.return_value = "Page 2"
            text = pdf_renamer.extract_pdf_text(mock_pdf_path)
            assert text == "Page 1Page 2"

    def test_pdf_without_text(self):
        mock_pdf_path = MagicMock(spec=Path)
        with patch('PyPDF2.PdfReader') as MockPdfReader:
            mock_reader_instance = MockPdfReader.return_value
            mock_reader_instance.pages = [MagicMock()]
            mock_reader_instance.pages[0].extract_text.return_value = ""
            text = pdf_renamer.extract_pdf_text(mock_pdf_path)
            assert text == ""

    def test_corrupted_pdf(self):
        mock_pdf_path = MagicMock(spec=Path)
        with patch('PyPDF2.PdfReader', side_effect=PyPDF2.errors.PdfReadError):
            with pytest.raises(PyPDF2.errors.PdfReadError):
                pdf_renamer.extract_pdf_text(mock_pdf_path)

class TestGenerateNewFilename:
    def test_successful_response(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {"response": "Sample Name"}
            mock_post.return_value.raise_for_status = MagicMock()
            new_filename = pdf_renamer.generate_new_filename(sample_text, original_file)
            assert new_filename == "2023.10.12 - Sample Name.pdf"

    def test_network_error(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post', side_effect=requests.exceptions.RequestException("Network error")):
            with pytest.raises(requests.exceptions.RequestException):
                pdf_renamer.generate_new_filename(sample_text, original_file)

    def test_invalid_date_format(self):
        sample_text = "Sample PDF content"
        original_file = Path("invalid_filename.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {"response": "Sample Name"}
            mock_post.return_value.raise_for_status = MagicMock()
            new_filename = pdf_renamer.generate_new_filename(sample_text, original_file)
            assert new_filename.startswith("UnknownDate - ")

    def test_missing_response_key(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {}  # Missing 'response' key
            mock_post.return_value.raise_for_status = MagicMock()
            with pytest.raises(KeyError):
                pdf_renamer.generate_new_filename(sample_text, original_file)

class TestProcessPdfs:
    def test_empty_directory(self, tmp_path):
        pdf_renamer.process_pdfs(tmp_path)
        assert len(list(tmp_path.iterdir())) == 0

    def test_successful_processing(self, tmp_path):
        # Create test PDF files
        pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        with patch('pdf_renamer.extract_pdf_text') as mock_extract, \
             patch('pdf_renamer.generate_new_filename') as mock_generate:
            mock_extract.return_value = "Test content"
            mock_generate.return_value = "2023.10.12 - Test Doc.pdf"
            
            pdf_renamer.process_pdfs(tmp_path)
            assert not pdf_file.exists()
            assert (tmp_path / "2023.10.12 - Test Doc.pdf").exists()

    def test_skip_non_matching_files(self, tmp_path):
        # Create a PDF file without date pattern
        pdf_file = tmp_path / "regular.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        pdf_renamer.process_pdfs(tmp_path)
        assert pdf_file.exists()  # File should not be processed

    def test_permission_error(self, tmp_path):
        pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        with patch('pathlib.Path.rename', side_effect=PermissionError):
            pdf_renamer.process_pdfs(tmp_path)
            assert pdf_file.exists()  # Original file should still exist