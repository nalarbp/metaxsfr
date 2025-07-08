#!/usr/bin/env python
import argparse
import datetime
import json
from scifrMutator import mutate_template_memory

def convert_tsv_to_flat_string(file_path):
   try:
       with open(file_path, 'r') as tsv_file:
           content = tsv_file.read()
           return content.replace("\t", ";t").replace("\n", ";n")
   except Exception as e:
       print(f"Warning: Could not read file {file_path}: {str(e)}")
       return 'NA'

def generate_metaxsfr_json(summary_table, taxonomy_table, params_json, pipeline_version):
   #summary data
   summary_data = 'NA'
   if summary_table:
       summary_data = convert_tsv_to_flat_string(summary_table)
   
   #taxonomy data
   taxonomy_data = 'NA'
   if taxonomy_table:
       taxonomy_data = convert_tsv_to_flat_string(taxonomy_table)
   
   #params data
   params_data = {}
   if params_json:
       try:
           with open(params_json, 'r') as params_file:
               params_data = json.loads(params_file.read())
                       
               #simplify reports path
               if 'reports' in params_data and params_data['reports']:
                   path_parts = params_data['reports'].split('/')
                   if len(path_parts) > 1:
                       params_data['reports'] = '/' + '/'.join(path_parts[-2:])
                       
               #only keep taxonomy data relevant to the selected database
               if 'report_db' in params_data:
                   db_type = params_data['report_db'].lower()
                   if db_type == 'ncbi':
                       if 'taxid_gtdb' in params_data:
                           del params_data['taxid_gtdb']
                       if 'taxrank_gtdb' in params_data:
                           del params_data['taxrank_gtdb']
                   elif db_type == 'gtdb':
                       if 'taxid_ncbi' in params_data:
                           del params_data['taxid_ncbi']
                       if 'taxrank_ncbi' in params_data:
                           del params_data['taxrank_ncbi']
       except Exception as e:
           print(f"Warning: Could not read params file: {str(e)}")
   
   #add pipeline version and timestamp
   params_data['pipeline_version'] = pipeline_version
   params_data['created'] = datetime.datetime.now().isoformat()
   
   #create the combined data structure
   combined_data = {
           "startIdx": "@@METAXSFR@@INPUT@@START@@",
           "logData": params_data,
           "sampleSummary": summary_data,
           "sampleTaxonomy": taxonomy_data,
           "endIdx": "@@METAXSFR@@INPUT@@END@@"
   }
   return combined_data

def generate_metaxsfr(summary_table, taxonomy_table, template_path, out_html, out_json, params_json, pipeline_version, save_intermediate=False):
   try:
       combined_data = generate_metaxsfr_json(summary_table, taxonomy_table, params_json, pipeline_version)
       
       #speed up by not saving intermediate json file
       if save_intermediate:
           with open(out_json, 'w') as json_file:
               json.dump(combined_data, json_file, indent=2)
       
       #template mutation (in-memory)
       start_marker = combined_data["startIdx"] 
       end_marker = combined_data["endIdx"]
       mutate_template_memory(combined_data, template_path, out_html, start_marker, end_marker)
       
       print(f"Successfully generated METAXSFR report: {out_html}")
       if save_intermediate:
           print(f"JSON data saved to: {out_json}")
           
   except Exception as e:
       print(f"Error generating METAXSFR report: {str(e)}")
       raise

def main():
   parser = argparse.ArgumentParser(description="Generate METAXSFR report")
   parser.add_argument("--summary_table", help="Sample summary table (TSV)", required=True)
   parser.add_argument("--taxonomy_table", help="Taxonomy table (TSV)", required=True)
   parser.add_argument("--template", help="HTML template file", required=True)
   parser.add_argument("--out_html", help="Output HTML report file", required=True)
   parser.add_argument("--out_json", help="Output JSON file (optional)")
   parser.add_argument("--params_data", help="Parameters JSON file", required=True)
   parser.add_argument("--pipeline_version", help="Pipeline version", required=True)
   parser.add_argument("--save_intermediate", help="Save intermediate JSON file", action="store_true", default=False)
   
   args = parser.parse_args()
   save_json = args.save_intermediate and args.out_json is not None
   
   generate_metaxsfr(
       args.summary_table,
       args.taxonomy_table,
       args.template,
       args.out_html,
       args.out_json,
       args.params_data,
       args.pipeline_version,
       save_json
   )

if __name__ == "__main__":
   main()