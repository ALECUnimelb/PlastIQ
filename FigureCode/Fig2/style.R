pbmt_dimension_levels <- c(
  "Toxicity", "Bioaccumulation", "Mobility", "Persistence"
)

pbmt_coverage_levels <- c(
  "Independent only", "Shared", "PlastChem only", "Neither"
)

pbmt_agreement_levels <- c(
  "Exact", "Near non-exact (<=0.5)", "Moderate (0.5-1)", "Large (>1)"
)

pbmt_plastchem_score_levels <- c(0, 0.25, 0.5, 1, 2)
pbmt_computational_score_levels <- c(0, 0.5, 1, 2)

# Use the dataset's explicit policy, never infer it from observed score values.
configure_pbmt_scale <- function() {
  if (isTRUE(three_level_pbmt)) {
    pbmt_plastchem_score_levels <<- c(0,1,2)
    pbmt_computational_score_levels <<- c(0,1,2)
    pbmt_agreement_levels <<- c('Exact','One-level difference','Two-level difference')
  } else {
    pbmt_plastchem_score_levels <<- c(0,0.25,0.5,1,2)
    pbmt_computational_score_levels <<- c(0,0.5,1,2)
    pbmt_agreement_levels <<- c('Exact','Near non-exact (<=0.5)','Moderate (0.5-1)','Large (>1)')
  }
}

pbmt_named_palette <- function(config, field) {
  values <- unlist(config[[field]], use.names = TRUE)
  if (identical(field,'agreement_palette') && isTRUE(three_level_pbmt)) {
    values <- setNames(unname(values[c('Exact','Moderate (0.5-1)','Large (>1)')]),pbmt_agreement_levels)
  }
  stats::setNames(as.character(values), names(values))
}

pbmt_score_label <- function(value) {
  formatC(as.numeric(value), format = "fg", digits = 3, drop0trailing = TRUE)
}

pbmt_theme <- function(base_size = 7) {
  theme_manuscript(base_size = base_size) +
    ggplot2::theme(
      legend.title = ggplot2::element_blank(),
      legend.key.height = grid::unit(3.3, "mm"),
      legend.key.width = grid::unit(4.5, "mm"),
      legend.margin = ggplot2::margin(0, 0, 0, 0),
      plot.title = ggplot2::element_text(
        face = "bold", size = base_size + 1.2, hjust = 0,
        margin = ggplot2::margin(b = 2)
      ),
      plot.subtitle = ggplot2::element_text(
        colour = "#555555", size = base_size - 0.2, hjust = 0,
        margin = ggplot2::margin(b = 4)
      ),
      plot.margin = ggplot2::margin(4, 5, 4, 6)
    )
}

pbmt_dimension_config <- function(config, dimension_id) {
  matches <- Filter(
    function(item) identical(item$dimension_id, dimension_id),
    config$dimensions
  )
  if (length(matches) != 1L) {
    stop("Unknown PBMT dimension ID: ", dimension_id, call. = FALSE)
  }
  matches[[1]]
}
