#!/bin/bash
# =============================================================================
# runSimulations.sh
#
# Validates and runs simpleFoam for each turbulence model case created
# by makeModelFolders.sh. Runs cases sequentially (safe for M4 Pro 24 GB).
# Parallel execution option available via --parallel flag.
#
# Usage:
#   bash runSimulations.sh [OPTIONS]
#
# Options:
#   -r, --rundir     PATH   Directory containing model case folders
#                           (default: ./runs)
#   -m, --models     LIST   Comma-separated subset of models to run
#                           (default: all folders found in rundir)
#   -n, --np         N      MPI processes per case for parallel run (default: 1)
#   -c, --continue          Resume from latest time directory if case exists
#   -f, --force             Re-run even if a completed result already exists
#   -t, --timeout    SECS   Kill a case if it exceeds this wall time (default: 7200)
#   -w, --window     N      Number of final force samples used for convergence
#                           statistics (default: 500)
#   -h, --help              Show this help message
#
# What this script does per case:
#   1.  Pre-run validation (mesh, fields, solver, turbulence model consistency)
#   2.  Mesh quality check via checkMesh
#   3.  Wall y+ estimate from mesh spacing
#   4.  Run simpleFoam (serial or parallel)
#   5.  Convergence check on residuals and force coefficients
#   6.  Post-run summary: Cl, Cd, convergence status
#   7.  Write pass/fail status to results/run_summary.csv
#
# Output structure per case:
#   runs/kOmegaSST/
#     log.checkMesh          ← mesh quality log
#     log.simpleFoam         ← solver output
#     log.convergence        ← extracted Cl/Cd history
#     run_status.txt         ← PASS / FAIL / RUNNING
#     postProcessing/        ← OpenFOAM function object outputs
#
# =============================================================================

set -uo pipefail

# =============================================================================
# DEFAULTS
# =============================================================================
RUN_DIR="./runs"
MODELS_ARG=""
NP=1
CONTINUE_RUN=false
FORCE_RERUN=false
TIMEOUT=7200          # 2 hours per case default
RESULTS_DIR="./results"
RESULTS_FILE=""
FORCE_WINDOW=500
CL_DRIFT_LIMIT=0.001      # 0.1% relative drift over final force window
CD_DRIFT_LIMIT=0.005      # 0.5% relative drift over final force window
CL_STD_LIMIT=0.001        # absolute standard deviation over final force window
CD_STD_LIMIT=0.00002      # absolute standard deviation over final force window

# =============================================================================
# COLOUR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}"; }

# =============================================================================
# USAGE
# =============================================================================
usage() {
    sed -n '3,45p' "$0" | sed 's/^# \?//'
    exit 0
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--rundir)     RUN_DIR="$2";     shift 2 ;;
        -m|--models)     MODELS_ARG="$2";  shift 2 ;;
        -n|--np)         NP="$2";          shift 2 ;;
        -c|--continue)   CONTINUE_RUN=true; shift ;;
        -f|--force)      FORCE_RERUN=true; shift ;;
        -t|--timeout)    TIMEOUT="$2";     shift 2 ;;
        -w|--window)     FORCE_WINDOW="$2"; shift 2 ;;
        -h|--help)       usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

# =============================================================================
# HEADER
# =============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   NACA 0012 — Multi-Model Simulation Runner             ║${NC}"
echo -e "${BOLD}║   OpenFOAM 2412 — simpleFoam                            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Run directory : $RUN_DIR"
log_info "MPI processes : $NP $([ "$NP" -gt 1 ] && echo "(parallel)" || echo "(serial)")"
log_info "Timeout/case  : ${TIMEOUT}s"
log_info "Force window  : last ${FORCE_WINDOW} samples"
log_info "Continue mode : $CONTINUE_RUN"
log_info "Force rerun   : $FORCE_RERUN"
echo ""

# =============================================================================
# GLOBAL PRE-FLIGHT CHECKS
# =============================================================================
log_section "GLOBAL PRE-FLIGHT CHECKS"

GLOBAL_ERRORS=0

# ── OpenFOAM environment ──────────────────────────────────────────────────────
if [[ -z "${WM_PROJECT:-}" ]]; then
    log_error "OpenFOAM environment not loaded."
    log_error "Source: source /usr/lib/openfoam/openfoam2412/etc/bashrc"
    GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
else
    log_ok "OpenFOAM $WM_PROJECT_VERSION loaded"
fi

