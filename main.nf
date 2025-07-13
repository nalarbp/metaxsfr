#!/usr/bin/env nextflow

//params
params.reports = null
params.report_type = null
params.report_db = null
params.results_directory = null
params.taxid_map = null
params.taxrank_list = null
params.pipeline_version = null
params.min_percent_abundance = null
params.executor = null

//validation, key requeirements
if (params.reports == null) {
    error("ERROR: Required parameter 'reports' not specified!")
}

if (params.report_type == null) {
    error("ERROR: Required parameter 'report_type' not specified!")
}

if (params.report_db == null) {
    error("ERROR: Required parameter 'report_db' not specified!")
}

//workflow
workflow {
    ch_reports = Channel
        .fromPath(
            params.reports.contains(',') ? 
            params.reports.split(',').collect { it.trim().replaceAll('"', '') } : 
            params.reports.trim().replaceAll('"', ''), 
        checkIfExists: true
        )
        .map { report ->
            def id = report.baseName.replaceAll(/[^a-zA-Z0-9_]/, '_')
            tuple(id, report)
        }

    //parse input reports
    if (params.report_type == 'kraken2' || params.report_type == 'bracken') {
        ch_parsed_reports = PROCESSING_KRAKENLIKE_REPORTS(ch_reports)
    }
    else if (params.report_type == 'metaphlan4') {
        ch_parsed_reports = PROCESSING_METAPHLAN4_REPORTS(ch_reports)
    }

    //compile parsed reports
    ch_compiled_summary = COMPILING_SUMMARIES(ch_parsed_reports.sample_summary.collect())
    ch_compiled_taxonomy = COMPILING_TAXONOMIES(ch_parsed_reports.taxonomy_table.collect())

    //generate final report
    template_file = file("${baseDir}/bin/metaxsfr_template.html")
    scifr_output = GENERATING_REPORT(
        ch_compiled_summary, 
        ch_compiled_taxonomy,
        template_file
    )
    //validate final report
    VALIDATE_REPORT(scifr_output.scifr_report)
}

//processes
process PROCESSING_KRAKENLIKE_REPORTS {
    tag "${id}"
    publishDir "${params.results_directory}/ParsedReports", mode: 'copy'
    
    input:
    tuple val(id), path(report)
    
    output:
    path("${id}_sample_summary.tsv"), emit: sample_summary
    path("${id}_taxonomy_table.tsv"), emit: taxonomy_table
    
    script:
    def report_type = params.report_type == 'bracken' ? 'bracken' : 'kraken2'
    """
    processKrakenBrackenReport.py \\
        --input_id ${id} \\
        --input_report ${report} \\
        --report_type '${report_type}' \\
        --taxids_map '${params.taxid_map}' \\
        --taxranks '${params.taxrank_list}' \\
        --out_summary '${id}_sample_summary.tsv' \\
        --out_taxonomy '${id}_taxonomy_table.tsv' \\
        --min_percent ${params.min_percent_abundance}
    """
}

process PROCESSING_METAPHLAN4_REPORTS {
    tag "${id}"
    publishDir "${params.results_directory}/ParsedReports", mode: 'copy'
    
    input:
    tuple val(id), path(report)
    
    output:
    path("${id}_sample_summary.tsv"), emit: sample_summary
    path("${id}_taxonomy_table.tsv"), emit: taxonomy_table
    
    script:
    """
    processMetaphlan4Report.py \\
        --input_id ${id} \\
        --input_report ${report} \\
        --report_type 'metaphlan4' \\
        --taxids_map '${params.taxid_map}' \\
        --taxranks '${params.taxrank_list}' \\
        --out_summary '${id}_sample_summary.tsv' \\
        --out_taxonomy '${id}_taxonomy_table.tsv' \\
        --min_percent ${params.min_percent_abundance}
    """
}

