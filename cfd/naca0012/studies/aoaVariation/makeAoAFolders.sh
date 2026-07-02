#!/bin/bash
# =============================================================================
# makeAoAFolders.sh
#
# Creates one OpenFOAM case folder per angle of attack using the validated
# Family II level 4 mesh case as the template.
#
# Usage:
#   bash makeAoAFolders.sh [OPTIONS]
#
# Options:
#   -t, --template  PATH   Converted L4 template case
#                          (default: ../meshIndependence/runs/familyII_4)
#   -o, --outdir    PATH   Output directory for AoA cases (default: ./runs)
#   -a, --aoa-list  LIST   Comma-separated AoA values (default: 0,4,8,10,12,14,15)
#   --end-time      N      SIMPLE iterations per case (default: 10000)
#   --write-interval N     Field write interval (default: 1000)
#   -h, --help             Show this help message
#
# =============================================================================

set -euo pipefail

TEMPLATE_CASE="../meshIndependence/runs/familyII_4"
OUT_DIR="./runs"
AOA_LIST="0,4,8,10,12,14,15"
END_TIME="10000"
WRITE_INTERVAL="1000"
U_INF="51.48"
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

sed_inplace() {
    local expr="$1"
    local file="$2"
    if sed --version >/dev/null 2>&1; then
        sed -i "$expr" "$file"
    else
        sed -i '' "$expr" "$file"
    fi
}

case_name_for_aoa() {
    python3 - "$1" <<'PY'
import sys
a = float(sys.argv[1])
sign = "m" if a < 0 else ""
value = abs(a)
if value.is_integer():
    text = str(int(value))
else:
    text = (f"{value:g}").replace(".", "p")
print(f"aoa_{sign}{text}")
PY
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--template) TEMPLATE_CASE="$2"; shift 2 ;;
        -o|--outdir) OUT_DIR="$2"; shift 2 ;;
        -a|--aoa-list) AOA_LIST="$2"; shift 2 ;;
        --end-time) END_TIME="$2"; shift 2 ;;
        --write-interval) WRITE_INTERVAL="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

IFS=',' read -ra AOAS <<< "$AOA_LIST"

echo ""
echo -e "${BOLD}NACA 0012 - L4 AoA Case Generator${NC}"
echo ""
log_info "Template case : $TEMPLATE_CASE"
log_info "Output dir    : $OUT_DIR"
log_info "AoA list      : ${AOAS[*]}"
log_info "Model         : $MODEL"
log_info "End time      : $END_TIME"
log_info "Write interval: $WRITE_INTERVAL"

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

for subdir in 0 constant system constant/polyMesh; do
    if [[ ! -d "$TEMPLATE_CASE/$subdir" ]]; then
        log_error "Template missing directory: $TEMPLATE_CASE/$subdir"
        ERRORS=$((ERRORS+1))
    else
        log_ok "Template has: $subdir"
    fi
done

for file in 0/include/initialConditions 0/U system/controlDict constant/turbulenceProperties; do
    if [[ ! -f "$TEMPLATE_CASE/$file" ]]; then
        log_error "Template missing file: $TEMPLATE_CASE/$file"
        ERRORS=$((ERRORS+1))
    else
        log_ok "Template has: $file"
    fi
done