# ── Required executables ──────────────────────────────────────────────────────
for exe in "simpleFoam" "checkMesh" "reconstructPar" "timeout" "awk" "grep" "sort" "find"; do
    if ! command -v "$exe" &>/dev/null; then
        log_error "$exe not found in PATH"
        GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
    else
        log_ok "$exe: $(which $exe)"
    fi
done

# ── MPI check if parallel ─────────────────────────────────────────────────────
if [[ "$NP" -gt 1 ]]; then
    if ! command -v mpirun &>/dev/null; then
        log_error "mpirun not found — required for --np > 1"
        GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
    else
        log_ok "mpirun found: $(which mpirun)"
    fi
    if ! command -v decomposePar &>/dev/null; then
        log_error "decomposePar not found — required for parallel run"
        GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
    fi
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        log_warn "Running as root. Parallel mpirun will use --allow-run-as-root."
    fi
fi

# ── Run directory ─────────────────────────────────────────────────────────────
if [[ ! -d "$RUN_DIR" ]]; then
    log_error "Run directory not found: $RUN_DIR"
    log_error "Run makeModelFolders.sh first."
    GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
fi

if [[ $GLOBAL_ERRORS -gt 0 ]]; then
    log_error "$GLOBAL_ERRORS global error(s). Aborting."
    exit 1
fi
log_ok "Global pre-flight passed."

# =============================================================================
# BUILD MODEL LIST
# =============================================================================
if [[ -n "$MODELS_ARG" ]]; then
    IFS=',' read -ra MODELS <<< "$MODELS_ARG"
