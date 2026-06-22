#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Clinical ETL Platform — Quick Setup & Run Script
# Srinivas Gampasani — Portfolio Project 13
# ─────────────────────────────────────────────────────────────────────────────

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  🏥  Clinical Data ETL Platform — Setup & Run${NC}"
echo -e "${BLUE}  📋  Portfolio Project 13 | Srinivas Gampasani${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Python version...${NC}"
python3 --version || { echo -e "${RED}Python 3 not found. Install Python 3.9+${NC}"; exit 1; }
echo -e "${GREEN}  ✓ Python OK${NC}"

# ── Create virtual environment ────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/5] Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}  ✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}  ✓ Virtual environment already exists${NC}"
fi

source venv/bin/activate

# ── Install dependencies ──────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/5] Installing dependencies...${NC}"
pip install --upgrade pip --quiet
pip install \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    Faker \
    pydantic \
    python-dotenv \
    --quiet

echo -e "${GREEN}  ✓ Core dependencies installed${NC}"

# Optional heavy deps (skip if fail)
pip install great-expectations dbt-core apache-airflow --quiet 2>/dev/null && \
    echo -e "${GREEN}  ✓ Optional dependencies (GE, dbt, Airflow) installed${NC}" || \
    echo -e "${YELLOW}  ⚠  Optional deps skipped (will use built-in implementations)${NC}"

# ── Create directories ────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/5] Creating directories...${NC}"
mkdir -p outputs logs
echo -e "${GREEN}  ✓ Directories ready${NC}"

# ── Copy .env ─────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}  ✓ .env created from template (DEMO_MODE=true)${NC}"
fi

# ── Run Pipeline ──────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/5] Running the Clinical ETL Pipeline...${NC}"
echo ""
python3 scripts/run_pipeline.py --mode demo

echo ""
echo -e "${YELLOW}Generating proof charts...${NC}"
python3 scripts/generate_proof_charts.py

echo ""
echo -e "${YELLOW}Generating HTML dashboard...${NC}"
python3 dashboard/app.py

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅  Setup Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  📊  Dashboard:  ${BLUE}outputs/dashboard.html${NC}  (open in browser)"
echo -e "  📈  Charts:     ${BLUE}outputs/chart_*.png${NC}"
echo -e "  📋  Report:     ${BLUE}outputs/pipeline_run_report.json${NC}"
echo -e "  🗃   Database:   ${BLUE}outputs/clinical_dw.db${NC}  (SQLite)"
echo -e "  📝  Logs:       ${BLUE}logs/pipeline.log${NC}"
echo ""
echo -e "  Run unit tests: ${YELLOW}python3 -m unittest tests/unit/test_pipeline.py -v${NC}"
echo ""
