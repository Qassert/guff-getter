# OBJECT generator domain audit

This audit classifies the existing OBJECT vocabulary without changing it. The live generator continues to read the two-column `object-generator-vocabulary.csv`; `object-generator-domains.csv` is a metadata-only sidecar and is not loaded at runtime. Rows join by the exact compound key `(category, word)`.

## Coverage

- Total classified entries: **419**
- Physical `object`/`device` entries: **249**
- Descriptor entries: **170**
- Entries marked `needs_review`: **24**

### Counts by grammatical category

| Category | Count |
|---|---:|
| `adjective` | 73 |
| `surreal_descriptor` | 97 |
| `object` | 187 |
| `device` | 62 |

## Physical-object domains

| Domain | Count | Percentage of 249 | Examples |
|---|---:|---:|---|
| `kitchen_and_food_preparation` | 58 | 23.3% | `barbecue grill`, `bowl`, `cheese grater`, `chopping board`, `corkscrew` |
| `electronics_and_computing` | 32 | 12.9% | `antenna`, `battery`, `computer mouse`, `doorbell`, `earphones` |
| `furniture_and_interiors` | 32 | 12.9% | `armchair`, `attic`, `awning`, `bath towel`, `bedframe` |
| `tools_and_hardware` | 29 | 11.6% | `charger`, `extension cord`, `fusebox`, `glue stick`, `hammer` |
| `cleaning_and_laundry` | 18 | 7.2% | `broom`, `compost bin`, `drying rack`, `dust bin`, `dust pan` |
| `office_and_stationery` | 16 | 6.4% | `ballpointpen`, `binder`, `calendar`, `filing cabinet`, `notepad` |
| `clothing_and_accessories` | 11 | 4.4% | `apron`, `backpack`, `button`, `clothes peg`, `key holder` |
| `plumbing_and_sanitation` | 10 | 4.0% | `bathroom scale`, `shower gel`, `showerhead`, `sink strainer`, `soap dish` |
| `gardening_and_outdoors` | 9 | 3.6% | `flower pot`, `garden hose`, `garden rake`, `hedge trimmer`, `lawn mower` |
| `transport_and_maritime` | 7 | 2.8% | `axle`, `car battery`, `carjack`, `car seat`, `gearstick` |
| `safety_and_monitoring` | 7 | 2.8% | `fire extinguisher`, `smoke detector`, `alarm system`, `baby monitor`, `blood pressure monitor` |
| `sports_and_recreation` | 5 | 2.0% | `baseball bat`, `bicycle`, `treadmill`, `bicycle pump`, `fitness tracker` |
| `containers_and_storage` | 5 | 2.0% | `basket`, `bucket`, `plastic container`, `tissue box`, `tray` |
| `domestic_appliances` | 4 | 1.6% | `air conditioner`, `blender`, `juicer`, `bread maker` |
| `lighting_and_heating` | 3 | 1.2% | `bulb`, `candle`, `radiator` |
| `medical_equipment` | 2 | 0.8% | `hot water bottle`, `thermometer` |
| `toys_and_novelty` | 1 | 0.4% | `balloon pump` |

### Kitchen and food share

Kitchen and food-preparation entries account for **58/249 (23.3%)** of physical OBJECT vocabulary.

## Descriptor domains

| Domain | Count | Examples |
|---|---:|---|
| `personality_and_social` | 30 | `obnoxious`, `peculiar`, `pompous`, `ridiculous`, `scandalous` |
| `condition_and_damage` | 21 | `ancient`, `broken`, `filthy`, `flimsy`, `greasy` |
| `physical_property` | 18 | `absurd`, `awkward`, `automatic`, `bizarre`, `boiling` |
| `emotion_and_mood` | 16 | `anxious`, `breathless`, `depressed`, `dizzy`, `embarrassed` |
| `motion_and_mechanics` | 12 | `bouncy`, `chaotic`, `explosive`, `jittery`, `pulsing` |
| `texture_and_surface` | 9 | `damp`, `furry`, `hairy`, `moist`, `prickly` |
| `medical_and_biological` | 9 | `abnormal`, `anatomical`, `bacterial`, `behavioral`, `biological` |
| `scientific_and_technical` | 9 | `auxiliary`, `barometrical`, `chemical`, `functional`, `interactive` |
| `logical_and_abstract` | 9 | `causal`, `collective`, `divine`, `ethical`, `illogical` |
| `light_and_colour` | 8 | `fluorescent`, `glittering`, `luminous`, `psychedelic`, `shiny` |
| `shape_and_geometry` | 7 | `crooked`, `distorted`, `jagged`, `lopsided`, `triangular` |
| `size_and_proportion` | 6 | `bulky`, `enormous`, `gargantuan`, `gigantic`, `massive` |
| `sound` | 5 | `clattering`, `noisy`, `squeaky`, `sonic`, `tonal` |
| `supernatural_and_mystical` | 5 | `demonic`, `mysterious`, `sinister`, `spooky`, `spiritual` |
| `legal_and_institutional` | 3 | `accusative`, `legal`, `objective` |
| `political_and_economic` | 3 | `economic`, `political`, `strategic` |

