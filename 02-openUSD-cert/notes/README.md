# OpenUSD NCP Certification — Study Notes

> **NVIDIA-Certified Professional: OpenUSD Development (NCP-OUSD)**  
> Complete study notes aligned to the official exam domain blueprint.

---

## Study Guide

| Day                                              | Topic                         | Domains Covered                                                                      |
| ------------------------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------ |
| [Day 1](day-01-usd-foundations.md)               | USD Foundations               | Stage, Layer, Prim, Properties, Paths, File Formats, Metadata, Time Samples          |
| [Day 2](day-02-composition-arcs-part-1.md)       | Composition Arcs Part 1       | Opinions, Value Resolution, LIVERPS, Sublayers, References, Payloads                 |
| [Day 3](day-03-composition-arcs-part-2.md)       | Composition Arcs Part 2       | Variants, Inherits, Specializes, Fallback Selections                                 |
| [Day 4](day-04-advanced-composition.md)          | Advanced Composition          | Edit Target, Session Layer, Sparse Overrides, Flatten, Encapsulation                 |
| [Day 5](day-05-schemas-and-data-modeling.md)     | Schemas and Data Modeling     | IsA/API schemas, usdGenSchema, TfType, SdfFileFormat, Model Kinds                    |
| [Day 6](day-06-visualization.md)                 | Visualization                 | Mesh, Primvars, Materials, Shaders, Lights, UsdGeomCamera                            |
| [Day 7](day-07-pipeline-and-data-exchange.md)    | Pipeline and Data Exchange    | Exporters, Importers, usdchecker, Hooks, Data Mapping, Build Config                  |
| [Day 8](day-08-content-aggregation.md)           | Content Aggregation           | Instancing, PointInstancer, Asset Management                                         |
| [Day 9](day-09-debugging-and-troubleshooting.md) | Debugging and Troubleshooting | PrimStack, PropertyStack, TfDebug, MuteLayer, Composition Errors                     |
| [Day 10](day-10-custom-schemas.md)               | Custom Schemas                | IsA/API schemas, usdGenSchema, TfType, SdfFileFormat, Model Kinds, Variant Fallbacks |

---

## Exam Domain Weightings

_Source: [NVIDIA Official Exam Blueprint](https://www.nvidia.com/en-us/learn/certification/openusd-development-professional/)_

| Domain                            | % of Exam | What is Tested                                                                                                   |
| --------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------- |
| **Composition**                   | **23%**   | All composition arcs, LIVERPS, debugging complex composition scenarios                                           |
| **Data Exchange**                 | **15%**   | Conceptual data mapping documents, custom importers, exporters, interchange scripts                              |
| **Pipeline Development**          | **14%**   | Pipeline design, asset management, versioning, exporters, build config, flattening, removing proprietary deps    |
| **Data Modeling**                 | **13%**   | Usd/Sdf data structures, prims, attributes, relationships, primvars, value types, time samples, built-in schemas |
| **Debugging and Troubleshooting** | **11%**   | Introspect stages, fix composition results, identify poorly authored data, optimise load/render                  |
| **Content Aggregation**           | **10%**   | Modular components, instancing (native and point), strategies for overriding instanced assets                    |
| **Visualization**                 | **8%**    | UsdGeom, UsdShade, UsdLux — meshes, cameras, materials, lights                                                   |
| **Customizing USD**               | **6%**    | Custom schemas, file format plugins, custom model kinds, variant fallback selections                             |

> **Total: 100%** — Composition is the single heaviest domain at nearly a quarter of the exam. Combined, Composition + Data Exchange + Pipeline Development + Data Modeling account for **65%** of all questions.

---

## Quick Reference — Function Signatures

### Stage API

```python
Usd.Stage.CreateNew(path: str) -> Usd.Stage
Usd.Stage.Open(path: str, load=Usd.Stage.LoadAll) -> Usd.Stage
Usd.Stage.CreateInMemory() -> Usd.Stage
stage.Save()
stage.Export(path: str)
stage.Flatten() -> SdfLayer
stage.GetRootLayer() -> SdfLayer
stage.GetSessionLayer() -> SdfLayer
stage.GetLayerStack() -> list[SdfLayer]
stage.GetEditTarget() -> Usd.EditTarget
stage.SetEditTarget(target: SdfLayer | Usd.EditTarget)
stage.GetCompositionErrors() -> list[PcpError]
stage.MuteLayer(identifier: str)
stage.UnmuteLayer(identifier: str)
stage.GetMutedLayers() -> list[str]
stage.Load(path: str)
stage.Unload(path: str)
stage.Traverse() -> Usd.PrimRange
stage.GetPrimAtPath(path: str) -> Usd.Prim
stage.DefinePrim(path: str, typeName: str = "") -> Usd.Prim
stage.SetDefaultPrim(prim: Usd.Prim)
```

### Prim API

```python
prim.GetPath() -> Sdf.Path
prim.GetTypeName() -> str
prim.IsValid() -> bool
prim.IsDefined() -> bool
prim.IsActive() -> bool
prim.IsA(schemaType) -> bool
prim.HasAPI(apiSchemaType) -> bool
prim.GetChildren() -> list[Usd.Prim]
prim.GetPrimStack() -> list[SdfPrimSpec]          # no parameters
prim.GetPrimIndex() -> PcpPrimIndex
prim.GetPrimIndex().DumpToString() -> str
prim.SetInstanceable(instanceable: bool)
prim.IsInstanceable() -> bool
prim.GetAttribute(name: str) -> Usd.Attribute
prim.CreateAttribute(name: str, typeName: Sdf.ValueTypeName) -> Usd.Attribute
prim.GetInherits() -> Usd.Inherits
prim.GetSpecializes() -> Usd.Specializes
prim.GetReferences() -> Usd.References
prim.GetPayloads() -> Usd.Payloads
prim.GetVariantSets() -> Usd.VariantSets
```

### Attribute API

```python
attr.Get(time: Usd.TimeCode = Usd.TimeCode.Default()) -> value
attr.Set(value, time: Usd.TimeCode = Usd.TimeCode.Default())
attr.GetTimeSamples() -> list[float]
attr.HasAuthoredValue() -> bool
# timeCode is REQUIRED — no default argument:
attr.GetPropertyStack(timeCode: Usd.TimeCode) -> list[SdfPropertySpec]
# Shorthand: attr.GetPropertyStack(24) == attr.GetPropertyStack(Usd.TimeCode(24))
# WARNING: 0 != TimeCode.Default() — 0 means frame 0, Default() means no-time
```

### UsdUtils

```python
UsdUtils.FlattenLayerStack(stage: Usd.Stage) -> SdfLayer  # sublayers only
UsdUtils.ComputeAllDependencies(path: str) -> (layers, assets, unresolved)
UsdUtils.CreateNewUsdzPackage(src: str, dst: str)
```

---

## Key Mnemonics

**LIVERPS** — composition arc strength order, strongest to weakest:

```
L — Local
I — Inherit
V — Variant
E — rEference
R — (R was Relocates in older USD)
P — Payload
S — Specializes
```

**`def` / `over` / `class`** — the three prim specifiers:

```
def   = Define  — creates and owns the prim
over  = Override — modifies without owning
class = Class   — abstract template, never rendered
```

---

_Notes built from the NVIDIA Learn OpenUSD curriculum and real NCP-OUSD exam analysis._
