# Numerical selections are explicit preparation work. Rendering reads only the RDS.
read_gic_payload <- function(folder,facts_path) {
 config <- jsonlite::fromJSON(facts_path,simplifyVector=FALSE)
 comp <- readr::read_csv(file.path(folder,'level_gic_composition.csv'),show_col_types=FALSE)
 metrics <- readr::read_csv(file.path(folder,'capture_metrics.csv'),show_col_types=FALSE)
 primary <- config$primary_endpoint
 b <- metrics[metrics$family=='reference' & metrics$endpoint==primary & metrics$budget_pct==5,]
 b <- b[match(c('baseline','hazard_only','exposure_only','no_inventory'),b$scenario),]
 w <- metrics[metrics$family=='one_at_a_time' & metrics$endpoint==primary & metrics$budget_pct==5,]
 stopifnot(nrow(b)==4L,nrow(w)==20L,sum(comp$n)==config$population,
           all(b$target_total==1451),all(w$target_total==1451),
           all(abs(b$quota-756.25)<1e-9),all(abs(w$quota-756.25)<1e-9))
 list(composition=comp,comparison=b,weights=w,config=config)
}
