# Mesh-Independence Cluster Workflow

These Slurm scripts run NACA 0012 Family II mesh cases on a Conda-installed OpenFOAM environment. They are path-independent and can run from any checkout location.

## Expected Cluster Location

Choose site-specific locations and login details:

```bash
export AIRFOIL_CLUSTER_ROOT=/path/to/cluster/naca0012
export AIRFOIL_LOCAL_ROOT=/path/to/airfoil-digital-twin
export AIRFOIL_CLUSTER_LOGIN=user@cluster.example
```

The scripts do not hardcode this path. They resolve `PROJECT_ROOT`, `STUDY_DIR`, and case paths from the location of the Slurm script.

## Environment Defaults

`cluster_env.sh` defaults to:

```bash
source /path/to/miniconda/bin/activate of_parallel
export WM_PROJECT_DIR="$CONDA_PREFIX"
export FOAM_MPI=mpich-3.3
export WM_MPLIB=MPICH
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib/mpich-3.3:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"
```

Override these if another machine uses different names:

```bash
sbatch --export=ALL,LEVEL=7,CONDA_ENV=my_of_env cluster/submit_single_mesh.slurm
```

## Prepare Cases

From the mesh study directory:

```bash
cd "$AIRFOIL_CLUSTER_ROOT/studies/meshIndependence"
bash makeMeshFolders.sh --levels 1,2,3,4,5,6,7
```

Convert meshes if OpenFOAM conversion tools are available on the cluster:

```bash
bash convertMeshes.sh --grids ../../grids/NACA0012numerics_grids --force
```

If conversion is too heavy on the cluster, convert locally and transfer the `runs/familyII_*` folders with `rsync`.

## Submit One Mesh

Coarse smoke test:

```bash
sbatch --ntasks=4 --time=02:00:00 --export=ALL,LEVEL=7 cluster/submit_single_mesh.slurm
```

Fine-grid examples:

```bash
sbatch --ntasks=16 --time=24:00:00 --export=ALL,LEVEL=4 cluster/submit_single_mesh.slurm
sbatch --ntasks=32 --time=48:00:00 --export=ALL,LEVEL=3 cluster/submit_single_mesh.slurm
sbatch --ntasks=48 --time=72:00:00 --export=ALL,LEVEL=2 cluster/submit_single_mesh.slurm
sbatch --ntasks=64 --time=96:00:00 --export=ALL,LEVEL=1 cluster/submit_single_mesh.slurm
```

## Submit An Array

All Family II levels:

```bash
sbatch --array=1-7 --ntasks=16 --time=48:00:00 cluster/submit_mesh_array.slurm
```

Fine levels only:

```bash
sbatch --array=1-4 --ntasks=32 --time=72:00:00 --export=ALL,LEVELS_CSV=1,2,3,4 cluster/submit_mesh_array.slurm
```

## Logs

Each case writes cluster logs into its own folder:

```text
runs/familyII_<level>/log.checkMesh.cluster
runs/familyII_<level>/log.decomposePar.cluster
runs/familyII_<level>/log.simpleFoam.cluster
runs/familyII_<level>/log.reconstructPar.cluster
runs/familyII_<level>/run_status_cluster.txt
```

Status values include `RUNNING`, `COMPLETE`, `INCOMPLETE`, `FAILED_CHECKMESH`, `FAILED_DECOMPOSE`, `FAILED_SOLVER`, and `FAILED_RECONSTRUCT`.

## Postprocess

After runs complete:

```bash
cd ~/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/meshIndependence
python3 postprocess_mesh_independence.py --notes-dir ../../notes --refdir ../../references
```

The postprocessor updates the flat `results/` folder and `../../notes/mesh-independence-study.md`.

## Transfer From Laptop

From the laptop, after making local script changes:

```bash
rsync -avh --progress \
  --exclude '.DS_Store' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "$AIRFOIL_LOCAL_ROOT/cfd/naca0012/" \
  "${AIRFOIL_CLUSTER_LOGIN}:${AIRFOIL_CLUSTER_ROOT}/"
```

Pull cluster outputs back with:

```bash
rsync -avh --progress \
  "${AIRFOIL_CLUSTER_LOGIN}:${AIRFOIL_CLUSTER_ROOT}/studies/meshIndependence/runs/" \
  "$AIRFOIL_LOCAL_ROOT/cfd/naca0012/studies/meshIndependence/runs/"
```