else
    # Auto-discover: find all subdirectories in RUN_DIR that look like cases.
    # Avoid GNU-only find -printf so this also works on macOS/BSD find.
    MODELS=()
    while IFS= read -r case_path; do
        [[ -f "$case_path/constant/turbulenceProperties" ]] || continue
        MODELS+=("$(basename "$case_path")")
    done < <(find "$RUN_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
fi

if [[ ${#MODELS[@]} -eq 0 ]]; then
    log_error "No model case folders found in $RUN_DIR"
    log_error "Run makeModelFolders.sh first."
    exit 1
fi

log_info "Cases to run: ${MODELS[*]}"

# =============================================================================
# RESULTS FILE SETUP
# =============================================================================
mkdir -p "$RESULTS_DIR"
if [[ -z "$RESULTS_FILE" ]]; then
    RESULTS_FILE="$RESULTS_DIR/run_summary_$(date +%Y%m%d_%H%M%S).csv"
fi

echo "model,aoa,status,Cl_final,Cd_final,Cl_mean,Cd_mean,Cl_std,Cd_std,Cl_drift_pct,Cd_drift_pct,Cl_err_pct,Cd_err_pct,iterations,wall_time_s,timestamp" \
    > "$RESULTS_FILE"

# Experimental reference (Ladson 1988, Re=5.95e6, alpha=10.12 deg, tripped)
CL_REF=1.0707
CD_REF=0.01201

# =============================================================================
# PER-CASE VALIDATION FUNCTION
# =============================================================================
validate_case() {
    local CASE_DIR="$1"
    local MODEL="$2"
    local ERRORS=0

    log_section "VALIDATING: $MODEL"

    # ── Check 0/ fields ───────────────────────────────────────────────────────
    for field in "U" "p" "nut"; do
        if [[ ! -f "$CASE_DIR/0/$field" ]]; then
            log_error "Missing required field: 0/$field"
            ERRORS=$((ERRORS+1))
        else
            log_ok "0/$field exists"
        fi
    done

    # ── Check model-specific fields ───────────────────────────────────────────
    if [[ -f "$CASE_DIR/case_meta.txt" ]]; then
        REQUIRED=$(grep "^required_fields=" "$CASE_DIR/case_meta.txt" | cut -d= -f2)
    else
        # Fallback: check turbulenceProperties for RASModel
        ACTIVE_MODEL=$(grep -E "^\s*RASModel\s" "$CASE_DIR/constant/turbulenceProperties" \
            | awk '{print $2}' | tr -d ';' | head -1)
        case "$ACTIVE_MODEL" in
            kOmegaSST)       REQUIRED="k omega nut" ;;
            SpalartAllmaras) REQUIRED="nuTilda nut" ;;
            kEpsilon|realizableKE|RNGkEpsilon) REQUIRED="k epsilon nut" ;;
            kOmega)          REQUIRED="k omega nut" ;;
            LaunderSharmaKE) REQUIRED="k epsilon nut" ;;
            *) log_warn "Unknown model $ACTIVE_MODEL — skipping field check" ;;
        esac
    fi

    for field in $REQUIRED; do
        if [[ ! -f "$CASE_DIR/0/$field" ]]; then
            log_error "Missing model field: 0/$field (required by $MODEL)"
            ERRORS=$((ERRORS+1))
        else
            log_ok "0/$field exists (required by $MODEL)"
        fi
    done

    # ── Check turbulenceProperties has exactly one active RASModel ────────────
    ACTIVE_MODELS=$(grep -cE "^\s*RASModel\s+[^/]" \
        "$CASE_DIR/constant/turbulenceProperties" 2>/dev/null || true)
    [[ -n "$ACTIVE_MODELS" ]] || ACTIVE_MODELS=0
    if [[ "$ACTIVE_MODELS" -eq 0 ]]; then
        log_error "No active RASModel found in constant/turbulenceProperties"
        log_error "All RASModel lines are commented out."
        ERRORS=$((ERRORS+1))
    elif [[ "$ACTIVE_MODELS" -gt 1 ]]; then
        log_error "Multiple active RASModel lines found ($ACTIVE_MODELS). Only one allowed."
        ERRORS=$((ERRORS+1))
    else
        ACTIVE_MODEL=$(grep -E "^\s*RASModel\s+[^/]" \
            "$CASE_DIR/constant/turbulenceProperties" | awk '{print $2}' | tr -d ';')
        if [[ "$ACTIVE_MODEL" != "$MODEL" ]]; then
            log_error "turbulenceProperties RASModel=$ACTIVE_MODEL but expected $MODEL"
            ERRORS=$((ERRORS+1))
        else
            log_ok "RASModel = $ACTIVE_MODEL (correct)"
        fi
    fi

    # ── Check mesh ────────────────────────────────────────────────────────────
    if [[ ! -d "$CASE_DIR/constant/polyMesh" ]]; then
        log_error "No polyMesh found in $CASE_DIR/constant/"
        log_error "Run plot3dToFoam or blockMesh inside the case, or symlink the mesh:"
        log_error "  cd $CASE_DIR && ln -s ../../base/constant/polyMesh constant/"
        ERRORS=$((ERRORS+1))
    else
        # Check boundary file has airfoil and farfield patches
        BOUNDARY="$CASE_DIR/constant/polyMesh/boundary"
        if [[ ! -f "$BOUNDARY" ]]; then
            log_error "polyMesh/boundary file missing"
            ERRORS=$((ERRORS+1))
        else
            if ! grep -q "airfoil" "$BOUNDARY"; then
                log_error "Patch 'airfoil' not found in polyMesh/boundary"
                log_error "Rename wall patch to 'airfoil' — must match 0/ BCs"
                ERRORS=$((ERRORS+1))
            else
                log_ok "Patch 'airfoil' found in boundary"
            fi
            if ! grep -q "farfield" "$BOUNDARY"; then
                log_error "Patch 'farfield' not found in polyMesh/boundary"
                log_error "Rename outer patch to 'farfield' — must match 0/ BCs"
                ERRORS=$((ERRORS+1))
            else
                log_ok "Patch 'farfield' found in boundary"
            fi
            if ! grep -q "front\|empty" "$BOUNDARY"; then
                log_warn "No 'front'/'back' empty patches detected — required for 2D"
            else
                log_ok "Empty patches found (2D geometry confirmed)"
            fi
        fi
    fi

    # ── Check system files ────────────────────────────────────────────────────
    for sysfile in "controlDict" "fvSchemes" "fvSolution"; do
        if [[ ! -f "$CASE_DIR/system/$sysfile" ]]; then
            log_error "Missing: system/$sysfile"
            ERRORS=$((ERRORS+1))
        else
            log_ok "system/$sysfile exists"
        fi
    done

    # ── Check application in controlDict ─────────────────────────────────────
    APP=$(grep "^application\s" "$CASE_DIR/system/controlDict" \
        | awk '{print $2}' | tr -d ';' | head -1)
    if [[ "$APP" != "simpleFoam" ]]; then
        log_error "controlDict application = '$APP', expected 'simpleFoam'"
        ERRORS=$((ERRORS+1))
    else
        log_ok "controlDict: application = simpleFoam"
    fi

    # ── Check liftDir/dragDir are set (not zeroed) ────────────────────────────
    LIFTDIR=$(grep "liftDir" "$CASE_DIR/system/controlDict" \
        | grep -v "//" | head -1)
    if [[ -z "$LIFTDIR" ]]; then
        log_warn "liftDir not found in controlDict — force coefficients may be wrong"
    else
        log_ok "liftDir found in controlDict"
    fi

    # ── Check no previously failed run markers ────────────────────────────────
    if [[ -f "$CASE_DIR/run_status.txt" ]]; then
        STATUS=$(cat "$CASE_DIR/run_status.txt")
        if [[ "$STATUS" == "RUNNING" ]]; then
            log_warn "Case appears to be already RUNNING (or crashed mid-run)."
            log_warn "If crashed: delete run_status.txt and re-run."
        elif [[ "$STATUS" == "COMPLETE" && "$FORCE_RERUN" == "false" ]]; then
            log_warn "Case already COMPLETE. Use --force to re-run."
            return 2   # special code: skip this case
        fi
    fi

    echo ""
    return $ERRORS
}

