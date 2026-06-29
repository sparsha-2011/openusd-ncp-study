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
main_chair = stage3.DefinePrim("/World/Chair")
main_chair.GetReferences().AddReference(ref_layer.identifier, "/Chair")

# Add a local override
main_chair.CreateAttribute(
    "chair:colour", Sdf.ValueTypeNames.String).Set("blue")

# PrintComposition — output goes to stdout
print(f"  Calling Usd.Debug.PrintComposition on /World/Chair:\n")
print("  " + "-" * 55)
Usd.Debug.PrintComposition(main_chair)
print("  " + "-" * 55)

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

  CLI for composition arc inspection (no Python needed):
    usdcat --print-composition scene.usda
    → Same as PrintComposition but for the whole file from CLI
""")
