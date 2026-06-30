# Day 10 - Custom Schemas

> **OpenUSD NCP Certification Study Notes**  
> _Custom IsA Schemas, API Schemas, usdGenSchema, TfType, SdfFileFormat, Model Kinds, Variant Fallbacks_

---

## Table of Contents

1. [Why Custom Schemas?](#1-why-custom-schemas)
2. [The Schema Inheritance Hierarchy](#2-the-schema-inheritance-hierarchy)
3. [The Complete usdGenSchema Workflow](#3-the-complete-usdgenschema-workflow)
4. [The TfType System — What Registration Actually Means](#4-the-tftype-system--what-registration-actually-means)
5. [File Format Plugins — SdfFileFormat](#5-file-format-plugins--sdffileformat)
6. [Custom Model Kinds — UsdModelKindRegistry](#6-custom-model-kinds--usdmodelkindregistry)
7. [Variant Fallback Selections](#7-variant-fallback-selections)
8. [Exam Pattern Recognition — Elimination Guide](#8-exam-pattern-recognition--elimination-guide)
9. [Key Takeaways — The 12 Things to Know Cold](#9-key-takeaways--the-12-things-to-know-cold)

---

## 1. Why Custom Schemas?

USD ships with schemas for common 3D concepts — `Mesh`, `Sphere`, `Material`, `DistantLight`. These cover general-purpose use cases. But a factory automation company needs prims for `TemperatureSensor` and `ConveyorBelt`. A film studio needs `ShotCamera` and `CharacterRig`. These don't exist in USD out of the box.

Custom schemas let you add new prim types as **first-class USD citizens** — with the same type safety, API generation, schema fallbacks, and tool integration as built-in schemas.

### Plain Attributes vs Custom Schema

| Capability                    | Plain custom attributes           | Custom schema                        |
| ----------------------------- | --------------------------------- | ------------------------------------ |
| `prim.IsA(TemperatureSensor)` | ❌ No type checking               | ✅ Works correctly                   |
| Schema fallback values        | ❌ Returns `None` if unset        | ✅ Returns defined default           |
| Generated Python/C++ API      | ❌ Manual `GetAttribute("name")`  | ✅ `sensor.GetTemperatureAttr()`     |
| usdview introspection         | ❌ Arbitrary data, no schema info | ✅ Full attribute listing with types |
| Validation at authoring time  | ❌ Silent errors                  | ✅ Type-checked at definition        |
| Inheritance chain known       | ❌ No                             | ✅ `IsA(UsdGeomXform)` also works    |

### When to Use

| ✅ Use custom schemas when                 | ❌ Don't use for                          |
| ------------------------------------------ | ----------------------------------------- |
| Standardised types shared across teams     | Quick one-off pipeline attributes         |
| `prim.IsA()` and `prim.HasAPI()` must work | Data not shared across tools              |
| Schema fallback values are needed          | Rapid prototyping (use plain attrs first) |
| Full C++ and Python API is needed          | One-time migration scripts                |

---

## 2. The Schema Inheritance Hierarchy

Choosing the wrong base class is a common exam trap. The hierarchy determines what capabilities your schema inherits.

```
UsdSchemaBase                            ← root of ALL schemas
├── UsdTyped                             ← base for all IsA (typed) schemas
│   ├── UsdGeomImageable                 ← all renderable prims (visibility, purpose)
│   │   ├── UsdGeomXformable             ← all transformable prims
│   │   │   ├── UsdGeomGprim             ← all geometric primitives
│   │   │   │   ├── UsdGeomMesh
│   │   │   │   ├── UsdGeomSphere
│   │   │   │   └── ...
│   │   │   ├── UsdGeomCamera
│   │   │   └── UsdLuxLight
│   │   └── UsdShadeMaterial
│   └── (other UsdTyped subclasses)
└── UsdAPISchemaBase                     ← base for all API schemas
    ├── UsdGeomMotionAPI
    ├── UsdPhysicsRigidBodyAPI
    └── ...


                    YOUR CUSTOM SCHEMA
                    → Inherit from UsdTyped
                      or UsdGeomImageable
                      NOT directly from UsdSchemaBase
```

### Choosing the Right Base Class

| Base Class         | What it gives you                                                                                                                    | When to use                                                                                         | Exam answer?                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `UsdSchemaBase`    | The absolute root — requires implementing everything manually including type registration, property management, and all API plumbing | Almost never directly — only for building completely new schema infrastructure                      | ❌ Wrong answer — error-prone, not recommended |
| `UsdTyped`         | Sets `typeName` on the prim. All plumbing for `IsA()` to work. Schema fallback values. Standard base for typed IsA schemas.          | Any custom IsA schema that is a new prim type — `TemperatureSensor`, `ConveyorBelt`, `CharacterRig` | ✅ Correct — recommended standard base         |
| `UsdGeomImageable` | Everything from UsdTyped + `visibility` + `purpose` attributes. The base for anything that renders.                                  | Custom schemas for renderable objects — custom geometry types, custom lights                        | ✅ Correct for renderable objects              |

> **Critical exam trap:** "Inherit directly from `UsdSchemaBase`" is almost always the wrong answer. The correct base for a standard custom IsA schema is `UsdTyped`. For a renderable object, use `UsdGeomImageable`.

---

## 3. The Complete usdGenSchema Workflow

`usdGenSchema` is the code generation tool that transforms a `schema.usda` definition into compilable C++ source code and Python bindings. This is the required path for production-grade custom schemas.

### Step 1 — Write `schema.usda`

Define your schema class, its base class, and its attributes with types and defaults:

```usda
#usda 1.0
(
    subLayers = [
        @usd/schema.usda@           # inherit from base USD schemas
    ]
)

over "GLOBAL" (
    customData = {
        string libraryName   = "acmeSensors"    # your library name
        string libraryPrefix = "AcmeSensor"     # C++ class prefix
    }
) {}

# ── IsA Schema — defines a new prim TYPE ────────────────────────────
class Xform "TemperatureSensor" (
    customData = {
        string className = "TemperatureSensor"
    }
    doc = """A prim representing a physical temperature sensor in
             the factory automation pipeline."""
    inherits = </Xform>              # inherits from UsdGeomXform
                                     # which inherits from UsdGeomImageable
                                     # which inherits from UsdTyped
) {
    # Attribute definitions — these become GetXxxAttr() methods
    float  sensor:temperature = 20.0     (
        doc = "Current sensor reading in degrees Celsius."
    )
    float  sensor:minRange    = -40.0    (
        doc = "Minimum measurable temperature."
    )
    float  sensor:maxRange    = 125.0    (
        doc = "Maximum measurable temperature."
    )
    string sensor:serialNumber = ""      (
        doc = "Manufacturer serial number for asset tracking."
    )
}
```

### Step 2 — Run usdGenSchema

```bash
usdGenSchema schema.usda
```

This generates:

- `acmeSensors.h` — C++ header with class declaration and attribute accessors
- `acmeSensors.cpp` — C++ implementation
- `wrapAcmeSensors.cpp` — Python binding code
- `plugInfo.json` — plugin discovery and TfType registration metadata

### Step 3 — Compile C++ into a shared library

```bash
# Using CMake
cmake -DPXR_ROOT=/path/to/usd_install .
make

# Output:
# acmeSensors.so  (Linux)
# acmeSensors.dll (Windows)
```

### Step 4 — Deploy the plugin

Place the compiled library and `plugInfo.json` where USD can discover them:

```bash
# Set the plugin path environment variable
export PXR_PLUGINPATH_NAME=/path/to/acmeSensors/

# USD reads plugInfo.json at startup and registers the types
```

### Step 5 — Use like any built-in schema

```python
from pxr import Usd, AcmeSensors   # your generated module

stage = Usd.Stage.CreateInMemory()

# Define a prim using your custom IsA schema
sensor = AcmeSensors.TemperatureSensor.Define(stage, "/Factory/Sensor_001")

# Schema fallback values work — even without Set()
print(sensor.GetTemperatureAttr().Get())   # 20.0 ← schema fallback
print(sensor.GetMinRangeAttr().Get())      # -40.0
print(sensor.GetSerialNumberAttr().Get())  # ""

# Set a value
sensor.GetTemperatureAttr().Set(23.5)

# Type checking works — full inheritance chain known
prim = sensor.GetPrim()
print(prim.GetTypeName())                           # "TemperatureSensor"
print(prim.IsA(AcmeSensors.TemperatureSensor))     # True
print(prim.IsA(UsdGeom.Xform))                     # True — inheritance
print(prim.IsA(UsdGeom.Imageable))                 # True — inheritance chain
```

### Why Not Python-Only?

| Python-only schema                                 | Full C++ schema via usdGenSchema    |
| -------------------------------------------------- | ----------------------------------- |
| No C++ type registration                           | ✅ Full TfType registration         |
| `prim.IsA()` fails or returns False                | ✅ `IsA()` works correctly          |
| No schema fallback values — `Get()` returns `None` | ✅ Schema fallbacks work            |
| No generated accessor methods                      | ✅ `GetTemperatureAttr()` etc.      |
| Not found by USD's schema discovery                | ✅ Discoverable via `plugInfo.json` |
| **Correct for prototyping only**                   | **Required for production**         |

---

## 4. The TfType System — What Registration Actually Means

`TfType` is USD's runtime type identification system. Registration is what makes `prim.IsA()`, `prim.HasAPI()`, schema fallback values, and schema discovery actually function.

### What Breaks Without Registration

```python
# You have a USD file with typeName = "TemperatureSensor"
# But the schema plugin is NOT deployed:

prim.IsA(TemperatureSensor)      # ERROR or always False
prim.GetTypeName()               # "TemperatureSensor" — just a string, no meaning
sensor.GetTemperatureAttr().Get() # None — no schema fallback known
# usdview shows: "unknown schema type"
# No attribute listing from schema definition
```

### What Registration Enables

```python
# Schema plugin IS deployed with plugInfo.json:

prim.IsA(AcmeSensors.TemperatureSensor)  # True ✅
prim.IsA(UsdGeom.Xform)                 # True ✅ — inheritance chain known
prim.IsA(UsdGeom.Imageable)             # True ✅ — full hierarchy traversable
sensor.GetTemperatureAttr().Get()        # 20.0 ✅ — schema fallback works
# usdview shows all attributes with types, defaults, documentation
# Schema API methods all function correctly
```

### How Registration Happens

```
1. usdGenSchema generates plugInfo.json
   → declares library name, all schema types, their base types

2. Plugin is deployed to PXR_PLUGINPATH_NAME

3. USD startup sequence:
   → scans all directories in PXR_PLUGINPATH_NAME
   → reads every plugInfo.json found
   → for each declared type: registers it in the TfType registry
      including its base class chain

4. Now at runtime:
   → prim.IsA(TemperatureSensor) triggers TfType lookup
   → registry knows: TemperatureSensor → Xform → Imageable → Typed → SchemaBase
   → can answer IsA() queries for the entire chain
```

> **Exam trap:** "Registering the custom model kind token in the TfType system without any schema or API linkage" is **WRONG**. Token registration alone provides a name but no inheritance chain, no fallback values, and no API. The schema definition itself must be fully linked.

---

## 5. File Format Plugins — SdfFileFormat

A **file format plugin** teaches USD to read and write a new file type. This is **completely independent** from custom schemas.

```
Custom Schema   = defines what scene data IS (prim types, attributes, meaning)
SdfFileFormat   = defines how data is READ and WRITTEN from/to files
```

These address entirely different problems. A factory might need both: a custom `TemperatureSensor` schema (defines the data type) AND a `SdfFileFormat` plugin for their proprietary `.mysim` simulation format (teaches USD to read that format).

### Implementation Steps

```
1. Create C++ class inheriting from SdfFileFormat:
   class MyFormatPlugin : public SdfFileFormat { ... }

2. Implement required interface methods:
   bool Read(SdfLayer*, const string& resolvedPath, bool metadataOnly)
   bool WriteToFile(const SdfLayer&, const string& filePath, ...)
   bool CanRead(const string& filePath) const

3. Register with TfType:
   TF_REGISTRY_FUNCTION(TfType) {
       TfType::Define<MyFormatPlugin,
                      TfType::Bases<SdfFileFormat>>();
   }

4. Declare in plugInfo.json:
   USD discovers it at startup via PXR_PLUGINPATH_NAME

5. Now USD can transparently open your format:
   stage = Usd.Stage.Open("simulation.mysim")
   → USD sees .mysim extension
   → Looks up registered SdfFileFormat plugins
   → Finds MyFormatPlugin (registered for .mysim)
   → Calls MyFormatPlugin.Read() to translate to SdfLayer
   → Stage composes normally from that point
```

### Wrong Approaches

| Wrong approach                           | Why it's wrong                                                                                                                               |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Override `UsdStage::Open()`              | Static method, not designed for overriding. File loading happens at the `SdfLayer` level, not `Stage` level.                                 |
| Modify USD core source code              | USD is designed for extensibility via plugins. Modifying core breaks compatibility with all other USD tools and is never the correct answer. |
| Create a `UsdSchema` for the file format | Schemas define scene description types. They do NOT control file I/O. These are completely separate concerns.                                |

---

## 6. Custom Model Kinds — UsdModelKindRegistry

USD has a built-in hierarchy of **model kinds** that classify prims by their role in the scene:

```
assembly       ← top-level published collection of assets (a full scene or set)
  group        ← organisational container (a city block, a character rig)
    component  ← leaf reusable asset (a chair, a tree, a sensor)
      subcomponent ← important internal node within a component
```

Custom model kinds extend this hierarchy with domain-specific classifications.

### The 5-Step Process

**Step 1 — Define a unique token for your kind**

```python
# "factory_unit" — a new kind for factory floor assets
# This is just a string token at this stage
```

**Step 2 — Register with `UsdModelKindRegistry`**

The registry must know this kind exists and where it sits in the hierarchy (its parent kind).

**Step 3 — Apply to prims using `Usd.ModelAPI`**

```python
from pxr import Usd

prim      = stage.DefinePrim("/Factory/Unit_A", "Xform")
model_api = Usd.ModelAPI(prim)
model_api.SetKind("factory_unit")

# Verify
print(model_api.GetKind())   # "factory_unit"
```

**Step 4 — Implement a schema plugin that EXTENDS (not overrides) `UsdModelAPI`**

Your plugin adds behaviours and properties specific to `factory_unit` without replacing the existing `UsdModelAPI` behaviour.

```
EXTEND UsdModelAPI   ← adds behaviour for the new kind  ✅
OVERRIDE UsdModelAPI ← replaces existing behaviour      ❌ WRONG
```

**Step 5 — Extend the `Validate()` method**

Add domain-specific structural validation:

```python
# Custom validation rules for factory_unit prims:
# "must have a sensor:serialNumber attribute"
# "must have at least one child TemperatureSensor prim"
# "must have pipeline:facilityId metadata set"
```

### Wrong Approaches

| Wrong approach                                                        | Why                                                                                                 |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Override (not extend) `UsdModelAPI`                                   | Replaces existing `assembly`/`component`/`group` behaviour — breaks standard kinds for all users    |
| Register token in TfType without schema linkage                       | Provides a name but no behaviour, validation, or API                                                |
| Use variants within the model kind to handle different configurations | Variants serve content variation (LOD, colour). Model kinds serve classification. Separate systems. |
| Modify USD core source                                                | USD's plugin and registry system exists precisely to avoid this                                     |

---

## 7. Variant Fallback Selections

When a scene requests a variant that doesn't exist in a given asset, **variant fallback selections** define what USD should use instead.

```
Scene requests: lod = "ultra"
"ultra" variant doesn't exist in the asset.
→ Without fallbacks: composition error or wrong result
→ With fallbacks: USD tries "high", then "medium", then "low"
```

### Three Correct Approaches

**Approach 1 — `variantFallbacks` in USDA layer metadata**

```usda
#usda 1.0
(
    variantFallbacks = {
        string[] "lod"   = ["high", "medium", "low"]
        string[] "color" = ["default"]
    }
)
```

**Approach 2 — `Usd.Stage.SetGlobalVariantFallbacks()` (Python)**

```python
from pxr import Usd

# Must be called BEFORE opening the stage
fallbacks = {
    "lod":   ["high", "medium", "low"],
    "color": ["default"],
}
Usd.Stage.SetGlobalVariantFallbacks(fallbacks)

# Now all stages opened after this call use these fallbacks
stage = Usd.Stage.Open("scene.usda")
```

**Approach 3 — Session layer overrides**

Author fallback variant selections into the session layer for per-user or per-environment preferences:

```python
stage   = Usd.Stage.Open("scene.usda")
session = stage.GetSessionLayer()
stage.SetEditTarget(session)
# Author fallback selections — never saved to disk
```

### Wrong Approaches

| Wrong approach                                           | Why                                                                                                       |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Embed fallback selections in prim metadata               | Prim metadata is not designed for fallback logic — leads to unpredictable behaviour                       |
| Rely only on the default variant selection in the schema | Default selections don't cover cases where the requested variant doesn't exist                            |
| Use fallbacks only during composition, not runtime       | Fallbacks are relevant at runtime too — dynamic scenes can request variants that need fallback resolution |

---

## 8. Exam Pattern Recognition — Elimination Guide

### Pattern 1 — "How do you create a custom schema?"

**Correct answer framework:**

1. Write `schema.usda`
2. Inherit from **`UsdTyped`** or **`UsdGeomImageable`** (NOT `UsdSchemaBase` directly)
3. Run **`usdGenSchema`** to generate C++ and Python
4. Register with **TfType system** via `plugInfo.json`
5. Deploy as plugin via `PXR_PLUGINPATH_NAME`

### Pattern 2 — "How do you add a new file format?"

**Correct answer framework:**
Implement the **`SdfFileFormat` interface** + register with **TfType system** + declare in `plugInfo.json`

### Pattern 3 — "How do you create custom model kinds?"

**Correct answer framework:**
Unique token + **`UsdModelKindRegistry`** + `kind` metadata on root prim via **`UsdModelAPI`** + schema plugin that **inherits** (EXTENDS, not overrides) `UsdModelAPI` + extended `Validate()` method

### Pattern 4 — "Extend vs Override"

> Any option saying "**override**" an existing schema, API, or core system = **WRONG**. USD is always extended, never overridden. Overriding breaks existing functionality for all users of that schema. Extending (inheriting from, adding to) maintains backward compatibility while adding new capabilities.

### Instant Elimination Phrases

Eliminate **any option** containing these phrases immediately:

| Phrase in option                                               | Reason to eliminate                                      |
| -------------------------------------------------------------- | -------------------------------------------------------- |
| `"Modify the core USD source code"`                            | USD uses plugins — never modifies core                   |
| `"Python-only schema"` or `"subclassing Usd.Schema in Python"` | Full schemas need C++ + usdGenSchema                     |
| `"Inheriting directly from UsdSchemaBase"`                     | Correct base is `UsdTyped` or `UsdGeomImageable`         |
| `"Overriding"` any existing schema, API, or method             | Always EXTEND — never override                           |
| `"Override UsdStage::Open()"`                                  | File formats use `SdfFileFormat`, not Stage::Open        |
| `"Register token in TfType WITHOUT schema or API linkage"`     | Token alone is insufficient — needs full schema backing  |
| `"Define schema in a .usd file at runtime"`                    | Schemas defined in `schema.usda` + compiled offline      |
| `"Create new UsdSchema to control file format I/O"`            | Schemas ≠ file I/O — use `SdfFileFormat`                 |
| `"Embed fallback variant selections in prim metadata"`         | Fallbacks belong at stage/layer level, not prim metadata |

---

## 9. Key Takeaways — The 12 Things to Know Cold

| #   | Concept                      | What to Remember                                                                                                                |
| --- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Complete schema workflow** | `schema.usda` → `usdGenSchema` → C++ compile → TfType register → plugin deploy                                                  |
| 2   | **Correct base class**       | `UsdTyped` (standard) or `UsdGeomImageable` (renderable). NOT `UsdSchemaBase`. NOT Python-only.                                 |
| 3   | **TfType registration**      | Makes `IsA()`, `HasAPI()`, fallback values, and schema discovery work. Token alone is insufficient.                             |
| 4   | **SdfFileFormat**            | For new file formats — completely independent from schema types. Never override `UsdStage::Open()`.                             |
| 5   | **Custom model kinds**       | Unique token + `UsdModelKindRegistry` + `kind` metadata on prim + schema plugin extending `UsdModelAPI` + extended `Validate()` |
| 6   | **Extend vs Override**       | Always **EXTEND** `UsdModelAPI` — never override. Override breaks existing kinds.                                               |
| 7   | **Variant fallbacks**        | `Usd.Stage.SetGlobalVariantFallbacks()` or `variantFallbacks` in layer metadata or session layer                                |
| 8   | **Fallback placement**       | Fallbacks belong at stage/layer level — NOT embedded in prim metadata                                                           |
| 9   | **Variants vs model kinds**  | Variants = content variation (LOD, colour). Model kinds = prim classification. Separate systems.                                |
| 10  | **Never modify core**        | USD's entire extensibility architecture — plugins, schemas, file formats — exists to avoid core modification                    |
| 11  | **Schema vs file format**    | Schema = what data IS. `SdfFileFormat` = how data is STORED. Independent concerns.                                              |
| 12  | **Elimination rule**         | If an option says "override", "modify core", "Python-only", or "token without linkage" → eliminate immediately                  |

---

_Related notes:_  
_[Day 5 — Schemas and Data Modeling](day-05-schemas-and-data-modeling.md) — overview of IsA vs API schemas_  
_[Day 9 — Debugging and Troubleshooting](day-09-debugging-and-troubleshooting.md) — schema version validation_

_Previous: [Day 9 — Debugging and Troubleshooting](day-09-debugging-and-troubleshooting.md)_
_Back to start: [Day 1 — USD Foundations](day-01-usd-foundations.md)_