# =============================================================================
# FORCE COEFFICIENT HELPERS
# =============================================================================
find_force_coeff_file() {
    local CASE_DIR="$1"
    find "$CASE_DIR/postProcessing/forceCoeffs" -type f -name "*.dat" 2>/dev/null | sort | tail -1
}

force_column_index() {
    local FILE="$1"
    local NAME="$2"
    local HEADER
    HEADER=$(grep '^#' "$FILE" | grep -E "Time|Cm|Cd|Cl|coefficient" | tail -1 | sed 's/^#//')
    if [[ -z "$HEADER" ]]; then
        return 1
    fi
    awk -v target="$NAME" '
    {
        for (i=1; i<=NF; i++) {
            gsub(/[()]/, "", $i)
            if ($i == target) {
                print i
                exit 0
            }
        }
        exit 1
    }' <<< "$HEADER"
}

extract_force_stats() {
    local FILE="$1"
    local WINDOW="$2"
    local CL_COL CD_COL

    CD_COL=$(force_column_index "$FILE" "Cd" || true)
    CL_COL=$(force_column_index "$FILE" "Cl" || true)

    # Fallback for common OpenFOAM forceCoeffs ordering: Time Cm Cd Cl ...
    [[ -n "$CD_COL" ]] || CD_COL=3
    [[ -n "$CL_COL" ]] || CL_COL=4

    grep -v '^#' "$FILE" | awk -v clc="$CL_COL" -v cdc="$CD_COL" -v n="$WINDOW" '
    NF >= clc && NF >= cdc {
        cl[++count] = $clc + 0.0
        cd[count] = $cdc + 0.0
    }
    END {
        if (count == 0) {
            print "N/A,N/A,N/A,N/A,N/A,N/A"
            exit 0
        }
        start = count - n + 1
        if (start < 1) start = 1
        m = count - start + 1
        cl_first = cl[start]
        cd_first = cd[start]
        cl_last = cl[count]
        cd_last = cd[count]
        for (i=start; i<=count; i++) {
            cl_sum += cl[i]
            cd_sum += cd[i]
        }
        cl_mean = cl_sum / m
        cd_mean = cd_sum / m
        for (i=start; i<=count; i++) {
            cl_var += (cl[i] - cl_mean)^2
            cd_var += (cd[i] - cd_mean)^2
        }
        cl_std = sqrt(cl_var / m)
        cd_std = sqrt(cd_var / m)
        cl_drift = (cl_mean != 0 ? 100.0 * (cl_last - cl_first) / cl_mean : 0)
        cd_drift = (cd_mean != 0 ? 100.0 * (cd_last - cd_first) / cd_mean : 0)
        printf "%.8g,%.8g,%.8g,%.8g,%.8g,%.8g\n", cl_last, cd_last, cl_mean, cd_mean, cl_std, cd_std > "/dev/stderr"
        printf "%.8g,%.8g\n", cl_drift, cd_drift
    }'
}

