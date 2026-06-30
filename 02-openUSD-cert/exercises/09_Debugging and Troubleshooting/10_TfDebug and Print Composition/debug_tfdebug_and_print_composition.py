"""
Debug Exercise — TfDebug + Usd.Debug.PrintComposition
========================================================
Enable verbose internal logging and inspect composition arc details.

TOPICS:
  Tf.Debug.SetDebugSymbolsByName()  — verbose logging per subsystem
  Usd.Debug.PrintComposition(prim)  — detailed composition arc output
  usdcat --print-composition        — CLI equivalent

WHEN TO USE:
  TfDebug:          Stage fails to open, paths not resolving, payloads
                    not loading — you need to see what USD is doing internally.
  PrintComposition: A composition arc is not resolving as expected and
                    you need the most detailed possible breakdown of why.

Run: python debug_tfdebug_and_print_composition.py
"""

from pxr import Usd, UsdGeom, Sdf, Tf, Gf
import os

SEP = "=" * 65

# ── STEP 1: LIST ALL AVAILABLE SYMBOLS ──────────────────────────────
print(SEP)
print("  STEP 1 — List all available TfDebug symbols")
print(SEP)

all_symbols = Tf.Debug.GetDebugSymbolNames()
usd_symbols = sorted([s for s in all_symbols
                      if s.startswith("USD") or s.startswith("AR")])
sdf_symbols = sorted([s for s in all_symbols if s.startswith("SDF")])

print(f"\n  Total debug symbols available: {len(all_symbols)}")
print(f"  USD-related symbols:           {len(usd_symbols)}")
print(f"  SDF-related symbols:           {len(sdf_symbols)}")
print(f"\n  USD + AR symbols:")
for sym in usd_symbols:
    desc = Tf.Debug.GetDebugSymbolDescription(sym)
    print(f"    {sym:<38} {desc[:45]}")

# ── STEP 2: ENABLE A SYMBOL ─────────────────────────────────────────
print()
print(SEP)
print("  STEP 2 — Enable USD_STAGE_OPEN and open a stage")
print(SEP)
print("""
  When USD_STAGE_OPEN is enabled, USD prints verbose messages
  to stderr as it opens and composes the stage.
  You will see messages about layer loading, prim traversal, etc.
  (Watch your terminal's stderr output)
""")

Tf.Debug.SetDebugSymbolsByName("USD_STAGE_OPEN", True)
print(f"  USD_STAGE_OPEN enabled: "
      f"{Tf.Debug.IsDebugSymbolNameEnabled('USD_STAGE_OPEN')}\n")

# Open a stage — debug output goes to stderr
stage = Usd.Stage.CreateInMemory()
UsdGeom.Xform.Define(stage, "/World")
UsdGeom.Sphere.Define(stage, "/World/Ball")

Tf.Debug.SetDebugSymbolsByName("USD_STAGE_OPEN", False)
print(f"\n  USD_STAGE_OPEN disabled: "
      f"{not Tf.Debug.IsDebugSymbolNameEnabled('USD_STAGE_OPEN')}")

# ── STEP 3: ENABLE USD_COMPOSITION ──────────────────────────────────
print()
print(SEP)
print("  STEP 3 — Enable USD_COMPOSITION for arc resolution tracing")
print(SEP)
print("""
  USD_COMPOSITION shows how each composition arc is being resolved.
  Use when a reference, variant, or inherit is not resolving correctly.
""")

Tf.Debug.SetDebugSymbolsByName("USD_COMPOSITION", True)

# Create a stage with a variant to trigger composition
stage2 = Usd.Stage.CreateInMemory()
prim = UsdGeom.Xform.Define(stage2, "/World/Chair").GetPrim()
vset = prim.GetVariantSets().AddVariantSet("lod")
vset.AddVariant("high")
vset.AddVariant("low")
vset.SetVariantSelection("high")

Tf.Debug.SetDebugSymbolsByName("USD_COMPOSITION", False)
print(f"  USD_COMPOSITION disabled after variant composition test.")

# ── STEP 4: PRINT COMPOSITION ───────────────────────────────────────
print()
print(SEP)
print("  STEP 4 — Usd.Debug.PrintComposition(prim)")
print(SEP)
print("""
  PrintComposition prints the full composition arc breakdown
  for a specific prim — which layers contribute and how they combine.
  This is the MOST DETAILED programmatic composition debug tool.
""")

# Build a stage with references and variants for a rich composition
stage3 = Usd.Stage.CreateInMemory()

# Create a "referenced" asset in another layer
ref_layer = Sdf.Layer.CreateAnonymous("chair_asset.usda")
ref_stage = Usd.Stage.Open(ref_layer)
chair_ref = UsdGeom.Xform.Define(ref_stage, "/Chair")
chair_ref.GetPrim().CreateAttribute(
    "chair:height", Sdf.ValueTypeNames.Float).Set(90.0)

# Reference it in our stage
main_chair = UsdGeom.Sphere.Define(stage3, "/World/Chair").GetPrim()
main_chair.GetReferences().AddReference(ref_layer.identifier, "/Chair")

# Add a local override
main_chair.CreateAttribute(
    "chair:colour", Sdf.ValueTypeNames.String).Set("blue")

