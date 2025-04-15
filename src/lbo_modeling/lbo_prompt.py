import pandas as pd
import anthropic
import sqlite3
from pathlib import Path
import traceback
import os
import time  # Add import for time

# Anthropic API details
ANTHROPIC_API_KEY = "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"
CLAUDE_SONNET37 = "claude-3-7-sonnet-20250219"  # Updated model identifier

def get_available_companies():
    """Get a list of all companies in the database."""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('financial_metrics.db')
        cursor = conn.cursor()
        
        # Get unique company names
        cursor.execute("SELECT DISTINCT company_name FROM financial_metrics")
        companies = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return companies
    except Exception as e:
        print(f"Error getting companies: {str(e)}")
        return []

def get_financial_data(company_name=None):
    """
    Fetch financial data from SQLite database.
    
    Parameters:
    company_name (str): Optional company name to filter results
    
    Returns:
    pandas.DataFrame: Financial metrics data
    """
    try:
        # Connect to SQLite database
        db_path = 'financial_metrics.db'
        print(f"Looking for database at: {os.path.abspath(db_path)}")
        
        if not os.path.exists(db_path):
            print(f"⚠️ Database file not found at {os.path.abspath(db_path)}")
            return pd.DataFrame()
            
        conn = sqlite3.connect(db_path)
        
        # Build query
        if company_name:
            print(f"Querying data for company: {company_name}")
            query = """
            SELECT company_name as Company,
                   year as Year,
                   quarter as Quarter,
                   revenue as Revenue,
                   ebitda as EBITDA,
                   ebitda_margin as 'EBITDA Margin',
                   cash as Cash,
                   total_debt as 'Total Debt',
                   net_debt as 'Net Debt',
                   total_assets as 'Total Assets',
                   working_capital as 'Working Capital',
                   capex as CapEx,
                   capex_to_revenue as 'CapEx to Revenue',
                   revenue_growth as 'Revenue Growth',
                   ebitda_growth as 'EBITDA Growth'
            FROM financial_metrics
            WHERE company_name = ?
            ORDER BY year DESC, quarter DESC
            """
            df = pd.read_sql_query(query, conn, params=(company_name,))
        else:
            print("Querying data for all companies")
            query = """
            SELECT company_name as Company,
                   year as Year,
                   quarter as Quarter,
                   revenue as Revenue,
                   ebitda as EBITDA,
                   ebitda_margin as 'EBITDA Margin',
                   cash as Cash,
                   total_debt as 'Total Debt',
                   net_debt as 'Net Debt',
                   total_assets as 'Total Assets',
                   working_capital as 'Working Capital',
                   capex as CapEx,
                   capex_to_revenue as 'CapEx to Revenue',
                   revenue_growth as 'Revenue Growth',
                   ebitda_growth as 'EBITDA Growth'
            FROM financial_metrics
            ORDER BY company_name, year DESC, quarter DESC
            """
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        print(f"Retrieved {len(df)} rows of financial data")
        return df
    except Exception as e:
        print(f"Error getting financial data: {str(e)}")
        traceback.print_exc()
        return pd.DataFrame()

