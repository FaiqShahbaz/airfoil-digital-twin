#!/bin/bash
# =============================================================================
# convertMeshes.sh
#
# Converts NASA/TMR NACA0012 Family II formatted PLOT3D grids into OpenFOAM
# polyMesh folders for cases created by makeMeshFolders.sh.
#
# Usage:
#   bash convertMeshes.sh [OPTIONS]
#
# Options:
#   -r, --rundir  PATH   Directory containing familyII case folders (default: ./runs)
#   -g, --grids   PATH   NASA grid directory (default: ../grids/NACA0012numerics_grids)
#   -l, --levels  LIST   Comma-separated Family II levels (default: 1,2,3,4,5,6,7)
#   -f, --force          Remove existing polyMesh and reconvert
#   --no-dry-run         Skip simpleFoam -dry-run after checkMesh
#   -h, --help           Show this help message
#
# =============================================================================

set -euo pipefail

RUN_DIR="./runs"
GRID_DIR="../grids/NACA0012numerics_grids"
LEVELS_ARG="1,2,3,4,5,6,7"
FORCE=false
DRY_RUN=true

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
    sed -n '3,26p' "$0" | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--rundir) RUN_DIR="$2"; shift 2 ;;
        -g|--grids)  GRID_DIR="$2"; shift 2 ;;
        -l|--levels) LEVELS_ARG="$2"; shift 2 ;;
        -f|--force)  FORCE=true; shift ;;
        --no-dry-run) DRY_RUN=false; shift ;;
        -h|--help)   usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

IFS=',' read -ra LEVELS <<< "$LEVELS_ARG"

require_exe() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_error "$1 not found in PATH"
        return 1
    fi
    log_ok "$1: $(command -v "$1")"
}

boundary_start_face() {
    local boundary_file="$1"
    awk '/startFace/ { gsub(/;/, "", $2); print $2; exit }' "$boundary_file"
}

write_create_patch_dict() {
    local case_dir="$1"

    cat > "$case_dir/system/createPatchDict" << EOF
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      createPatchDict;
}

pointSync false;

patches
(
    {
        name front;
        patchInfo { type empty; }
        constructFrom set;
        set frontFaces;
    }
    {
        name back;
        patchInfo { type empty; }
        constructFrom set;
        set backFaces;
    }
    {
        name airfoil;
        patchInfo { type wall; }
        constructFrom set;
        set airfoilFaces;
    }
    {
        name farfield;
        patchInfo { type patch; }
        constructFrom set;
        set farfieldFaces;
    }
);
EOF
}

nmf_mesh_info() {
    local nmf_file="$1"
    awk '
        /^#/ || NF == 0 { next }
        blockSeen == 0 { blockSeen=1; next }
        dimsSeen == 0 && NF >= 4 {
            span=$2; ni=$3; nj=$4; dimsSeen=1; next
        }
        $1 ~ /viscous_solid/ && NF >= 7 {
            airStart=$6; airEnd=$7
        }
        END {
            if (!dimsSeen || airStart == "" || airEnd == "") exit 1
            print span, ni, nj, airStart, airEnd
        }
    ' "$nmf_file"
}

