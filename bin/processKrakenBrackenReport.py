#!/usr/bin/env python
import argparse
import json
import csv
import re
from pathlib import Path

def processReport(input_id, input_report, report_type, taxids_map, taxranks, out_summary, out_taxonomy, min_percent_abundance):
    print(f"Processing sample id: {input_id}")
    
    #taxids map
    try:
        tax_ids_json = json.loads(taxids_map)  # Using loads() for string instead of load() for file
    except Exception as e:
        raise Exception(f"Failed to parse taxids map JSON: {str(e)}")
    
    #taxranks arr
    try:
        taxa_ranks = taxranks.split(',')
    except Exception as e:
        raise Exception(f"Failed to parse taxranks string: {str(e)}")
    
    #check the report (normal or with minimizer)
    with open(input_report, 'r') as f:
        first_line = next((line for line in f if line.strip()), None)
        if not first_line:
            raise Exception(f"Empty report file: {input_report}")
        
        fields = first_line.strip().split('\t')
        num_fields = len(fields)
        
        #common fields
        percent_col = 0
        cladeReads_col = 1
        taxonReads_col = 2
        
        #variable fields
        if num_fields == 6: #normal 6 cols
            rank_col = 3
            taxid_col = 4
            name_col = 5
        elif num_fields == 8: #with minimiser 8 cols
            rank_col = 5
            taxid_col = 6
            name_col = 7
        else:
            raise Exception(f"Unrecognized kraken2 report format (found {num_fields} columns)")
    
    #init data placeholder
    summary_data = []
    taxonomy_tree = []
    
    #taxids map
    taxid_to_reads = {}
    for taxon, taxid in tax_ids_json.items():
        if taxid != "NA":
            if report_type == 'bracken':
                if taxid != "0":
                    taxid_to_reads[taxid] = 0
            else:
                taxid_to_reads[taxid] = 0
    
    #reverse LUT
    taxid_to_taxon = {}
    for taxon, taxid in tax_ids_json.items():
        if taxid != "NA":
            if report_type == 'bracken':
                if taxid != "0":
                    taxid_to_taxon[taxid] = taxon
            else:
                taxid_to_taxon[taxid] = taxon
    
    #proces line by line
    with open(input_report, 'r') as f:
        for line in f:
            if not line.strip():
                continue
                
            fields = line.strip().split('\t')
            try:
                percentage = float(fields[percent_col])
                clade_reads = int(fields[cladeReads_col])
                taxon_reads = int(fields[taxonReads_col])
                taxon_rank = fields[rank_col].strip()
                taxon_id = fields[taxid_col]
                raw_name = fields[name_col]
            except (IndexError, ValueError) as e:
                continue
            
            #capture row for sample summary
            if taxon_id in taxid_to_reads:
                taxid_to_reads[taxon_id] = clade_reads
            
            #capture row for taxonomy data
            ##skip taxa with abundance below threshold (this is to remove the noise and save filesize)
            if percentage < min_percent_abundance:
                continue 
            
            #get depth based on indentation level
            indent_match = re.match(r'^(\s*)', raw_name)
            depth = len(indent_match.group(1)) // 2 if indent_match else 0
            
            clean_name = raw_name.strip()
            taxonomy_tree.append({
                'percentage': percentage,
                'cladeReads': clade_reads,
                'taxonReads': taxon_reads,
                'taxonRank': taxon_rank,
                'taxonID': taxon_id,
                'name': clean_name,
                'depth': depth
            })
    
    #build complete taxonomy data
    taxonomy_data = []
    
    for i, node in enumerate(taxonomy_tree):
        rank_values = {rank: "" for rank in taxa_ranks}
        ancestors = []
        current_depth = node['depth']
        
        #look backwards through the tree to find parents
        for j in range(i-1, -1, -1):
            potential_parent = taxonomy_tree[j]
            if potential_parent['depth'] < current_depth:
                ancestors.insert(0, potential_parent)
                current_depth = potential_parent['depth']
                #if reach the root, stop
                if current_depth == 0:
                    break
        
        #build the lineage with separate rank values
        for ancestor in ancestors:
            if ancestor['depth'] > 0:  #skip the root
                rank = ancestor['taxonRank']
                name = ancestor['name']
                if rank != '-' and rank in taxa_ranks:
                    rank_values[rank] = name
        
        rank = node['taxonRank']
        name = node['name']
        
        if rank != '-' and node['depth'] > 0 and rank in taxa_ranks:  #skip root
            rank_values[rank] = name
            display_name = f"{rank.lower()}_{name}" if rank != 'U' else name
            
            #add to taxonomy data
            taxonomy_entry = {
                'sample': input_id,
                'percentage': node['percentage'],
                'cladeReads': node['cladeReads'],
                'name': display_name,
                'taxRank': rank
            }
            
            for rank_key in taxa_ranks:
                taxonomy_entry[rank_key] = rank_values[rank_key]
                
            taxonomy_data.append(taxonomy_entry)
                
    #populate taxids for summary
    for taxid, reads in taxid_to_reads.items():
        summary_data.append({
            'taxid': taxid,
            'taxon': taxid_to_taxon[taxid],
            'cladeReads': reads
        })

    #write outputs
    write_sample_summary(input_id, summary_data, out_summary)
    write_taxonomy_table(input_id, taxonomy_data, out_taxonomy, taxa_ranks)

def write_sample_summary(input_id, summary_data, out_summary):
    with open(out_summary, 'w', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['id', 'taxid', 'taxon', 'cladeReads'])
        for entry in summary_data:
            writer.writerow([
                input_id,
                entry['taxid'],
                entry['taxon'],
                entry['cladeReads']
            ])
    print(f"Sample summary written to {out_summary}")

def write_taxonomy_table(input_id, taxonomy_data, out_taxonomy, taxa_ranks):
    with open(out_taxonomy, 'w', newline='') as f:
        header = ['sample', 'percentage', 'cladeReads', 'name', 'taxRank'] + taxa_ranks
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(header)
        
        for row in taxonomy_data:
            row_data = [
                row['sample'],
                row['percentage'],
                row['cladeReads'],
                row['name'],
                row['taxRank']
            ]
            
            for rank in taxa_ranks:
                row_data.append(row[rank])
                
            writer.writerow(row_data)
    print(f"Taxonomy table written to {out_taxonomy}")

def main():
    parser = argparse.ArgumentParser(description="Process a Kraken-like report")
    parser.add_argument("--input_id", help="Input report id", required=True)
    parser.add_argument("--input_report", help="Input report file", required=True)
    parser.add_argument("--report_type", help="Kraken or Bracken", required=True)
    parser.add_argument("--taxids_map", help="Map of taxaids for sample summary", required=True)
    parser.add_argument("--taxranks", help="Array of taxa ranks for taxonomy table", required=True)
    parser.add_argument("--out_summary", help="Output name for sample summary file", required=True)
    parser.add_argument("--out_taxonomy", help="Output name for taxonomy table file", required=True)
    parser.add_argument("--min_percent", help="Minimum percentage abundance to include", type=float, required=True)
    
    args = parser.parse_args()
    
    try:
        processReport(args.input_id, args.input_report, args.report_type, args.taxids_map, args.taxranks, args.out_summary, args.out_taxonomy, args.min_percent)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()