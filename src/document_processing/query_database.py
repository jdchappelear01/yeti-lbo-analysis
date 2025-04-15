import sqlite3
from tabulate import tabulate

def connect_db():
    """Connect to the SQLite database."""
    return sqlite3.connect('financial_metrics.db')

def get_all_companies():
    """Get list of all companies in the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT company_name FROM financial_metrics')
    companies = cursor.fetchall()
    conn.close()
    return [company[0] for company in companies]

def get_company_metrics(company_name=None):
    """Get financial metrics for a specific company or all companies."""
    conn = connect_db()
    cursor = conn.cursor()
    
    if company_name:
        cursor.execute('''
            SELECT 
                company_name,
                year,
                quarter,
                revenue,
                ebitda,
                ebitda_margin,
                cash,
                total_debt,
                net_debt
            FROM financial_metrics
            WHERE company_name = ?
            ORDER BY year DESC, quarter DESC
        ''', (company_name,))
    else:
        cursor.execute('''
            SELECT 
                company_name,
                year,
                quarter,
                revenue,
                ebitda,
                ebitda_margin,
                cash,
                total_debt,
                net_debt
            FROM financial_metrics
            ORDER BY company_name, year DESC, quarter DESC
        ''')
    
    rows = cursor.fetchall()
    headers = ['Company', 'Year', 'Quarter', 'Revenue', 'EBITDA', 'EBITDA Margin', 'Cash', 'Total Debt', 'Net Debt']
    conn.close()
    
    return headers, rows

def main():
    while True:
        print("\nFinancial Metrics Database Query Tool")
        print("1. List all companies")
        print("2. View metrics for a specific company")
        print("3. View all companies' metrics")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            companies = get_all_companies()
            print("\nCompanies in database:")
            for company in companies:
                print(f"- {company}")
                
        elif choice == '2':
            companies = get_all_companies()
            print("\nAvailable companies:")
            for i, company in enumerate(companies, 1):
                print(f"{i}. {company}")
            
            try:
                idx = int(input("\nEnter company number: ")) - 1
                if 0 <= idx < len(companies):
                    headers, rows = get_company_metrics(companies[idx])
                    print("\n" + tabulate(rows, headers=headers, tablefmt='grid'))
                else:
                    print("Invalid company number")
            except ValueError:
                print("Please enter a valid number")
                
        elif choice == '3':
            headers, rows = get_company_metrics()
            print("\n" + tabulate(rows, headers=headers, tablefmt='grid'))
            
        elif choice == '4':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 