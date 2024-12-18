import pytest
import sys
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path
import requests
import pypdf
import pdf_renamer


class TestExtractPdfText:
    def test_valid_pdf(self):
        mock_pdf_path = MagicMock(spec=Path)
        mock_pdf_path.open.return_value.__enter__.return_value = MagicMock()
        with patch('pypdf.PdfReader') as MockPdfReader:
            mock_reader_instance = MockPdfReader.return_value
            mock_reader_instance.pages = [MagicMock(), MagicMock()]
            mock_reader_instance.pages[0].extract_text.return_value = "Page 1"
            mock_reader_instance.pages[1].extract_text.return_value = "Page 2"
            text = pdf_renamer.extract_pdf_text(mock_pdf_path)
            assert text == "Page 1Page 2"

    def test_pdf_without_text(self):
        mock_pdf_path = MagicMock(spec=Path)
        with patch('pypdf.PdfReader') as MockPdfReader:
            mock_reader_instance = MockPdfReader.return_value
            mock_reader_instance.pages = [MagicMock()]
            mock_reader_instance.pages[0].extract_text.return_value = ""
            text = pdf_renamer.extract_pdf_text(mock_pdf_path)
            assert text == ""

    def test_corrupted_pdf(self):
        mock_pdf_path = MagicMock(spec=Path)
        with patch('pypdf.PdfReader', side_effect=pypdf.errors.PdfReadError):
            with pytest.raises(pypdf.errors.PdfReadError):
                pdf_renamer.extract_pdf_text(mock_pdf_path)

class TestGenerateNewFilename:
    def test_successful_response(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "response": '{"date": "2023.10.12", "filename": "Sample Name"}'
            }
            mock_post.return_value.raise_for_status = MagicMock()
            new_filename = pdf_renamer.generate_new_filename(sample_text, original_file, "llama2")
            assert new_filename == "2023.10.12 - Sample Name"

    def test_network_error(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post', side_effect=requests.exceptions.RequestException("Network error")):
            with pytest.raises(requests.exceptions.RequestException):
                pdf_renamer.generate_new_filename(sample_text, original_file, "llama2")

    def test_invalid_date_format(self):
        sample_text = "Sample PDF content"
        original_file = Path("invalid_filename.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "response": '{"date": "UnknownDate", "filename": "Sample Name"}'
            }
            mock_post.return_value.raise_for_status = MagicMock()
            new_filename = pdf_renamer.generate_new_filename(sample_text, original_file, "llama2")
            assert new_filename.startswith("UnknownDate - ")

    def test_missing_response_key(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "response": '{"invalid": "data"}'  # Missing required keys
            }
            mock_post.return_value.raise_for_status = MagicMock()
            result = pdf_renamer.generate_new_filename(sample_text, original_file, "llama2")
            assert result is None

    def test_filename_length_validation(self):
        sample_text = "Sample PDF content"
        original_file = Path("2023_10_12_13_14_15_sample.pdf")
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "response": '{"date": "2023.10.12", "filename": "This is a very long filename that should be handled properly"}'
            }
            mock_post.return_value.raise_for_status = MagicMock()
            new_filename = pdf_renamer.generate_new_filename(sample_text, original_file, "llama2")
            assert len(new_filename) <= 50  # Adjusted for new requirements
            assert ' - ' in new_filename

class TestContextWindow:
    def test_calculate_context_window(self):
        model = "llama3.1:70b-instruct-q8_0"
        prompt = "Short prompt"
        result = pdf_renamer.calculate_context_window(model, prompt)
        assert result == len(prompt) + 1000  # prompt length + 1000 buffer

    def test_calculate_context_window_long_prompt(self):
        model = "llama3.1:70b-instruct-q8_0"
        prompt = "x" * 130000  # Exceeds max context
        result = pdf_renamer.calculate_context_window(model, prompt)
        assert result == 128000  # Should cap at model's max context

    def test_calculate_context_window_unknown_model(self):
        model = "unknown_model"
        prompt = "Test prompt"
        result = pdf_renamer.calculate_context_window(model, prompt)
        assert result == len(prompt) + 1000  # Should use default buffer size

