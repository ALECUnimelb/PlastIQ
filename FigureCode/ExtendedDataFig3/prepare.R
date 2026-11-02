#!/usr/bin/env Rscript
source('FigureCode/_shared/managed.R')
status <- system2(file.path(repo_root,'.venv/bin/python'),
 c(shQuote(file.path(module_dir,'prepare.py')),shQuote(output_dir)))
stopifnot(status==0L)
source(file.path(module_dir,'setup.R'))
save_plot_data(read_gic_payload(file.path(output_dir,'source_data'),file.path(output_dir,'caption_facts.json')))
