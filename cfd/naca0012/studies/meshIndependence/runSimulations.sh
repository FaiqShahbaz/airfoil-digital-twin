#!/bin/bash
# =============================================================================
# runSimulations.sh
#
# Runs simpleFoam for NACA0012 Family II mesh-independence cases.
# Cases are expected to be created by makeMeshFolders.sh and meshed by
# convertMeshes.sh.
#
# Usage:
#   bash runSimulations.sh [OPTIONS]
#
# Options:
#   -r, --rundir     PATH   Directory containing familyII case folders (default: ./runs)
#   -l, --levels     LIST   Comma-separated Family II levels (default: 1,2,3,4,5,6,7)
#   -n, --np         N      MPI processes per case (default: 1)
#   -c, --continue          Resume from latest time directory if case exists
#   -f, --force             Re-run even if case is already complete
#   -t, --timeout    SECS   Kill a case if it exceeds this wall time (default: 7200)
#   -w, --window     N      Final force samples used for statistics (default: 500)
#   -h, --help              Show this help message
#
# =============================================================================

set -uo pipefail

RUN_DIR="./runs"
LEVELS_ARG="1,2,3,4,5,6,7"
NP=1
CONTINUE_RUN=false
FORCE_RERUN=false
TIMEOUT=7200
RESULTS_DIR="./results"
RESULTS_FILE=""
FORCE_WINDOW=500
MODEL="SpalartAllmaras"

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
log_section() { echo -e "\n${BOLD}${CYAN}== $* ==${NC}"; }

usage() {
    sed -n '3,27p' "$0" | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--rundir)   RUN_DIR="$2"; shift 2 ;;
        -l|--levels)   LEVELS_ARG="$2"; shift 2 ;;
        -n|--np)       NP="$2"; shift 2 ;;
        -c|--continue) CONTINUE_RUN=true; shift ;;
        -f|--force)    FORCE_RERUN=true; shift ;;
        -t|--timeout)  TIMEOUT="$2"; shift 2 ;;
        -w|--window)   FORCE_WINDOW="$2"; shift 2 ;;
        -h|--help)     usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

IFS=',' read -ra LEVELS <<< "$LEVELS_ARG"

echo ""
echo -e "${BOLD}NACA 0012 - Family II Mesh Simulation Runner${NC}"
echo ""
log_info "Run directory : $RUN_DIR"
log_info "Levels        : ${LEVELS[*]}"
log_info "Model         : $MODEL"
log_info "MPI processes : $NP"
log_info "Timeout/case  : ${TIMEOUT}s"
log_info "Force window  : $FORCE_WINDOW"
log_info "Continue mode : $CONTINUE_RUN"
log_info "Force rerun   : $FORCE_RERUN"

log_section "GLOBAL PRE-FLIGHT CHECKS"
GLOBAL_ERRORS=0

if [[ -z "${WM_PROJECT:-}" ]]; then
    log_error "OpenFOAM environment not loaded."
    log_error "Source OpenFOAM first, for example: source /usr/lib/openfoam/openfoam2412/etc/bashrc"
    GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
else
    log_ok "OpenFOAM ${WM_PROJECT_VERSION:-unknown} loaded"
fi

for exe in simpleFoam checkMesh reconstructPar timeout awk grep sort find; do
    if ! command -v "$exe" >/dev/null 2>&1; then
        log_error "$exe not found in PATH"
        GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
    else
        log_ok "$exe: $(command -v "$exe")"
    fi
done

if [[ "$NP" -gt 1 ]]; then
    for exe in mpirun decomposePar; do
        if ! command -v "$exe" >/dev/null 2>&1; then
            log_error "$exe not found in PATH"
            GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
        else
            log_ok "$exe: $(command -v "$exe")"
        fi
    done
fi

if [[ ! -d "$RUN_DIR" ]]; then
    log_error "Run directory not found: $RUN_DIR"
    GLOBAL_ERRORS=$((GLOBAL_ERRORS+1))
fi

if [[ $GLOBAL_ERRORS -gt 0 ]]; then
    log_error "$GLOBAL_ERRORS global error(s). Aborting."
    exit 1
fi

mkdir -p "$RESULTS_DIR"
if [[ -z "$RESULTS_FILE" ]]; then
    RESULTS_FILE="$RESULTS_DIR/mesh_independence_summary_$(date +%Y%m%d_%H%M%S).csv"
fi

