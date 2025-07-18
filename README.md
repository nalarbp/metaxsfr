# METAXSFR
METAXSFR (Metagenome Taxonomic Explorer in a Single-File Report) is a Nextflow pipeline that processes taxonomic profiling reports from various metagenomics tools (Kraken2, Bracken, MetaPhlAn4) and generates an single HTML file for interactive visualisation and analysis.

## Example report
Try and download example of interactive METAXSFR report file from [https://scifr.fordelab.com/metaxsfr](https://scifr.fordelab.com/metaxsfr)

## Features
- **Multiple tool support**: Kraken2, Bracken, and MetaPhlAn4 reports
- **Database flexibility**: NCBI and GTDB taxonomic classifications
- **Batch processing**: Handle multiple samples efficiently using nextflow
- **Interactive reports**: Single self-contained HTML output built using [SCIFR](https://scifr.fordelab.com/)

## Installation

### Prerequisites
- Conda or Mamba (https://conda-forge.org/download/)
- Git (https://git-scm.com/downloads)

### Quick install
1. Clone this repository:
```bash
git clone https://github.com/nalarbp/metaxsfr.git
cd metaxsfr
```

2. Create and activate the conda environment:
```bash
mamba env create -f environment.yml
mamba activate metaxsfr
```

3. Install METAXSFR:
```bash
pip install -e .
metaxsfr -h #to confirm its installed properly
```

### How to update
1. Navigate to your Metaxsfr directory and activate the environment:
```bash
cd metaxsfr
mamba activate metaxsfr
```

2. Pull the latest changes and update from the repository:
```bash
git pull origin main
pip install -e . --force-reinstall
```

## Basic usage
This repository contains input file examples located in [sample/](sample/) directory for you to try metaxsfr. Run the following command:

```bash
ls sample/ #to see example of required input files
metaxsfr -r './sample/bracken/*.txt' -t bracken -d gtdb -o results
metaxsfr -r './sample/bracken/SRR23994336.breport.txt,./sample/bracken/SRR23994337.breport.txt' -t bracken -d gtdb -o results #use comma to separate multiple reports
```

### How to update

1. Navigate to your BLITSFR directory and activate the environment:
```bash
cd metaxsfr
mamba activate metaxsfr
```

2. Pull the latest changes and update from the repository:
```bash
git pull origin main
pip install -e . --force-reinstall
### Required parameters

- `-r, --reports`: Path to report file(s). Supports wildcards (must be quoted)
- `-t, --report-type`: Type of report (`kraken2`, `bracken`, `metaphlan4`)
- `-d, --database`: Taxonomic database (`ncbi`, `gtdb`)

### Optional parameters

- `-o, --output`: Output directory (default: `results`)
- `--min-abundance`: Minimum abundance threshold in % (default: `0.01`)
- `--executor`: Nextflow executor (default: `local`)
- `--resume`: Resume previous run
- `-c, --config`: Nextflow configuration file
- `--nf-args`: Additional Nextflow arguments

### Examples

#### Process MetaPhlAn4 reports
```bash
metaxsfr -r './sample/metaphlan4/*.txt' -t metaphlan4 -d ncbi -o metaphlan4_results
```

#### Process Kraken2 reports with GTDB database
```bash
metaxsfr -r './sample/kraken2/*.txt' -t kraken2 -d gtdb -o kraken2_results --min-abundance 0.01
```

#### Process single sample
```bash
metaxsfr -r './sample/metaphlan4/SRR23994343.metaphlan4.txt' -t metaphlan4 -d ncbi -o SRR23994343_results
```

#### Resume previous run
```bash
metaxsfr -r './sample/kraken2/*.txt' -t kraken2 -d gtdb -o kraken2_results --resume
```

## Input file formats

Example of input files for Kraken2, Bracken, and  MetaPhlAn4 reports are available in [sample/](sample/) directory.

## Output structure

```
results/
├── ParsedReports/ #Individual sample processing results
│   ├── sample1_sample_summary.tsv
│   ├── sample1_taxonomy_table.tsv
│   └── ...
├── TemplateInputs/ #Compiled data for report generation
│   ├── summaryTable.tsv
│   └── taxonomyTable.tsv
├── FinalReport/ #Generated reports
│   ├── metaxsfr.html
│   └── metaxsfr.json
├── metaxsfr.result.html #Final report
└── metaxsfr.result.html.gz #Compressed final report
```

## Citation
If you use METAXSFR in your research, please cite:

```
[Coming soon]
```

## License
This project is licensed under the Apache 2.0 - see the [LICENSE](LICENSE) for details.

## Documentation
[TODO] Add more detailed documentation on [docs/](docs/) dir.

## Support
- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/nalarbp/metaxsfr/issues)
- **Contact**: b.permana@uq.edu.au

## Acknowledgements
- Nextflow devs and community
- Kraken2, Bracken, and MetaPhlAn4 authors 
- NCBI and GTDB teams
- ReactJS devs and community 
- Core JS libraries (Jotai.js, Nivo.js, AgGrid.js, D3.js) devs and community

---

**Version**: v0.1.0 