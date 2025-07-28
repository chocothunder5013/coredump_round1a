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


def process_single_pdf(pdf_path: Path, output_dir: Path) -> bool:
    """
    Worker function to process and save a single PDF outline.
    Returns True on success, False on failure.
    """
    logging.info(f"Starting processing: {pdf_path.name}")
    try:
        # 1. Extract outline data
        outline_data = extract_outline_from_pdf(pdf_path)

        # 2. Write output file directly from the worker process
        if outline_data and outline_data["outline"]:
            output_filename = output_dir / f"{pdf_path.stem}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(outline_data, f, ensure_ascii=False, indent=4)
            logging.info(f"Successfully processed and saved: {pdf_path.name}")
            return True
        else:
            logging.warning(f"No outline found for: {pdf_path.name}")
            return False

    except Exception as e:
        logging.exception(f"Error processing {pdf_path.name}: {e}")
        return False


def main():
    """
    Main entry point. Finds all PDF files and processes them in parallel.
    Each worker process now handles its own JSON file output.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        logging.warning("No PDF files found in /app/input. Exiting.")
        return

    num_cores = os.cpu_count() or 1
    logging.info(
        f"Found {len(pdf_files)} PDF(s). Starting parallel processing on {num_cores} cores."
    )

    success_count = 0
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        # Map each pdf file to the worker function, providing the output directory
        results = executor.map(
            process_single_pdf, pdf_files, [OUTPUT_DIR] * len(pdf_files)
        )
        # Sum the boolean results to get the total success count
        success_count = sum(1 for r in results if r)

    logging.info(
        f"Processing complete. {success_count}/{len(pdf_files)} outlines generated."
    )


if __name__ == "__main__":
    main()
