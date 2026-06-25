# ModelFoundry ↔ DataRefinery binding pattern (D.a.27 spike outcome)

**Status:** spike-validated 2026-06-16 against `ml-modelfoundry==0.8.3` + `ml-datarefinery==0.21.0`.
**Deliverable of:** ModelFoundry integration spike — *investigation* flavor.
**Consumed by:** consumer project (ResNet-20 spec), notebook.

This document locks the concrete pattern for binding a ModelFoundry model recipe to
a materialized DataRefinery instance in *this* repo. It is implementation-ready: the
trivial spike (`models/.spike/mf-hello.yaml` + `models/.spike/forward_pass.py`) proved
every claim below end-to-end, including a live forward pass.

The spike artifacts under `models/.spike/` are **throwaway** — the persisted deliverable
is this document. They may be deleted once D.a.31 lands.

---

## 1. The binding mechanism (how an MF recipe references the DR cache)

ModelFoundry's library entry point mirrors DataRefinery's:

```python
from modelfoundry import ModelFoundry

mf = ModelFoundry.from_recipe("models/resnet20.yaml", data="./cache")
```

- The recipe's **`Data:`** block names the *DataRefinery recipe* (not a cache path):

  ```yaml
  Data:
    recipe: recipes/cifar10-base.yaml
    cache_root: ./cache          # see §4 — REQUIRED in this repo
  ```

- `from_recipe(..., data=...)` accepts **either** a path to the DR cache root (string/Path)
  **or** a pre-bound `DataRefineryInstance`. Passing `data="./cache"` resolves the recipe's
  `Data.recipe` against that cache root.
- Resolution does **not** re-derive DR's cache identity. MF calls DataRefinery's blessed
  `datarefinery.resolve_instance(recipe, cache_root=…, seed=…, variant=…)` and then
  `datarefinery.Instance.load(instance_path)`. This is the same resolution the project's
  own consumer project's `instances.py` helper performs — they agree on the path.
- **The plugin only needs to be _discoverable_, not _available_, to bind.** `from_recipe`
  succeeds and resolves the DR instance even when `torch` is absent (the `pytorch` plugin
  is discovered but reports `available=False`). torch is required only to *build a model*
  or *run/train* — see §5.

### Two consumption paths

1. **Just the `nn.Module`** (for `torchinfo.summary`, manual forward passes — D.a.32 cells):

   ```python
   from modelfoundry.plugins.pytorch.architecture import build_model
   model = build_model(mf.recipe.Architecture)   # an nn.Module / nn.Sequential
   ```

2. **The full trained instance** (train → optimize → evaluate → persist):

   ```python
   instance = mf.materialize()        # returns a ModelInstance (writes ./models/instances/…)
   ```

---

## 2. What schema fields MF reads from the DR instance

`mf.data` is a frozen `DataRefineryInstance`. The fields the binding actually reads
(verified live against the cifar10-base instance):

| Field / method | Value on cifar10-base | Source |
| --- | --- | --- |
| `.path` | `cache/instances/5e49ad15…/bd42cea6…/20260509` | DR resolver |
| `.splits` | `('train', 'val', 'test')` | `manifest.record_counts.keys()` |
| `.instance_num_classes()` | `10` | scans **train** JSONL, counts distinct label values |
| `.label_schema` | `{'field': 'label', 'source': {'kind': 'direct', …}}` | DR recipe `Labels` |
| `.record_schema` | keys `image`, `label`, `path` | DR recipe `Output.record_schema` |
| `.fitted_statistics` | present (≠ None) | DR `fitted_statistics/` sidecar |
| `.manifest.record_counts` | `{train: 1700, val: 300, test: 1000}` | DR manifest |

### Two record-format facts that bit during the spike (heads-up for D.a.29 / D.a.31)

- **`label` is a class-name _string_** (`"airplane"`, …), **not** an int, and the JSONL
  records carry **no inline `image`** array — pixels load from each record's `path`
  (e.g. `data/raw/cifar-10/train/6651.png`, which must exist on the resolving host).
  This contradicts `project-essentials.md` § "Materialized record format" (which says
  `image` uint8 `(32,32,3)` + `label` int + `partition`). **The project-essentials entry
  is stale** — reconcile it in (consumer story) when normalization moves into the recipe.
- **Label→index ordering is `sorted(label_strings)`** (alphabetical), *not* the canonical
  CIFAR `0..9` ordering. `DataRefineryDataset._derive_label_index` sorts the distinct
  string labels and assigns indices in that order. For the consumer-required evaluation this matters:
  reported per-class metrics will be keyed by the sorted-alphabetical index unless the
  recipe emits integer labels in canonical order. Decide
  whether to (a) accept alphabetical indices, or (b) have the DR recipe map labels to the
  canonical CIFAR ordering.

---

## 3. How the pytorch data adapter feeds the model

ModelFoundry's `pytorch` plugin wraps the bound instance in a `torch.utils.data.Dataset`:

```python
from modelfoundry.plugins.pytorch.data import DataRefineryDataset, build_dataloader

dataset = DataRefineryDataset(mf.data, "train")                 # one split
loader  = build_dataloader(dataset, mf.recipe.Training,
                           master_seed=mf.recipe.seed, shuffle=False)
images, labels = next(iter(loader))   # images: (B, 3, 32, 32) float32, labels: (B,)
```