for aoa in "${AOAS[@]}"; do
    if ! [[ "$aoa" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
        log_error "AoA must be numeric, got: $aoa"
        ERRORS=$((ERRORS+1))
    fi
done

if [[ $ERRORS -gt 0 ]]; then
    log_error "$ERRORS pre-flight error(s). Aborting."
    exit 1
fi

log_section "CREATING AOA CASES"
mkdir -p "$OUT_DIR"
CREATED=0
SKIPPED=0

for aoa in "${AOAS[@]}"; do
    CASE_NAME=$(case_name_for_aoa "$aoa")
    CASE_DIR="$OUT_DIR/$CASE_NAME"

    if [[ -d "$CASE_DIR" ]]; then
        log_warn "Already exists, skipping: $CASE_DIR"
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    read -r AOA_RAD UX UZ LIFT_X LIFT_Z DRAG_X DRAG_Z < <(python3 - "$aoa" "$U_INF" <<'PY'
import math
import sys
aoa = float(sys.argv[1])
u_inf = float(sys.argv[2])
rad = math.radians(aoa)
print(rad, u_inf * math.cos(rad), u_inf * math.sin(rad), -math.sin(rad), math.cos(rad), math.cos(rad), math.sin(rad))
PY
)

    AOA_RAD_FMT=$(printf "%.15f" "$AOA_RAD")
    UX_FMT=$(printf "%.6f" "$UX")
    UZ_FMT=$(printf "%.6f" "$UZ")
    LIFT_X_FMT=$(printf "%.8f" "$LIFT_X")
    LIFT_Z_FMT=$(printf "%.8f" "$LIFT_Z")
    DRAG_X_FMT=$(printf "%.8f" "$DRAG_X")
    DRAG_Z_FMT=$(printf "%.8f" "$DRAG_Z")

    log_info "Creating $CASE_NAME: flowVelocity=($UX_FMT 0 $UZ_FMT)"
    cp -r "$TEMPLATE_CASE" "$CASE_DIR"

    rm -rf "$CASE_DIR"/processor* \
           "$CASE_DIR/postProcessing" \
           "$CASE_DIR/postProcessing-dry-run" \
           "$CASE_DIR/dynamicCode" \
           "$CASE_DIR/VTK" \
           "$CASE_DIR/sets" \
           "$CASE_DIR/surfaces"
    rm -f "$CASE_DIR"/log.* "$CASE_DIR"/*.log "$CASE_DIR"/run_status*.txt
    find "$CASE_DIR" -maxdepth 1 -type d -regex '.*/[1-9][0-9]*\(\.[0-9]+\)?' -exec rm -rf {} +

    IC_FILE="$CASE_DIR/0/include/initialConditions"
    sed_inplace "s/^AoA[[:space:]].*/AoA             $aoa;/" "$IC_FILE"
    sed_inplace "s/^AoA_rad[[:space:]].*/AoA_rad         $AOA_RAD_FMT;/" "$IC_FILE"
    sed_inplace "s/^U_inf[[:space:]].*/U_inf           $U_INF;      \/\/ m\/s/" "$IC_FILE"
    sed_inplace "s/^Ux[[:space:]].*/Ux              $UX_FMT;/" "$IC_FILE"
    sed_inplace "s/^Uz[[:space:]].*/Uz              $UZ_FMT;/" "$IC_FILE"
    sed_inplace "s/^flowVelocity[[:space:]].*/flowVelocity    ($UX_FMT 0 $UZ_FMT);/" "$IC_FILE"

    CD_FILE="$CASE_DIR/system/controlDict"
    perl -0pi -e "s/startFrom\s+\w+;/startFrom       startTime;/" "$CD_FILE"
    perl -0pi -e "s/startTime\s+[-+0-9.eE]+;/startTime       0;/" "$CD_FILE"
    perl -0pi -e "s/endTime\s+[-+0-9.eE]+;/endTime         $END_TIME;/" "$CD_FILE"
    perl -0pi -e "s/writeInterval\s+[-+0-9.eE]+;/writeInterval   $WRITE_INTERVAL;/" "$CD_FILE"
    perl -0pi -e "s/liftDir\s+\([^)]*\);/liftDir         ($LIFT_X_FMT 0 $LIFT_Z_FMT);/g" "$CD_FILE"
    perl -0pi -e "s/dragDir\s+\([^)]*\);/dragDir         ($DRAG_X_FMT 0 $DRAG_Z_FMT);/g" "$CD_FILE"
    perl -0pi -e "s/UInf\s+\([^)]*\);/UInf            ($UX_FMT 0 $UZ_FMT);/g" "$CD_FILE"

    cat > "$CASE_DIR/case_meta.txt" << EOF
study=aoaVariation
case_name=${CASE_NAME}
template_case=$(cd "$(dirname "$TEMPLATE_CASE")" && pwd)/$(basename "$TEMPLATE_CASE")
grid_family=familyII
grid_level=4
model=${MODEL}
aoa=${aoa}
created=$(date -Iseconds)
endTime=${END_TIME}
writeInterval=${WRITE_INTERVAL}
U_inf=${U_INF}
AoA_rad=${AOA_RAD_FMT}
Ux=${UX_FMT}
Uz=${UZ_FMT}
flowVelocity=(${UX_FMT} 0 ${UZ_FMT})
liftDir=(${LIFT_X_FMT} 0 ${LIFT_Z_FMT})
dragDir=(${DRAG_X_FMT} 0 ${DRAG_Z_FMT})
EOF

    log_ok "Created: $CASE_DIR"
    CREATED=$((CREATED+1))
done

log_section "SUMMARY"
echo "Created : $CREATED case(s)"
echo "Skipped : $SKIPPED case(s)"
echo "Output  : $OUT_DIR"
