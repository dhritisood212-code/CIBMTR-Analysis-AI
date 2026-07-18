#' Marginal-only fallback: reconstruct individual patient data from a published KM curve.
#'
#' Used only when a study provides published KM curves but no usable IPD in the public file -
#' a last resort for the reproduction panel, never the default path. Wraps `IPDfromKM`.
#'
#' @param curve_points data.frame(time, surv) read off the published curve.
#' @param at_risk_table data.frame(time, n_risk) numbers-at-risk under the curve.
#' @param total_events optional integer total events, if reported.
#' @return data.frame(time, event) reconstructed pseudo-IPD (event: 0 = censored, 1 = event).
#' @export
ipd_from_km <- function(curve_points, at_risk_table, total_events = NULL) {
  pre <- IPDfromKM::preprocess(
    dat = curve_points,
    trisk = at_risk_table$time,
    nrisk = at_risk_table$n_risk,
    totalpts = if (length(at_risk_table$n_risk)) at_risk_table$n_risk[[1]] else NULL
  )
  est <- IPDfromKM::getIPD(prep = pre, armID = 1, tot.events = total_events)
  ipd <- est$IPD
  data.frame(time = ipd$time, event = as.integer(ipd$status),
             stringsAsFactors = FALSE, row.names = NULL)
}