process COMPILING_SUMMARIES {
    publishDir "${params.results_directory}/TemplateInputs", mode: 'copy'

    input:
    path summaries

    output:
    path("summaryTable.tsv"), emit: sample_summary_tsv

    script:
    def summary_files = summaries.collect { it.toString() }.join(' ')
    """
    compileSampleSummaries.py --out "summaryTable.tsv" ${summary_files}
    """
}

process COMPILING_TAXONOMIES {
    publishDir "${params.results_directory}/TemplateInputs", mode: 'copy'
    
    input:
    path taxonomies
    
    output:
    path("taxonomyTable.tsv"), emit: sample_taxonomy_tsv
    
    script:
    def taxonomy_files = taxonomies.collect { "\"$it\"" }.join(' ')
    """
    #!/bin/bash
    echo ${taxonomy_files} | tr ' ' '\\n' > taxonomy_file_list.txt
    head -n 1 \$(head -n 1 taxonomy_file_list.txt) > taxonomyTable.tsv
    while read file; do tail -n +2 "\$file" >> taxonomyTable.tsv ; done < taxonomy_file_list.txt
    """
}

process GENERATING_REPORT {
    publishDir "${params.results_directory}/FinalReport", mode: "copy"

    input:
    path sample_summary_tsv
    path sample_taxonomy_tsv
    path template_file

    output:
    path ("metaxsfr.json"), optional: true, emit: scifr_input_json
    path ("metaxsfr.html"), emit: scifr_report

    script:
    """
    echo '${groovy.json.JsonOutput.toJson(params)}' > params.json
    generateMetaxsfr.py \\
        --summary_table ${sample_summary_tsv} \\
        --taxonomy_table ${sample_taxonomy_tsv} \\
        --template ${template_file} \\
        --out_html "metaxsfr.html" \\
        --out_json "metaxsfr.json" \\
        --params_data params.json \\
        --pipeline_version "${params.pipeline_version}"
    """
}

process VALIDATE_REPORT {
    publishDir "${params.results_directory}", mode: 'copy', pattern: "*.{html,html.gz}"
    
    input:
    path html_report
    
    output:
    path "metaxsfr.result.html", emit: validated_html
    path "metaxsfr.result.html.gz", emit: validated_html_gz
    
    script:
    """
    #!/usr/bin/env bash
    if awk '/@@METAXSFR@@INPUT@@START@@/ && /@@METAXSFR@@INPUT@@END@@/' ${html_report} | grep -q .; then
        echo "Validation passed: Report contains the expected JSON data block"
        cp -P ${html_report} metaxsfr.result.html
        gzip -4 -c metaxsfr.result.html > metaxsfr.result.html.gz
        echo "Final report generated: metaxsfr.result.html and metaxsfr.result.html.gz"
    else
        echo "ERROR: VALIDATION FAILED - Report is not valid" >&2
        echo "The complete JSON data block with markers @@METAXSFR@@INPUT@@START@@ and @@METAXSFR@@INPUT@@END@@ was not found." >&2
        echo "This may be caused by error during template mutation, e.g. due to compute resource limitations." >&2
        echo "You may also want to verify there's sufficient memory available for the report generation step." >&2
        exit 1
    fi
    """
}

workflow.onComplete {
    def duration = workflow.duration
    def status = workflow.success ? 'SUCCESS' : 'FAILED'
    
    //ansi colour codes
    def green = '\033[32m'
    def red = '\033[31m'
    def blue = '\033[34m'
    def yellow = '\033[33m'
    def cyan = '\033[36m'
    def bold = '\033[1m'
    def reset = '\033[0m'
    
    def statusColour = workflow.success ? green : red
    
    println """
${blue}Started at:${reset} ${workflow.start}
${blue}Completed at:${reset} ${workflow.complete}
${yellow}Duration:${reset} ${bold}${duration}${reset}
${blue}Status:${reset} ${statusColour}${bold}${status}${reset}
"""
}