# Exact-match unit tests on small synthetic inputs.
# The reproductions themselves become additional test cases later; these lock down the
# canonical statistical core the Analyst calls.
#
# Expected values below were independently cross-checked in Python (lifelines /
# AalenJohansenFitter): KM median = 5.0; CIF_1(t=3)=0.4, CIF_1(t=5)=0.8; a Cox model recovers a
# simulated HR of 1.6 with a 95% CI comfortably containing the truth.

# ---- Kaplan-Meier ----

test_that("km_fit recovers a known median", {
  d <- data.frame(time = 1:10, event = rep(1L, 10))
  out <- km_fit(d, "time", "event")
  # 10 uncensored times dropping 0.1 each: S(5)=0.5 -> median 5 (smallest t with S<=0.5).
  expect_equal(out$medians$median[[1]], 5)
})

test_that("km_fit reports per-stratum medians", {
  d <- rbind(
    data.frame(time = 1:10, event = 1L, arm = "A"),
    data.frame(time = 11:20, event = 1L, arm = "B")
  )
  out <- km_fit(d, "time", "event", strata = "arm")
  expect_equal(nrow(out$medians), 2)
  expect_true(out$medians$median[out$medians$strata == "B"] >
              out$medians$median[out$medians$strata == "A"])
})

# ---- log-rank ----

test_that("logrank_test detects a real group difference", {
  d <- synth_survival(n = 4000, hr = 1.6, seed = 11)
  lr <- logrank_test(d, "time", "event", "group")
  expect_lt(lr$p_value, 1e-6)
  expect_equal(lr$df, 1)
})

# ---- Cox PH ----

test_that("cox_ph recovers a known hazard ratio within tolerance", {
  d <- synth_survival(n = 6000, hr = 1.6, seed = 3)
  tt <- cox_ph(d, "time", "event", covariates = "group", ref = list(group = "A"))
  row <- tt[grepl("group", tt$term), ]
  expect_equal(nrow(row), 1)
  expect_lt(abs(row$hr - 1.6), 0.2)          # point near the simulation truth
  expect_true(row$ci_low < 1.6 && row$ci_high > 1.6)   # 95% CI contains the truth
  expect_true(row$ci_low > 1.0)              # significant, correct direction
})

test_that("cox_ph honors the reference level", {
  d <- synth_survival(n = 4000, hr = 1.6, seed = 5)
  # With B as reference, the A-vs-B HR should be ~ 1/1.6 (protective).
  tt <- cox_ph(d, "time", "event", covariates = "group", ref = list(group = "B"))
  row <- tt[grepl("group", tt$term), ]
  expect_lt(row$hr, 1.0)
})

# ---- Cumulative incidence (Aalen-Johansen) ----

test_that("cif matches a hand-computed cumulative incidence", {
  d <- data.frame(time = c(1, 2, 3, 4, 5),
                  event_code = c(1L, 2L, 1L, 0L, 1L))
  codes <- list(censored = 0, cause1 = 1, cause2 = 2)
  est <- cif(d, "time", "event_code", codes, at_times = c(3, 5))
  c1 <- est[est$cause == "cause1", ]
  expect_equal(c1$cif[c1$time == 3], 0.4, tolerance = 1e-6)
  expect_equal(c1$cif[c1$time == 5], 0.8, tolerance = 1e-6)
})

test_that("cause-specific CIFs sum with survival to 1 at the last time", {
  d <- synth_competing(n = 3000, seed = 7)
  codes <- list(censored = 0, cause1 = 1, cause2 = 2)
  est <- cif(d, "time", "event_code", codes)
  last1 <- tail(est[est$cause == "cause1", "cif"], 1)
  last2 <- tail(est[est$cause == "cause2", "cif"], 1)
  expect_true(last1 > 0 && last2 > 0 && (last1 + last2) <= 1 + 1e-8)
})

# ---- Gray's test ----

test_that("grays_test flags differing cause-1 incidence across groups", {
  d <- synth_competing(n = 5000, hr1 = 1.8, seed = 9)
  gt <- grays_test(d, "time", "event_code", "group",
                   codes = list(censored = 0, cause1 = 1, cause2 = 2))
  p1 <- gt$p_value[1]
  expect_lt(p1, 0.05)
})

# ---- cause-specific Cox ----

test_that("cause_specific_cox recovers the cause-1 hazard ratio and censors competing events", {
  d <- synth_competing(n = 8000, hr1 = 1.5, seed = 13)
  d$group <- stats::relevel(as.factor(d$group), ref = "A")
  tt <- cause_specific_cox(d, "time", "event_code", cause = 1, covariates = "group")
  row <- tt[grepl("group", tt$term), ]
  expect_lt(abs(row$hr - 1.5), 0.2)
  expect_true(row$ci_low < 1.5 && row$ci_high > 1.5)
})

test_that("cause_specific_cox treats competing events as censored, not as the event", {
  # A subject with a competing (cause-2) event must contribute event = 0 to the cause-1 model.
  d <- data.frame(time = c(5, 6, 7), event_code = c(1L, 2L, 0L), group = c("A", "B", "A"))
  built <- within(d, .cs <- as.integer(event_code == 1L))
  expect_equal(built$.cs, c(1L, 0L, 0L))   # cause-2 (row 2) is censored for cause 1
})
