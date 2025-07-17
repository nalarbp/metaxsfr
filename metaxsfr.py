#!/usr/bin/env python
import argparse
import json
import os
import subprocess
import sys
import glob
from pathlib import Path

#const
TAXRANK_NCBI = ["D", "K", "P", "C", "O", "F", "G", "S"]
TAXRANK_GTDB = ["R1", "P", "C", "O", "F", "G", "S"]
SUPPORTED_REPORT_TYPES = ['kraken2', 'bracken', 'metaphlan4']
SUPPORTED_DATABASES = ['ncbi', 'gtdb']
TAXID_NCBI = {
    "unclassified": "0",
    "human": "9606",
    "bacterial": "2",
    "viral": "10239",
    "fungal": "4751",
    "archaeal": "2157"
}
TAXID_GTDB = {
    "unclassified": "0",
    "human": "NA",
    "bacterial": "3", 
    "viral": "NA",
    "fungal": "NA",
    "archaeal": "2"
}

def validate_inputs(reports, report_type, report_db):
    if report_type not in SUPPORTED_REPORT_TYPES:
        sys.exit(f"Error: Report type must be one of {SUPPORTED_REPORT_TYPES}, got '{report_type}'")
    
    if report_db not in SUPPORTED_DATABASES:
        sys.exit(f"Error: Database must be one of {SUPPORTED_DATABASES}, got '{report_db}'")
    
    #handle wildcard, for multi files
    if '*' in reports:
        report_files = glob.glob(reports)
        if not report_files:
            sys.exit(f"Error: No report files found matching pattern '{reports}'")
        print(f"+++ Found {len(report_files)} report files matching pattern")
    
    #handle multiple files, comma-separated    
    elif ',' in reports:
        files = [f.strip().strip('"\'') for f in reports.split(',')]
        total_files = 0
        
        for f in files:
            if '*' in f or '?' in f or '[' in f:
                matches = glob.glob(f)
                if not matches:
                    sys.exit(f"Error: No files found matching pattern '{f}'")
                total_files += len(matches)
            else:
                if not os.path.exists(f):
                    sys.exit(f"Error: File '{f}' does not exist")
                total_files += 1
        
        print(f"+++ Found {total_files} report files total")
    
    #handle single file or glob    
    else:
        if not os.path.exists(reports):
            sys.exit(f"Error: Reports path '{reports}' does not exist")

def transform_reports_for_nextflow(reports):
    #multiple files, comma-separated 
    if ',' in reports:
        files = [f.strip().strip('"\'') for f in reports.split(',')]
        expanded_files = []
        for f in files:
            if '*' in f or '?' in f or '[' in f:
                matches = glob.glob(f)
                expanded_files.extend(matches)
            else:
                expanded_files.append(f)
        
        #return comma-separated
        return ','.join(expanded_files)
    #else as is (single or glob)
    else:
        return reports
    
def get_taxid_map(report_db):
    if report_db == 'ncbi':
        return TAXID_NCBI
    elif report_db == 'gtdb':
        return TAXID_GTDB
    else:
        sys.exit(f"Error: Unsupported database '{report_db}'")

def get_taxrank_list(report_db):
    if report_db == 'ncbi':
        return TAXRANK_NCBI
    elif report_db == 'gtdb':
        return TAXRANK_GTDB
    else:
        sys.exit(f"Error: Unsupported database '{report_db}'")

def find_main_nf():
    script_path = os.path.realpath(os.path.abspath(__file__))
    script_dir = os.path.dirname(script_path)
    
    #in script directory
    main_nf_path = os.path.join(script_dir, 'main.nf')
    if os.path.exists(main_nf_path):
        return main_nf_path
    
    #if installed via conda, for later
    # conda_prefix = os.environ.get('CONDA_PREFIX')
    # if conda_prefix and os.path.exists(os.path.join(conda_prefix, 'metaxsfr', 'main.nf')):
    #     return os.path.join(conda_prefix, 'metaxsfr', 'main.nf')
    
    sys.exit("Error: Cannot find main.nf. Please ensure METAXSFR is correctly installed.")

def run_metaxsfr_pipeline(reports, report_type, report_db, output, 
                         min_abundance, executor, resume, config, nf_args, version):
    
    print(f"+++ Starting METAXSFR v{version}")
    
    #preflight
    validate_inputs(reports, report_type, report_db)
    transformed_reports = transform_reports_for_nextflow(reports)
    taxid_map = get_taxid_map(report_db)
    taxrank_list = get_taxrank_list(report_db)
    main_nf_path = find_main_nf()
    print(f"+++ Using workflow: {main_nf_path}")
    
    #build nf command
    nextflow_cmd = ["nextflow", "run", main_nf_path]
    nextflow_cmd.extend([
        f"--reports={transformed_reports}",
        f"--report_type={report_type}",
        f"--report_db={report_db}",
        f"--results_directory={output}",
        f"--taxid_map={json.dumps(taxid_map)}",
        f"--taxrank_list={','.join(taxrank_list)}",
        f"--min_percent_abundance={min_abundance}",
        f"--executor={executor}",
        f"--pipeline_version={version}"
    ])
    
    #add nf options
    if resume:
        nextflow_cmd.append("-resume")
    
    if config:
        nextflow_cmd.append(f"-c {config}")
    
    if nf_args:
        nextflow_cmd.append(nf_args)
    
    #run nf
    print(f"+++ Executing: {' '.join(nextflow_cmd)}")
    try:
        subprocess.run(nextflow_cmd, check=True)
        print("\n+++ METAXSFR completed successfully!")
    except subprocess.CalledProcessError as e:
        sys.exit(f"\n+++ METAXSFR failed with exit code {e.returncode}")
    except KeyboardInterrupt:
        print("\n+++ METAXSFR execution interrupted by user")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog="metaxsfr",
        description="METAXSFR: Metagenome Taxonomic Explorer in a Single-File Report",
        epilog="Example: metaxsfr -r 'reports/*.txt' -t bracken -d gtdb -o results",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    #version
    version = '0.1.1'
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {version}")
    
    #required params
    parser.add_argument("-r", "--reports", required=True,
                       help="Path to report file(s). Can use wildcards like 'reports/*.txt' (must be quoted)")
    parser.add_argument("-t", "--report-type", required=True, choices=SUPPORTED_REPORT_TYPES,
                       help="Type of taxonomic profiling report")
    parser.add_argument("-d", "--database", required=True, choices=SUPPORTED_DATABASES,
                       help="Taxonomic database used for classification")
    
    #optional params
    parser.add_argument("-o", "--output", default="results",
                       help="Output directory for results")
    parser.add_argument("--min-abundance", type=float, default=0.01,
                       help="Minimum abundance threshold (percentage)")
    parser.add_argument("--executor", default="local",
                       help="Nextflow executor to use")
    
    #nextflow related params
    parser.add_argument("--resume", action="store_true",
                       help="Resume previous run (Nextflow -resume flag)")
    parser.add_argument("-c", "--config", default=None,
                       help="Nextflow configuration file")
    parser.add_argument("--nf-args", default="",
                       help="Additional arguments to pass to Nextflow (as quoted string)")
    
    args = parser.parse_args()
    
    #run metaxsfr
    run_metaxsfr_pipeline(
        reports=args.reports,
        report_type=args.report_type,
        report_db=args.database,
        output=args.output,
        min_abundance=args.min_abundance,
        executor=args.executor,
        resume=args.resume,
        config=args.config,
        nf_args=args.nf_args,
        version=version
    )

if __name__ == "__main__":
    main()