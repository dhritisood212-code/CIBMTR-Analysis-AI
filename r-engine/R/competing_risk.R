#' Canonical competing-risk endpoints (relapse / NRM / GVHD / engraftment).
#'
#' `event_code` is the multi-state integer column from analytic.parquet:
#'   0 = censored, 1 = event of interest, 2.. = competing events.
#' `codes` names them, e.g. list(censored = 0, nrm = 1, relapse = 2). The event of interest is
#' the code named first after `censored` unless a `cause` argument is given.
#'
#' CIF point estimates use the Aalen-Johansen estimator via `cmprsk::cuminc`; Fine-Gray uses
#' `survival::finegray`; cause-specific Cox treats competing events as censored.

#' @keywords internal
.cause_value <- function(codes, cause = NULL) {
  if (!is.null(cause)) return(codes[[cause]])
  nm <- setdiff(names(codes), "censored")
  codes[[nm[[1]]]]
}

#' @keywords internal
.cencode <- function(codes) if ("censored" %in% names(codes)) codes[["censored"]] else 0

#' Cumulative incidence function (Aalen-Johansen) with point estimates + 95% CIs.
#'
#' @param at_times optional numeric vector of times to report; NULL = all event times.
#' @return data.frame(cause, time, cif, ci_low, ci_high)
#' @export
cif <- function(data, time, event_code, codes, at_times = NULL) {
  ft <- data[[time]]
  fs <- data[[event_code]]
  ci <- cmprsk::cuminc(ftime = ft, fstatus = fs, cencode = .cencode(codes))
  # Names of estimate groups look like "1 <cause>"; keep only cause-of-interest style entries.
  cause_labels <- setdiff(names(codes), "censored")
  code_by_label <- vapply(cause_labels, function(l) as.character(codes[[l]]), character(1))
  out <- list()
  for (nm in names(ci)) {
    if (identical(nm, "Tests")) next
    est <- ci[[nm]]
    # cmprsk names elements "<group> <cause>"; the cause is the LAST token.
    toks <- strsplit(nm, " ")[[1]]
    cause_code <- toks[[length(toks)]]                   # "1", "2", ...
    label <- names(code_by_label)[match(cause_code, code_by_label)]
    if (is.na(label)) label <- cause_code
    if (is.null(at_times)) {
      tt <- est$time; ss <- est$est; vv <- est$var
    } else {
      tp <- cmprsk::timepoints(ci[nm], at_times)
      tt <- at_times
      ss <- as.numeric(tp$est[1, ])
      vv <- as.numeric(tp$var[1, ])
    }
    se <- sqrt(vv)
    out[[nm]] <- data.frame(
      cause   = label,
      time    = tt,
      cif     = ss,
      ci_low  = pmax(0, ss - 1.96 * se),
      ci_high = pmin(1, ss + 1.96 * se),
      stringsAsFactors = FALSE, row.names = NULL
    )
  }
  do.call(rbind, out)
}

#' Gray's test for equality of cause-specific CIFs across groups.
#'
#' @return data.frame(cause, stat, df, p_value)
#' @export
grays_test <- function(data, time, event_code, group, codes) {
  ci <- cmprsk::cuminc(ftime = data[[time]], fstatus = data[[event_code]],
                       group = data[[group]], cencode = .cencode(codes))
  tests <- as.data.frame(ci$Tests)
  data.frame(
    cause   = rownames(tests),
    stat    = tests[["stat"]],
    df      = tests[["df"]],
    p_value = tests[["pv"]],
    stringsAsFactors = FALSE, row.names = NULL
  )
}

#' Fine-Gray subdistribution-hazard model for one cause.
#'
#' @param cause name of the cause of interest in `codes` (default: first non-censored).
#' @return data.frame(term, shr, ci_low, ci_high, p_value)  (shr = subdistribution HR)
#' @export
finegray_model <- function(data, time, event_code, covariates, codes, cause = NULL) {
  cval <- .cause_value(codes, cause)
  # Build a multi-state event factor: "censor" + one level per non-censor code.
  lev <- setdiff(names(codes), "censored")
  fac <- factor(rep("censor", nrow(data)), levels = c("censor", lev))
  for (l in lev) fac[data[[event_code]] == codes[[l]]] <- l
  d <- data[, covariates, drop = FALSE]
  d$.status <- fac
  d$.time <- data[[time]]
  cause_label <- names(codes)[match(cval, unlist(codes))]
  rhs <- paste(sprintf("`%s`", covariates), collapse = " + ")
  prep_f <- stats::as.formula(sprintf("survival::Surv(.time, .status) ~ %s", rhs))
  fg <- survival::finegray(prep_f, data = d, etype = cause_label)
  f <- stats::as.formula(sprintf(
    "survival::Surv(fgstart, fgstop, fgstatus) ~ %s", rhs))
  fit <- survival::coxph(f, data = fg, weights = fg$fgwt)
  tt <- .tidy_cox(fit)
  names(tt)[names(tt) == "hr"] <- "shr"
  tt
}

#' Cause-specific Cox model (competing events treated as censored).
#'
#' @param cause name of the cause of interest in `codes`.
#' @return data.frame(term, hr, ci_low, ci_high, p_value)
#' @export
cause_specific_cox <- function(data, time, event_code, cause, covariates) {
  # NB: pass `codes` implicitly via `cause` being the numeric code OR resolve upstream.
  cval <- if (is.numeric(cause)) cause else stop("pass the numeric cause code to cause_specific_cox")
  d <- data
  d$.cs_event <- as.integer(data[[event_code]] == cval)   # competing + censored both 0
  cox_ph(d, time = time, event = ".cs_event", covariates = covariates)
}
