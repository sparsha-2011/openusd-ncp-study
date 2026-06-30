"""
Debug Exercise — UsdUtilsFlattenLayerStack vs stage.Flatten()
================================================================
Understand the difference between the two flattening approaches.

TOPIC: UsdUtils.FlattenLayerStack() vs stage.Flatten()
WHEN TO USE:
  FlattenLayerStack → See the combined sublayer result. References kept.
  stage.Flatten()   → See the fully resolved scene. Everything resolved.

THE KEY DIFFERENCE:
  FlattenLayerStack merges SUBLAYERS ONLY.
  References, payloads, and variants are NOT resolved.

  stage.Flatten() resolves EVERYTHING.
  References gone. Variants baked to selected. Time samples PRESERVED.

Run: python debug_flatten_layer_stack.py
"""

from pxr import Usd, UsdGeom, Sdf, UsdUtils, Gf
import os

SEP = "=" * 65

# ── BUILD A STAGE WITH SUBLAYERS, REFERENCE, AND VARIANTS ──────────
root    = Sdf.Layer.CreateAnonymous("root.usda")
anim    = Sdf.Layer.CreateAnonymous("anim.usda")
layout  = Sdf.Layer.CreateAnonymous("layout.usda")

root.subLayerPaths = [anim.identifier, layout.identifier]
stage = Usd.Stage.Open(root)

# Define /World as Xform in layout layer so hierarchy is visible in usdview
stage.SetEditTarget(layout)
UsdGeom.Xform.Define(stage, "/World")

# Layout defines the chair at its base position
stage.SetEditTarget(layout)
chair = UsdGeom.Xform.Define(stage, "/World/Chair")
prim = chair.GetPrim()
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(0, 0, 0))

# Add a variant set with two variants
# Each variant needs its own GetVariantEditContext() block
vset = prim.GetVariantSets().AddVariantSet("material")

vset.AddVariant("wood")
vset.SetVariantSelection("wood")
with vset.GetVariantEditContext():
    prim.CreateAttribute("mat:type", Sdf.ValueTypeNames.String).Set("wood")

vset.AddVariant("metal")
vset.SetVariantSelection("metal")
with vset.GetVariantEditContext():
    prim.CreateAttribute("mat:type", Sdf.ValueTypeNames.String).Set("metal")

# Switch back to wood as the active selection
vset.SetVariantSelection("wood")

# Anim layer overrides translate
stage.SetEditTarget(anim)
stage.OverridePrim("/World/Chair")
UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(5, 0, 0))

# Animate the translate across frames
attr = prim.GetAttribute("xformOp:translate")
attr.Set(Gf.Vec3d(0, 0, 0), time=1)
attr.Set(Gf.Vec3d(5, 0, 0), time=24)
attr.Set(Gf.Vec3d(10, 0, 0), time=48)

# Add a reference from root
stage.SetEditTarget(root)
table = stage.DefinePrim("/World/Table")
table.GetReferences().AddReference("./table.usda")

# ── STEP 1: STAGE BEFORE ANY FLATTENING ─────────────────────────────
print(SEP)
print("  STEP 1 — Stage structure before flattening")
print(SEP)

p = stage.GetPrimAtPath("/World/Chair")
attr = p.GetAttribute("xformOp:translate")
time_samples = attr.GetTimeSamples()

print(f"\n  Sublayers: {len(stage.GetLayerStack())} layers")
print(f"  /World/Chair composed translate (default): {attr.Get()}")
print(f"  /World/Chair time samples: {time_samples}")
print(f"  /World/Chair variant sets: {list(p.GetVariantSets().GetNames())}")
print(f"  /World/Chair variant selection: "
      f"{p.GetVariantSets().GetVariantSet('material').GetVariantSelection()}")
print(f"  /World/Table has references: "
      f"{bool(table.GetMetadata('references'))}")

# ── STEP 2: FLATTENLAYERSTACK — sublayers only ──────────────────────
print()
print(SEP)
print("  STEP 2 — UsdUtils.FlattenLayerStack() — sublayers only")
print(SEP)

flat_layer = UsdUtils.FlattenLayerStack(stage)
flat_stage_a = Usd.Stage.Open(flat_layer)

fc = flat_stage_a.GetPrimAtPath("/World/Chair")
ft = flat_stage_a.GetPrimAtPath("/World/Table")

print(f"\n  /World/Chair exists:         {fc.IsValid()}")
fattr = fc.GetAttribute("xformOp:translate")
print(f"  /World/Chair translate:      {fattr.Get()}")
print(f"  /World/Chair time samples:   {fattr.GetTimeSamples()}")
print(f"  /World/Chair variant sets:   {list(fc.GetVariantSets().GetNames())}")

# Check if reference is preserved
table_refs = ft.GetMetadata("references")
print(f"  /World/Table reference arc:  "
      f"{'PRESERVED' if table_refs else 'GONE'}")

print(f"""
  RESULT:
  ✅ Sublayers merged — translate shows (5,0,0) from anim layer
  ✅ Time samples PRESERVED — animation still has 3 keyframes
  ✅ Variant sets PRESERVED — can still switch material
  ✅ Reference to table.usda PRESERVED — not resolved
""")