def perform_lbo_analysis(financial_data_df):
    """
    Perform LBO analysis on company financial data using Claude's API.
    
    Parameters:
    financial_data_df (pandas.DataFrame): DataFrame containing quarterly financial data
                                         with columns for Company, Year, Quarter, Revenue, EBITDA, etc.
    
    Returns:
    str: The full LBO analysis from Claude
    """
    try:
        # Format the DataFrame as a markdown table string
        table_string = financial_data_df.to_markdown(index=False)
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Add delay to avoid rate limiting
        print("Waiting 90 seconds to avoid rate limiting...")
        time.sleep(90)
        
        # Create the prompt with the financial data
        prompt = f"""
I need you to perform a detailed leveraged buyout (LBO) analysis for a company based on the following quarterly financial data:

{table_string}

<task>
Conduct a comprehensive leveraged buyout analysis for this company. Use the historical financial data to build a forward-looking model that calculates potential returns for a private equity investor.

PHASE 1: DATA ANALYSIS
- Analyze the historical financial performance across all quarters
- Calculate key growth rates, margins, and trends
- Identify any seasonality or unusual patterns in the data

PHASE 2: LBO MODEL SETUP
Establish the following baseline assumptions:
- Purchase multiple: 10.0x TTM EBITDA
- Transaction date: End of last available quarter
- Projection period: 5 years from transaction date
- Exit multiple: Same as entry multiple (10.0x)
- Debt structure:
  * Senior debt: 4.0x EBITDA at SOFR + 300bps (assume current SOFR at 5.3%)
  * Subordinated debt: 2.0x EBITDA at SOFR + 500bps
  * Required annual debt amortization: 10% of initial senior debt balance
- Revenue growth: Average of historical YoY growth, tapering by 0.5% annually
- EBITDA margin: Average of historical margins, with 0.25% annual expansion
- CapEx: Maintain historical percentage of revenue
- Working capital: Maintain historical percentage of revenue
- Minimum cash balance required: $10 million

PHASE 3: DETAILED CALCULATIONS
For each year in the projection period, calculate:
1. Revenue projection based on growth assumptions
2. EBITDA projection based on margin assumptions
3. CapEx requirements
4. Changes in working capital
5. Free cash flow available for debt service
6. Debt paydown schedule and ending debt balances
7. Interest expenses for each debt tranche
8. Cash balance at year end

PHASE 4: RETURNS ANALYSIS
Calculate:
1. Exit enterprise value (Year 5 EBITDA × exit multiple)
2. Exit equity value (Enterprise value - net debt at exit)
3. Multiple on invested capital (MOIC)
4. Internal rate of return (IRR)
5. Cash-on-cash return

PHASE 5: SENSITIVITY ANALYSIS
Perform sensitivity analysis on:
1. Entry multiple (9.0x, 10.0x, 11.0x)
2. Exit multiple (9.0x, 10.0x, 11.0x)
3. Revenue growth rates (base case -1%, base case, base case +1%)

PHASE 6: INVESTMENT RECOMMENDATION
Based on the analysis:
1. Assess the attractiveness of this LBO opportunity
2. Identify key value creation levers
3. Highlight potential risks and mitigating factors
4. Make a clear recommendation (Proceed, Proceed with Caution, or Do Not Proceed)

Present your work systematically, showing all calculations, assumptions, and reasoning. The analysis should be rigorous enough to withstand scrutiny from investment committee members.
</task>
"""
        
        # Call Claude API
        print("Calling Claude API for LBO analysis...")
        message = client.messages.create(
            model=CLAUDE_SONNET37,
            max_tokens=20000,
            thinking={
                "type": "enabled",
                "budget_tokens": 5000  # Large thinking budget for complex financial modeling
            },
            system="""
You are a top-tier private equity analyst with expertise in leveraged buyout modeling. You are highly analytical, precise with numbers, and methodical in your approach. You excel at building financial models, understanding capital structures, and evaluating investment opportunities.

When performing LBO analysis:
1. Be rigorous and transparent in your calculations
2. Show your step-by-step mathematical work
3. Clearly state all assumptions and their rationale
4. Use multiple analytic approaches to cross-validate your findings
5. Think carefully about the limitations of your analysis
6. Present your final recommendation with appropriate confidence based on data quality

Structure your analysis in a clear, logical progression that walks through each phase of the LBO analysis. Use tables when presenting financial projections to improve readability. Express all monetary values in millions unless otherwise specified, and round to two decimal places for clarity.

When writing your response, think of yourself as presenting to sophisticated financial professionals who expect precise calculations, sound reasoning, and a balanced assessment of the investment opportunity.
""",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract and return the response
        print("Received response from Claude API")
        full_output = ""
        for block in message.content:
            if hasattr(block, 'text'):
                full_output += block.text + "\n"
            else:
                full_output += str(block) + "\n"
                
        return full_output
    except Exception as e:
        print(f"Error performing LBO analysis: {str(e)}")
        traceback.print_exc()
        return f"Error performing LBO analysis: {str(e)}"

def save_analysis(company_name, analysis_text):
    """
    Save the LBO analysis to a file.
    
    Parameters:
    company_name (str): Name of the company
    analysis_text (str): The full LBO analysis text
    """
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Clean the analysis text to remove thinking tokens
        # Find the start of the actual analysis
        analysis_start = analysis_text.find("# LEVERAGED BUYOUT ANALYSIS:")
        if analysis_start == -1:
            # If not found, try alternative format
            analysis_start = analysis_text.find("# Leveraged Buyout Analysis:")
        
        if analysis_start != -1:
            # Only keep the actual analysis part
            cleaned_analysis = analysis_text[analysis_start:]
        else:
            cleaned_analysis = analysis_text
        
        # Save analysis to file
        output_file = output_dir / f"{company_name}_lbo_analysis.txt"
        with open(output_file, 'w') as f:
            f.write(cleaned_analysis)
        print(f"✓ Analysis saved to: {output_file}")
        return True
    except Exception as e:
        print(f"Error saving analysis: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """
    Main function to run LBO analysis on all available data in the database.
    """
    try:
        print("\nStarting automated LBO analysis...")
        
        # Get list of available companies
        companies = get_available_companies()
        
        if not companies:
            print("⚠️ No companies found in the database")
            # Try running with all data if no specific companies found
            all_data = get_financial_data()
            if not all_data.empty:
                print("Running analysis on all available data...")
                analysis = perform_lbo_analysis(all_data)
                save_analysis("combined_companies", analysis)
                print("\n✓ Analysis complete!")
            else:
                print("❌ No financial data found in the database")
            return
        
        print(f"Found {len(companies)} companies in the database: {', '.join(companies)}")
        
        # Process each company
        for company in companies:
            print(f"\nAnalyzing {company}...")
            company_data = get_financial_data(company)
            
            if company_data.empty:
                print(f"⚠️ No data found for {company}")
                continue
            
            print(f"✓ Retrieved {len(company_data)} rows of financial data for {company}")
            
            # Perform LBO analysis
            print(f"\nPerforming LBO analysis for {company}...")
            analysis = perform_lbo_analysis(company_data)
            
            # Save the analysis
            save_analysis(company, analysis)
            print(f"\n✓ Analysis for {company} complete!")
        
        print("\nAll analyses completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in main function: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()