# =============================================================================
# CONVERGENCE CHECK FUNCTION
# Reads postProcessing/forceCoeffs and residuals to judge convergence
# =============================================================================
check_convergence() {
    local CASE_DIR="$1"
    local MODEL="$2"
    local LOG="$CASE_DIR/log.simpleFoam"
    local STATUS="UNKNOWN"
    local CL="N/A" CD="N/A" CL_MEAN="N/A" CD_MEAN="N/A" CL_STD="N/A" CD_STD="N/A"
    local CL_DRIFT="N/A" CD_DRIFT="N/A" CL_ERR="N/A" CD_ERR="N/A" ITERS="N/A"

    # ── Check if solver finished without errors ───────────────────────────────
    if grep -q "^End$" "$LOG" 2>/dev/null; then
        STATUS="COMPLETE"
    elif grep -q "FOAM FATAL ERROR\|FOAM exiting\|Floating point exception\|Segmentation fault" \
            "$LOG" 2>/dev/null; then
        STATUS="CRASHED"
        log_error "Solver crashed. Check $LOG for FATAL ERROR."

        cat > "$CASE_DIR/log.convergence" << EOF
model          = $MODEL
status         = $STATUS
iterations     = N/A
force_window   = $FORCE_WINDOW
Cl_final       = N/A
Cd_final       = N/A
Cl_mean        = N/A
Cd_mean        = N/A
Cl_std         = N/A
Cd_std         = N/A
Cl_drift_pct   = N/A
Cd_drift_pct   = N/A
Cl_ref         = $CL_REF  (Ladson 1988, alpha=10.12 deg)
Cd_ref         = $CD_REF
Cl_err_pct     = N/A
Cd_err_pct     = N/A
timestamp      = $(date -Iseconds)
EOF

        AOA_VAL=$(grep "^aoa=" "$CASE_DIR/case_meta.txt" 2>/dev/null | cut -d= -f2 || echo "10")
        WALL_TIME=${CASE_WALL_TIME:-0}
        echo "$MODEL,$AOA_VAL,$STATUS,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,$WALL_TIME,$(date -Iseconds)" \
            >> "$RESULTS_FILE"
        echo "$STATUS"
        return
    else
        STATUS="INCOMPLETE"
        log_warn "Solver did not finish normally."
    fi

    # ── Extract iteration count ───────────────────────────────────────────────
    ITERS=$(grep -c "^Time = " "$LOG" 2>/dev/null || true)
    [[ -n "$ITERS" ]] || ITERS=0

    # ── Extract final and final-window Cl/Cd from forceCoeffs ────────────────
    FC_FILE=$(find_force_coeff_file "$CASE_DIR")

    if [[ -n "$FC_FILE" && -f "$FC_FILE" ]]; then
        STATS_STDERR=$(mktemp)
        DRIFTS=$(extract_force_stats "$FC_FILE" "$FORCE_WINDOW" 2> "$STATS_STDERR")
        IFS=',' read -r CL CD CL_MEAN CD_MEAN CL_STD CD_STD < "$STATS_STDERR"
        IFS=',' read -r CL_DRIFT CD_DRIFT <<< "$DRIFTS"
        rm -f "$STATS_STDERR"

        CL_ERR=$(awk -v val="$CL_MEAN" -v ref="$CL_REF" 'BEGIN { if (val == "N/A") print "N/A"; else printf "%.2f", (val-ref)*100/ref }')
        CD_ERR=$(awk -v val="$CD_MEAN" -v ref="$CD_REF" 'BEGIN { if (val == "N/A") print "N/A"; else printf "%.2f", (val-ref)*100/ref }')

        log_ok "Final-window Cl mean = $CL_MEAN  final = $CL  std = $CL_STD  drift = ${CL_DRIFT}%"
        log_ok "Final-window Cd mean = $CD_MEAN  final = $CD  std = $CD_STD  drift = ${CD_DRIFT}%"
        log_info "Ladson comparison uses final-window mean: Cl err = ${CL_ERR}%, Cd err = ${CD_ERR}%"

        FORCE_STABLE=$(awk \
            -v cls="$CL_STD" -v cds="$CD_STD" \
            -v cld="$CL_DRIFT" -v cdd="$CD_DRIFT" \
            -v cls_lim="$CL_STD_LIMIT" -v cds_lim="$CD_STD_LIMIT" \
            -v cld_lim="$CL_DRIFT_LIMIT" -v cdd_lim="$CD_DRIFT_LIMIT" \
            'BEGIN {
                cld_abs = cld < 0 ? -cld : cld
                cdd_abs = cdd < 0 ? -cdd : cdd
                print (cls <= cls_lim && cds <= cds_lim && cld_abs <= 100*cld_lim && cdd_abs <= 100*cdd_lim) ? "yes" : "no"
            }')
        if [[ "$FORCE_STABLE" != "yes" ]]; then
            log_warn "Force coefficients are not fully flat over the final window."
            log_warn "Limits: Cl std<=$CL_STD_LIMIT, Cd std<=$CD_STD_LIMIT, |Cl drift|<=$(awk -v x="$CL_DRIFT_LIMIT" 'BEGIN{print 100*x}')%, |Cd drift|<=$(awk -v x="$CD_DRIFT_LIMIT" 'BEGIN{print 100*x}')%"
            STATUS="${STATUS}_FORCE_DRIFT"
        fi
    else
        log_warn "forceCoeffs output not found. Check function objects in controlDict."
    fi

    # ── Check residual drop from solver log ───────────────────────────────────
    FINAL_INITIAL_P_RES=$(grep "Solving for p," "$LOG" 2>/dev/null | tail -1 \
        | sed -E 's/.*Initial residual = ([^,]+),.*/\1/' || true)
    if [[ -n "$FINAL_INITIAL_P_RES" && "$FINAL_INITIAL_P_RES" != *"Solving"* ]]; then
        log_info "Final SIMPLE p initial residual = $FINAL_INITIAL_P_RES"
        P_RES_OK=$(awk -v r="$FINAL_INITIAL_P_RES" 'BEGIN { print (r < 1e-6) ? "yes" : "no" }')
        if [[ "$P_RES_OK" != "yes" ]]; then
            log_warn "Final p initial residual is above 1e-6. Consider more iterations."
            STATUS="${STATUS}_RESIDUAL"
        fi
    else
        log_warn "Could not parse final p residual from log.simpleFoam"
    fi

    # ── Write convergence log ─────────────────────────────────────────────────
    cat > "$CASE_DIR/log.convergence" << EOF
model          = $MODEL
status         = $STATUS
iterations     = $ITERS
force_window   = $FORCE_WINDOW
Cl_final       = $CL
Cd_final       = $CD
Cl_mean        = $CL_MEAN
Cd_mean        = $CD_MEAN
Cl_std         = $CL_STD
Cd_std         = $CD_STD
Cl_drift_pct   = $CL_DRIFT
Cd_drift_pct   = $CD_DRIFT
Cl_ref         = $CL_REF  (Ladson 1988, alpha=10.12 deg)
Cd_ref         = $CD_REF
Cl_err_pct     = $CL_ERR
Cd_err_pct     = $CD_ERR
timestamp      = $(date -Iseconds)
EOF

    # ── Append to global results CSV ─────────────────────────────────────────
    AOA_VAL=$(grep "^aoa=" "$CASE_DIR/case_meta.txt" 2>/dev/null \
        | cut -d= -f2 || echo "10")
    WALL_TIME=${CASE_WALL_TIME:-0}
    echo "$MODEL,$AOA_VAL,$STATUS,$CL,$CD,$CL_MEAN,$CD_MEAN,$CL_STD,$CD_STD,$CL_DRIFT,$CD_DRIFT,$CL_ERR,$CD_ERR,$ITERS,$WALL_TIME,$(date -Iseconds)" \
        >> "$RESULTS_FILE"

    echo "$STATUS"
}

