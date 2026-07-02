#!/bin/bash
# =============================================================================
# makeMeshFolders.sh
#
# Creates one OpenFOAM case folder per NASA NACA0012 Family II grid level.
# The turbulence model is fixed to SpalartAllmaras so only mesh resolution varies.
#
# Usage:
#   bash makeMeshFolders.sh [OPTIONS]
#
# Options:
#   -b, --base      PATH   Base case directory
#                          (default: ../../baseCase/naca0012_SA_familyII5)
#   -o, --outdir    PATH   Output directory for mesh cases (default: ./runs)
#   -g, --grids     PATH   NASA grid directory
#                          (default: ../../grids/NACA0012numerics_grids)
#   -l, --levels    LIST   Comma-separated Family II levels (default: 1,2,3,4,5,6,7)
#   -a, --aoa       DEG    Angle of attack in degrees (default: 10)
#   -h, --help             Show this help message
#
# Output:
#   runs/
#     familyII_1/
#     familyII_2/
#     ...
#     familyII_7/
#
# =============================================================================

set -euo pipefail

BASE_CASE="../../baseCase/naca0012_SA_familyII5"
OUT_DIR="./runs"
GRID_DIR="../../grids/NACA0012numerics_grids"
LEVELS_ARG="1,2,3,4,5,6,7"
AOA=10
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
    sed -n '3,36p' "$0" | sed 's/^# \?//'
    exit 0
}

sed_inplace() {
    local expr="$1"
    local file="$2"
    if sed --version >/dev/null 2>&1; then
        sed -i "$expr" "$file"
    else
        sed -i '' "$expr" "$file"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -b|--base)   BASE_CASE="$2"; shift 2 ;;
        -o|--outdir) OUT_DIR="$2"; shift 2 ;;
        -g|--grids)  GRID_DIR="$2"; shift 2 ;;
        -l|--levels) LEVELS_ARG="$2"; shift 2 ;;
        -a|--aoa)    AOA="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

IFS=',' read -ra LEVELS <<< "$LEVELS_ARG"

echo ""
echo -e "${BOLD}NACA 0012 - Family II Mesh Case Generator${NC}"
echo ""
log_info "Base case  : $BASE_CASE"
log_info "Output dir : $OUT_DIR"
log_info "Grid dir   : $GRID_DIR"
log_info "Levels     : ${LEVELS[*]}"
log_info "Model      : $MODEL"
log_info "AoA        : ${AOA} deg"

log_section "PRE-FLIGHT CHECKS"
ERRORS=0

for util in python3 cp rm grep perl sed date; do
    if ! command -v "$util" >/dev/null 2>&1; then
        log_error "Required utility not found in PATH: $util"
        ERRORS=$((ERRORS+1))
    else
        log_ok "Utility found: $util"
    fi
done

if [[ ! -d "$BASE_CASE" ]]; then
    log_error "Base case directory not found: $BASE_CASE"
    ERRORS=$((ERRORS+1))
else
    log_ok "Base case exists"
fi

if [[ ! -d "$GRID_DIR" ]]; then
    log_error "Grid directory not found: $GRID_DIR"
    ERRORS=$((ERRORS+1))
else
    log_ok "Grid directory exists"
fi

for subdir in 0 constant system; do
    if [[ ! -d "$BASE_CASE/$subdir" ]]; then
        log_error "Missing base case directory: $BASE_CASE/$subdir"
        ERRORS=$((ERRORS+1))
    else
        log_ok "Found base case directory: $subdir"
    fi
done

for file in constant/turbulenceProperties constant/transportProperties system/controlDict system/fvSchemes system/fvSolution 0/U 0/p 0/nut 0/nuTilda 0/include/initialConditions; do
    if [[ ! -f "$BASE_CASE/$file" ]]; then
        log_error "Missing base case file: $BASE_CASE/$file"
        ERRORS=$((ERRORS+1))
    else
        log_ok "Found base case file: $file"
    fi
done

