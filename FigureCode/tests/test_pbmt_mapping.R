# Regression: source evidence stays raw, both comparison axes map, missing != 0.
source('FigureCode/_shared/validation.R')
source('FigureCode/Fig2/style.R')
source('FigureCode/Fig2/data.R')
config <- jsonlite::fromJSON('FigureCode/Fig2/figure.yml',simplifyVector=FALSE)
pairs <- expand.grid(independent=c(0,0.5,1,2),curated=c(0,0.25,0.5,1,2))
pairs <- rbind(pairs,c(NA,0.25),c(0.5,NA),c(NA,NA))
keys <- sprintf('compound-%02d',seq_len(nrow(pairs)))
raw_final <- ifelse(is.na(pairs$independent),pairs$curated,pairs$independent)
map <- function(x) {x[!is.na(x)&x %in% c(0.25,0.5)]<-1;x}
db <- DBI::dbConnect(RSQLite::SQLite(),':memory:')
raw <- data.frame(inchikey=keys)
for (item in pbmt_dimension_schema) {
  raw[[item$evidence_field]] <- vapply(seq_len(nrow(pairs)),function(i) {
    jsonlite::toJSON(list(qsar_toxicity=list(selected=list(score=pairs$independent[i])),
      qsar_bcf_models=list(selected=list(bioaccumulation_score=pairs$independent[i])),
      curated_db=list(selected=list(score=pairs$curated[i])),
      final_selection=list(independent_candidate=list(score=pairs$independent[i]),selected=list(score=raw_final[i])),
      final_mobility=list(independent_score=pairs$independent[i],score=raw_final[i])),auto_unbox=TRUE,na='null')
  },character(1))
}
DBI::dbWriteTable(db,'current_compounds',raw)
read_current <- function(fields) {
  frame <- data.frame(Inchikey_std=keys)
  for (item in pbmt_dimension_schema) {
    frame[[item$final_score_field]] <- if(three_level_pbmt) map(raw_final) else raw_final
    frame[[item$basis_field]] <- 'preserved_source'
  }
  frame
}
snapshot <- list(row_count=nrow(pairs))
for (mode in c(FALSE,TRUE,FALSE)) {
  three_level_pbmt <- mode
  configure_pbmt_scale()
  input <- read_pbmt_concordance_input(snapshot,config)
  tables <- prepare_pbmt_source_data(input,snapshot,config)$source_data
  stopifnot(nrow(input)==4*nrow(pairs),all(tables$coverage_metrics$shared_count==20),
            all(tables$agreement_metrics$shared_n==20),
            identical(input$plastchem_score_raw,rep(pairs$curated,4)),
            identical(input$computational_score_raw,rep(pairs$independent,4)),
            sum(is.na(input$plastchem_score))==8,
            sum(is.na(input$computational_score))==8,
            nrow(tables$score_pair_matrix)==4*if(mode) 9 else 20,
            nrow(tables$agreement_band_summary)==4*if(mode) 3 else 4)
  if (mode) stopifnot(identical(input$plastchem_score,map(input$plastchem_score_raw)),
                      identical(input$computational_score,map(input$computational_score_raw)),
                      all(input$stored_final_score==input$selected_final_score,na.rm=TRUE))
}
three_level_pbmt <- TRUE;configure_pbmt_scale()
stopifnot(inherits(try(pbmt_agreement_band(c(0,0.5),config),silent=TRUE),'try-error'))
stopifnot(identical(names(pbmt_named_palette(config,'agreement_palette')),pbmt_agreement_levels))
DBI::dbExecute(db,"UPDATE current_compounds SET Toxicity_evidence=json_set(Toxicity_evidence,'$.curated_db.selected.score',0.3) WHERE inchikey='compound-01'")
stopifnot(inherits(try(read_pbmt_concordance_input(snapshot,config),silent=TRUE),'try-error'))
DBI::dbDisconnect(db)
cat('PBMT source preservation, mapping, legacy mode, missingness and count conservation passed.\n')

source('FigureCode/Fig3/panels/exposure_component_profiles/data.R')
three_level_exposure <- TRUE
profiles <- build_exposure_profiles(list(inventory=c(0,1,2,NA)))$profiles
stopifnot(!'Low (0.5)' %in% profiles$score_class, sum(profiles$compound_count)==4)
stopifnot(inherits(try(build_exposure_profiles(list(inventory=c(0,0.5,1))),silent=TRUE),'try-error'))
three_level_exposure <- FALSE
profiles <- build_exposure_profiles(list(inventory=c(0,0.5,1,2,NA)))$profiles
stopifnot(profiles$compound_count[profiles$score_class=='Low (0.5)']==1)
cat('Exposure rule profiles reject fractional scores and retain legacy rendering support.\n')
