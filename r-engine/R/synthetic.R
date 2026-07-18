#' Synthetic data generators for the test suite (and for demos).
#'
#' These make the unit tests self-contained and deterministic: the "truth" is the simulation
#' parameter, so tests assert that the estimators recover a known quantity rather than matching
#' a hardcoded fitted value.

#' Exponential survival data with a known group hazard ratio.
#'
#' Group B has hazard = hr * baseline. With administrative censoring at `tau`.
#' @return data.frame(time, event, group) with group in {"A","B"} (A = reference).
#' @export
synth_survival <- function(n = 4000, hr = 1.6, base_rate = 0.05, tau = 60, seed = 1) {
  set.seed(seed)
  group <- factor(sample(c("A", "B"), n, replace = TRUE), levels = c("A", "B"))
  rate <- base_rate * ifelse(group == "B", hr, 1)
  t_event <- stats::rexp(n, rate = rate)
  time <- pmin(t_event, tau)
  event <- as.integer(t_event <= tau)
  data.frame(time = time, event = event, group = group,
             stringsAsFactors = FALSE)
}

#' Two-cause competing-risks data with known cause-specific hazard ratios.
#'
#' Cause 1 (event of interest) and cause 2 (competing) each drawn from exponential
#' cause-specific hazards; the first to occur wins. Group B multiplies the cause-1 hazard by
#' `hr1`.  event_code: 0 censored, 1 cause-1, 2 cause-2.
#' @return data.frame(time, event_code, group)
#' @export
synth_competing <- function(n = 5000, h1 = 0.04, h2 = 0.03, hr1 = 1.5, tau = 60, seed = 2) {
  set.seed(seed)
  group <- factor(sample(c("A", "B"), n, replace = TRUE), levels = c("A", "B"))
  rate1 <- h1 * ifelse(group == "B", hr1, 1)
  t1 <- stats::rexp(n, rate = rate1)
  t2 <- stats::rexp(n, rate = h2)
  t_first <- pmin(t1, t2)
  cause <- ifelse(t1 <= t2, 1L, 2L)
  time <- pmin(t_first, tau)
  event_code <- ifelse(t_first <= tau, cause, 0L)
  data.frame(time = time, event_code = as.integer(event_code), group = group,
             stringsAsFactors = FALSE)
}
