# NVIDIA Tesla M10 Training Guide

This guide is for the requested host with two visible Tesla M10 GPUs. It is a qualification procedure, not a statement that the current graph/model fits.

## Compatibility facts

- An M10 board contains four Maxwell GPUs with 8 GB per GPU (32 GB per board). A process sees and allocates each GPU separately; ordinary multi-GPU training does not pool memory. See the [NVIDIA Tesla M10 product brief](https://images.nvidia.com/content/pdf/tesla/PB-08118-001_v03_TeslaM10-Product-Brief_12-16.pdf).
- NVIDIA lists Maxwell support through CUDA 12.x and the R580 driver branch in its [architecture matrix](https://docs.nvidia.com/datacenter/tesla/drivers/latest/cuda-toolkit-driver-and-architecture-matrix.html).
- NVIDIA's [minor-version compatibility table](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html) gives minimum driver families, but the installed card and driver must also remain mutually supported.
- PyTorch announced CUDA 12.6 as its final published wheel line supporting Maxwell. Use the current PyTorch release documentation and the [Maxwell wheel notice](https://dev-discuss.pytorch.org/t/notice-cuda-12-6-wheels-will-no-longer-be-published-from-pytorch-2-15-drops-maxwell-pascal-volta/3432) when pinning the environment.

## Required setup

1. On the M10 host, record the driver and device inventory:

   ```bash
   nvidia-smi
   nvidia-smi --query-gpu=index,name,driver_version,memory.total --format=csv
   ```

2. Create a clean Python 3.11 environment. Do not reuse an environment containing NumPy 2 or an unknown CUDA build.

3. Install `numpy<2` and a PyTorch wheel that explicitly retains Maxwell support. As of this audit, the intended stack is PyTorch 2.14.0 with the official CUDA 12.6 wheel; confirm the command on the [official PyTorch site](https://pytorch.org/get-started/locally/) at installation time:

   ```bash
   python -m pip install "numpy<2"
   python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cu126
   python -m pip install torch-geometric
   python -m pip install -e .
   ```

   Do not replace this with an unconstrained `pip install torch`; CUDA 13 builds do not support Maxwell.

4. Run the repository hardware gate:

   ```bash
   python scripts/check_environment.py --require-gpus 2 --require-name "Tesla M10"
   ```

   It must report two visible devices, approximately 8 GiB each, their actual compute capability, the CUDA version used to build PyTorch, and a compatible architecture in `torch.cuda.get_arch_list()`.
   It also runs a real forward/backward tensor operation on each GPU. A lower
   minor cubin in the same compute-capability major (for example `sm_50` for an
   `sm_52` M10) is accepted according to CUDA binary compatibility.

5. Run the full software tests and graph validation in that clean environment before training.

## Memory-safe qualification

Start with one device and one case per batch:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/train_experiment.py \
  --config configs/experiments/naca0012_gcn_smoke.yaml \
  --device cuda \
  --max-epochs 2 \
  --limit-train-cases 2 \
  --limit-val-cases 1
```

Required observations for each model family:

- peak allocated and reserved CUDA memory;
- forward/backward completion without OOM;
- finite loss and gradients;
- time after warm-up, with CUDA synchronization;
- checkpoint save/load/resume;
- no architecture/kernel compatibility error.

The current full graph has about 229k nodes and 916k directed edges. Edge-heavy MPNN and MeshGraphNet configurations deserve special caution. If a model does not fit, reduce hidden width and layer count first and record the changed config. Do not silently change graph sampling or physics semantics.

## Multi-GPU policy

Use one process per GPU with DistributedDataParallel only after the single-GPU job is stable. DDP replicates the model on both devices and partitions cases; it does not turn two 8 GB GPUs into one 16 GB GPU. Avoid `DataParallel` for the primary study.

Because the default batch size is one graph, DDP needs at least two independent cases per optimizer step to benefit. Gradient accumulation can increase effective batch size without increasing per-step graph memory. Any sampler must preserve the immutable train/validation/test case split.

## Mixed precision

FP32 is the required baseline. AMP is optional and must be benchmarked separately. Maxwell has no tensor cores, and half precision can be slower or less stable for scatter/message-passing operations. Enable it only if measured memory savings are needed and field metrics remain equivalent within a predeclared tolerance.

## Long-run operation

- Write runs to persistent local storage, not a temporary directory.
- Keep `last.pt`, `best.pt`, `history.csv`, `summary.json`, the resolved config, dataset paths/checksums, environment export, and `nvidia-smi` snapshot.
- Resume with `--resume`; checkpoints now restore optimizer, RNG, best metric, and early-stopping counter.
- Treat thermal throttling, ECC/Xid errors, OOMs, NaNs, missing artifacts, or data-gate failures as failed runs. Do not omit them from the experiment record.