echo "grid_family,grid_level,case,model,aoa,status,Cl_final,Cd_final,Cl_mean,Cd_mean,Cl_std,Cd_std,Cl_drift_pct,Cd_drift_pct,iterations,wall_time_s,timestamp" > "$RESULTS_FILE"

find_force_coeff_file() {
    local case_dir="$1"
    find "$case_dir/postProcessing/forceCoeffs" -type f -name "*.dat" 2>/dev/null | sort | tail -1
}

force_column_index() {
    local file="$1"
    local name="$2"
    local header
    header=$(grep '^#' "$file" | grep -E "Time|Cm|Cd|Cl|coefficient" | tail -1 | sed 's/^#//')
    [[ -n "$header" ]] || return 1
    awk -v target="$name" '{ for (i=1; i<=NF; i++) { gsub(/[()]/, "", $i); if ($i == target) { print i; exit 0 } } exit 1 }' <<< "$header"
}

extract_force_stats() {
    local file="$1"
    local window="$2"
    local cl_col cd_col
    cd_col=$(force_column_index "$file" "Cd" || true)
    cl_col=$(force_column_index "$file" "Cl" || true)
    [[ -n "$cd_col" ]] || cd_col=3
    [[ -n "$cl_col" ]] || cl_col=4

    grep -v '^#' "$file" | awk -v clc="$cl_col" -v cdc="$cd_col" -v n="$window" '
    NF >= clc && NF >= cdc {
        cl[++count] = $clc + 0.0
        cd[count] = $cdc + 0.0
    }
    END {
        if (count == 0) {
            print "N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A"
            exit 0
        }
        start = count - n + 1
        if (start < 1) start = 1
        m = count - start + 1
        cl_first = cl[start]
        cd_first = cd[start]
        cl_last = cl[count]
        cd_last = cd[count]
        for (i=start; i<=count; i++) { cl_sum += cl[i]; cd_sum += cd[i] }
        cl_mean = cl_sum / m
        cd_mean = cd_sum / m
        for (i=start; i<=count; i++) { cl_var += (cl[i]-cl_mean)^2; cd_var += (cd[i]-cd_mean)^2 }
        cl_std = sqrt(cl_var / m)
        cd_std = sqrt(cd_var / m)
        cl_drift = (cl_mean != 0 ? 100.0 * (cl_last - cl_first) / cl_mean : 0)
        cd_drift = (cd_mean != 0 ? 100.0 * (cd_last - cd_first) / cd_mean : 0)
        printf "%.8g,%.8g,%.8g,%.8g,%.8g,%.8g,%.8g,%.8g\n", cl_last, cd_last, cl_mean, cd_mean, cl_std, cd_std, cl_drift, cd_drift
    }'
}

case_meta_value() {
    local case_dir="$1"
    local key="$2"
    grep "^${key}=" "$case_dir/case_meta.txt" 2>/dev/null | head -1 | cut -d= -f2-
}

validate_case() {
    local case_dir="$1"
    local case_name="$2"
    local errors=0

    log_section "VALIDATING: $case_name"

    for field in U p nut nuTilda; do
        if [[ ! -f "$case_dir/0/$field" ]]; then
            log_error "Missing field: 0/$field"
            errors=$((errors+1))
        else
            log_ok "0/$field exists"
        fi
    done

    if [[ ! -f "$case_dir/constant/turbulenceProperties" ]]; then
        log_error "Missing constant/turbulenceProperties"
        errors=$((errors+1))
    else
        active_model=$(grep -E "^[[:space:]]*RASModel[[:space:]]+" "$case_dir/constant/turbulenceProperties" | awk '{print $2}' | tr -d ';' | head -1)
        if [[ "$active_model" != "$MODEL" ]]; then
            log_error "Expected RASModel=$MODEL, found: ${active_model:-none}"
            errors=$((errors+1))
        else
            log_ok "RASModel = $MODEL"
        fi
    fi

    if [[ ! -d "$case_dir/constant/polyMesh" ]]; then
        log_error "No polyMesh found. Run convertMeshes.sh first."
        errors=$((errors+1))
    elif [[ ! -f "$case_dir/constant/polyMesh/boundary" ]]; then
        log_error "Missing constant/polyMesh/boundary"
        errors=$((errors+1))
    else
        for patch in airfoil farfield front back; do
            if ! grep -q "^[[:space:]]*$patch[[:space:]]*$" "$case_dir/constant/polyMesh/boundary"; then
                log_error "Missing boundary patch: $patch"
                errors=$((errors+1))
            else
                log_ok "Boundary patch found: $patch"
            fi
        done
    fi

    for sysfile in controlDict fvSchemes fvSolution; do
        if [[ ! -f "$case_dir/system/$sysfile" ]]; then
            log_error "Missing system/$sysfile"
            errors=$((errors+1))
        else
            log_ok "system/$sysfile exists"
        fi
    done

    if [[ -f "$case_dir/run_status.txt" ]]; then
        status=$(head -1 "$case_dir/run_status.txt" | tr -d '\r')
        if [[ "$status" == "COMPLETE" && "$FORCE_RERUN" == "false" ]]; then
            log_warn "Case already COMPLETE. Use --force to re-run."
            return 2
        fi
    fi

    return $errors
}

