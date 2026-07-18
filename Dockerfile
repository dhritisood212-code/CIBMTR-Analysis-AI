# Backend API image — now includes the R runtime so agent-produced R actually executes.
# Build context is the REPO ROOT (the backend reads agents/, schemas/, infra/, r-engine/).
#
#   docker build -t cibmtr-repro-api .
#   docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-... cibmtr-repro-api
#
# R runs via infra/run_r_sandboxed.sh (resource limits + workspace scoping + best-effort
# network isolation). See infra/README.md for the full hardening ladder.
FROM python:3.11-slim

# System deps: R + its dev toolchain (to compile R packages) and util-linux for `unshare`.
RUN apt-get update && apt-get install -y --no-install-recommends \
        r-base \
        r-base-dev \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

# The two R packages the engine needs, from CRAN. `survival` ships with R; `cmprsk` compiles
# (Fortran) via r-base-dev. Fail the build loudly if either doesn't end up installed.
RUN Rscript -e 'install.packages(c("survival","cmprsk"), repos="https://cloud.r-project.org"); \
    if (!all(c("survival","cmprsk") %in% rownames(installed.packages()))) quit(status = 1)'

WORKDIR /app
COPY backend/ ./backend/
COPY agents/ ./agents/
COPY schemas/ ./schemas/
COPY infra/ ./infra/
COPY r-engine/ ./r-engine/

# Install the internal R package (cibmtrrepro): the canonical, unit-tested endpoint/model
# functions the Analyst's scripts call. Make the sandbox runner executable.
RUN R CMD INSTALL --no-multiarch --no-docs /app/r-engine \
    && chmod +x /app/infra/run_r_sandboxed.sh

WORKDIR /app/backend
RUN pip install --no-cache-dir -e .

ENV RUNS_DIR=/app/backend/runs
ENV CORS_ORIGINS=*
ENV R_SANDBOX_CMD=/app/infra/run_r_sandboxed.sh
EXPOSE 8000

# Render/Railway/Fly set $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
