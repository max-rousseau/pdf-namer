import click
import re
import json
import time
from pathlib import Path
import requests
import pypdf
from click import style

DEFAULT_MODEL = "llama3.1:70b-instruct-q8_0"


def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extracts text from a PDF file.

    Args:
        pdf_path (Path): Path to the PDF file.

    Returns:
        str: Extracted text.
    """
    text = ""
    with pdf_path.open("rb") as file:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


def generate_new_filename(text: str, original_file: Path, model: str) -> str:
    """
    Generates a new filename based on PDF content and date extracted from the original filename.

    Args:
        text (str): The content of the PDF file.
        original_file (Path): The original PDF file.
        model (str): The LLM model to use for generating filenames.

    Returns:
        str: The new filename.
    """

    max_summarized_length = 17

    # Read the prompt from 'prompt.md'
    prompt_path = Path("prompt.md")
    prompt = prompt_path.read_text()
    prompt = prompt.format(text=text)

    print(style("="*50, fg="blue"))
    print(style("Prompt Analysis", fg="green", bold=True))
    print(f"Sending prompt to Ollama (length: {len(prompt)} characters)")

    # Send the request to the Ollama service and measure time
    start_time = time.time()
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.5},
            "format": "json",
        },
        timeout=600,
    )
    response.raise_for_status()
    elapsed_time = time.time() - start_time
    print(f"Received response from Ollama in {elapsed_time:.2f} seconds")
    print(style("="*50, fg="blue"))
    try:
        data = response.json()
        if "response" not in data:
            print(
                f"Error: The API response does not contain the 'response' key.\n{data}"
            )
            return None

        # Parse the JSON response
        try:
            data = json.loads(data["response"])
        except json.JSONDecodeError:
            print("Error: Invalid JSON response from API")
            return None

        # Validate JSON structure
        expected_keys = {"date", "filename"}
        actual_keys = set(data.keys())

        if not expected_keys.issubset(actual_keys):
            missing_keys = expected_keys - actual_keys
            print(f"Error: Missing required keys in response: {missing_keys}\n{data}")
            return None

        if actual_keys != expected_keys:
            extra_keys = actual_keys - expected_keys
            print(f"Error: Unexpected extra keys in response: {extra_keys}\n{data}")
            return None

        # Clean and validate the summarized name
        date = data["date"].strip() if data["date"] else "YYYY.MM.DD"
        summarized_name = f"{date} - {data['filename'].strip()}"

        # Construct the new filename
        return summarized_name
    except Exception as e:
        print(f"Error generating filename: {str(e)}")
        return None


def process_pdfs(directory: Path, test_mode: bool, model: str):
    """
    Processes PDF files in the given directory.

    Args:
        directory (Path): The directory containing PDF files.
        test_mode (bool): Whether to run in test mode without renaming
        model (str): The LLM model to use for generating filenames
    """
    # Regular expression to match the date pattern
    date_pattern = re.compile(r"\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}")

    # Find all PDF files matching the date pattern
    pdf_files = [
        file
        for file in directory.iterdir()
        if file.is_file()
        and file.suffix.lower() == ".pdf"
        and date_pattern.search(file.name)
    ]

    # Process each PDF file
    for pdf_file in pdf_files:
        print(style("="*50, fg="blue"))
        print(style(f"Processing {pdf_file.name}", fg="green", bold=True))
        try:
            text = extract_pdf_text(pdf_file)
            new_filename = generate_new_filename(text, pdf_file, model)
            if not new_filename:
                print(f"Error processing {pdf_file.name}. Ignoring.")
            if test_mode:
                print(f"Original filename: {pdf_file.name}")
                print(f"New filename: {new_filename}")
            else:
                pdf_file.rename(directory / new_filename)
        except requests.exceptions.RequestException as e:
            print(f"Network error processing {pdf_file.name}: {e}")
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")


@click.command()
@click.argument("scan_directory", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--test-mode", is_flag=True, help="Run in test mode without renaming files."
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    help="Specify the LLM model to use for generating filenames.",
)
def main(scan_directory, test_mode, model):
    """Process PDF files in the provided directory."""
    process_pdfs(Path(scan_directory), test_mode, model)


if __name__ == "__main__":
    main()
