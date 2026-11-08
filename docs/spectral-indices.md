# Sentinel-2 spectral-index analysis

This project computes its own NDVI, NDBI and MNDWI composites and a simple index-rule classification for the whole City of Gold Coast, for 2020 and 2025. The aim is to check whether a transparent index method picks out developed areas, such as the streets of Arundel, that DEA Land Cover maps as vegetation. The outputs are this project's own analysis. They are not DEA classes, and the app labels them as such.

- **Processing:** Python in [`analysis/`](../analysis). Settings and thresholds are in [`analysis/config.toml`](../analysis/config.toml).
- **Records:** every run writes a processing manifest per year, for example [`analysis/results/2025/processing_manifest.json`](../analysis/results/2025/processing_manifest.json) and [`analysis/results/2020/processing_manifest.json`](../analysis/results/2020/processing_manifest.json).
- **Web outputs:** static PNG tiles and `layers.json` per year in [`public/data/sentinel2-2025/`](../public/data/sentinel2-2025) and [`public/data/sentinel2-2020/`](../public/data/sentinel2-2020).

The 2025 facts below were checked on 4–5 November 2026, and the 2020 and 2015 facts on 8 November 2026. Unless a section says otherwise, it describes 2025, and 2020 was processed the same way.

## Years

| Year | Status | Source | Acquisitions used | Actual period | Clear observations per pixel (median, 1st percentile) |
| --- | --- | --- | --- | --- | --- |
| 2025 | In the app | Earth Search Collection 1, baseline 05.11, Sentinel-2A, 2B and 2C | 144 of 172 | 3 Jan – 31 Dec 2025 | 78, 32 |
| 2020 | In the app | Earth Search Collection 1, baseline 05.00, Sentinel-2A and 2B | 125 of 143 | 1 Jan – 31 Dec 2020 | 66, 23 |
| 2015 | Not added | See *2015* below | 10 at most | 29 Sep – 28 Dec 2015 | 2, 0 |

### 2020

`python -m spectral_indices --year 2020 all` reused everything from 2025 unchanged: the 20 m grid, boundary mask, SCL masks and cloud buffer, index formulas, compositing method, minimum of 5 observations and classification thresholds. Before processing, `plan` confirmed that 2020 is compatible:

- **Items:** 285 items from the same two MGRS tiles, grouped into 143 acquisitions, on the same two relative orbits (R030 and R130). One acquisition was published for one tile only.
- **Product:** all items are Collection 1 Level-2A, processing baseline 05.00, from the same reprocessing campaign as 2025's 05.11. Sentinel-2C did not exist yet, so there are fewer acquisitions.
- **Bands and scaling:** the same assets (`green`, `red`, `nir08`, `swir16`, `scl`), the same native resolutions, and the same `scale 0.0001, offset −0.1` on every reflectance band.
- **10 m bands:** the COGs carry the same AVERAGE overview on the same 20 m lattice (origin 499980/6900040).
- **Grid:** identical to 2025, including the tile split at row 2098.
- **Quality layer:** SCL with no-data 0 and the same class meanings.

Results:
- **Download:** 18 acquisitions had less than 1% clear pixels and were skipped, and 125 were stored. Reading took about 40 minutes and 5.52 GB, and the cache is 3.8 GB.
- **Coverage:** clear observations per pixel range from 5 to 97 (median 66), and 62 pixels (0.02 km²) are below the minimum for at least one index.
- **Checks:** `verify` passed every check (see *Verification*).
- **Not re-assessed:** the 2025 reference labels describe 2025 imagery, so `calibrate` and `assess` run only for 2025. The 2020 classes use the 2025 thresholds without a separate accuracy check.

### 2015

2015 was checked and not added as a regional layer. Two separate problems stop it.

**Access.**
- **Earth Search:** its Collection 1 catalogue (`sentinel-2-c1-l2a`) returns no items over the study area for 2015 or 2016.
- **Copernicus Data Space:** the STAC catalogue (`https://stac.dataspace.copernicus.eu/v1`, collection `sentinel-2-l2a`) returns 20 items for 2015. They are Collection 1, baseline 05.00, from both MGRS tiles, and form 10 acquisitions from 29 September to 28 December 2015.
  - **Credentials:** every asset is marked as needing either S3 keys or an OpenID Connect token. An anonymous HTTPS download returned HTTP 401, and the S3 endpoint returned HTTP 403.
  - **What it would take:** a free Copernicus Data Space account, whose credentials this project does not have.
  - **Asset layout:** the assets are JPEG 2000 files inside SAFE products (`B03_10m`, `B04_10m`, `B8A_20m`, `B11_20m`, `SCL_20m`) with `raster:scale 0.0001, raster:offset −0.1`, not cloud-optimised GeoTIFFs.
- **Microsoft Planetary Computer:** this free catalogue needs no account and lists the same 10 acquisitions for 2015, but from older processing baselines (02.12 and 03.00), not Collection 1.

**Coverage.** Sentinel-2A was the only satellite in orbit in 2015 and began routine imaging in late 2015, so there are only 10 acquisitions over the Gold Coast. The SCL layers of all 10 were read from Planetary Computer onto this project's grid and boundary, with this project's mask (SCL 4–7, 40 m buffer around cloud and shadow). This was a one-off check, not a pipeline stage.

| Date | Relative orbit | Observed inside the boundary | Clear inside the boundary |
| --- | --- | --- | --- |
| 2015-09-29 | R130 | 62% | 54% |
| 2015-10-19 | R130 | 100% | 13% |
| 2015-10-23 | R030 | 69% | 37% |
| 2015-11-12 | R030 | 78% | 8% |
| 2015-11-22 | R030 | 57% | 1% |
| 2015-11-28 | R130 | 61% | 20% |
| 2015-12-08 | R130 | 64% | 16% |
| 2015-12-18 | R130 | 100% | 52% |
| 2015-12-22 | R030 | 52% | 4% |
| 2015-12-28 | R130 | 62% | 31% |

- **Per pixel:** the median pixel inside the boundary has 2 clear observations, and the best pixel has 8.
- **Against the minimum:** only 11% of pixels reach the minimum of 5. With the minimum kept, 89% of the city would be "Insufficient observations", in a composite covering only spring and early summer.
- **Different SCL processing:** Planetary Computer's older scene classification differs in detail from Collection 1. But no cloud mask can raise any pixel above 10 observations, and most dates are largely cloudy.

