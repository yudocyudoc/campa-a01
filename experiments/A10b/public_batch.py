#!/usr/bin/env python3
"""A10b public producer: no sealed label files exist before analyst finishes."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from experiments.A10b.design import SEEDS,ORIGINAL_A10_SEED,validate
from experiments.A10b.packager import produce

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main(out:Path):
    validate()
    out.mkdir(parents=True,exist_ok=True)
    historical=Path("experiments/A10/evidence/public")
    if not historical.is_dir():raise RuntimeError("A10 original evidence unavailable for baseline check")
    public_rows=[]
    for seed in SEEDS:
        directory=out/str(seed)
        p=produce(directory,seed=seed,include_sealed=False)
        if p["noise_seed"]!=seed:raise AssertionError("Seed mismatch")
        if (directory/"sealed_truth.json").exists():
            raise AssertionError("An adjudication label leaked into public data")
        public_rows.append({ "seed":seed,"checksums":{
            path.name:sha(path) for path in sorted(directory.iterdir()) if path.is_file()
        }})
        if seed==ORIGINAL_A10_SEED:
            for name in ("train_noiseless.csv","train_noisy_1pct.csv","holdout_inputs.csv"):
                if sha(directory/name)!=sha(historical/name):
                    raise AssertionError(f"A10 original-run anchor mismatch {name}")
        print(f"PUBLIC_ONLY_SEED {seed} baseline_verified={seed==ORIGINAL_A10_SEED}",flush=True)
    for name in ("train_noiseless.csv","holdout_inputs.csv"):
        if len({row["checksums"][name] for row in public_rows})!=1:
            raise AssertionError("Common no-noise training/holdout inputs vary across noise seeds")
    (out/"a10b_public_batch_manifest.json").write_text(json.dumps({
        "experiment":"A10b","seed_count":len(SEEDS),"seeds":list(SEEDS),
        "public_data_only":True,"sealed_labels_not_generated_or_published":True,
        "first_seed_A10_original_csv_exact":True,"per_seed":public_rows,
        "note":"All held-out true outcomes are regenerated only after analyst job has frozen all predictions."
    },indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("A10B_PUBLIC_COMPLETE",len(SEEDS))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=Path("results/A10b/public"))
    main(p.parse_args().out)
