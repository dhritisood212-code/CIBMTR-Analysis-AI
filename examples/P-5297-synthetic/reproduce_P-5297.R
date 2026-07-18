# =============================================================================================
# reproduce_P-5297.R  --  "Age no bar" (MM18-03a / P-5297) reproduction artifact
#
# This is the GOLDEN reference artifact: the clean, rerunnable R script the Analyst agent is
# expected to produce. It is what a biostatistician actually reads, reruns, and edits.
#
#   * Deterministic (seed set), self-contained, sectioned, commented.
#   * Reads the analytic table via the sidecar ROLES (analytic.schema.yaml), never hardcoded
#     column names, so the same script serves any study with the same schema.
#   * Every number it reports is computed here and written to results/ and agent-results.yaml;
#     nothing is transcribed by hand.
#   * Estimator is chosen by the estimand: composite-survival -> KM + Cox; competing-risk ->
#     cumulative incidence + cause-specific Cox (the estimator the paper used for these).
#
# NOTE: In this example the input is a SYNTHETIC, schema-faithful stand-in for the T&C-gated
# public file (see make_synthetic_data.py). On the real dataset, only the data path changes.
# =============================================================================================

suppressPackageStartupMessages({
  library(cibmtrrepro)   # canonical KM/Cox/CIF/cause-specific implementations (unit-tested)
  library(yaml)
})

set.seed(20200101)       # determinism: same inputs -> same outputs on every rerun

# --- 0. Load analytic data + schema roles ----------------------------------------------------
args     <- commandArgs(trailingOnly = TRUE)
data_dir <- if (length(args) >= 1) args[[1]] else "."
dat      <- read.csv(file.path(data_dir, "synthetic_P-5297.csv"), stringsAsFactors = FALSE)
schema   <- yaml::read_yaml(file.path(data_dir, "analytic.schema.yaml"))

dir.create(file.path(data_dir, "results"), showWarnings = FALSE)

# Code the exposure/covariates to the reference levels the paper used, so HRs are comparable.
dat$age_grp   <- relevel(factor(dat$age_grp,   levels = schema$exposure$levels),
                         ref = schema$exposure$reference)                       # ref = <60
dat$kps_grp   <- relevel(factor(dat$kps_grp,   levels = c("<90", ">=90")), ref = "<90")
dat$hctci_grp <- relevel(factor(dat$hctci_grp, levels = c("0", "1-2", ">=3")), ref = "0")

adj <- c("age_grp", "kps_grp", "hctci_grp")   # adjustment set (age main effect + covariates)
results <- list()                             # collected -> agent-results.yaml

# --- 1. OS: Kaplan-Meier median + adjusted Cox PH --------------------------------------------
# Estimand: time from transplant to death (any cause). Composite-survival -> KM + Cox.
os_km  <- km_fit(dat, time = "time_os", event = "event_os")
os_cox <- cox_ph(dat, time = "time_os", event = "event_os",
                 covariates = adj, ref = list(age_grp = "<60"))
write.csv(os_km$medians, file.path(data_dir, "results", "os_km_medians.csv"), row.names = FALSE)
write.csv(os_cox,        file.path(data_dir, "results", "os_cox_hr.csv"),     row.names = FALSE)

os_hr70 <- os_cox[os_cox$term == "age_grp>=70", ]
results[["os_median"]] <- list(
  observed = list(point = round(os_km$medians$median[[1]], 1), unit = "months"),
  source = "km_fit(time_os, event_os)$medians$median[1]")
results[["os_hr_age_ge70"]] <- list(
  observed = list(point = round(os_hr70$hr, 3), ci_low = round(os_hr70$ci_low, 3),
                  ci_high = round(os_hr70$ci_high, 3), unit = "HR",
                  significance_verdict = if (os_hr70$ci_low > 1) "significant" else "not-significant"),
  source = 'cox_ph(time_os,event_os,covariates=age+kps+hctci)[term=="age_grp>=70"]')

# --- 2. PFS: Kaplan-Meier median + adjusted Cox PH -------------------------------------------
# Estimand: time to progression/relapse or death, whichever first. Composite-survival.
pfs_km  <- km_fit(dat, time = "time_pfs", event = "event_pfs")
pfs_cox <- cox_ph(dat, time = "time_pfs", event = "event_pfs",
                  covariates = adj, ref = list(age_grp = "<60"))