write_result_row() {
    local case_dir="$1"
    local case_name="$2"
    local status="$3"
    local iterations="$4"
    local wall_time="$5"
    local stats="$6"

    local grid_family grid_level aoa
    grid_family=$(case_meta_value "$case_dir" grid_family)
    grid_level=$(case_meta_value "$case_dir" grid_level)
    aoa=$(case_meta_value "$case_dir" aoa)
    [[ -n "$grid_family" ]] || grid_family="familyII"
    [[ -n "$grid_level" ]] || grid_level="${case_name#familyII_}"
    [[ -n "$aoa" ]] || aoa="10"

    echo "$grid_family,$grid_level,$case_name,$MODEL,$aoa,$status,$stats,$iterations,$wall_time,$(date -Iseconds)" >> "$RESULTS_FILE"
}

check_convergence() {
    local case_dir="$1"
    local case_name="$2"
    local wall_time="$3"
    local log="$case_dir/log.simpleFoam"
    local status="UNKNOWN"
    local iterations="0"
    local stats="N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A"

    if grep -q "^End$" "$log" 2>/dev/null; then
        status="COMPLETE"
    elif grep -q "FOAM FATAL ERROR\|FOAM exiting\|Floating point exception\|Segmentation fault" "$log" 2>/dev/null; then
        status="CRASHED"
    else
        status="INCOMPLETE"
    fi

    iterations=$(grep -c "^Time = " "$log" 2>/dev/null || true)
    [[ -n "$iterations" ]] || iterations=0

    fc_file=$(find_force_coeff_file "$case_dir")
    if [[ -n "$fc_file" && -f "$fc_file" ]]; then
        stats=$(extract_force_stats "$fc_file" "$FORCE_WINDOW")
        IFS=',' read -r cl cd cl_mean cd_mean cl_std cd_std cl_drift cd_drift <<< "$stats"
        log_ok "Cl mean = $cl_mean, Cd mean = $cd_mean over final window"
    else
        log_warn "forceCoeffs output not found"
    fi

    cat > "$case_dir/log.convergence" << EOF
case           = $case_name
model          = $MODEL
status         = $status
iterations     = $iterations
force_window   = $FORCE_WINDOW
stats          = $stats
wall_time_s    = $wall_time
timestamp      = $(date -Iseconds)
EOF

    write_result_row "$case_dir" "$case_name" "$status" "$iterations" "$wall_time" "$stats"
    echo "$status" > "$case_dir/run_status.txt"

    if [[ "$status" == "COMPLETE" ]]; then
        log_ok "$case_name: COMPLETE"
        return 0
    fi

    log_warn "$case_name: $status"
    return 1
}

