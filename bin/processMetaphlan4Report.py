#!/usr/bin/env python
import argparse
import json
import csv

def processReport(input_id, input_report, report_type, taxids_map, taxranks, out_summary, out_taxonomy, min_percent_abundance):
    print(f"Processing sample id: {input_id}")
    
    #taxids map
    try:
        tax_ids_json = json.loads(taxids_map)
    except Exception as e:
        raise Exception(f"Failed to parse taxids map JSON: {str(e)}")
    
    #taxranks arr
    try:
        taxa_ranks = taxranks.split(',')
    except Exception as e:
        raise Exception(f"Failed to parse taxranks string: {str(e)}")
    
    #validate metaphlan4 format
    with open(input_report, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                fields = line.strip().split('\t')
                if len(fields) != 5:
                    raise Exception(f"Invalid Metaphlan4 format: expected 5 columns, got {len(fields)}")
                break
        else:
            raise Exception(f"No valid data lines found in {input_report}")
    
    #init data
    summary_data = []
    taxonomy_tree = []
    
    #taxids map for summary
    taxid_to_reads = {}
    for taxon, taxid in tax_ids_json.items():
        if taxid != "NA" and taxid != "0":
            taxid_to_reads[taxid] = 0
    
    #reverse LUT
    taxid_to_taxon = {}
    for taxon, taxid in tax_ids_json.items():
        if taxid != "NA" and taxid != "0":
            taxid_to_taxon[taxid] = taxon
    
    #rank prefixes mapping
    rank_prefixes = {
        'k__': 'K', 'p__': 'P', 'c__': 'C', 'o__': 'O', 
        'f__': 'F', 'g__': 'G', 's__': 'S'
    }
    
    #process metaphlan4 report
    with open(input_report, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
                
            fields = line.strip().split('\t')
            try:
                clade_name = fields[0]
                clade_taxid = fields[1]
                relative_abundance = float(fields[2])
                coverage = float(fields[3])
                estimated_reads = int(fields[4])
            except (IndexError, ValueError) as e:
                continue
            
            #skip low abundance
            if relative_abundance < min_percent_abundance:
                continue
            
            #capture for summary if any taxid in compound matches
            compound_taxids = clade_taxid.split('|')
            for single_taxid in compound_taxids:
                if single_taxid in taxid_to_reads:
                    #use the highest read count for this taxid
                    taxid_to_reads[single_taxid] = max(taxid_to_reads[single_taxid], estimated_reads)
            
            #parse taxonomic hierarchy
            taxa_parts = clade_name.split('|')
            depth = len(taxa_parts) - 1
            
            #get current taxon info
            current_taxon = taxa_parts[-1]
            current_rank = 'U'
            current_name = current_taxon
            
            #extract rank from prefix
            for prefix, rank in rank_prefixes.items():
                if current_taxon.startswith(prefix):
                    current_rank = rank
                    current_name = current_taxon[3:]  #remove prefix
                    break
            
            #build rank values from hierarchy
            rank_values = {rank: "" for rank in taxa_ranks}
            
            for taxon_part in taxa_parts:
                for prefix, rank in rank_prefixes.items():
                    if taxon_part.startswith(prefix) and rank in taxa_ranks:
                        rank_values[rank] = taxon_part[3:]
                        break
            
            #create taxonomy entry
            if current_rank in taxa_ranks:
                display_name = f"{current_rank.lower()}_{current_name}" if current_rank != 'U' else current_name
                
                taxonomy_entry = {
                    'sample': input_id,
                    'percentage': relative_abundance,
                    'cladeReads': estimated_reads,
                    'name': display_name,
                    'taxRank': current_rank
                }
                
                for rank_key in taxa_ranks:
                    taxonomy_entry[rank_key] = rank_values[rank_key]
                    
                taxonomy_tree.append(taxonomy_entry)
    
    #populate summary data, skip zero reads
    for taxid, reads in taxid_to_reads.items():
        if reads > 0:
            summary_data.append({
                'taxid': taxid,
                'taxon': taxid_to_taxon[taxid],
                'cladeReads': reads
            })

    #write outputs
    write_sample_summary(input_id, summary_data, out_summary)
    write_taxonomy_table(input_id, taxonomy_tree, out_taxonomy, taxa_ranks)

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
    parser = argparse.ArgumentParser(description="Process a Metaphlan4 report")
    parser.add_argument("--input_id", help="Input report id", required=True)
    parser.add_argument("--input_report", help="Input report file", required=True)
    parser.add_argument("--report_type", help="Report type (metaphlan4)", required=True)
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