write.csv(pfs_km$medians, file.path(data_dir, "results", "pfs_km_medians.csv"), row.names = FALSE)
write.csv(pfs_cox,        file.path(data_dir, "results", "pfs_cox_hr.csv"),     row.names = FALSE)

pfs_hr70 <- pfs_cox[pfs_cox$term == "age_grp>=70", ]
results[["pfs_median"]] <- list(
  observed = list(point = round(pfs_km$medians$median[[1]], 1), unit = "months"),
  source = "km_fit(time_pfs, event_pfs)$medians$median[1]")
results[["pfs_hr_age_ge70"]] <- list(
  observed = list(point = round(pfs_hr70$hr, 3), ci_low = round(pfs_hr70$ci_low, 3),
                  ci_high = round(pfs_hr70$ci_high, 3), unit = "HR",
                  significance_verdict = if (pfs_hr70$ci_low > 1) "significant" else "not-significant"),
  source = 'cox_ph(time_pfs,event_pfs,...)[term=="age_grp>=70"]')

# --- 3. NRM & relapse: cumulative incidence (competing risks) --------------------------------
# NRM and relapse share one clock (event_cr: 0 censored, 1 NRM, 2 relapse). Competing-risk
# estimand -> cumulative incidence for the point estimates. 1-year (12-month) CIF reported.
nrm_codes <- list(censored = 0, nrm = 1, relapse = 2)     # event of interest = NRM
rel_codes <- list(censored = 0, relapse = 2, nrm = 1)     # event of interest = relapse
nrm_cif <- cif(dat, time = "time_cr", event_code = "event_cr", codes = nrm_codes, at_times = 12)
rel_cif <- cif(dat, time = "time_cr", event_code = "event_cr", codes = rel_codes, at_times = 12)
write.csv(nrm_cif, file.path(data_dir, "results", "nrm_cif.csv"), row.names = FALSE)
write.csv(rel_cif, file.path(data_dir, "results", "rel_cif.csv"), row.names = FALSE)

results[["nrm_cif_1yr"]] <- list(
  observed = list(point = round(nrm_cif$cif[nrm_cif$cause == "nrm"][[1]], 3), unit = "proportion"),
  source = "cif(time_cr, event_cr, interest=NRM) at t=12")
results[["rel_cif_1yr"]] <- list(
  observed = list(point = round(rel_cif$cif[rel_cif$cause == "relapse"][[1]], 3), unit = "proportion"),
  source = "cif(time_cr, event_cr, interest=relapse) at t=12")

# Cause-specific Cox for the age effect on each competing endpoint (paper's regression choice).
nrm_cox <- cause_specific_cox(dat, time = "time_cr", event_code = "event_cr",
                              cause = 1, covariates = adj)
rel_cox <- cause_specific_cox(dat, time = "time_cr", event_code = "event_cr",
                              cause = 2, covariates = adj)
write.csv(nrm_cox, file.path(data_dir, "results", "nrm_cause_specific_cox.csv"), row.names = FALSE)
write.csv(rel_cox, file.path(data_dir, "results", "rel_cause_specific_cox.csv"), row.names = FALSE)

# --- 4. Coarsening-limited target: continuous-age model --------------------------------------
# The paper's exposure is age at transplant. The public file provides age GROUPS only, so a
# continuous-age HR CANNOT be computed here. We deliberately DO NOT fabricate one; we record
# why. The categorical-age effect above (os_hr_age_ge70) is the reproducible counterpart.
results[["os_hr_age_continuous"]] <- list(
  observed = NULL,
  not_computed_reason = paste("Continuous age is not in the analytic file (age_grp only);",
                              "flagged coarsening-limited up front by the Interpreter."))

# --- 5. Emit agent-results.yaml (agent-results.schema.json) + sessionInfo ---------------------
agent_results <- list(
  study_id = "P-5297-SYNTHETIC",
  script   = "reproduce_P-5297.R",
  seed     = 20200101L,
  r_session = list(exit_code = 0L),
  cohort   = list(n = nrow(dat), produced_by = "cohort-assembler"),
  results  = lapply(names(results), function(id) c(list(target_id = id), results[[id]]))
)
writeLines(as.yaml(agent_results), file.path(data_dir, "agent-results.yaml"))
writeLines(capture.output(sessionInfo()), file.path(data_dir, "sessionInfo.txt"))

cat("reproduce_P-5297.R complete. Wrote results/, agent-results.yaml, sessionInfo.txt\n")