- **DataRefinery owns the statistics; the consumer applies them.** The adapter reads the
  recipe's `Transformations`; for `normalize` / `mean_subtract` (fit-on-train ops) it pulls
  the persisted per-channel mean/std from `.fitted_statistics` and applies them to every
  split — using DR's exact `std == 0 → 1.0` zero-variance guard. `cifar10-base.yaml`
  already declares `normalize_per_channel` (fit on `train`), so the spike's batch arrived
  **already normalized**.
- **Pixel-altering (geometry) transforms are refused** unless the instance ships aggressive
  sidecars (`image_path`) or a sink — reading `path` would decode *pre-transform* pixels.
  `normalize`/`mean_subtract` are exempt (they're applied numerically, not baked).
- Decode precedence: aggressive sidecar (`image_path`, relative to `dataset/`) wins over
  the source `path`. cifar10-base has no sidecars, so it decodes `path` → RGB → `[0,1]`
  CHW float, then normalizes.

---

## 4. Cache-root mismatch — the one configuration gotcha

MF's default `--data-cache-root` is **`./data`**; this project's DR cache root is **`./cache`**.
A bare `ModelFoundry.from_recipe(recipe)` (no `data=`) would resolve against `./data` and
miss. **Always** either:

- pass `data="./cache"` to `from_recipe`, **or**
- set `cache_root: ./cache` in the recipe's `Data:` block (the spike recipe does both
  belt-and-suspenders).

MF writes *its own* instances under **`./models/instances/<recipe_hash16>/<data_instance_hash16>/<seed>/`**
(default `--cache-root ./models`). Add `models/instances/` to `.gitignore` before D.a.32
materializes anything (the `models/*.yaml` specs are committed; the materialized output is not).

---

## 5. Install requirements & env placement (gotchas for D.a.30)

- **`ml-modelfoundry` base install carries _no_ ML framework.** The `pytorch` plugin needs
  the **`[pytorch]`** extra: `pip install 'ml-modelfoundry[pytorch]'`, which pulls
  `torch>=2.5`, **`torchinfo>=1.8`**, `torchmetrics>=1.4`, `torchvision>=0.20`.
  → Plans to add `torchinfo` separately; it is **already covered** by the extra.
- **`optuna` is a _base_ MF dependency** (not gated behind an extra) — also already covered;
  Separate `optuna` line is redundant if MF is installed.
- **Root env is deliberately torch-free** (`pyve.toml [env.root]` = "No ML stack"; torch is
  isolated in the lazy `[env.smoke-torch]` venv, `tests/integration/env/torch.txt`). The
  spike installed `torch` **transiently** into root to run the forward pass, then
  **uninstalled it** to restore the design. **D.a.30 must decide torch's permanent home** —
  candidates: (a) extend `smoke-torch`, (b) a new model-build env, (c) relax the torch-free
  root rule. Do **not** silently leave torch in root.
- **The minimal forward-pass dep is `torch` alone** — `build_model` (Flatten/Linear/Conv) and
  the dataloader need only `torch` (+ numpy + pillow, already present). `torchvision` /
  `torchmetrics` / `torchinfo` are needed for augmentation / metrics / summary, i.e. training
  and D.a.32's `torchinfo.summary`, not a bare forward pass.
- **Dependency drift to reconcile in D.a.30:** the stories assume a conda `environment.yml`
  (pip-installs paragraph + `pyve lock`). That file **does not exist** — the project uses
  `pyve.toml` venv envs (`environment-deprecated.yml` is the retired one). D.a.30's
  "add to environment.yml / run pyve lock" tasks need re-expressing against `pyve.toml`.
- **`ml-modelfoundry` floors `ml-datarefinery>=0.20.0`.** Installing MF silently upgraded the
  repo's DR (0.19 → 0.20). The repo pin is now `>=0.21.0` (Follow-up: 0.20.0 was
  flagged flawed upstream). Re-run `tests/test_recipes_*` after any DR bump to confirm the
  recipes still materialize bit-identically.

---

## 6. Failure modes (all raise `modelfoundry.DataBindingError`)

| Condition | Trigger |
| --- | --- |
| Instance not materialized | DR `cache_status == "miss"` → "run `datarefinery materialize` first" |
| Instance corrupt | DR `cache_status == "corrupt"` |
| Partial materialize | `FAILED` marker present, or `manifest.is_partial` |
| DR schema too new | DR recipe `schema_version` > MF's known max → "upgrade ml-modelfoundry" |
| Missing aggressive sidecar | a record's `image_path` points at a file that isn't on disk |
| Unbaked geometry transform | recipe declares a pixel-altering transform but instance has no sidecar/sink |
| Missing fitted statistic | `normalize`/`mean_subtract` declared but `fitted_statistics` absent |

**Coupling is loose (DR v1 / FR-TRANS-1):** MF self-verifies the bound instance's
`recipe_hash` against its persisted `recipe.json`, but the upstream DR recipe hash does
**not** participate in MF's own cache identity. Re-materializing the DR instance does not
auto-invalidate a downstream MF instance — same manual-invalidation discipline as the
Recipe A ↔ Recipe B coupling documented in `project-essentials.md`.

---

## 7. Reproducing the spike

```bash
pyve run pip install torch                       # transient; root is torch-free by design
pyve run python models/.spike/forward_pass.py    # binds, builds, one forward pass
pyve run pip uninstall -y torch                  # restore torch-free root
```

Expected tail: `forward logits : shape=(16, 10) dtype=torch.float32` then `FORWARD PASS OK`.
