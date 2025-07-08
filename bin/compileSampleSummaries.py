#!/usr/bin/env python
import argparse
import csv
from collections import defaultdict

def compileSummaries(summary_files, out):
    print(f"Processing {len(summary_files)} summary files")
    if len(summary_files) == 0:
        raise ValueError("No summary files provided")
    
    all_rows = []
    headers = None
    
    for file_path in summary_files:
        print(f"Reading file: {file_path}")
        with open(file_path, 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            current_headers = next(reader)
            
            if headers is None:
                headers = current_headers
            
            for row in reader:
                all_rows.append(dict(zip(headers, row)))
    
    wide_data = transform_to_wide_format(all_rows)
    write_tsv(wide_data, out)

def transform_to_wide_format(rows):
    sample_data = defaultdict(dict)
    all_taxa = set()
    for row in rows:
        taxon = row['taxon']
        all_taxa.add(taxon)
    
    taxa_columns = sorted(list(all_taxa))
    print(f"Detected taxa columns: {taxa_columns}")

    #transform data
    for row in rows:
        id = row['id']
        taxon = row['taxon']
        clade_reads = row['cladeReads']
        sample_data[id][taxon] = clade_reads
    
    wide_rows = []
    header_row = ['id'] + taxa_columns
    wide_rows.append(header_row)
    
    for id, taxa_values in sample_data.items():
        row = [id]
        for taxon in taxa_columns:
            row.append(taxa_values.get(taxon, '0'))
        wide_rows.append(row)
    
    return wide_rows

def write_tsv(data, output_file):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        for row in data:
            writer.writerow(row)
    
    print(f"TSV file written to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Compile summaries into a flat json file")
    parser.add_argument("--out", help="Output name for compiled summaries file", required=True)
    parser.add_argument("summary_files", nargs='+', help="One or more summary files to process")
    args = parser.parse_args()
    
    try:
        compileSummaries(args.summary_files, args.out)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()