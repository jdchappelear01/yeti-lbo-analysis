# YETI LBO Analysis

A web application that performs a Leveraged Buyout (LBO) analysis on YETI Holdings financial data from SEC filings.

## Features

- Extracts financial data from YETI quarterly SEC filings (10-Q) using Claude AI
- Processes and stores key financial metrics in a SQLite database
- Performs comprehensive LBO analysis with Claude AI
- Displays detailed LBO analysis through a simple web interface

## Requirements

- Python 3.x
- Required Python packages (see requirements.txt)
- Anthropic API key for Claude AI access

## Setup

1. Clone the repository
```bash
git clone https://github.com/jdchappelear01/yeti-lbo-analysis.git
cd yeti-lbo-analysis
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the server
```bash
python run_analysis.py
```

4. Open a web browser and navigate to http://localhost:8000

## Usage

1. Click the "Start YETI Analysis" button
2. Wait for the analysis to complete (this may take several minutes)
3. View the detailed LBO analysis results

## Project Structure

- `run_analysis.py`: Main web server script
- `src/document_processing/`: PDF extraction and data processing
- `src/lbo_modeling/`: LBO analysis script
- `data/sec_filings/`: YETI quarterly SEC filings
- `output/`: Generated analysis files
- `index.html`: Simple web interface 