# ── STEP 3: STAGE.FLATTEN() — full composition ──────────────────────
print(SEP)
print("  STEP 3 — stage.Flatten() — full composition resolved")
print(SEP)

full_flat = stage.Flatten()
flat_stage_b = Usd.Stage.Open(full_flat)

fc2 = flat_stage_b.GetPrimAtPath("/World/Chair")
ft2 = flat_stage_b.GetPrimAtPath("/World/Table")

fattr2 = fc2.GetAttribute("xformOp:translate")
print(f"\n  /World/Chair exists:         {fc2.IsValid()}")
print(f"  /World/Chair translate:      {fattr2.Get()}")
print(f"  /World/Chair time samples:   {fattr2.GetTimeSamples()}")
print(f"  /World/Chair variant sets:   {list(fc2.GetVariantSets().GetNames())}")
print(f"  mat:type value:              "
      f"{fc2.GetAttribute('mat:type').Get() if fc2.GetAttribute('mat:type').IsValid() else 'no attr'}")

print(f"""
  RESULT:
  ✅ Sublayers merged — translate shows (5,0,0)
  ✅ Time samples PRESERVED — animation still exists
  ✅ Selected variant content baked in — mat:type='wood' is present
  ❌ Variant SETS removed — can no longer switch to 'metal'
  (table reference resolved but fails silently — file doesn't exist)
""")

# ── STEP 4: SIDE-BY-SIDE COMPARISON ─────────────────────────────────
print(SEP)
print("  STEP 4 — Side-by-side comparison")
print(SEP)
print("""
  Feature                    FlattenLayerStack    stage.Flatten()
  ─────────────────────────────────────────────────────────────────
  Sublayers merged           ✅ YES               ✅ YES
  References resolved        ❌ NO  (kept as-is)  ✅ YES (resolved)
  Payloads resolved          ❌ NO  (kept as-is)  ✅ YES (resolved)
  Variants preserved         ✅ YES               ❌ NO (baked to selected)
  Time samples preserved     ✅ YES               ✅ YES
  Geometry types changed     ❌ NO                ❌ NO
  Time samples baked static  ❌ NO                ❌ NO

  USE FOR:
  FlattenLayerStack → Debug sublayer conflicts. Keep references intact.
  stage.Flatten()   → See fully composed scene. Delivery format.

  CLI equivalents:
  UsdUtils.FlattenLayerStack → no direct CLI equivalent
  stage.Flatten()            → usdcat --flatten scene.usda
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — How to see flattening visually")
print(SEP)
print("""
  usdview can show you the difference between the composed stage
  and what a flat file looks like by opening both side by side.

  ORIGINAL STAGE:
  1. .\\scripts\\usdview.bat debug_flatten_original.usda
     → Metadata/Composition → LayerStack tab
       Shows 3 layers: anim.usda, layout.usda, root.usda
       Each layer's opinions are visible separately
     → /World/Chair: Composition tab shows variant set arc
     → /World/Table: Composition tab shows reference arc

  FLAT FILE (FlattenLayerStack result):
  2. .\\scripts\\usdview.bat debug_flatten_layerstack.usda
     → LayerStack tab shows ONLY ONE layer (the merged result)
     → /World/Chair: STILL has variant set in Composition tab
     → /World/Table: STILL has reference arc in Composition tab
     → Sublayers are merged but references/variants are preserved

  FULLY FLAT FILE (stage.Flatten() result):
  3. .\\scripts\\usdview.bat debug_flatten_full.usda
     → LayerStack shows ONE layer
     → /World/Chair: NO variant sets in Composition tab (baked)
     → /World/Table: reference arc attempted (file missing = error)

  Compare all three in usdview to see the difference visually.
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Export 1: the original composed stage
out_original = os.path.join(SCRIPT_DIR, "debug_flatten_original.usda")
path_anim   = os.path.join(SCRIPT_DIR, "debug_fl_anim.usda")
path_layout = os.path.join(SCRIPT_DIR, "debug_fl_layout.usda")

for fpath in [path_anim, path_layout, out_original]:
    if os.path.exists(fpath): os.remove(fpath)

anim.Export(path_anim)
layout.Export(path_layout)

root_out = Sdf.Layer.CreateNew(out_original)
root_out.subLayerPaths = [
    os.path.basename(path_anim),
    os.path.basename(path_layout),
]
root_out.Save()
print(f"  Original stage saved → {out_original}")

# Export 2: FlattenLayerStack result
out_layerstack = os.path.join(SCRIPT_DIR, "debug_flatten_layerstack.usda")
flat_layer.Export(out_layerstack)
print(f"  FlattenLayerStack saved → {out_layerstack}")

# Export 3: full Flatten result
out_full = os.path.join(SCRIPT_DIR, "debug_flatten_full.usda")
full_flat.Export(out_full)
print(f"  stage.Flatten() saved → {out_full}")

print(f"""
  Open all three in usdview and compare:
    .\\scripts\\usdview.bat {out_original}
    .\\scripts\\usdview.bat {out_layerstack}
    .\\scripts\\usdview.bat {out_full}

  What to look for in each:
    Original:        3 layers in LayerStack tab. Variants intact.
    FlattenLayerStack: 1 layer. Variants still there. Reference still there.
    Full Flatten:    1 layer. Variants GONE (baked). Reference resolved.
""")