class TestProcessPdfs:
    def test_process_pdfs_test_mode_with_confirmation(self, tmp_path):
        pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch('pdf_renamer.extract_pdf_text') as mock_extract, \
             patch('pdf_renamer.generate_new_filename') as mock_generate, \
             patch('click.confirm') as mock_confirm:
            
            mock_extract.return_value = "Test content"
            mock_generate.return_value = "2023.10.12 - Test Doc.pdf"
            
            # Test when user confirms rename
            mock_confirm.return_value = True
            pdf_renamer.process_pdfs(tmp_path, test_mode=True, model="llama2")
            assert not pdf_file.exists()
            assert (tmp_path / "2023.10.12 - Test Doc.pdf").exists()

            # Reset the test environment
            (tmp_path / "2023.10.12 - Test Doc.pdf").rename(pdf_file)
            
            # Test when user declines rename
            mock_confirm.return_value = False
            pdf_renamer.process_pdfs(tmp_path, test_mode=True, model="llama2")
            assert pdf_file.exists()
            assert not (tmp_path / "2023.10.12 - Test Doc.pdf").exists()

    def test_main_with_test_mode(self, tmp_path):
        runner = CliRunner()
        with patch('pdf_renamer.process_pdfs') as mock_process:
            result = runner.invoke(pdf_renamer.main, ['--test-mode', '--model', 'llama2', str(tmp_path)])
            assert result.exit_code == 0
            mock_process.assert_called_once_with(Path(tmp_path), True, 'llama2', False)

    def test_main_with_all_files(self, tmp_path):
        runner = CliRunner()
        with patch('pdf_renamer.process_pdfs') as mock_process:
            result = runner.invoke(pdf_renamer.main, ['--all-files', '--model', 'llama2', str(tmp_path)])
            assert result.exit_code == 0
            mock_process.assert_called_once_with(Path(tmp_path), False, 'llama2', True)
    def test_empty_directory(self, tmp_path):
        pdf_renamer.process_pdfs(tmp_path, test_mode=False, model="llama2")
        assert len(list(tmp_path.iterdir())) == 0

    def test_successful_processing(self, tmp_path):
        # Create test PDF files
        pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        with patch('pdf_renamer.extract_pdf_text') as mock_extract, \
             patch('pdf_renamer.generate_new_filename') as mock_generate:
            mock_extract.return_value = "Test content"
            mock_generate.return_value = "2023.10.12 - Test Doc.pdf"
            
            pdf_renamer.process_pdfs(tmp_path, test_mode=False, model="llama2")
            assert not pdf_file.exists()
            assert (tmp_path / "2023.10.12 - Test Doc.pdf").exists()

    def test_skip_large_content(self, tmp_path):
        # Create a PDF file with large content
        pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        with patch('pdf_renamer.extract_pdf_text') as mock_extract:
            mock_extract.return_value = "x" * 10001  # Create text longer than 10000 chars
            pdf_renamer.process_pdfs(tmp_path, test_mode=False, model="llama2")
            assert pdf_file.exists()  # File should not be processed due to length

    def test_skip_non_matching_files(self, tmp_path):
        # Create a PDF file without date pattern
        pdf_file = tmp_path / "regular.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        pdf_renamer.process_pdfs(tmp_path, test_mode=False, model="llama2")
        assert pdf_file.exists()  # File should not be processed

    def test_permission_error(self, tmp_path):
        pdf_file = tmp_path / "2023_10_12_13_14_15_sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        
        with patch('pathlib.Path.rename', side_effect=PermissionError):
            pdf_renamer.process_pdfs(tmp_path, test_mode=False, model="llama2")
            assert pdf_file.exists()  # Original file should still exist