**Possible next steps,** if an earlier Sentinel-2 year is wanted:
- **2016:** Planetary Computer lists 125 items (about 62 acquisitions) for the study area.
- **Collection 1 for 2015 or 2016:** a Copernicus Data Space account would give access, at the cost of reading JPEG 2000 files.

## Imagery source and access

| Item | Value |
| --- | --- |
| Product | Sentinel-2 Level-2A surface reflectance, Collection 1 (ESA processing baseline 05.11 for every 2025 item, 05.00 for every 2020 item) |
| Catalogue | Element 84 Earth Search STAC API, `https://earth-search.aws.element84.com/v1`, collection `sentinel-2-c1-l2a` |
| Files | Cloud-optimised GeoTIFFs in the public bucket `e84-earth-search-sentinel-data` (AWS us-west-2), `requester_pays: false` |
| Access | Anonymous HTTPS. No account, API key, token or paid service |
| Licence | Copernicus Sentinel data legal notice (free, full and open). Required credit: "Contains modified Copernicus Sentinel data 2025", or 2020 for that year |
| Citation | `https://doi.org/10.5270/S2_-742ikth` (the collection's `cite-as` link) |

Alternatives that were not chosen:
- **Microsoft Planetary Computer** needs a signed token for every request.
- **Copernicus Data Space** needs an account for downloads (confirmed again for 2015, see *Years*).
- **DEA's own Sentinel-2 product** is a different surface reflectance product (ARD), not ESA Level-2A.

### What the search found

A STAC search over the boundary's bounding box for 2025-01-01 to 2025-12-31 returned:
- **Items:** 344, from two MGRS tiles, 56JNQ (north) and 56JNP (south), 172 items each.
- **Acquisitions:** the items group into 172 acquisitions (datatakes), because each acquisition appears once per tile.
- **Satellites:** 2A, 2B and 2C.
- **Orbits:** two relative orbits, R030 and R130.
- **First and last:** 2025-01-03 to 2025-12-31.

Every item is in WGS 84 / UTM zone 56S (EPSG:32756).

### Bands and quality layer

| Use | Band | Asset | Native resolution | Read as |
| --- | --- | --- | --- | --- |
| Green | B03 | `green` | 10 m | The COG's first overview (20 m) |
| Red | B04 | `red` | 10 m | The COG's first overview (20 m) |
| NIR | B8A (narrow NIR) | `nir08` | 20 m | Full resolution |
| SWIR1 | B11 | `swir16` | 20 m | Full resolution |
| Quality | Scene Classification Layer (SCL) | `scl` | 20 m | Full resolution |

**Why B8A rather than B08.** B8A is the NIR band ESA itself provides at 20 m. Using it means the NIR values for NDVI and NDBI need no resampling, and both indices use the same NIR band.

**10 m bands read from the overview.**
- **What the overview is:** each 10 m COG stores `OVR_RESAMPLING_ALG=AVERAGE`, and its first overview sits exactly on the 20 m lattice (origin 499980/6900040).
- **Test:** on a cloud-free 1024 × 1024 block, that overview matched a 2 × 2 mean of the full-resolution pixels within 0.5 DN (integer rounding, 0.00005 reflectance). Picking a single 10 m pixel instead differed by up to 1,871 DN.
- **Effect:** reading the overview is therefore an exact 2 × 2 area average, at a quarter of the download.
- **At swath edges:** GDAL's average skips no-data pixels, so a 20 m value can come from fewer than four valid 10 m pixels.

### Scale and offset

Each item's STAC `raster:bands` gives `scale 0.0001, offset -0.1` for all four bands. ESA's own product metadata (`product_metadata.xml`) confirms this, with `BOA_QUANTIFICATION_VALUE 10000` and `BOA_ADD_OFFSET -1000` for every band.

- **Applied before any index is calculated:** reflectance = DN × 0.0001 − 0.1.
- **Taken from each item:** the values are stored per acquisition in its status file. Acquisition fails if two tiles of one acquisition disagree.

## Inspecting before downloading

`plan` reads only STAC metadata (9.7 s) and estimates the volume:

| Quantity | Value |
| --- | --- |
| The five needed assets as whole files, all 344 items | 112.83 GB |
| Estimated windowed reads (boundary bounding box only, 10 m bands from the overview) | 4.72 GB |
| Actual compressed bytes read (exact, from each COG's `BLOCK_SIZE` tags) | **6.40 GB** |

The actual figure is higher than the estimate because the overviews compress worse than a quarter of the full band. Three things keep the volume down:

- **Only the boundary window:** each read covers only the analysis grid's rows and columns.
- **No duplicate reads in the tile overlap:** 56JNQ and 56JNP overlap by 9.8 km, and the same acquisition appears in both. The grid is split at the middle of the overlap: rows 0–2097 come from 56JNQ and rows 2098–3183 from 56JNP. Each pixel is read once, and the overlap is never counted twice in the composite.
- **SCL first:** the small SCL band is read before the reflectance bands. An acquisition with less than 1% clear pixels inside the boundary (`minimum_clear_fraction = 0.01`) is recorded and skipped. This skipped 28 acquisitions, and 144 were stored.

**Time.**
- **Wall time:** 2,616 s (43.6 minutes), with four acquisitions downloading in parallel. The link delivered about 1.5–2 MB/s in total, whatever the parallelism.
- **Recorded in the manifest:** the sum of the per-acquisition times, 10,394 s.

The stored cache is 4.39 GB of 5-band uint16 GeoTIFFs in `analysis/work/acquisitions/`, which Git ignores.

## Grid and boundary

| Item | Value |
| --- | --- |
| CRS | EPSG:32756, WGS 84 / UTM zone 56S, the imagery's own CRS |
| Resolution | 20 m |
| Extent | x 516,620–554,200, y 6,873,400–6,937,080 (1,879 × 3,184 pixels) |
| Alignment | Edges snapped outward to multiples of 20 m. Every Sentinel-2 tile origin in zone 56 is also a multiple of 20 m, so the grid lines up exactly with the native 20 m pixels and with 2 × 2 blocks of 10 m pixels. No reflectance band is resampled except the 2 × 2 average described above |
| Boundary transformation | The boundary file is GDA2020 geographic (EPSG:7844). It is transformed explicitly with pyproj, from EPSG:7844 to EPSG:32756, before rasterising. PROJ chose "GDA2020 to WGS 84 (2) + UTM zone 56S", stated accuracy 3 m |
| Boundary mask | Pixel-centre rule (`all_touched=False`). 3,438,748 pixels = 1,375.50 km², equal to the polygon's area in UTM (1,375.50 km²) and to the published `ca_area_sqkm` of 1,376.57 km² within the UTM scale factor |

Outside the boundary, every output is no-data. That includes the ocean beaches at Surfers Paradise, Main Beach, Burleigh, Palm Beach and Mermaid Beach, because the LGA boundary follows the esplanade there. South Stradbroke Island and the Spit are inside.

## Masks and invalid values

Each pixel of each acquisition is used only if all of these hold:

1. **SCL class is 4, 5, 6 or 7:** vegetation, not vegetated, water or unclassified.
   - Unclassified (7) is kept because bright roofs and other urban surfaces often end up there. Excluding it would remove built surfaces in particular.
   - Excluded: 0 no data, 1 saturated or defective, 2 cast shadow, 3 cloud shadow, 8 and 9 cloud, 10 thin cirrus, 11 snow and ice.
2. **Not near cloud:** the pixel is not within 2 pixels (40 m) of SCL classes 3, 8, 9 or 10. A square dilation catches cloud and shadow edges that Sen2Cor misses.
3. **Both bands valid for that index:** DN above 0 (0 is no-data), and reflectance above 0.0 and at most 1.0.
   - Values at or below zero would make a normalised difference meaningless.
   - Values above 1.0 point to glint or saturation.
4. **Denominator not near zero:** the sum of the two reflectances must be above 0.001. Below that the ratio is unstable.

These rules are applied separately for each index, so a pixel can be valid for MNDWI but not for NDBI. All results lie within [−1, 1] by construction. The `verify` stage confirms this, along with the other valid-data checks under *Verification*.

## Compositing

The method is the **median of per-observation index values**:
- **Step 1:** for each acquisition, NDVI, NDBI and MNDWI are calculated per pixel from that date's reflectances.
- **Step 2:** the composite is the per-pixel median of each index over all valid 2025 observations. For an even count it is the mean of the two middle values.

**Why indices are calculated before compositing.**
- **Same date:** each ratio's numerator and denominator then come from one date and one illumination. A per-band median can combine, say, a January red with a July NIR.
- **Robustness:** the median then resists residual cloud, shadow and haze that the SCL misses.
- **Cost:** the three index medians can come from different dates. They describe each index's typical 2025 value, not one consistent spectrum.

**Observation counts.**
- **Recorded per pixel:** clear observations, and valid observations for each index, in `analysis/work/composite/observation_counts.tif`.
- **Inside the boundary:** the clear count ranges from 5 to 112, with a median of 78. 1% of pixels have 32 or fewer.
- **Minimum:** a pixel needs at least 5 valid observations for every index (`minimum_valid_observations = 5`). With 5 values, a median still holds if two of them are bad.
- **Below the minimum:** the pixel is "Insufficient observations" in the classes, and transparent in the index views. That happened for 60 pixels (0.02 km²).

## Indices

| Index | Formula | Bands |
| --- | --- | --- |
| NDVI | (NIR − Red) / (NIR + Red) | B8A, B04 |
| NDBI | (SWIR1 − NIR) / (SWIR1 + NIR) | B11, B8A |
| MNDWI | (Green − SWIR1) / (Green + SWIR1) | B03, B11 |

## Classification rule

Every setting is in `[classification]` in `config.toml`. Each pixel takes the first class whose conditions it meets:

1. **No data:** outside the study boundary.
2. **Insufficient observations:** any index has fewer than 5 valid observations.
3. **Water:** MNDWI ≥ 0.3 (threshold 0.2 + margin 0.1).
4. **Vegetation:** NDVI ≥ 0.65 (threshold 0.6 + margin 0.05).
5. **Candidate artificial surface:** all of the following:
   - NDVI ≤ 0.55, so clearly not vegetation
   - MNDWI ≤ 0.1, so clearly not water
   - NDBI ≥ −0.15
   - NDBI **outside** the bare-or-sand range 0.00 ≤ NDBI < 0.15
6. **Uncertain or other surface:** everything else, including:
   - values inside the margins around the vegetation and water thresholds
   - low-NDVI pixels with NDBI below −0.15
   - low-NDVI pixels in the bare-or-sand NDBI range, where bare soil, sand and some roofs cannot be told apart with these indices

**Low NDVI alone never assigns artificial surface.** It also needs NDBI evidence and no water signal.

### How the thresholds were chosen

The thresholds come only from the 32 calibration samples (table below), placed at different locations from the assessment samples. The calibration values (min / median / max):

| Reference | n | NDVI | NDBI | MNDWI |
| --- | --- | --- | --- | --- |
| Vegetation | 6 | 0.771 / 0.892 / 0.938 | −0.510 / −0.444 / −0.295 | −0.724 / −0.587 / −0.541 |
| Water | 3 | −0.661 / −0.453 / −0.166 | 0.202 / 0.246 / 0.347 | 0.429 / 0.445 / 0.600 |
| Artificial | 10 | −0.047 / 0.117 / 0.424 | −0.125 / 0.013 / 0.400 | −0.377 / −0.268 / 0.003 |
| Bare soil or sand | 4 inside the boundary | 0.049 / 0.082 / 0.380 | 0.027 / 0.061 / 0.122 | −0.513 / −0.271 / −0.136 |
| Mixed (not used) | 7 | −0.655 / 0.300 / 0.699 | −0.320 / −0.079 / 0.099 | −0.439 / −0.278 / 0.655 |

- **Water:** MNDWI 0.2 lies midway between the highest non-water value (0.003, a resort roof) and the lowest water value (0.429). The ±0.1 margin keeps shorelines and mixed water pixels uncertain.
- **Vegetation:** NDVI 0.6 lies between the highest built or bare value (0.424) and the lowest vegetation value (0.771). The ±0.05 margin keeps leafy suburbs with roof-and-tree mixtures (NDVI 0.55–0.65) uncertain rather than forcing a class.
- **Artificial versus bare or sand:**
  - **The overlap.** Built surfaces span NDBI −0.125 to +0.400. Residential roofs mixed with gardens are slightly negative, while metal and large industrial roofs are strongly positive. Bare soil and sand span only +0.027 to +0.122, inside the built range. NDVI and MNDWI overlap too. These three indices cannot separate them.
  - **How the rule handles it.** It keeps 0.00–0.15 as an uncertain band, with the upper bound just above the highest bare value. Below −0.15 the pixels look like sparse vegetation.
  - **On the calibration set:** 7 of 10 artificial pixels become candidate artificial, the other 3 uncertain. All 4 bare/sand pixels become uncertain.
- **Conventional NDBI > 0.** This rule was tried first (NDBI ≥ 0.03 with the provisional thresholds). It missed residential roofs and roads with negative NDBI, and labelled cleared soil as built.

## Assessment

### Reference data and sample design

- **Reference labels.**
  - **Source:** visual interpretation of each sample's 20 m cell on Esri World Imagery (Vantor Vivid). The source date comes from Esri's identify service at that point.
  - **Dates:** 75 of 76 samples have imagery dated 22 August to 1 December 2025 (37 on 1 December, 26 on 10 October, 9 on 27 November, 2 on 22 August).
  - **Exception:** A17 (Springbrook rainforest, outside the boundary) uses imagery from 2 May 2023.
  - **Cross-check:** each label was compared with the Queensland Government 2022 10 cm aerial capture (`Gold_Coast_LGA_2022_10cm_SISP`, 24 July to 12 September 2022). Changes since 2022 are noted, such as earthworks or moving sandbanks.
  - **Limits:** one interpreter labelled every sample, and none is field-verified. Each label has a confidence of high, medium or low.
  - **Rule for a single class:** a class is given only when it covers roughly 60% or more of the cell. Otherwise the cell is "mixed".
- **Dates.** The dates per sample are in [`analysis/results/2025/reference_imagery_dates.csv`](../analysis/results/2025/reference_imagery_dates.csv). The chips are kept in `analysis/work/2025/reference_chips/` for review only and are not published.
- **Strata.** Residential, Arundel, industrial and commercial, dense vegetation, beach, construction and bare, water, and mixed coastal.
- **Separate locations.** Calibration and assessment samples are in different suburbs and features. For example, industrial calibration is at Yatala, West Burleigh and Currumbin Waters, while industrial assessment is in Arundel and Molendinar.
- **Placement.**
  - **Most samples:** placed by place name, then checked on the imagery.
  - **Beach samples:** placed 40 m inland of the boundary's coastline, then moved onto the dry sand shown in the imagery.
  - **Calibration only:** a few water, roof and earthworks points were found by searching a provisional composite near the intended place. Labels still came from the imagery. Assessment points were not placed with the composite.
- **Not scored.** Mixed, low-confidence and outside-boundary samples are listed but not scored.

### Results on the assessment set

Results come from 29 scored assessment samples inside the boundary. "Rule agrees" counts the expected outcome: vegetation → Vegetation, water → Water, artificial → Candidate artificial, and bare or sand → Uncertain/other, because the rule has no bare class.

| Comparison | Agreeing | Proportion | Wilson 95% interval |
| --- | --- | --- | --- |
| Index rule vs reference | 22 / 29 | 0.76 | 0.58–0.88 |
| DEA Level 3 2025 vs the same references | 20 / 29 | 0.69 | 0.51–0.83 |
| Index rule vs DEA 2025 (all 68 samples inside the boundary; agreement only, not accuracy) | 42 / 68 | 0.62 | 0.50–0.72 |

| Reference | Index rule | DEA 2025 |
| --- | --- | --- |
| Artificial (7) | 3 candidate artificial, 4 uncertain | 2 artificial, 5 vegetation |
| Bare or sand (5) | 3 uncertain, 2 candidate artificial | 1 bare, 2 artificial, 2 vegetation |
| Vegetation (13) | 13 vegetation | 13 vegetation |
| Water (4) | 3 water, 1 candidate artificial | 4 water |

**What the samples support.**
- **Totals:** the two totals are not statistically different with 29 samples. Their intervals overlap almost entirely, and the labels come from one interpreter. They are a provisional result for review, not an accuracy estimate for either product.
- **Where the methods differ** is clearer than the totals:
  - DEA labels 5 of 7 artificial reference pixels as vegetation. These are Arundel's arterial road, the M1 motorway, an arterial road at Coomera, and roofs at Molendinar and Labrador.
  - The index rule never labels an artificial reference pixel as vegetation, but leaves 4 of 7 uncertain.
  - The rule's errors are bare surfaces and dark water labelled candidate artificial.

### Failures and ambiguous examples

- **A36 Burleigh Lake (water → candidate artificial).** The dark, tannin-coloured water has MNDWI −0.02, NDVI −0.43 and NDBI +0.36. Green reflectance is lower than SWIR1, so the water rule never applies. This is the rule's clearest failure; DEA has it right.
- **A25 dune sand on the Spit and A35 fresh earthworks at Coomera (bare → candidate artificial).**
  - A25 has NDBI −0.04, just below the bare-or-sand band.
  - A35 was a golf course in the 2022 aerial and earthworks in late 2025, so its annual median mixes grass and soil (NDVI 0.39).
  - DEA calls A25 Artificial Surface and A35 Cultivated Terrestrial Vegetation.
- **A11 Arundel industrial roof and yard (artificial → uncertain).** NDBI +0.004 falls in the bare-or-sand band, which is exactly the built-versus-bare confusion. DEA has it right.
- **A08 Arundel arterial road, A12 Molendinar roofs, A16 Labrador roofs (artificial → uncertain).**
  - The 20 m cells include street trees and gardens, giving NDVI 0.50–0.60.
  - A08 also has NDBI −0.21, below the −0.15 limit.
  - DEA calls all three vegetation.
- **Tidal and changing water.**
  - C24 (Coombabah Lake) is water in the 2025 image but exposed sand ripples in 2022, and A41 (Stradbroke west) is shallow water beside a sandbank. Both are mixed, and the rule calls them water.
  - C22 (Broadwater) is now a deep channel where a sandbar sat in 2022.
- **A30 Luscombe quarry.** Bare rock and gravel: human-made but not built. The rule gives uncertain (as expected); DEA gives Cultivated Terrestrial Vegetation.
- **Mixed residential cells (A01–A03, A06, A07, A09, C01, C04).**
  - These dominate the developed parts of Arundel.
  - The rule labels some candidate artificial and others uncertain, depending on how much canopy the cell holds. DEA labels most of them vegetation.
  - With no single reference class, they are not scored.

### Arundel spot checks

DEA values are read from DEA's original Level 3 continental mosaics (`ga_ls_landcover_class_cyear_3` v2.0.0, `continental_mosaics/{year}--P1Y/..._level3.tif`). They are taken at each sample's 20 m cell centre and transformed to EPSG:3577.

| ID | Cell centre (lon, lat) | Reference | DEA 2010 | DEA 2025 | Rule class 2025 | Reference note |
| --- | --- | --- | --- | --- | --- | --- |
| A06 | 153.361964, -27.936943 | mixed | 112 NTV | 112 NTV | Uncertain/other | Arundel street: road, roof edge and tree |
| A07 | 153.355068, -27.942017 | mixed | 112 NTV | 112 NTV | Candidate artificial | Arundel street: road, roofs and gardens |
| A08 | 153.370072, -27.930061 | artificial | 112 NTV | 112 NTV | Uncertain/other | Arundel arterial road asphalt |
| A09 | 153.368093, -27.945954 | mixed | 112 NTV | 112 NTV | Uncertain/other | Arundel road edge with tall trees |
| A10 | 153.358088, -27.932982 | vegetation | 112 NTV | 112 NTV | Vegetation | Arundel parkland grass and trees |
| A11 | 153.373968, -27.939981 | artificial | 215 Artificial | 215 Artificial | Uncertain/other | Arundel industrial roof and concrete yard |

DEA labels the four developed street cells as (Semi-)Natural Terrestrial Vegetation in both 2010 and 2025, which matches what was observed in the app. The index rule flags one of them (A07) as candidate artificial, leaves the other three uncertain, and still misses the industrial roof that DEA gets right (A11).

### Full sample table

The authoritative table, with all columns, is [`analysis/results/2025/sample_assessment.csv`](../analysis/results/2025/sample_assessment.csv). It includes cell centres, grid row and column, per-index observation counts, DEA 2010 and 2025 values, and agreement flags. Rerunning `assess` regenerates it. DEA abbreviations used below: CTV Cultivated Terrestrial Vegetation, NTV (Semi-)Natural Terrestrial Vegetation, NAV Natural Aquatic Vegetation.

#### Assessment samples

| ID | Place | Reference (confidence) | Image date | NDVI | NDBI | MNDWI | Clear obs | Rule class | DEA 2025 | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A01 | Varsity Lakes | mixed (medium) | 2025-10-10 | 0.596 | −0.152 | −0.447 | 29 | Uncertain/other | CTV | not scored (mixed) |
| A02 | Pacific Pines | mixed (medium) | 2025-12-01 | 0.326 | −0.006 | −0.344 | 83 | Candidate artificial | CTV | not scored (mixed) |
| A03 | Ashmore | mixed (medium) | 2025-10-10 | 0.509 | −0.081 | −0.427 | 46 | Candidate artificial | Artificial | not scored (mixed) |
| A04 | Mudgeeraba | vegetation (medium) | 2025-12-01 | 0.699 | −0.252 | −0.475 | 41 | Vegetation | NTV | rule ✓, DEA ✓ |
| A05 | Coombabah | mixed (medium) | 2025-12-01 | 0.844 | −0.549 | −0.345 | 88 | Vegetation | NAV | not scored (mixed) |
| A06 | Arundel | mixed (medium) | 2025-12-01 | 0.594 | −0.05 | −0.556 | 87 | Uncertain/other | NTV | not scored (mixed) |
| A07 | Arundel | mixed (medium) | 2025-12-01 | 0.48 | −0.037 | −0.494 | 77 | Candidate artificial | NTV | not scored (mixed) |
| A08 | Arundel | artificial (high) | 2025-10-10 | 0.499 | −0.208 | −0.325 | 86 | Uncertain/other | NTV | rule ✗, DEA ✗ |
| A09 | Arundel | mixed (medium) | 2025-12-01 | 0.636 | −0.168 | −0.555 | 83 | Uncertain/other | NTV | not scored (mixed) |
| A10 | Arundel | vegetation (high) | 2025-12-01 | 0.766 | −0.237 | −0.612 | 84 | Vegetation | NTV | rule ✓, DEA ✓ |
| A11 | Arundel | artificial (high) | 2025-10-10 | 0.265 | 0.004 | −0.264 | 71 | Uncertain/other | Artificial | rule ✗, DEA ✓ |
| A12 | Molendinar | artificial (medium) | 2025-12-01 | 0.571 | −0.069 | −0.562 | 62 | Uncertain/other | NTV | rule ✗, DEA ✗ |
| A13 | Nerang | vegetation (high) | 2025-12-01 | 0.838 | −0.375 | −0.596 | 76 | Vegetation | NTV | rule ✓, DEA ✓ |
| A14 | Stapylton | vegetation (high) | 2025-11-27 | 0.88 | −0.433 | −0.608 | 80 | Vegetation | NTV | rule ✓, DEA ✓ |
| A15 | Coomera marine precinct | water (high) | 2025-12-01 | −0.277 | 0.052 | 0.413 | 83 | Water | Water | rule ✓, DEA ✓ |
| A16 | Labrador | artificial (medium) | 2025-10-10 | 0.599 | −0.13 | −0.465 | 47 | Uncertain/other | NTV | rule ✗, DEA ✗ |
| A17 | Springbrook south | vegetation (high) | 2023-05-02 | – | – | – | 0 | No data (outside boundary) | NTV | outside boundary |
| A18 | Austinville | vegetation (high) | 2025-12-01 | 0.886 | −0.451 | −0.587 | 79 | Vegetation | NTV | rule ✓, DEA ✓ |
| A19 | Tallebudgera Valley | vegetation (high) | 2025-12-01 | 0.86 | −0.534 | −0.479 | 43 | Vegetation | NTV | rule ✓, DEA ✓ |
| A20 | Coomera River forest | vegetation (medium) | 2025-11-27 | 0.922 | −0.433 | −0.648 | 72 | Vegetation | NTV | rule ✓, DEA ✓ |
| A21 | Nerang State Forest | vegetation (medium) | 2025-12-01 | 0.858 | −0.35 | −0.597 | 79 | Vegetation | NTV | rule ✓, DEA ✓ |
| A22 | Burleigh Beach | bare or sand (high) | 2025-12-01 | – | – | – | 0 | No data (outside boundary) | Artificial | outside boundary |
| A23 | Palm Beach | bare or sand (high) | 2025-12-01 | – | – | – | 0 | No data (outside boundary) | Bare | outside boundary |
| A24 | Mermaid Beach | bare or sand (high) | 2025-10-10 | – | – | – | 0 | No data (outside boundary) | Bare | outside boundary |
| A25 | The Spit ocean beach | bare or sand (medium) | 2025-10-10 | 0.173 | −0.036 | −0.186 | 27 | Candidate artificial | Artificial | rule ✗, DEA ✗ |
| A26 | South Stradbroke south | bare or sand (high) | 2025-10-10 | – | – | – | 0 | No data (outside boundary) | Bare | outside boundary |
| A27 | Pimpama north | vegetation (high) | 2025-12-01 | 0.664 | −0.082 | −0.589 | 85 | Vegetation | NTV | rule ✓, DEA ✓ |
| A28 | Coomera west | artificial (medium) | 2025-12-01 | 0.508 | −0.114 | −0.413 | 88 | Candidate artificial | NTV | rule ✓, DEA ✗ |
| A29 | Gaven | vegetation (high) | 2025-12-01 | 0.784 | −0.325 | −0.621 | 78 | Vegetation | NTV | rule ✓, DEA ✓ |
| A30 | Luscombe | bare or sand (medium) | 2025-11-27 | 0.006 | 0.076 | −0.106 | 51 | Uncertain/other | CTV | rule ✓, DEA ✗ |
| A31 | Ormeau east | vegetation (high) | 2025-12-01 | 0.842 | −0.432 | −0.552 | 84 | Vegetation | NTV | rule ✓, DEA ✓ |
| A32 | Little Nerang Dam | vegetation (high) | 2025-12-01 | 0.869 | −0.454 | −0.576 | 79 | Vegetation | NTV | rule ✓, DEA ✓ |
| A33 | Broadwater south | water (high) | 2025-10-10 | −0.573 | 0.412 | 0.665 | 46 | Water | Water | rule ✓, DEA ✓ |
| A34 | Hinze Dam north | vegetation (high) | 2025-12-01 | 0.88 | −0.41 | −0.649 | 80 | Vegetation | NTV | rule ✓, DEA ✓ |
| A35 | Coomera River | bare or sand (medium) | 2025-12-01 | 0.393 | −0.032 | −0.381 | 97 | Candidate artificial | CTV | rule ✗, DEA ✗ |
| A36 | Burleigh Lake | water (high) | 2025-12-01 | −0.434 | 0.359 | −0.019 | 32 | Candidate artificial | Water | rule ✗, DEA ✓ |
| A37 | Coomera River mangroves | water (high) | 2025-08-22 | −0.445 | 0.0 | 0.587 | 87 | Water | Water | rule ✓, DEA ✓ |
| A38 | Currumbin Creek | artificial (high) | 2025-12-01 | 0.227 | −0.036 | −0.199 | 44 | Candidate artificial | NTV | rule ✓, DEA ✗ |
| A39 | Tallebudgera Creek mouth | artificial (medium) | 2025-12-01 | 0.046 | −0.048 | 0.005 | 49 | Candidate artificial | Artificial | rule ✓, DEA ✓ |
| A40 | Broadwater sand flats | mixed (medium) | 2025-10-10 | 0.594 | −0.098 | −0.599 | 24 | Uncertain/other | Water | not scored (mixed) |
| A41 | Stradbroke west shore | mixed (low) | 2025-08-22 | −0.071 | −0.28 | 0.396 | 66 | Water | Water | not scored (mixed) |
| A42 | South Stradbroke Island north | bare or sand (medium) | 2025-10-10 | 0.118 | 0.07 | −0.257 | 23 | Uncertain/other | Artificial | rule ✓, DEA ✗ |
| A43 | South Stradbroke Island central | bare or sand (medium) | 2025-10-10 | 0.074 | 0.041 | −0.181 | 25 | Uncertain/other | Bare | rule ✓, DEA ✓ |

#### Calibration samples

| ID | Place | Reference (confidence) | Image date | NDVI | NDBI | MNDWI | Clear obs | Rule class | DEA 2025 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | Helensvale | mixed (medium) | 2025-12-01 | 0.426 | −0.143 | −0.278 | 88 | Candidate artificial | CTV |
| C02 | Robina | artificial (high) | 2025-10-10 | 0.424 | −0.047 | −0.377 | 38 | Candidate artificial | Artificial |
| C03 | Paradise Point | artificial (medium) | 2025-10-10 | 0.257 | −0.037 | −0.32 | 62 | Candidate artificial | Artificial |
| C04 | Burleigh Waters | mixed (medium) | 2025-10-10 | 0.35 | −0.079 | −0.35 | 49 | Candidate artificial | Artificial |
| C05 | Yatala | bare or sand (medium) | 2025-11-27 | 0.38 | 0.074 | −0.513 | 78 | Uncertain/other | NTV |
| C06 | West Burleigh | artificial (high) | 2025-10-10 | −0.037 | 0.4 | −0.37 | 45 | Candidate artificial | Artificial |
| C07 | Currumbin Waters | artificial (high) | 2025-12-01 | 0.005 | 0.258 | −0.27 | 44 | Candidate artificial | Artificial |
| C08 | Yatala | artificial (high) | 2025-11-27 | −0.047 | 0.144 | −0.115 | 75 | Uncertain/other | Artificial |
| C09 | Springbrook | vegetation (high) | 2025-11-27 | 0.889 | −0.443 | −0.597 | 66 | Vegetation | NTV |
| C10 | Nerang National Park | vegetation (high) | 2025-12-01 | 0.938 | −0.444 | −0.724 | 79 | Vegetation | NTV |
| C11 | Currumbin Valley | vegetation (high) | 2025-10-10 | 0.895 | −0.51 | −0.541 | 41 | Vegetation | NTV |
| C12 | Numinbah Valley | vegetation (high) | 2025-11-27 | 0.88 | −0.497 | −0.546 | 80 | Vegetation | NTV |
| C13 | Surfers Paradise beach | bare or sand (high) | 2025-10-10 | – | – | – | 0 | No data (outside boundary) | Bare |
| C14 | Main Beach | bare or sand (high) | 2025-10-10 | – | – | – | 0 | No data (outside boundary) | Bare |
| C15 | South Stradbroke Island beach | bare or sand (high) | 2025-10-10 | 0.049 | 0.027 | −0.136 | 28 | Uncertain/other | Bare |
| C16 | Rainbow Bay | mixed (medium) | 2025-12-01 | 0.3 | −0.153 | −0.133 | 51 | Uncertain/other | Artificial |
| C17 | Pimpama | artificial (medium) | 2025-12-01 | 0.262 | −0.004 | −0.251 | 80 | Candidate artificial | Artificial |
| C18 | Coomera | artificial (high) | 2025-12-01 | 0.299 | −0.125 | −0.277 | 78 | Candidate artificial | Artificial |
| C19 | Ormeau Hills | vegetation (medium) | 2025-11-27 | 0.771 | −0.295 | −0.577 | 78 | Vegetation | NTV |
| C20 | Upper Coomera | vegetation (high) | 2025-12-01 | 0.92 | −0.441 | −0.664 | 77 | Vegetation | NTV |
| C21 | Hinze Dam | water (high) | 2025-12-01 | −0.661 | 0.202 | 0.6 | 69 | Water | Water |
| C22 | Broadwater | water (medium) | 2025-10-10 | −0.166 | 0.246 | 0.445 | 43 | Water | Water |
| C23 | Nerang River | water (high) | 2025-10-10 | −0.453 | 0.347 | 0.429 | 37 | Water | Water |
| C24 | Coombabah Lake | mixed (medium) | 2025-10-10 | −0.655 | 0.014 | 0.655 | 88 | Water | Water |
| C25 | Coombabah wetlands | mixed (medium) | 2025-10-10 | 0.699 | −0.32 | −0.439 | 83 | Vegetation | NTV |
| C26 | Southport Spit | bare or sand (high) | 2025-10-10 | 0.055 | 0.048 | −0.17 | 46 | Uncertain/other | Artificial |
| C27 | Jacobs Well | mixed (medium) | 2025-10-10 | 0.29 | −0.031 | −0.209 | 85 | Candidate artificial | Artificial |
| C28 | Currumbin estuary | artificial (high) | 2025-12-01 | 0.088 | −0.076 | 0.003 | 45 | Candidate artificial | NTV |
| C29 | Pimpama | artificial (high) | 2025-12-01 | 0.116 | 0.03 | −0.146 | 76 | Uncertain/other | Artificial |
| C30 | Coomera | bare or sand (high) | 2025-12-01 | 0.109 | 0.122 | −0.372 | 84 | Uncertain/other | NTV |
| C31 | Ormeau | artificial (high) | 2025-11-27 | 0.118 | 0.143 | −0.266 | 80 | Uncertain/other | Artificial |
| C32 | Upper Coomera | mixed (medium) | 2025-12-01 | 0.199 | 0.099 | −0.341 | 75 | Uncertain/other | NTV |

## Verification

`verify` writes `analysis/results/{year}/verification.json` ([2025](../analysis/results/2025/verification.json), [2020](../analysis/results/2020/verification.json)). All checks passed for both years:

- **Grid alignment:** the grid origin is a multiple of 20 m. For one acquisition, a full grid row of B04 (read through the overview) and of B8A was read directly from the source COG; both rows are identical to the cached rows.
- **Boundary masking:** the masked area equals the polygon's area (1,375.50 km²). All pixels outside the boundary have no values, zero counts and class no-data.
- **Valid data:**
  - All finite values lie within [−1, 1].
  - NaN occurs exactly where an index's valid count is 0.
  - No index count exceeds the clear count.
  - Every low-count pixel inside the boundary is "Insufficient observations".
- **Formulas, median and classes:** for every sixth sample (13 samples), a plain-Python recomputation from the raw cache matched the pipeline exactly: masks with the cloud buffer, scale and offset, formulas, invalid-value rules, median, counts and the rule's class.
- **In the browser** (2025, made before the Smooth display switch existed, with the same nearest-neighbour drawing the Classes view now always uses):
  - Twelve sample cells drew exactly their exported class colour on screen at zoom 15.
  - Class tiles contained only the five class colours at zooms 9.6, 11.4 and 12.7.
  - NDVI pixels drew within a colour distance of 0–12 of their expected ramp colour.

## Web outputs

| Layer | Tiles per year | 2025 size | 2020 size | Rendering |
| --- | --- | --- | --- | --- |
| Classes | 218 | 0.85 MB | 0.90 MB | 8-bit palette PNG, class value = palette index |
| NDVI | 218 | 3.90 MB | 4.05 MB | 8-bit palette PNG, 100 colour steps over −0.2…0.9 |
| NDBI | 218 | 4.45 MB | 4.54 MB | 8-bit palette PNG, 100 colour steps over −0.6…0.3 |
| MNDWI | 218 | 3.69 MB | 3.63 MB | 8-bit palette PNG, 100 colour steps over −0.8…0.8 |
| `layers.json` | 1 | 2 KB | 2 KB | Legends, ranges, period, resolution and source text for the app |

That is 873 files per year: 12.9 MB for 2025 and 13.1 MB for 2020. The largest tile is 51 KB. Both years use the same colour ranges, so equal colours mean equal index values.

The tile writer is shared with the clipped DEA tiles ([land-cover.md](land-cover.md#clipping-and-tiling)). After it was split out, re-exporting 2025 from its existing composites gave 872 tiles byte-identical to the published ones.

**Zooms and coverage.**
- **Range:** zooms 8–13. Zoom 13 tiles are about 16.9 m per pixel at this latitude, just finer than the 20 m data. Beyond zoom 13, the app enlarges zoom-13 tiles. Below zoom 8, the layers are hidden and the panel says "Zoom in to see this layer."
- **Bounds:** every tile within the boundary's bounding box is written, including transparent ones, so the browser never requests a missing tile.

**Resampling to Web Mercator** (`export`):

| Layer type | Zoom 13 (finer than 20 m) | Zooms 8–12 (coarser than 20 m) |
| --- | --- | --- |
| Classes | Nearest neighbour | Mode (the most common class) |
| Indices | Bilinear | Average |

Index values are binned into 100 steps after resampling. No-data and below-minimum pixels are fully transparent (palette index 0).

**In the browser.**
- **Fixed rendering, no Smooth display switch.** The Sentinel-2 views do not show the switch and do not follow the DEA setting:
  - **Classes:** always nearest neighbour, so every pixel shows its exact class colour and no blend can look like another class.
  - **NDVI, NDBI and MNDWI:** always linear, so neighbouring values blend on screen into a continuous surface. Blended colours are a display effect only; the tiles and index values are unchanged.
- **Tile zoom:** every analysis source uses floor tile zoom and no anisotropic filtering, so the Classes view stays exact at any zoom and after tilting (see [land-cover.md](land-cover.md#smooth-display-and-exact-class-colours)).
- **Years and views.** Each year and view has its own source and layer, with keys such as `sentinel-2020-ndvi`. The app loads both years' small `layers.json` files at startup, and a year's tiles only when that year and view are shown. A late tile from one year can only be drawn by that year's own layer, which is hidden once another year is selected.
  - **Held-response test:** 2020 MNDWI tile responses were held back, the year was switched to 2025, and the held tiles were then released as solid magenta. No magenta pixel appeared while 2025 was selected; the same tiles appeared once 2020 was selected again. Seven rapid year clicks, and a burst of view and year clicks, each ended with only the last selection visible.
- **Caption and source note.** The caption gives the year and the dates of the first and last acquisitions used, for example "NDVI 2020 · median of 1 Jan – 31 Dec 2020 · 20 m pixels". The source note gives the number of acquisitions, and the attribution credits that year's Copernicus data.
- **Classes** also use no fade, so a tile never cross-fades with its parent.
- **Placement:** every analysis layer has a style-level `minzoom`, and sits below the Gold Coast outline and labels.

The tiles are static files, so the app is compatible with GitHub Pages. A production build with base path `/goldcoast_remotesensing/` loaded the boundary, both years' `layers.json`, the tiles and the MapLibre worker from that subpath, with no requests outside it.

## Reproducing the pipeline (PowerShell)

From the repository root:

```powershell
python -m venv analysis\.venv
analysis\.venv\Scripts\python.exe -m pip install --upgrade "pip>=26.2"
analysis\.venv\Scripts\python.exe -m pip install -r analysis\requirements.txt
cd analysis
.venv\Scripts\python.exe -m spectral_indices --year 2025 plan
.venv\Scripts\python.exe -m spectral_indices --year 2025 acquire
.venv\Scripts\python.exe -m spectral_indices --year 2025 composite
.venv\Scripts\python.exe -m spectral_indices --year 2025 calibrate
.venv\Scripts\python.exe -m spectral_indices --year 2025 classify
.venv\Scripts\python.exe -m spectral_indices --year 2025 verify
.venv\Scripts\python.exe -m spectral_indices --year 2025 export
.venv\Scripts\python.exe -m spectral_indices --year 2025 assess
.venv\Scripts\python.exe -m spectral_indices --year 2025 reference-chips
.venv\Scripts\python.exe -m spectral_indices --year 2020 all
.venv\Scripts\python.exe -m spectral_indices dea-tiles dea-verify
```

**Stages.**
- **Years:** every Sentinel-2 stage needs `--year`, which must be one of `years` in `[imagery]` (2020 and 2025). The period is 1 January to 31 December of that year. Each year keeps its own cache in `analysis/work/{year}/`, records in `analysis/results/{year}/` and tiles in `public/data/sentinel2-{year}/`.
- **Reruns:** each stage reads the previous stage's files from that year's work folder, so a failed stage can be rerun on its own.
- **`acquire` resumes:** it skips any acquisition that already has a status file. A complete rerun takes about 2 s.
- **`all`:** runs `plan` to `assess` in order. For years other than 2025 it leaves out `calibrate` and `assess`, which need the 2025 reference labels; asking for them explicitly stops with a message.
- **`reference-chips`:** optional, 2025 only. It refreshes the review images and the imagery dates.
- **`dea-tiles` and `dea-verify`:** build and check the clipped DEA land cover tiles for every year in `[dea_land_cover]`. They take no `--year`. See [land-cover.md](land-cover.md#clipping-and-tiling).

The environment was tested with Python 3.13.14 on Windows 10. Reading 5.5–6.4 GB takes roughly 40–45 minutes at 2 MB/s, and the later stages take about 5 minutes per year.

## Files

| Path | Tracked | Content |
| --- | --- | --- |
| `analysis/requirements.txt` | Yes | Pinned Python packages |
| `analysis/config.toml` | Yes | Source, grid, masks, index limits, compositing, thresholds, web styling |
| `analysis/spectral_indices/` | Yes | The pipeline |
| `analysis/samples.csv` | Yes | Sample locations and reference labels |
| `analysis/results/2025/` | Yes | Processing manifest, verification, calibration and assessment tables, reference imagery dates |
| `analysis/results/2020/` | Yes | Processing manifest and verification |
| `public/data/sentinel2-2025/`, `public/data/sentinel2-2020/` | Yes | Browser tiles and `layers.json` |
| `analysis/work/{year}/` | No | STAC items, plan, acquisition cache (4.4 GB for 2025, 3.8 GB for 2020), composites, classification, reference chips (2025) |
| `analysis/.venv/` | No | Python environment |

## Limitations

- **Bare versus built:** the three indices cannot separate artificial surfaces from bare soil and sand. The uncertain band keeps that visible, but it also leaves some real roofs uncertain, and some sand and earthworks still fall outside it.
- **Dark water:** dark, tannin-coloured lakes can have negative MNDWI and become candidate artificial.
- **Annual medians blur change:** a site that changed during 2025 gets a median of its before and after states (A35).
- **Mixed cells:** most of a leafy suburb's 20 m cells mix roof, road and canopy. Neither the rule nor DEA (30 m) assigns them one class reliably.
- **Thresholds:** they come from 32 calibration samples, 4 of them bare/sand inside the boundary, so they may not transfer elsewhere or to other years.
- **2020 is not assessed:** it uses the 2025 thresholds unchanged, and no reference labels exist for 2020. Its classes have not had an accuracy check of their own.
- **Comparing years:** 2020 had two satellites and baseline 05.00, and 2025 three satellites and baseline 05.11. The median pixel therefore has fewer observations in 2020 (66 against 78). Weather, tides and season mix also differ between the years, so a change in an index or class between them is not by itself evidence of a change on the ground.
- **No 2015 layer:** see *Years*.
- **Assessment:**
  - It is small (29 scored samples).
  - All labels come from one interpreter, and none is field-checked.
  - Placement is purposive, not a probability sample, so it cannot give area-weighted accuracy.
- **SCL masking:** this depends on Sen2Cor. The 40 m buffer and the median reduce, but cannot remove, residual cloud and shadow.
- **Boundary datum:** the transformation from GDA2020 to WGS 84 uses PROJ's "GDA2020 to WGS 84 (2)" (stated accuracy 3 m), far below one 20 m pixel.
- **Outside the boundary:** most mainland ocean beaches are outside the LGA polygon and have no values.