run_case() {
    local case_dir="$1"
    local case_name="$2"

    log_section "RUNNING: $case_name"
    echo "RUNNING" > "$case_dir/run_status.txt"
    t_start=$(date +%s)

    log_info "Running checkMesh..."
    (cd "$case_dir" && checkMesh -noFunctionObjects > log.checkMesh 2>&1)
    cm_exit=$?
    if [[ $cm_exit -ne 0 ]]; then
        log_warn "checkMesh exited with code $cm_exit. Check $case_dir/log.checkMesh"
    fi
    if grep -q "FOAM FATAL ERROR\|negative volume" "$case_dir/log.checkMesh" 2>/dev/null; then
        log_error "Fatal mesh error. Skipping solver."
        echo "FAILED_MESH" > "$case_dir/run_status.txt"
        write_result_row "$case_dir" "$case_name" "FAILED_MESH" "0" "0" "N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A"
        return 1
    fi

    if [[ "$NP" -gt 1 ]]; then
        log_info "Decomposing domain for $NP processors..."
        rm -rf "$case_dir"/processor*
        if [[ ! -f "$case_dir/system/decomposeParDict" ]]; then
            cat > "$case_dir/system/decomposeParDict" << EOF
FoamFile { version 2.0; format ascii; class dictionary; location "system"; object decomposeParDict; }
numberOfSubdomains  $NP;
method              scotch;
EOF
        fi
        (cd "$case_dir" && decomposePar -force > log.decomposePar 2>&1)
        if [[ $? -ne 0 ]]; then
            log_error "decomposePar failed. Check $case_dir/log.decomposePar"
            echo "FAILED_DECOMPOSE" > "$case_dir/run_status.txt"
            return 1
        fi
    fi

    if [[ "$CONTINUE_RUN" == "true" ]]; then
        solver_start="latestTime"
    else
        solver_start="startTime"
    fi

    if [[ -f "$case_dir/system/controlDict" ]]; then
        perl -0pi -e "s/startFrom\s+\w+;/startFrom       $solver_start;/" "$case_dir/system/controlDict"
    fi

    if [[ "$NP" -gt 1 ]]; then
        if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
            run_cmd="mpirun --allow-run-as-root -np $NP simpleFoam -parallel"
        else
            run_cmd="mpirun -np $NP simpleFoam -parallel"
        fi
    else
        run_cmd="simpleFoam"
    fi

    log_info "Running simpleFoam with startFrom=$solver_start..."
    log_info "Log: $case_dir/log.simpleFoam"
    (cd "$case_dir" && timeout "$TIMEOUT" $run_cmd > log.simpleFoam 2>&1)
    solver_exit=$?

    t_end=$(date +%s)
    wall_time=$((t_end - t_start))

    if [[ $solver_exit -eq 124 ]]; then
        log_error "simpleFoam timed out after ${TIMEOUT}s"
        echo "TIMEOUT" > "$case_dir/run_status.txt"
        write_result_row "$case_dir" "$case_name" "TIMEOUT" "0" "$wall_time" "N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A"
        return 1
    elif [[ $solver_exit -ne 0 ]]; then
        log_warn "simpleFoam exited with code $solver_exit. Attempting result extraction."
    fi

    if [[ "$NP" -gt 1 ]]; then
        log_info "Reconstructing latest time..."
        (cd "$case_dir" && reconstructPar -latestTime > log.reconstructPar 2>&1)
        if [[ $? -ne 0 ]]; then
            log_warn "reconstructPar failed. Force coefficients may still be available."
        fi
    fi

    check_convergence "$case_dir" "$case_name" "$wall_time"
}

log_section "STARTING SIMULATIONS"
TOTAL=${#LEVELS[@]}
PASSED=0
FAILED=0
SKIPPED=0

for level in "${LEVELS[@]}"; do
    CASE_NAME="familyII_${level}"
    CASE_DIR="$RUN_DIR/$CASE_NAME"

    if [[ ! -d "$CASE_DIR" ]]; then
        log_error "Case directory not found: $CASE_DIR"
        FAILED=$((FAILED+1))
        continue
    fi

    validate_case "$CASE_DIR" "$CASE_NAME"
    val_exit=$?
    if [[ $val_exit -eq 2 ]]; then
        SKIPPED=$((SKIPPED+1))
        continue
    elif [[ $val_exit -ne 0 ]]; then
        log_error "Validation failed for $CASE_NAME"
        echo "FAILED_VALIDATION" > "$CASE_DIR/run_status.txt"
        FAILED=$((FAILED+1))
        continue
    fi

    run_case "$CASE_DIR" "$CASE_NAME"
    run_exit=$?
    if [[ $run_exit -eq 0 ]]; then
        PASSED=$((PASSED+1))
    else
        FAILED=$((FAILED+1))
    fi
done

log_section "FINAL SUMMARY"
echo "Total cases : $TOTAL"
echo "Passed      : $PASSED"
echo "Failed      : $FAILED"
echo "Skipped     : $SKIPPED"
echo "Results CSV : $RESULTS_FILE"

if [[ -f "$RESULTS_FILE" ]]; then
    echo ""
    if command -v column >/dev/null 2>&1; then
        column -t -s',' "$RESULTS_FILE" | head -20
    else
        head -20 "$RESULTS_FILE"
    fi
fi

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi

exit 0
