#!/usr/bin/env Rscript

# Reference protocol-v1 bridge for the CRAN redatamx package.
#
# STATUS: implementation candidate; not yet qualified against the user's local
# RedEngine 1.3.0 Census 2022 runtime. It deliberately uses only supported
# redatamx APIs and never patches RedEngine or uses TABLE VIEW.

suppressPackageStartupMessages(library(redatamx))
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("jsonlite is required by the rxdb bridge")
}

PROTOCOL_VERSION <- "1"

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
}

nonempty_or_null <- function(x) {
  if (length(x) == 0L || is.na(x) || !nzchar(as.character(x))) return(NULL)
  as.character(x)
}

read_request <- function() {
  input <- paste(readLines(file("stdin"), warn = FALSE), collapse = "\n")
  if (!nzchar(input)) stop("empty bridge request")
  request <- jsonlite::fromJSON(input, simplifyVector = FALSE)
  if (!is.list(request)) stop("bridge request must be a JSON object")
  if (!identical(as.character(request$protocol_version), PROTOCOL_VERSION)) {
    stop("unsupported protocol version")
  }
  request
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

inspect_database <- function(database) {
  dic <- redatam_open(database)
  on.exit(redatam_close(dic), add = TRUE)

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
      # redatamx 1.3's public redatam_entities() result does not expose parent
      # relationships. Portable adapter profiles can supply a validated parent_map;
      # a future bridge may fill this field from a stronger native metadata API.
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

execute_record_plan <- function(database, plan) {
  if (is.null(plan$spc) || is.null(plan$dimension_fields) || is.null(plan$own_id)) {
    stop("record plan is missing spc/dimension_fields/own_id")
  }
  dimensions <- unlist(plan$dimension_fields, use.names = FALSE)
  if (!length(dimensions)) stop("record plan has no dimensions")

  dic <- redatam_open(database)
  on.exit(redatam_close(dic), add = TRUE)

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
  # one final count column. Preserve the raw value + mask here and let the Python
  # core decide which cells are records.
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

handle_request <- function(request) {
  action <- as.character(request$action)
  if (identical(action, "capabilities")) {
    return(capabilities_result())
  }
  if (identical(action, "inspect")) {
    if (is.null(request$database)) stop("inspect requires database")
    return(inspect_database(as.character(request$database)))
  }
  if (identical(action, "execute_record_plan")) {
    if (is.null(request$database) || is.null(request$plan)) {
      stop("execute_record_plan requires database and plan")
    }
    return(execute_record_plan(as.character(request$database), request$plan))
  }
  stop(sprintf("unsupported bridge action: %s", action))
}

tryCatch({
  request <- read_request()
  respond(TRUE, handle_request(request))
}, error = function(e) {
  respond(FALSE, error = conditionMessage(e))
})