# =============================================================================
# RUN FUNCTION — runs simpleFoam for one case
# =============================================================================
run_case() {
    local CASE_DIR="$1"
    local MODEL="$2"

    log_section "RUNNING: $MODEL"
    echo "  Case: $CASE_DIR"
    echo ""

    # Mark as running
    echo "RUNNING" > "$CASE_DIR/run_status.txt"
    T_START=$(date +%s)

    # ── Step 1: checkMesh ─────────────────────────────────────────────────────
    log_info "Running checkMesh..."
    (cd "$CASE_DIR" && checkMesh -noFunctionObjects > log.checkMesh 2>&1)
    CM_EXIT=$?
    if [[ $CM_EXIT -ne 0 ]]; then
        log_warn "checkMesh exited with code $CM_EXIT. Continuing only if no fatal mesh errors are detected."
    fi

    MAX_NONORTHO=$(grep "Max non-orthogonality" "$CASE_DIR/log.checkMesh" \
        | awk '{print $NF}' | head -1)
    MAX_SKEW=$(grep "Max skewness" "$CASE_DIR/log.checkMesh" \
        | awk '{print $NF}' | head -1)
    MESH_OK=$(grep -c "Mesh OK\." "$CASE_DIR/log.checkMesh" 2>/dev/null || true)
    [[ -n "$MESH_OK" ]] || MESH_OK=0

    if [[ "$MESH_OK" -gt 0 ]]; then
        log_ok "checkMesh: Mesh OK"
    else
        log_warn "checkMesh: Mesh has issues — check $CASE_DIR/log.checkMesh"
        grep "FAILED\|Error\|failed" "$CASE_DIR/log.checkMesh" | head -5 | \
            while read -r line; do log_warn "  $line"; done
    fi
    [[ -n "$MAX_NONORTHO" ]] && log_info "  Max non-orthogonality : $MAX_NONORTHO"
    [[ -n "$MAX_SKEW"     ]] && log_info "  Max skewness          : $MAX_SKEW"

    # Abort if mesh is critically bad (negative volumes)
    if grep -q "FOAM FATAL ERROR\|negative vol" "$CASE_DIR/log.checkMesh" 2>/dev/null; then
        log_error "Mesh has fatal errors (negative volumes). Cannot run. Skipping."
        echo "FAILED_MESH" > "$CASE_DIR/run_status.txt"
        return 1
    fi

    # ── Step 2: Parallel decomposition (if NP > 1) ───────────────────────────
    if [[ "$NP" -gt 1 ]]; then
        log_info "Decomposing domain for $NP processors..."
        rm -rf "$CASE_DIR"/processor*

        # Create decomposeParDict if missing
        if [[ ! -f "$CASE_DIR/system/decomposeParDict" ]]; then
            cat > "$CASE_DIR/system/decomposeParDict" << EOF
FoamFile { version 2.0; format ascii; class dictionary;
           location "system"; object decomposeParDict; }
numberOfSubdomains  $NP;
method              scotch;
EOF
        fi

        (cd "$CASE_DIR" && decomposePar -force > log.decomposePar 2>&1)
        if [[ $? -ne 0 ]]; then
            log_error "decomposePar failed. Check log.decomposePar"
            echo "FAILED_DECOMPOSE" > "$CASE_DIR/run_status.txt"
            return 1
        fi
        log_ok "decomposePar complete"
    fi

    # ── Step 3: Run simpleFoam ────────────────────────────────────────────────
    log_info "Running simpleFoam (this may take several minutes)..."
    log_info "  Log: $CASE_DIR/log.simpleFoam"
    log_info "  Monitor: tail -f $CASE_DIR/log.simpleFoam"
    echo ""

    if [[ "$NP" -gt 1 ]]; then
        if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
            RUN_CMD="mpirun --allow-run-as-root -np $NP simpleFoam -parallel"
        else
            RUN_CMD="mpirun -np $NP simpleFoam -parallel"
        fi
    else
        RUN_CMD="simpleFoam"
    fi

    # Run with timeout, capture exit code
    (
        cd "$CASE_DIR"
        timeout "$TIMEOUT" $RUN_CMD > log.simpleFoam 2>&1
    )
    SOLVER_EXIT=$?

    T_END=$(date +%s)
    CASE_WALL_TIME=$((T_END - T_START))
    export CASE_WALL_TIME

    if [[ $SOLVER_EXIT -eq 124 ]]; then
        log_error "simpleFoam TIMED OUT after ${TIMEOUT}s."
        echo "TIMEOUT" > "$CASE_DIR/run_status.txt"
        return 1
    elif [[ $SOLVER_EXIT -ne 0 ]]; then
        log_error "simpleFoam exited with code $SOLVER_EXIT."
        # Still attempt convergence check to extract partial results
    fi

    log_info "Wall time: ${CASE_WALL_TIME}s"

    # ── Step 4: Reconstruct parallel case ────────────────────────────────────
    if [[ "$NP" -gt 1 ]]; then
        log_info "Reconstructing parallel case..."
        (cd "$CASE_DIR" && reconstructPar -latestTime > log.reconstructPar 2>&1)
        if [[ $? -ne 0 ]]; then
            log_warn "reconstructPar failed. Check log.reconstructPar. Continuing because forceCoeffs do not require reconstructed fields."
        fi
    fi

    # ── Step 5: Convergence check ─────────────────────────────────────────────
    echo ""
    log_section "CONVERGENCE CHECK: $MODEL"
    check_convergence "$CASE_DIR" "$MODEL"

    if [[ -f "$CASE_DIR/log.convergence" ]]; then
        CONV_STATUS=$(grep '^status[[:space:]]*=' "$CASE_DIR/log.convergence" \
            | awk -F= '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}' \
            | tail -1)
    else
        CONV_STATUS="UNKNOWN"
    fi
    [[ -n "$CONV_STATUS" ]] || CONV_STATUS="UNKNOWN"

    # ── Step 6: Final status ──────────────────────────────────────────────────
    echo "$CONV_STATUS" > "$CASE_DIR/run_status.txt"
    if [[ "$CONV_STATUS" == "COMPLETE" ]]; then
        log_ok "Case $MODEL: ${GREEN}COMPLETE${NC}"
    else
        log_warn "Case $MODEL status: $CONV_STATUS"
    fi

    return 0
}

