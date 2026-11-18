import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from pipeline import run_pipeline
except ImportError:
    from src.pipeline import run_pipeline

def run_end_to_end():
    print("==================================================")
    print("   CANTILL SPEND PIPELINE - END-TO-END EXECUTION  ")
    print("==================================================")
    
    os.makedirs('submission', exist_ok=True)
    
    jobs = [
        {
            "name": "Company A",
            "config": "configs/company_a.json",
            "data_dir": "company_A",
            "output": "submission/aditi_A.csv"
        },
        {
            "name": "Company B",
            "config": "configs/company_b.json",
            "data_dir": "company_B",
            "output": "submission/aditi_B.csv"
        }
    ]
    
    for job in jobs:
        print(f"\n[+] Processing {job['name']}...")
        print(f"    Config:   {job['config']}")
        print(f"    Data Dir: {job['data_dir']}")
        print(f"    Output:   {job['output']}")
        
        if os.path.exists(job['config']) and os.path.exists(job['data_dir']):
            run_pipeline(job['config'], job['data_dir'], job['output'])
            print(f"    ✅ {job['name']} processed and saved successfully.")
        else:
            print(f"    ❌ Error: Missing config file or data directory for {job['name']}.")
            sys.exit(1)

    print("\n==================================================")
    print(" All pipelines executed successfully!")
    print("   Output compliance files generated in submission/")
    print("==================================================")

if __name__ == "__main__":
    run_end_to_end()