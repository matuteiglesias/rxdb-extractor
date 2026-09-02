#!/usr/bin/env Rscript

# Reference protocol-v1 bridge for the CRAN redatamx package.
#
# The one-shot mode remains the simplest compatibility boundary.  Passing
# ``--serve`` switches to a JSON-lines loop that keeps R/redatamx and opened
# databases alive across requests; this is intended for national extraction.
# It deliberately uses only supported redatamx APIs and never patches RedEngine
# or uses TABLE VIEW.

suppressPackageStartupMessages(library(redatamx))
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("jsonlite is required by the rxdb bridge")
}

PROTOCOL_VERSION <- "1"
.database_cache <- new.env(parent = emptyenv())

respond <- function(ok, result = NULL, error = NULL) {
  payload <- list(protocol_version = PROTOCOL_VERSION, ok = ok)
  if (ok) payload$result <- result else payload$error <- as.character(error)
  cat(jsonlite::toJSON(
    payload,
    auto_unbox = TRUE,
    null = "null",
    na = "null",
    dataframe = "rows",
    digits = NA
  ))
  cat("\n")
  flush(stdout())
}

nonempty_or_null <- function(x) {
  if (length(x) == 0L || is.na(x) || !nzchar(as.character(x))) return(NULL)
  as.character(x)
}

parse_request <- function(input) {
  if (!nzchar(input)) stop("empty bridge request")
  request <- jsonlite::fromJSON(input, simplifyVector = FALSE)
  if (!is.list(request)) stop("bridge request must be a JSON object")
  if (!identical(as.character(request$protocol_version), PROTOCOL_VERSION)) {
    stop("unsupported protocol version")
  }
  request
}

read_request <- function() {
  input <- paste(readLines(file("stdin"), warn = FALSE), collapse = "\n")
  parse_request(input)
}

engine_version_tuple <- function(version) {
  match <- regmatches(version, regexpr("[0-9]+\\.[0-9]+\\.[0-9]+", version))
  if (!length(match) || !nzchar(match)) return(c(0L, 0L, 0L))
  as.integer(strsplit(match, "\\.")[[1]])
}

version_at_least <- function(version, target) {
  lhs <- engine_version_tuple(version)
  rhs <- as.integer(strsplit(target, "\\.")[[1]])
  for (i in seq_along(rhs)) {
    if (lhs[[i]] > rhs[[i]]) return(TRUE)
    if (lhs[[i]] < rhs[[i]]) return(FALSE)
  }
  TRUE
}

capabilities_result <- function() {
  version <- redatam_version()
  list(
    redengine_version = as.character(version),
    redatamx_version = as.character(utils::packageVersion("redatamx")),
    selection = TRUE,
    number = TRUE,
    inherited_define = TRUE,
    freq = TRUE,
    cmpcode = version_at_least(version, "1.2.0"),
    # TABLE VIEW is intentionally not a bridge capability. It is unavailable in
    # RedEngine 1.3 and is not part of the production extraction design.
    table_view = FALSE
  )
}

.database_key <- function(database) {
  normalizePath(database, mustWork = FALSE)
}

get_database <- function(database, persistent = FALSE) {
  if (!persistent) return(redatam_open(database))
  key <- .database_key(database)
  if (!exists(key, envir = .database_cache, inherits = FALSE)) {
    assign(key, redatam_open(database), envir = .database_cache)
  }
  get(key, envir = .database_cache, inherits = FALSE)
}

close_cached_databases <- function() {
  keys <- ls(envir = .database_cache, all.names = TRUE)
  for (key in keys) {
    dic <- get(key, envir = .database_cache, inherits = FALSE)
    try(redatam_close(dic), silent = TRUE)
    rm(list = key, envir = .database_cache)
  }
  invisible(NULL)
}

inspect_database <- function(database, persistent = FALSE) {
  dic <- get_database(database, persistent = persistent)
  if (!persistent) on.exit(redatam_close(dic), add = TRUE)

  entities <- redatam_entities(dic)
  result_entities <- lapply(seq_len(nrow(entities)), function(i) {
    entity_name <- as.character(entities$name[[i]])
    variables <- redatam_variables(dic, entity_name)
    result_variables <- lapply(seq_len(nrow(variables)), function(j) {
      list(
        name = as.character(variables$name[[j]]),
        alias = nonempty_or_null(variables$alias[[j]]),
        label = nonempty_or_null(variables$label[[j]]),
        type_name = nonempty_or_null(variables$typeName[[j]])
      )
    })
    list(
      name = entity_name,
      alias = NULL,
      # redatamx's public entity inventory is flat and does not expose parent
      # relationships. Portable adapter profiles supply the validated parent_map.
      parent = NULL,
      selectable = isTRUE(as.logical(entities$selectable[[i]])),
      variables = result_variables
    )
  })

  list(
    entities = result_entities,
    metadata = list(
      database = normalizePath(database, mustWork = FALSE),
      redatamx_version = as.character(utils::packageVersion("redatamx")),
      redengine_version = as.character(redatam_version()),
      hierarchy_complete = FALSE
    )
  )
}

