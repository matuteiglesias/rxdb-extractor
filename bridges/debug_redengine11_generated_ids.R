#!/usr/bin/env Rscript

# Diagnostic probe for RedEngine 1.1 FREQ layout of generated and inherited IDs.
# Usage:
#   Rscript bridges/debug_redengine11_generated_ids.R /path/to/cpv2022.rxdb [RADIO]
#
# This does not write data. It runs one tiny HOGAR frequency and prints the raw
# Redatam table representation before the JSON bridge canonicalizes it.

suppressPackageStartupMessages(library(redatamx))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop("usage: debug_redengine11_generated_ids.R DATABASE [RADIO]")
}

database <- args[[1]]
radio <- if (length(args) >= 2L) args[[2]] else "061120902"

spc <- paste(
  "RUNDEF RXDB_ROWS",
  sprintf('SELECTION RADIO == "%s"', radio),
  "DEFINE VIVIENDA.XVID AS NUMBER RADIO",
  "DEFINE HOGAR.XHID AS NUMBER RADIO",
  "DEFINE HOGAR.XVID AS VIVIENDA.XVID",
  "FREQ HOGAR.XHID BY HOGAR.XVID",
  sep = "\n"
)

cat("=== runtime ===\n")
cat("redatamx:", as.character(utils::packageVersion("redatamx")), "\n")
cat("RedEngine:", as.character(redatam_version()), "\n\n")
cat("=== SPC ===\n")
cat(spc, "\n\n")

dic <- redatam_open(database)
on.exit(redatam_close(dic), add = TRUE)

outputs <- redatam_internal_query(dic, spc)
if (length(outputs) != 1L) {
  stop(sprintf("expected one output; got %d", length(outputs)))
}
raw <- outputs[[1]]

cat("=== attributes ===\n")
print(attributes(raw)[c("redatam.table.type", "redatam.table.name", "redatam.table.vars")])
cat("\n=== shape ===\n")
cat("rows:", nrow(raw), "cols:", ncol(raw), "\n")
cat("column names:\n")
print(names(raw))
cat("\ncolumn classes:\n")
print(vapply(raw, function(x) paste(class(x), collapse = "/"), character(1)))
cat("\n=== first rows (raw) ===\n")
print(utils::head(raw, 12L))
cat("\n=== first rows as dput ===\n")
dput(utils::head(raw, 6L))
cat("\n=== per-dimension triples ===\n")
if (ncol(raw) >= 7L) {
  cat("HOGAR.XHID triple (columns 1:3):\n")
  print(utils::head(raw[, 1:3, drop = FALSE], 12L))
  cat("\nHOGAR.XVID triple (columns 4:6):\n")
  print(utils::head(raw[, 4:6, drop = FALSE], 12L))
  cat("\ncount column (7):\n")
  print(utils::head(raw[, 7, drop = FALSE], 12L))
}