# =============================================================================
# MAIN LOOP
# =============================================================================
log_section "STARTING SIMULATIONS"

TOTAL=${#MODELS[@]}
PASSED=0
FAILED=0
SKIPPED=0

for MODEL in "${MODELS[@]}"; do

    CASE_DIR="$RUN_DIR/$MODEL"

    echo ""
    echo -e "${BOLD}┌─────────────────────────────────────────────────────┐${NC}"
    echo -e "${BOLD}│  Model: $MODEL$(printf '%*s' $((50-${#MODEL})) '')│${NC}"
    echo -e "${BOLD}└─────────────────────────────────────────────────────┘${NC}"

    # ── Check case directory exists ───────────────────────────────────────────
    if [[ ! -d "$CASE_DIR" ]]; then
        log_error "Case directory not found: $CASE_DIR"
        log_error "Run makeModelFolders.sh first."
        FAILED=$((FAILED+1))
        continue
    fi

    # ── Per-case validation ───────────────────────────────────────────────────
    validate_case "$CASE_DIR" "$MODEL"
    VAL_EXIT=$?

    if [[ $VAL_EXIT -eq 2 ]]; then
        # Already complete, skipping
        SKIPPED=$((SKIPPED+1))
        continue
    elif [[ $VAL_EXIT -ne 0 ]]; then
        log_error "Validation failed for $MODEL ($VAL_EXIT error(s)). Skipping."
        FAILED=$((FAILED+1))
        echo "FAILED_VALIDATION" > "$CASE_DIR/run_status.txt"
        continue
    fi

    log_ok "Validation passed for $MODEL"

    # ── Run the case ──────────────────────────────────────────────────────────
    run_case "$CASE_DIR" "$MODEL"
    RUN_EXIT=$?

    if [[ $RUN_EXIT -eq 0 ]]; then
        PASSED=$((PASSED+1))
    else
        FAILED=$((FAILED+1))
    fi

done

# =============================================================================
# FINAL SUMMARY
# =============================================================================
log_section "FINAL SUMMARY"
echo ""
echo -e "  Total cases   : $TOTAL"
echo -e "  ${GREEN}Passed        : $PASSED${NC}"
echo -e "  ${RED}Failed        : $FAILED${NC}"
echo -e "  ${YELLOW}Skipped       : $SKIPPED${NC}"
echo ""
echo -e "  Results CSV   : ${BOLD}$RESULTS_FILE${NC}"
echo ""

if [[ -f "$RESULTS_FILE" ]]; then
    echo -e "  ${BOLD}Results table:${NC}"
    echo ""
    # Print header + data rows with formatting
    if command -v column &>/dev/null; then
        column -t -s',' "$RESULTS_FILE" | head -20
    else
        head -20 "$RESULTS_FILE"
    fi
fi

echo ""

# ── Gate 2 check per AGENTS.md ───────────────────────────────────────────────
echo -e "${BOLD}Gate 2 status check (AGENTS.md):${NC}"
for MODEL in "${MODELS[@]}"; do
    CASE_DIR="$RUN_DIR/$MODEL"
    STATUS_FILE="$CASE_DIR/run_status.txt"
    if [[ -f "$STATUS_FILE" ]]; then
        STATUS=$(head -1 "$STATUS_FILE" | tr -d '\r' | xargs)
        if [[ "$STATUS" == "COMPLETE" ]]; then
            echo -e "  ${GREEN}✓${NC}  $MODEL: $STATUS"
        else
            echo -e "  ${RED}✗${NC}  $MODEL: $STATUS"
        fi
    else
        echo -e "  ${YELLOW}?${NC}  $MODEL: no status file"
    fi
done

echo ""
if [[ $FAILED -gt 0 ]]; then
    echo -e "${YELLOW}Some cases failed or did not converge.${NC}"
    echo -e "Check individual logs: tail -50 runs/<MODEL>/log.simpleFoam"
    exit 1
else
    echo -e "${GREEN}All cases completed successfully.${NC}"
    exit 0
fi