execute_record_plan <- function(database, plan, persistent = FALSE) {
  if (is.null(plan$spc) || is.null(plan$dimension_fields) || is.null(plan$own_id)) {
    stop("record plan is missing spc/dimension_fields/own_id")
  }
  dimensions <- unlist(plan$dimension_fields, use.names = FALSE)
  if (!length(dimensions)) stop("record plan has no dimensions")

  dic <- get_database(database, persistent = persistent)
  if (!persistent) on.exit(redatam_close(dic), add = TRUE)

  outputs <- withCallingHandlers(
    redatam_internal_query(dic, as.character(plan$spc)),
    warning = function(w) stop(paste("RedEngine warning:", conditionMessage(w)))
  )
  if (length(outputs) != 1L) {
    stop(sprintf("expected exactly one FREQ output, received %d", length(outputs)))
  }
  raw <- outputs[[1]]
  if (!is.data.frame(raw)) stop("RedEngine output is not a data frame")
  table_type <- attr(raw, "redatam.table.type")
  if (!is.null(table_type) && !identical(as.character(table_type), "table")) {
    stop(sprintf("expected table output, received %s", as.character(table_type)))
  }

  # redatamx's own redatam_query() treats each table dimension as a three-column
  # group and uses every third column as the total/NA/MV mask. FREQ then appends
  # one final count column. Preserve raw value + mask and let Python normalize.
  expected_cols <- length(dimensions) * 3L + 1L
  if (ncol(raw) != expected_cols) {
    stop(sprintf(
      "unexpected FREQ shape: %d dimensions imply %d columns, got %d",
      length(dimensions), expected_cols, ncol(raw)
    ))
  }

  canonical <- list()
  mask_fields <- list()
  for (i in seq_along(dimensions)) {
    field <- as.character(dimensions[[i]])
    value_index <- (i - 1L) * 3L + 1L
    mask_index <- i * 3L
    mask_field <- paste0(field, "__mask")
    canonical[[field]] <- raw[[value_index]]
    canonical[[mask_field]] <- raw[[mask_index]]
    mask_fields[[field]] <- mask_field
  }
  canonical$count <- raw[[expected_cols]]
  rows <- as.data.frame(canonical, check.names = FALSE, stringsAsFactors = FALSE)

  list(rows = rows, mask_fields = mask_fields, count_field = "count")
}

handle_request <- function(request, persistent = FALSE) {
  action <- as.character(request$action)
  if (identical(action, "capabilities")) {
    return(capabilities_result())
  }
  if (identical(action, "inspect")) {
    if (is.null(request$database)) stop("inspect requires database")
    return(inspect_database(as.character(request$database), persistent = persistent))
  }
  if (identical(action, "execute_record_plan")) {
    if (is.null(request$database) || is.null(request$plan)) {
      stop("execute_record_plan requires database and plan")
    }
    return(execute_record_plan(
      as.character(request$database), request$plan, persistent = persistent
    ))
  }
  stop(sprintf("unsupported bridge action: %s", action))
}

serve_loop <- function() {
  on.exit(close_cached_databases(), add = TRUE)
  input <- file("stdin", open = "r")
  on.exit(close(input), add = TRUE)
  repeat {
    line <- readLines(input, n = 1L, warn = FALSE)
    if (!length(line)) break
    if (!nzchar(trimws(line))) next
    tryCatch({
      request <- parse_request(line)
      respond(TRUE, handle_request(request, persistent = TRUE))
    }, error = function(e) {
      respond(FALSE, error = conditionMessage(e))
    })
  }
  invisible(NULL)
}

args <- commandArgs(trailingOnly = TRUE)
if ("--serve" %in% args) {
  serve_loop()
} else {
  tryCatch({
    request <- read_request()
    respond(TRUE, handle_request(request, persistent = FALSE))
  }, error = function(e) {
    respond(FALSE, error = conditionMessage(e))
  })
}
