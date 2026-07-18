#' Canonical composite-survival endpoints (OS / DFS / PFS / GRFS).
#'
#' These wrap the `survival` package and return tidy data.frames the Analyst writes to
#' results/*.csv and reads into agent-results.yaml. Every function is deterministic given its
#' inputs and covered by exact-match unit tests in tests/testthat/.
#'
#' Event columns for composite-survival endpoints are 0 = censored, 1 = event (per the
#' analytic.parquet contract).

#' Build a tidy hazard-ratio table from a fitted coxph model.
#' @keywords internal
.tidy_cox <- function(fit) {
  s <- summary(fit)
  coefs <- s$coefficients          # rows: term; cols incl. coef, Pr(>|z|)
  ci <- s$conf.int                 # cols: exp(coef), lower .95, upper .95
  data.frame(
    term    = rownames(coefs),
    hr      = unname(ci[, "exp(coef)"]),
    ci_low  = unname(ci[, "lower .95"]),
    ci_high = unname(ci[, "upper .95"]),
    p_value = unname(coefs[, "Pr(>|z|)"]),
    stringsAsFactors = FALSE,
    row.names = NULL
  )
}

#' Apply reference levels to factor covariates before modeling.
#' @keywords internal
.apply_refs <- function(data, ref) {
  for (v in names(ref)) {
    if (v %in% names(data)) {
      data[[v]] <- stats::relevel(as.factor(data[[v]]), ref = ref[[v]])
    }
  }
  data
}

#' Kaplan-Meier fit with a median-survival table.
#'
#' @param data data.frame.
#' @param time,event column names (event: 0 = censored, 1 = event).
#' @param strata optional grouping column name; NULL = overall.
#' @return list(fit = survfit object,
#'              medians = data.frame(strata, median, ci_low, ci_high))
#' @export
km_fit <- function(data, time, event, strata = NULL) {
  rhs <- if (is.null(strata)) "1" else sprintf("`%s`", strata)
  f <- stats::as.formula(sprintf("survival::Surv(`%s`, `%s`) ~ %s", time, event, rhs))
  fit <- survival::survfit(f, data = data)
  tab <- summary(fit)$table
  if (is.null(dim(tab))) tab <- t(as.matrix(tab))   # single-stratum -> vector
  medians <- data.frame(
    strata  = if (is.null(strata)) "overall" else sub(".*=", "", rownames(tab)),
    median  = unname(tab[, "median"]),
    ci_low  = unname(tab[, "0.95LCL"]),
    ci_high = unname(tab[, "0.95UCL"]),
    stringsAsFactors = FALSE, row.names = NULL
  )
  list(fit = fit, medians = medians)
}

#' Log-rank test across groups.
#'
#' @return list(chisq, df, p_value)
#' @export
logrank_test <- function(data, time, event, group) {
  f <- stats::as.formula(sprintf("survival::Surv(`%s`, `%s`) ~ `%s`", time, event, group))
  sd <- survival::survdiff(f, data = data)
  df <- length(sd$n) - 1L
  p <- stats::pchisq(sd$chisq, df = df, lower.tail = FALSE)
  list(chisq = unname(sd$chisq), df = df, p_value = p)
}

#' Cox proportional-hazards model with a tidy HR table.
#'
#' @param covariates character vector of column names.
#' @param ref named list mapping factor covariate -> reference level.
#' @return data.frame(term, hr, ci_low, ci_high, p_value)
#' @export
cox_ph <- function(data, time, event, covariates, ref = list()) {
  data <- .apply_refs(data, ref)
  rhs <- paste(sprintf("`%s`", covariates), collapse = " + ")
  f <- stats::as.formula(sprintf("survival::Surv(`%s`, `%s`) ~ %s", time, event, rhs))
  fit <- survival::coxph(f, data = data)
  .tidy_cox(fit)
}