## Entries requiring review

- `object:attic` — currently `furniture_and_interiors` / `location_or_space`. It is a room or location rather than a portable object.
- `object:curtains` — currently `furniture_and_interiors` / `fixture`. They can be treated as furnishings or architectural fixtures.
- `object:fabric softener` — currently `cleaning_and_laundry` / `consumable`. It is a consumable represented in the object bank.
- `object:freezer` — currently `kitchen_and_food_preparation` / `powered_device`. It can be treated as a domestic appliance or storage equipment.
- `object:keyboard` — currently `electronics_and_computing` / `passive_object`. It can mean computing equipment or a musical instrument.
- `object:laptop` — currently `electronics_and_computing` / `passive_object`. It is a portable computer rather than a generic passive object.
- `object:microwave` — currently `kitchen_and_food_preparation` / `powered_device`. The inherited shorthand can denote an appliance or electromagnetic radiation.
- `object:postitnotes` — currently `office_and_stationery` / `passive_object`. The inherited compressed spelling needs editorial review.
- `object:shower gel` — currently `plumbing_and_sanitation` / `consumable`. It is a consumable represented in the object bank.
- `object:superglue` — currently `tools_and_hardware` / `consumable`. It is a consumable represented in the object bank.
- `object:toothpaste` — currently `plumbing_and_sanitation` / `consumable`. It is a consumable represented in the object bank.
- `object:treadmill` — currently `sports_and_recreation` / `powered_device`. It is a powered exercise machine represented in the object bank.
- `object:wax paper` — currently `kitchen_and_food_preparation` / `consumable`. It is a consumable/material represented in the object bank.
- `object:aluminum foil` — currently `kitchen_and_food_preparation` / `consumable`. It is a material/consumable represented in the object bank.
- `device:camera` — currently `electronics_and_computing` / `powered_device`. It may be consumer electronics or monitoring equipment.
- `device:heater` — currently `electronics_and_computing` / `powered_device`. It may be a domestic appliance or industrial equipment.
- `device:router` — currently `electronics_and_computing` / `powered_device`. It may mean networking equipment or a woodworking tool.
- `device:thermometer` — currently `medical_equipment` / `measuring_instrument`. It may be medical, domestic, or scientific measuring equipment.
- `device:timer` — currently `electronics_and_computing` / `measuring_instrument`. It may be a measuring instrument or electronic control component.
- `device:drill bit` — currently `tools_and_hardware` / `component`. It is a component despite occurring in the device category.
- `device:oscillatingfan` — currently `electronics_and_computing` / `powered_device`. The inherited compressed spelling needs review; it crosses appliance/electronics domains.
- `device:pressurewasher` — currently `cleaning_and_laundry` / `powered_device`. The inherited compressed spelling needs review; it crosses domestic-tool and industrial-machinery domains.
- `device:razorblade` — currently `tools_and_hardware` / `component`. It is a component/consumable despite occurring in the device category.
- `device:steamer basket` — currently `kitchen_and_food_preparation` / `container`. It is a passive kitchen implement despite occurring in the device category.

## Gaps and expansion priorities

The following requested physical domains are absent: `industrial_machinery`, `scientific_and_laboratory_equipment`, `agriculture_and_farming`, `musical_instruments`, `entertainment_and_theatre`, and `historical_and_ceremonial_objects`. `toys_and_novelty` has only one entry; `medical_equipment` and `lighting_and_heating` are also poorly represented.

Future expansion should prioritise recognisable entries in those absent domains, followed by transport, gardening, safety equipment, and clothing. This would reduce the present concentration in kitchen, electronics, and interior objects without changing phrase grammar. Descriptor expansion should prioritise precise scientific/technical, medical/biological, shape, sound, legal/institutional, and political/economic properties while retaining immediately understandable imagery.

## Maintenance and safety

- Do not add metadata columns to the live two-column vocabulary: its parser rejects rows that do not contain exactly two fields.
- Do not modify the six shared files in `newsmuncher/resources/words/`; MUNGE CLASSIC and other services consume them directly.
- Add or review metadata in the sidecar using the exact existing spelling and `(category, word)` key.
- A `confirmed` status means the primary classification is straightforward. `needs_review` preserves uncertainty without changing generator eligibility.
- `source_file` records the verified category-level provenance: descriptor categories were copied from `adverbs.csv`; physical categories were copied from `animalsAndObjects.csv`. The sidecar contains copies, not runtime references.