if ! [[ "$AOA" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
    log_error "AoA must be numeric, got: $AOA"
    ERRORS=$((ERRORS+1))
fi

for level in "${LEVELS[@]}"; do
    if ! [[ "$level" =~ ^[1-7]$ ]]; then
        log_error "Invalid Family II level: $level. Valid levels are 1-7."
        ERRORS=$((ERRORS+1))
        continue
    fi
    if [[ ! -f "$GRID_DIR/n0012familyII.${level}.p3dfmt.gz" ]]; then
        log_error "Missing grid file: $GRID_DIR/n0012familyII.${level}.p3dfmt.gz"
        ERRORS=$((ERRORS+1))
    else
        log_ok "Found Family II level $level PLOT3D grid"
    fi
done

if [[ $ERRORS -gt 0 ]]; then
    log_error "$ERRORS pre-flight error(s). Aborting."
    exit 1
fi

U_INF="51.48"
read -r AOA_RAD UX UZ LIFT_X LIFT_Z DRAG_X DRAG_Z < <(python3 - "$AOA" "$U_INF" <<'PY'
import math
import sys

aoa = float(sys.argv[1])
u_inf = float(sys.argv[2])
rad = math.radians(aoa)
print(
    rad,
    u_inf * math.cos(rad),
    u_inf * math.sin(rad),
    -math.sin(rad),
    math.cos(rad),
    math.cos(rad),
    math.sin(rad),
)
PY
)

AOA_RAD_FMT=$(printf "%.15f" "$AOA_RAD")
UX_FMT=$(printf "%.6f" "$UX")
UZ_FMT=$(printf "%.6f" "$UZ")
LIFT_X=$(printf "%.8f" "$LIFT_X")
LIFT_Z=$(printf "%.8f" "$LIFT_Z")
DRAG_X=$(printf "%.8f" "$DRAG_X")
DRAG_Z=$(printf "%.8f" "$DRAG_Z")

log_info "AoA=${AOA} deg: flowVelocity=($UX_FMT 0 $UZ_FMT)"
log_info "AoA=${AOA} deg: liftDir=($LIFT_X 0 $LIFT_Z), dragDir=($DRAG_X 0 $DRAG_Z)"

log_section "CREATING MESH CASES"
mkdir -p "$OUT_DIR"
CREATED=0
SKIPPED=0

for level in "${LEVELS[@]}"; do
    CASE_NAME="familyII_${level}"
    CASE_DIR="$OUT_DIR/$CASE_NAME"
    GRID_FILE="$GRID_DIR/n0012familyII.${level}.p3dfmt.gz"

    if [[ -d "$CASE_DIR" ]]; then
        log_warn "Already exists, skipping: $CASE_DIR"
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    log_info "Creating: $CASE_DIR"
    cp -r "$BASE_CASE" "$CASE_DIR"

    rm -rf "$CASE_DIR/constant/polyMesh" \
           "$CASE_DIR"/processor* \
           "$CASE_DIR/postProcessing" \
           "$CASE_DIR/dynamicCode" \
           "$CASE_DIR/VTK" \
           "$CASE_DIR/sets" \
           "$CASE_DIR/surfaces"
    rm -f "$CASE_DIR"/log.* "$CASE_DIR"/*.log "$CASE_DIR/run_status.txt"

    IC_FILE="$CASE_DIR/0/include/initialConditions"
    sed_inplace "s/^AoA[[:space:]].*/AoA             $AOA;/" "$IC_FILE"
    sed_inplace "s/^AoA_rad[[:space:]].*/AoA_rad         $AOA_RAD_FMT;/" "$IC_FILE"
    sed_inplace "s/^U_inf[[:space:]].*/U_inf           $U_INF;      \/\/ m\/s/" "$IC_FILE"
    sed_inplace "s/^Ux[[:space:]].*/Ux              $UX_FMT;/" "$IC_FILE"
    sed_inplace "s/^Uz[[:space:]].*/Uz              $UZ_FMT;/" "$IC_FILE"
    sed_inplace "s/^flowVelocity[[:space:]].*/flowVelocity    ($UX_FMT 0 $UZ_FMT);/" "$IC_FILE"

    TP_FILE="$CASE_DIR/constant/turbulenceProperties"
    if grep -q "^[[:space:]]*RASModel[[:space:]]" "$TP_FILE"; then
        sed_inplace "s/^[[:space:]]*RASModel[[:space:]].*/    RASModel        ${MODEL};/" "$TP_FILE"
    else
        log_error "No active RASModel entry found in $TP_FILE"
        exit 1
    fi

    CD_FILE="$CASE_DIR/system/controlDict"
    perl -0pi -e "s/liftDir\s+\([^)]*\);/liftDir         ($LIFT_X 0 $LIFT_Z);/g" "$CD_FILE"
    perl -0pi -e "s/dragDir\s+\([^)]*\);/dragDir         ($DRAG_X 0 $DRAG_Z);/g" "$CD_FILE"
    perl -0pi -e "s/UInf\s+\([^)]*\);/UInf            ($UX_FMT 0 $UZ_FMT);/g" "$CD_FILE"

    cat > "$CASE_DIR/case_meta.txt" << EOF
study=meshIndependence
grid_family=familyII
grid_level=${level}
case_name=${CASE_NAME}
model=${MODEL}
aoa=${AOA}
created=$(date -Iseconds)
base_case=$(cd "$(dirname "$BASE_CASE")" && pwd)/$(basename "$BASE_CASE")
grid_file=$(cd "$(dirname "$GRID_FILE")" && pwd)/$(basename "$GRID_FILE")
required_fields=nuTilda nut
U_inf=${U_INF}
AoA_rad=${AOA_RAD_FMT}
Ux=${UX_FMT}
Uz=${UZ_FMT}
flowVelocity=(${UX_FMT} 0 ${UZ_FMT})
liftDir=(${LIFT_X} 0 ${LIFT_Z})
dragDir=(${DRAG_X} 0 ${DRAG_Z})
EOF

    log_ok "Created: $CASE_DIR"
    CREATED=$((CREATED+1))
done

log_section "SUMMARY"
echo "Created : $CREATED case(s)"
echo "Skipped : $SKIPPED case(s)"
echo "Output  : $OUT_DIR"
echo ""
echo "Next steps:"
echo "  bash convertMeshes.sh"
echo "  bash runSimulations.sh --np 6 --timeout 14400 --window 500"
