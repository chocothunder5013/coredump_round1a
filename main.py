import os
import json
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from src.extractor import extract_outline_from_pdf

# Configure structured logging for production environments
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

INPUT_DIR = Path("/app/input")
OUTPUT_DIR = Path("/app/output")


def process_single_pdf(pdf_path: Path):
    """
    Worker function to process a single PDF, handling exceptions gracefully.

    Args:
        pdf_path: The path to the PDF file to process.

    Returns:
        A tuple of (pdf_path, extracted_data) or (pdf_path, None) on error.
    """
    logging.info(f"Starting processing: {pdf_path.name}")
    try:
        outline_data = extract_outline_from_pdf(pdf_path)
        logging.info(f"Successfully processed: {pdf_path.name}")
        return pdf_path, outline_data
    except Exception as e:
        # Log the full exception traceback for easier debugging in production
        logging.exception(f"Error processing {pdf_path.name}: {e}")
        return pdf_path, None


def main():
    """
    Main entry point. Finds all PDF files in the input directory and processes
    them in parallel using a process pool.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        logging.warning("No PDF files found in /app/input. Exiting.")
        return

    logging.info(
        f"Found {len(pdf_files)} PDF(s). Starting parallel processing on {os.cpu_count()} cores."
    )

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        results = list(executor.map(process_single_pdf, pdf_files))

    success_count = 0
    for pdf_path, outline_data in results:
        if outline_data:
            output_filename = OUTPUT_DIR / f"{pdf_path.stem}.json"
            try:
                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(outline_data, f, ensure_ascii=False, indent=4)
                success_count += 1
            except IOError as e:
                logging.error(f"Failed to write output file for {pdf_path.name}: {e}")

    logging.info(
        f"Processing complete. {success_count}/{len(pdf_files)} outlines generated."
    )


if __name__ == "__main__":
    main()
