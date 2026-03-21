# Keep the shell on the primary toolchain unless a legacy workspace explicitly
# needs the compatibility shims.
export BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PATH="$BENCH_ROOT/opt/conda/envs/ml-stack/bin:$BENCH_ROOT/usr/local/cuda-12.4/bin:$PATH"
export CUDA_HOME="$BENCH_ROOT/usr/local/cuda-12.4"
export RUNTIME_FALLBACK_MODE="disabled"