# ── Usd.Debug.PrintComposition — availability note ──────────────────
# Usd.Debug.PrintComposition only exists in full USD builds compiled
# from source. It is NOT available in the pip-installed usd-core package.
# The equivalent in usd-core is prim.GetPrimIndex().DumpToString()
# which gives the same composition arc graph as text output.

print(f"  prim.GetPrimIndex().DumpToString() on /World/Chair:")
print(f"  (This is the usd-core equivalent of Usd.Debug.PrintComposition)\n")
print("  " + "-" * 55)
index = main_chair.GetPrimIndex()
dump  = index.DumpToString()
# Print the full dump — shows every composition arc
for line in dump.split("\n"):
    print(f"  {line}")
print("  " + "-" * 55)

print(f"""
  HOW TO READ THE OUTPUT:
  Each indented block = one composition arc
  "root node"         = the prim's local opinions (strongest)
  "reference"         = a reference arc and what it contributes
  "path"              = the prim path within the referenced layer
  "layer stack"       = which layers are part of this arc

  Usd.Debug.PrintComposition (full USD builds only):
    → Identical information, slightly different formatting
    → Available when USD is compiled from source
    → NOT available in: pip install usd-core

  prim.GetPrimIndex().DumpToString() (usd-core compatible):
    → Same composition arc graph
    → Available in ALL USD installations including pip usd-core
    → Use this in your scripts for maximum compatibility

  CLI equivalent (works everywhere):
    usdcat --print-composition scene.usda
    → Prints composition arcs for all prims in the file
    → No Python needed
""")

# ── STEP 5: REFERENCE TABLE ─────────────────────────────────────────
print()
print(SEP)
print("  STEP 5 — Quick reference: when to use which symbol")
print(SEP)
print("""
  ┌─────────────────────────┬──────────────────────────────────────────┐
  │ Symbol                  │ Use when                                 │
  ├─────────────────────────┼──────────────────────────────────────────┤
  │ USD_STAGE_OPEN          │ Stage opens but prims are missing/wrong  │
  │ USD_COMPOSITION         │ Reference or variant not resolving       │
  │ AR_RESOLVER_INIT        │ Asset path fails to find the file        │
  │ USD_PAYLOADS            │ Payload geometry not appearing           │
  │ USD_CHANGES             │ Too many change notifications — perf     │
  │ USD_INSTANCING          │ Instancing not sharing prototypes        │
  └─────────────────────────┴──────────────────────────────────────────┘

  CLI ALTERNATIVE — set env var before launching usdview or scripts:
    Windows:  set TF_DEBUG=USD_STAGE_OPEN AR_RESOLVER_INIT
    Linux:    export TF_DEBUG=USD_STAGE_OPEN AR_RESOLVER_INIT
    Wildcard: TF_DEBUG=USD* enables ALL USD_* symbols at once

  COMPOSITION ARC INSPECTION — by availability:
    prim.GetPrimIndex().DumpToString()    ← ALL builds including pip usd-core
    Usd.Debug.PrintComposition(prim)      ← full source builds ONLY, not pip usd-core
    usdcat --print-composition scene.usda ← CLI, works everywhere
""")

# ── USDVIEW EQUIVALENT + EXPORT ──────────────────────────────────────
print(SEP)
print("  USDVIEW — Visual equivalent of PrintComposition")
print(SEP)
print("""
  usdview's Composition tab is the visual equivalent of
  prim.GetPrimIndex().DumpToString() (or Usd.Debug.PrintComposition
  in full USD source builds). It shows the full composition arc graph
  for any selected prim without writing any Python.

  1. Open usdview:
     .\\scripts\\usdview.bat debug_tfdebug_composition.usda

  2. Click /World/Chair in the Scenegraph

  3. Metadata/Composition → Composition tab
     This is the FULL composition arc graph — visual equivalent of:
     Usd.Debug.PrintComposition(prim)
     OR
     prim.GetPrimIndex().DumpToString()

     You will see:
     ┌ Root arc (local opinions)
     └── Reference arc → chair_asset.usda
         └── /Chair prim in that layer

  4. This shows:
     - Which arcs contribute to this prim
     - The strength ordering of each arc
     - Where each arc's data comes from (file + path)
     - Any errors on broken arcs

  TfDebug (Python) vs usdview Composition tab:
  TfDebug → runs during stage loading, shows internal decisions
            useful for path resolution failures and stage open issues
  Composition tab → shows the RESULT of composition, after the fact
                    useful for understanding what composed and why

  For most debugging: start with usdview Composition tab (fast, visual)
  For load-time issues: use TfDebug (shows what happens during loading)
""")

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(SCRIPT_DIR, "debug_tfdebug_composition.usda")
stage3.Export(output_path)
print(f"  Saved → {output_path}")
print(f"  Open in usdview:")
print(f"    .\\scripts\\usdview.bat {output_path}")
print(f"\n  In usdview:")
print(f"    1. Click /World/Chair in Scenegraph")
print(f"    2. Metadata/Composition → Composition tab")
print(f"       → See the reference arc to chair_asset.usda")
print(f"       → Compare to PrintComposition output above")
print(f"    3. Metadata/Composition → LayerStack tab")
print(f"       → See layers: local layer + chair_asset layers")