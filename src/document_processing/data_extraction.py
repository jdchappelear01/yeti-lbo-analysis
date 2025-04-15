import anthropic
import os
import json
import base64
from pathlib import Path
import sqlite3
from datetime import datetime
import time
import subprocess
import sys

# Anthropic API details
ANTHROPIC_API_KEY = "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"
CLAUDE_SONNET35 = "claude-3-5-sonnet-20241022"
CLAUDE_SONNET37 = "claude-3-7-sonnet-20250219"

def init_database():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect('financial_metrics.db')
    cursor = conn.cursor()
    
    # Create table for financial metrics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS financial_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        year INTEGER,
        quarter INTEGER,
        filing_date TEXT,
        revenue REAL,
        ebitda REAL,
        ebitda_margin REAL,
        cash REAL,
        total_debt REAL,
        net_debt REAL,
        total_assets REAL,
        working_capital REAL,
        capex REAL,
        capex_to_revenue REAL,
        revenue_growth REAL,
        ebitda_growth REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    return conn

def get_pdf_files(directory):
    """Get all PDF files from a directory."""
    pdf_files = []
    for pdf_file in Path(directory).glob('**/*.pdf'):
        pdf_files.append(pdf_file)
    return pdf_files

def extract_form_10q_lbo_data(pdf_path, company_name):
    """Extract LBO data from a Form 10-Q PDF file."""
    # Read the PDF file
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    # Convert PDF to base64
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Construct content array
    content = []

    # Add Form 10-Q PDF
    content.append({
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": pdf_base64
        }
    })

    # Add the prompt text
    content.append({
        "type": "text",
        "text": f"""
You have been provided with the Form 10-Q of {company_name}.

<task>
Your task is to extract key financial data from this Form 10-Q that would be necessary to build a simple Leveraged Buyout (LBO) model.

PHASE 1: DOCUMENT ANALYSIS
- Review the Form 10-Q to locate the key financial statements (Income Statement, Balance Sheet, Cash Flow Statement)
- Identify the current quarter and year-to-date figures
- Extract the reporting period information (Year and Quarter)

PHASE 2: EXTRACT THE FOLLOWING KEY METRICS
<required_json_output>
{{
"Period_Info": {{
  "Year": "Fiscal year of the report",
  "Quarter": "Quarter number (1-4)",
  "Filing_Date": "Date of the filing"
}},
"Income_Statement": {{
  "Revenue": "Total revenue/net sales for the most recent quarter in millions USD",
  "EBITDA": "EBITDA for the most recent quarter in millions USD (calculate as Operating Income + Depreciation & Amortization if not directly stated)",
  "EBITDA_Margin": "EBITDA as a percentage of Revenue for the most recent quarter"
}},
"Balance_Sheet": {{
  "Cash": "Cash and cash equivalents in millions USD",
  "Total_Debt": "Total debt (current and long-term) in millions USD",
  "Net_Debt": "Total debt minus cash in millions USD",
  "Total_Assets": "Total assets in millions USD",
  "Working_Capital": "Current assets minus current liabilities in millions USD"
}},
"Cash_Flow": {{
  "CapEx": "Capital expenditures for the year-to-date period in millions USD",
  "CapEx_to_Revenue": "CapEx as a percentage of revenue"
}},
"Growth_Metrics": {{
  "Revenue_Growth": "Year-over-year revenue growth percentage for the most recent quarter",
  "EBITDA_Growth": "Year-over-year EBITDA growth percentage for the most recent quarter"
}}
}}
</required_json_output>

PHASE 3: VERIFICATION
For each metric, within <metrics></metrics> XML tags:
- Note the exact source (page or section)
- Show any calculations performed
- Verify time periods are correctly identified

PHASE 4: FINAL OUTPUT
Present the final metrics in a JSON object within <answer></answer> XML tags.

Only include metrics that are explicitly stated in the document or can be directly calculated. If a metric cannot be found, leave its value blank in the JSON.
</task>
        """
    })

    message = client.messages.create(
        model=CLAUDE_SONNET37,
        max_tokens=8192,
        thinking={
            "type": "enabled",
            "budget_tokens": 4096
        },
        system="""
You are a financial analyst extracting key data for LBO modeling from Form 10-Q documents. Focus only on the essential metrics needed for a simple LBO model demonstration.

Extract accurate financial data from the quarterly report, focusing specifically on:
1. Revenue and EBITDA figures
2. Debt and cash positions
3. Capital expenditures
4. Working capital
5. Growth rates

Document your work process and calculations within <metrics></metrics> tags. This work will not be shown to the user.

Your final answer should be a clean JSON object within <answer></answer> XML tags containing only the requested financial metrics.
    """,
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    # Extract everything from response.content to include thinking
    full_output = ""
    for block in message.content:
        if hasattr(block, 'text'):
            full_output += block.text + "\n"
        else:
            full_output += str(block) + "\n"

    return full_output

def extract_json_from_output(output):
    """Extract JSON data from Claude's output between <answer></answer> tags."""
    import re
    answer_match = re.search(r'<answer>(.*?)</answer>', output, re.DOTALL)
    if answer_match:
        try:
            return json.loads(answer_match.group(1).strip())
        except json.JSONDecodeError:
            print("Error parsing JSON from Claude's output")
            return None
    return None

def save_to_database(conn, data, company_name):
    """Save the extracted financial data to SQLite database."""
    cursor = conn.cursor()
    
    # Extract period info
    period_info = data.get('Period_Info', {})
    year = period_info.get('Year')
    quarter = period_info.get('Quarter')
    filing_date = period_info.get('Filing_Date')
    
    # Extract other metrics
    income_stmt = data.get('Income_Statement', {})
    balance_sheet = data.get('Balance_Sheet', {})
    cash_flow = data.get('Cash_Flow', {})
    growth_metrics = data.get('Growth_Metrics', {})
    
    cursor.execute('''
    INSERT INTO financial_metrics (
        company_name, year, quarter, filing_date,
        revenue, ebitda, ebitda_margin,
        cash, total_debt, net_debt, total_assets, working_capital,
        capex, capex_to_revenue,
        revenue_growth, ebitda_growth
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        company_name, year, quarter, filing_date,
        income_stmt.get('Revenue'), income_stmt.get('EBITDA'), income_stmt.get('EBITDA_Margin'),
        balance_sheet.get('Cash'), balance_sheet.get('Total_Debt'), balance_sheet.get('Net_Debt'),
        balance_sheet.get('Total_Assets'), balance_sheet.get('Working_Capital'),
        cash_flow.get('CapEx'), cash_flow.get('CapEx_to_Revenue'),
        growth_metrics.get('Revenue_Growth'), growth_metrics.get('EBITDA_Growth')
    ))
    
    conn.commit()

def run_lbo_analysis():
    """Run the LBO analysis script after data extraction."""
    print("\nWaiting 60 seconds before starting LBO analysis...")
    for remaining in range(60, 0, -1):
        print(f"\r{remaining} seconds remaining...", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 30 + "\r", end="", flush=True)  # Clear the countdown line
    
    print("\nStarting LBO analysis...")
    # Get the path to the lbo_prompt.py script
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    lbo_script_path = project_root / "src" / "lbo_modeling" / "lbo_prompt.py"
    
    try:
        # Run the LBO analysis script using the same Python interpreter
        subprocess.run([sys.executable, str(lbo_script_path)], check=True)
        print("✓ LBO analysis completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running LBO analysis: {str(e)}")

def main():
    # Initialize database
    conn = init_database()
    
    # Directory containing SEC filings
    sec_filings_dir = "data/sec_filings"
    
    # Get all PDF files
    pdf_files = get_pdf_files(sec_filings_dir)
    total_files = len(pdf_files)
    
    print(f"\nFound {total_files} PDF files to process")
    
    # Process each PDF file sequentially
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\nProcessing file {i}/{total_files}: {pdf_file}")
        company_name = pdf_file.parent.name  # Use the directory name as company name
        
        try:
            # Extract data
            print("Sending to Claude for analysis...")
            results = extract_form_10q_lbo_data(pdf_file, company_name)
            
            # Create output directory if it doesn't exist
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # Save raw output to JSON file
            output_file = output_dir / f"{company_name}_{pdf_file.stem}_analysis.json"
            with open(output_file, 'w') as f:
                f.write(results)
            print(f"✓ Raw results saved to: {output_file}")
            
            # Extract JSON data from output
            print("Extracting structured data...")
            json_data = extract_json_from_output(results)
            if json_data:
                # Save to database
                save_to_database(conn, json_data, company_name)
                print(f"✓ Data saved to database for {company_name}")
            else:
                print("⚠ No structured data found in the output")
            
            print(f"✓ Completed processing {pdf_file.name}")
            
            # Add delay between files to avoid rate limiting
            if i < total_files:  # Don't wait after the last file
                print("\nWaiting 60 seconds before processing next file to avoid rate limiting...")
                for remaining in range(60, 0, -1):
                    print(f"\r{remaining} seconds remaining...", end="", flush=True)
                    time.sleep(1)
                print("\r" + " " * 30 + "\r", end="", flush=True)  # Clear the countdown line
            
        except Exception as e:
            print(f"❌ Error processing {pdf_file}: {str(e)}")
            print("Continuing with next file...")
            
            # Still add delay even if there was an error
            if i < total_files:
                print("\nWaiting 60 seconds before processing next file to avoid rate limiting...")
                for remaining in range(60, 0, -1):
                    print(f"\r{remaining} seconds remaining...", end="", flush=True)
                    time.sleep(1)
                print("\r" + " " * 30 + "\r", end="", flush=True)  # Clear the countdown line
    
    # Close database connection
    conn.close()
    print("\nAll files processed!")
    
    # Run LBO analysis
    run_lbo_analysis()

if __name__ == "__main__":
    main()