split_default_faces() {
    local case_dir="$1"
    local nmf_file="$2"

    perl - "$case_dir" "$nmf_file" > "$case_dir/log.patchSplit" 2>&1 <<'PERL'
use strict;
use warnings;

my ($caseDir, $nmfFile) = @ARGV;
my $poly = "$caseDir/constant/polyMesh";
my $boundaryFile = "$poly/boundary";
my $facesFile = "$poly/faces";
my $pointsFile = "$poly/points";
my $setsDir = "$poly/sets";
my $airfoilZLimit = 0.2;
my $xTol = 1e-6;

sub read_boundary_default {
    my ($file) = @_;
    open(my $fh, '<', $file) or die "Cannot open $file: $!\n";
    local $/;
    my $txt = <$fh>;
    close($fh);
    $txt =~ /defaultFaces\s*\{.*?nFaces\s+(\d+)\s*;.*?startFace\s+(\d+)\s*;/s
        or die "Could not find defaultFaces nFaces/startFace in $file\n";
    return ($2 + 0, $1 + 0);
}

sub read_nmf_expected {
    my ($file) = @_;
    open(my $fh, '<', $file) or die "Cannot open $file: $!\n";
    my ($blockSeen, $dimsSeen) = (0, 0);
    my ($span, $ni, $nj, $airStart, $airEnd);
    while (my $line = <$fh>) {
        next if $line =~ /^\s*#/ || $line =~ /^\s*$/;
        my @f = split(' ', $line);
        if (!$blockSeen) { $blockSeen = 1; next; }
        if (!$dimsSeen && @f >= 4) {
            ($span, $ni, $nj) = @f[1,2,3];
            $dimsSeen = 1;
            next;
        }
        if ($line =~ /viscous_solid/ && @f >= 7) {
            ($airStart, $airEnd) = @f[5,6];
        }
    }
    close($fh);
    die "Could not parse dimensions/airfoil range from $file\n"
        unless defined $ni && defined $nj && defined $airStart && defined $airEnd;
    return (
        ($ni - 1) * ($nj - 1),
        ($ni - 1) * ($nj - 1),
        $airEnd - $airStart,
        2 * ($nj - 1) + ($ni - 1),
        $span, $ni, $nj, $airStart, $airEnd
    );
}

sub parse_face_indices {
    my ($line) = @_;
    return unless $line =~ /\(([^()]*)\)/;
    return split(' ', $1);
}

sub read_boundary_faces {
    my ($file, $start, $nFaces) = @_;
    open(my $fh, '<', $file) or die "Cannot open $file: $!\n";
    my $inList = 0;
    my $faceId = 0;
    my (@front, @back, @sideFaces);
    my %sidePointNeeded;

    while (my $line = <$fh>) {
        my $s = $line;
        $s =~ s/^\s+|\s+$//g;
        if (!$inList) {
            $inList = 1 if $s eq '(';
            next;
        }
        last if $s eq ')';
        if ($faceId < $start || $faceId >= $start + $nFaces) {
            $faceId++ if $s =~ /\(/;
            next;
        }

        my @pts = parse_face_indices($s);
        die "Could not parse face $faceId in $file\n" unless @pts;

        my $allEven = 1;
        my $allOdd = 1;
        for my $p (@pts) {
            $allEven = 0 if $p % 2;
            $allOdd = 0 unless $p % 2;
        }

        if ($allEven) {
            push @front, $faceId;
        } elsif ($allOdd) {
            push @back, $faceId;
        } else {
            push @sideFaces, [$faceId, [@pts]];
            $sidePointNeeded{$_} = 1 for @pts;
        }
        $faceId++;
    }
    close($fh);
    return (\@front, \@back, \@sideFaces, \%sidePointNeeded);
}

sub read_needed_points {
    my ($file, $needed) = @_;
    open(my $fh, '<', $file) or die "Cannot open $file: $!\n";
    my $inList = 0;
    my $pointId = 0;
    my %coords;
    while (my $line = <$fh>) {
        my $s = $line;
        $s =~ s/^\s+|\s+$//g;
        if (!$inList) {
            $inList = 1 if $s eq '(';
            next;
        }
        last if $s eq ')';
        if (exists $needed->{$pointId}) {
            $s =~ /\(([^()]*)\)/ or die "Could not parse point $pointId in $file\n";
            my @v = split(' ', $1);
            $coords{$pointId} = [$v[0] + 0.0, $v[1] + 0.0, $v[2] + 0.0];
        }
        $pointId++ if $s =~ /^\(/;
    }
    close($fh);
    return \%coords;
}

sub classify_side_faces {
    my ($sideFaces, $coords) = @_;
    my (@airfoil, @farfield);
    for my $entry (@$sideFaces) {
        my ($faceId, $pts) = @$entry;
        my ($minX, $maxX, $maxAbsZ) = (1e99, -1e99, 0);
        for my $p (@$pts) {
            my $c = $coords->{$p} or die "Missing coordinates for point $p\n";
            my ($x, undef, $z) = @$c;
            $minX = $x if $x < $minX;
            $maxX = $x if $x > $maxX;
            my $az = abs($z);
            $maxAbsZ = $az if $az > $maxAbsZ;
        }
        if ($minX >= -$xTol && $maxX <= 1.0 + $xTol && $maxAbsZ <= $airfoilZLimit) {
            push @airfoil, $faceId;
        } else {
            push @farfield, $faceId;
        }
    }
    return (\@airfoil, \@farfield);
}

sub write_faceset {
    my ($dir, $name, $labels) = @_;
    mkdir $dir unless -d $dir;
    open(my $fh, '>', "$dir/$name") or die "Cannot write $dir/$name: $!\n";
    print $fh "FoamFile\n{\n";
    print $fh "    version     2.0;\n";
    print $fh "    format      ascii;\n";
    print $fh "    class       faceSet;\n";
    print $fh "    location    \"constant/polyMesh/sets\";\n";
    print $fh "    object      $name;\n";
    print $fh "}\n\n";
    print $fh scalar(@$labels), "\n(\n";
    print $fh "$_\n" for @$labels;
    print $fh ")\n";
    close($fh);
}

my ($start, $nFaces) = read_boundary_default($boundaryFile);
my ($expFront, $expBack, $expAirfoil, $expFarfield, $span, $ni, $nj, $airStart, $airEnd) = read_nmf_expected($nmfFile);
print "defaultFaces start=$start nFaces=$nFaces\n";
print "NMF span=$span ni=$ni nj=$nj airfoilRange=$airStart-$airEnd\n";

my ($front, $back, $sideFaces, $sidePointNeeded) = read_boundary_faces($facesFile, $start, $nFaces);
my $coords = read_needed_points($pointsFile, $sidePointNeeded);
my ($airfoil, $farfield) = classify_side_faces($sideFaces, $coords);

print "classified front=", scalar(@$front), " back=", scalar(@$back), " airfoil=", scalar(@$airfoil), " farfield=", scalar(@$farfield), "\n";
die "front count mismatch: got ".scalar(@$front)." expected $expFront\n" unless scalar(@$front) == $expFront;
die "back count mismatch: got ".scalar(@$back)." expected $expBack\n" unless scalar(@$back) == $expBack;
die "airfoil count mismatch: got ".scalar(@$airfoil)." expected $expAirfoil\n" unless scalar(@$airfoil) == $expAirfoil;
die "farfield count mismatch: got ".scalar(@$farfield)." expected $expFarfield\n" unless scalar(@$farfield) == $expFarfield;

write_faceset($setsDir, 'frontFaces', $front);
write_faceset($setsDir, 'backFaces', $back);
write_faceset($setsDir, 'airfoilFaces', $airfoil);
write_faceset($setsDir, 'farfieldFaces', $farfield);
print "faceSets written to $setsDir\n";
PERL
}

normalize_patches() {
    local case_dir="$1"
    local nmf_file="$2"
    local boundary_file="$case_dir/constant/polyMesh/boundary"

    if [[ ! -f "$boundary_file" ]]; then
        log_error "Boundary file missing after conversion: $boundary_file"
        return 1
    fi

    if ! grep -q "defaultFaces" "$boundary_file"; then
        log_error "Expected a defaultFaces patch from plot3dToFoam, but none was found in $boundary_file"
        return 1
    fi

    log_info "Classifying defaultFaces into geometric faceSets..."
    if ! split_default_faces "$case_dir" "$nmf_file"; then
        log_error "Patch face classification failed. Check $case_dir/log.patchSplit"
        return 1
    fi

    write_create_patch_dict "$case_dir"
    log_info "Running createPatch..."
    if ! (cd "$case_dir" && createPatch -overwrite > log.createPatch 2>&1); then
        log_error "createPatch failed. Check $case_dir/log.createPatch"
        return 1
    fi

    for patch in front back airfoil farfield; do
        if ! grep -q "^[[:space:]]*$patch[[:space:]]*$" "$boundary_file"; then
            log_error "Patch '$patch' not found after createPatch"
            return 1
        fi
    done

    log_ok "Boundary created from geometric faceSets"
}

validate_check_mesh() {
    local case_dir="$1"
    local log_file="$case_dir/log.checkMesh"

    if ! grep -q "^End$" "$log_file"; then
        log_error "checkMesh did not reach End"
        return 1
    fi
    if grep -q "FOAM FATAL ERROR\|negative volume" "$log_file"; then
        log_error "Fatal mesh problem detected in checkMesh log"
        return 1
    fi
    if grep -q "Mesh has 0 geometric\|Mesh has 0 solution\|Number of edges not aligned" "$log_file"; then
        log_error "Mesh has wrong empty-patch geometry. Check $log_file"
        return 1
    fi
    if ! grep -q "Mesh has 2 geometric (non-empty/wedge) directions (1 0 1)" "$log_file"; then
        log_error "Expected 2 geometric directions (1 0 1), but checkMesh did not report them"
        return 1
    fi
    if ! grep -q "Mesh has 2 solution (non-empty) directions (1 0 1)" "$log_file"; then
        log_error "Expected 2 solution directions (1 0 1), but checkMesh did not report them"
        return 1
    fi

    log_ok "checkMesh geometry directions validated"
}

echo ""
echo -e "${BOLD}NACA 0012 - Family II Mesh Converter${NC}"
echo ""
log_info "Run dir : $RUN_DIR"
log_info "Grid dir: $GRID_DIR"
log_info "Levels  : ${LEVELS[*]}"
log_info "Force   : $FORCE"
log_info "Dry run : $DRY_RUN"

log_section "PRE-FLIGHT CHECKS"
ERRORS=0
[[ -d "$RUN_DIR" ]] || { log_error "Run directory not found: $RUN_DIR"; ERRORS=$((ERRORS+1)); }
[[ -d "$GRID_DIR" ]] || { log_error "Grid directory not found: $GRID_DIR"; ERRORS=$((ERRORS+1)); }
require_exe plot3dToFoam || ERRORS=$((ERRORS+1))
require_exe foamFormatConvert || ERRORS=$((ERRORS+1))
require_exe createPatch || ERRORS=$((ERRORS+1))
require_exe checkMesh || ERRORS=$((ERRORS+1))
require_exe simpleFoam || ERRORS=$((ERRORS+1))
require_exe gzip || ERRORS=$((ERRORS+1))
require_exe mktemp || ERRORS=$((ERRORS+1))
require_exe perl || ERRORS=$((ERRORS+1))

if [[ $ERRORS -gt 0 ]]; then
    log_error "$ERRORS pre-flight error(s). Aborting."
    exit 1
fi

log_section "CONVERTING MESHES"
CONVERTED=0
SKIPPED=0
FAILED=0

for level in "${LEVELS[@]}"; do
    CASE_DIR="$RUN_DIR/familyII_${level}"
    GRID_GZ="$GRID_DIR/n0012familyII.${level}.p3dfmt.gz"
    NMF_FILE="$GRID_DIR/n0012familyII.${level}.nmf"

    echo ""
    log_section "FAMILY II LEVEL $level"

    if [[ ! -d "$CASE_DIR" ]]; then
        log_error "Case directory not found: $CASE_DIR"
        FAILED=$((FAILED+1))
        continue
    fi
    if [[ ! -f "$GRID_GZ" ]]; then
        log_error "Grid file not found: $GRID_GZ"
        FAILED=$((FAILED+1))
        continue
    fi
    if [[ ! -f "$NMF_FILE" ]]; then
        log_error "NMF file not found: $NMF_FILE"
        FAILED=$((FAILED+1))
        continue
    fi

    if [[ -d "$CASE_DIR/constant/polyMesh" && "$FORCE" == "false" ]]; then
        log_warn "polyMesh already exists, skipping conversion. Use --force to reconvert."
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    rm -rf "$CASE_DIR/constant/polyMesh"
    TMP_DIR=$(mktemp -d)
    TMP_P3D="$TMP_DIR/n0012familyII.${level}.p3dfmt"

    log_info "Decompressing PLOT3D grid..."
    gzip -dc "$GRID_GZ" > "$TMP_P3D"

    log_info "Running plot3dToFoam -noBlank..."
    if plot3dToFoam -case "$CASE_DIR" -noBlank "$TMP_P3D" > "$CASE_DIR/log.plot3dToFoam" 2>&1; then
        PLOT3D_EXIT=0
    else
        PLOT3D_EXIT=$?
    fi
    rm -rf "$TMP_DIR"

    if [[ $PLOT3D_EXIT -ne 0 ]]; then
        log_error "plot3dToFoam failed. Check $CASE_DIR/log.plot3dToFoam"
        FAILED=$((FAILED+1))
        continue
    fi

    if [[ ! -d "$CASE_DIR/constant/polyMesh" ]]; then
        log_error "plot3dToFoam completed but constant/polyMesh was not created"
        FAILED=$((FAILED+1))
        continue
    fi

    log_info "Converting mesh files to ASCII for geometric patch splitting..."
    perl -0pi -e 's/writeFormat\s+\w+;/writeFormat     ascii;/' "$CASE_DIR/system/controlDict"
    if ! foamFormatConvert -case "$CASE_DIR" -constant > "$CASE_DIR/log.foamFormatConvert" 2>&1; then
        log_error "foamFormatConvert failed. Check $CASE_DIR/log.foamFormatConvert"
        FAILED=$((FAILED+1))
        continue
    fi

    if ! normalize_patches "$CASE_DIR" "$NMF_FILE"; then
        FAILED=$((FAILED+1))
        continue
    fi

    # Keep solver output behavior consistent with the base case after the
    # temporary ASCII conversion needed for patch classification.
    perl -0pi -e 's/writeFormat\s+\w+;/writeFormat     binary;/' "$CASE_DIR/system/controlDict"

    log_info "Running checkMesh..."
    if (cd "$CASE_DIR" && checkMesh -noFunctionObjects > log.checkMesh 2>&1); then
        CM_EXIT=0
    else
        CM_EXIT=$?
    fi
    if [[ $CM_EXIT -ne 0 ]]; then
        log_warn "checkMesh exited with code $CM_EXIT. Check $CASE_DIR/log.checkMesh"
    fi

    if ! validate_check_mesh "$CASE_DIR"; then
        FAILED=$((FAILED+1))
        continue
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Running simpleFoam -dry-run..."
        if ! (cd "$CASE_DIR" && simpleFoam -dry-run > log.simpleFoam.dryRun 2>&1); then
            log_error "simpleFoam -dry-run failed. Check $CASE_DIR/log.simpleFoam.dryRun"
            FAILED=$((FAILED+1))
            continue
        fi
        log_ok "simpleFoam -dry-run passed"
    fi

    log_ok "Converted Family II level $level"
    CONVERTED=$((CONVERTED+1))
done

log_section "SUMMARY"
echo "Converted: $CONVERTED"
echo "Skipped  : $SKIPPED"
echo "Failed   : $FAILED"

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
