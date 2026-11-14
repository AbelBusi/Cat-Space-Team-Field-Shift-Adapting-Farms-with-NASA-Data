# Field Shift: problem, users, solution and impact

The case we present at NASA Space Apps 2026 (challenge **"Field Shift: Adapting Farms with NASA Data"**). Every number has a
reference at the end ([1], [2]…). Where a figure is a press or business estimate rather than a peer-reviewed or official one,
we say so. Numbers we computed ourselves from NASA data are marked **(our analysis)**.

## 1. The problem in one sentence

Farmers in Lambayeque, Peru keep planting the same crop on a calendar their parents used, while the climate under them has
changed (more extreme El Niño rain, scarcer irrigation water, saltier soil), and **the satellite data that could warn them exists
but does not reach them in a form, a scale or a language they can use.**

## 2. Why it matters: the global picture

| Fact | Value | Source |
|---|---|---|
| Crop and livestock losses caused by disasters, 1991–2021 | **USD 3.8 trillion**, about USD 123 billion a year | FAO 2023 [1] |
| Share of all disaster losses that falls on agriculture (2007–2022) | **23 %**; for droughts, **over 65 %** | FAO 2023 [1] |
| Effect of human-caused climate change on global farm productivity since 1961 | **−21 %** (≈ 7 years of growth lost); **−26 to −34 %** in Latin America, the Caribbean and Africa | Ortiz-Bobea et al. 2021, *Nature Climate Change* [2] |
| Extreme El Niño events under greenhouse warming | Frequency projected to **double** (from about one every 20 years to one per decade) | Cai et al. 2014, *Nature Climate Change* [3] |
| Farms in the world | **> 608 million**; 5 of 6 are smaller than 2 ha and produce **≈ 35 %** of the world's food | Lowder et al. 2021, *World Development* [4] |

Small farms feed a large part of the world, and they are the ones with the least access to the data and advice that would
help them adapt.

## 3. The case: Lambayeque, Peru

### 3.1 A desert that floods

| Fact | Value | Source |
|---|---|---|
| Typical rain at the Chiclayo grid cell | **217 mm a year** | GPM IMERG 0.1°, 2001–2024 **(our analysis)** |
| Rain in the 2017 coastal El Niño, same cell | **412 mm**, about 2× a normal year | GPM IMERG **(our analysis)** |
| Wettest year since 1981 | **1998** (the 1997–98 El Niño), about 4× a normal year | NASA POWER **(our analysis)** |
| Coastal El Niño years since 1981 | 1983, 1998, 2016, 2017, 2023 | NOAA Niño 1+2 index, Jan–Apr anomaly ≥ 0.8 °C [12] |
| Damage of the 2017 coastal El Niño in Peru | **≈ USD 3.1 billion, 1.6 % of GDP**; 162 deaths | Macroconsult estimate, reported by El Comercio [5]; BCRP gives ≈ USD 3 billion |
| Damage in Lambayeque alone (2017) | **≈ USD 435 million, 8.9 % of the regional GDP** (second most affected region in relative terms) | Same estimate [5] |
| Farmland hit in Lambayeque's valleys (La Leche, Zaña, Chancay–Lambayeque), 2017 | **≈ 21,000 ha**, losses above PEN 100 million | Regional Agriculture Office, press report [6] (early estimate) |
| Damage of the 1997–98 El Niño in Peru | **≈ 4.5 % of GDP** | CAF consultant, UN-ISDR [7] |

The same El Niño that floods the coast can be followed by years when the Tinajones reservoir runs low. Farmers face **both
too much and too little water**, sometimes in consecutive seasons.

### 3.2 One thirsty crop

- Rice is the main crop of Lambayeque's valleys: between **≈ 25,000 and 50,000 ha per season**, depending on the water
  available (regional figures reported in the press [8]).
- A hectare of flooded rice uses about **14,000–15,000 m³ of water** per season according to Peru's Ministry of Agriculture,
  compared with about 1,000 m³ for quinoa [9]. Field trials on the north coast measured **12,800–17,600 m³/ha** under continuous
  flooding, and lower-water irrigation saved about 27 % [9].
- After the rice harvest the field often stays **bare for about six months**, exposed to wind erosion, and pest cycles are
  never broken because the same crop returns every year.

### 3.3 Salt in the soil

- Lambayeque's business chamber estimates that the region's valleys **lose about 3,000 ha a year** to salinity from poor
  drainage, with **≈ 27,000 ha lost by 2021** in the Olmos, Motupe, La Leche, Zaña and Chancay valleys [10] (business estimate,
  not an official survey).
- On the whole Peruvian coast, about **300,000 ha** have drainage and salinity problems (ONERN, 1970s; INRENA 2005 gives
  306,701 ha) [10].
- No NASA satellite measures soil salinity directly. Our plan for using indirect signs is in
  [`LAMBAYEQUE_RISKS.md`](LAMBAYEQUE_RISKS.md).

### 3.4 Who farms, and what help they get

| Fact | Value | Source |
|---|---|---|
| Farmers in Peru | **2.26 million**; **81.9 %** farm less than 5 ha | IV National Agricultural Census (CENAGRO) 2012, INEI [11] |
| Farmers who received technical assistance | **≈ 5 %**; about 8 % any training or advice | CENAGRO 2012, INEI [11] |
| Agricultural land in Lambayeque | **≈ 225,000 ha**, 73 % owned by individual farmers | CENAGRO 2012, via BCRP [11] |
| Workers in agriculture, fishing and mining (Peru, 2023) | **≈ 24 %** of all employed people; about 92 % of them informal | INEI employment reports [13] |
| Rural households with a mobile phone | **86.6 %** (Q3 2024); 89.5 % of rural internet users go online by phone | INEI ICT report [14] |
| Rural households with home internet | **≈ 22 %** | INEI [14] |
| People whose mother tongue is Quechua | **13.9 %** of Peruvians aged 5+ (≈ 4 million speakers) | 2017 Census, INEI [15] |
| Quechua in Lambayeque | Inkawasi-Kañaris Quechua in the Ferreñafe highlands; in Incahuasi district **≈ 86 %** learned Quechua as their first language (2007 census) | [15] |

**What this tells us:** most farmers work small plots, almost none get technical advice, nearly all have a phone but few have
home internet, and a real share of the highland population thinks in Quechua.

## 4. The root cause: an information gap, not a data gap

NASA already observes every one of these fields: rain (GPM IMERG), heat and soil wetness (NASA POWER), plant greenness (MODIS),
soil moisture (SMAP), underground water (GRACE-FO) and terrain (NASADEM). The gap is in between:

1. **Format.** The data come as NetCDF/HDF files, APIs and scientific units (mm/hr, NDVI, kg/m²). A farmer needs "will March be
   too wet for maize?".
2. **Scale.** A 55 km climate cell is not "your field". Tools that hide the pixel size give false confidence.
3. **Language.** Advice in technical Spanish or English excludes Quechua speakers.
4. **Trust and fit.** Systematic reviews of climate information services for smallholders find that adoption fails mainly
   when the information does not match the farmers' own crops and needs, and when they do not trust externally produced
   information [16]. Receiving advice is not the same as using it.

## 5. Who is affected, and who uses Field Shift

| Segment | Who | What they need | How Field Shift serves them |
|---|---|---|---|
| **Primary: small irrigated farmers** | Rice and maize growers with < 5 ha in the Chancay–Lambayeque, La Leche, Zaña, Motupe and Olmos valleys | "What should I plant next season, and what can go wrong?" | **Farmer mode**: tools they know (thermometer, rain gauge, a handful of soil, a plant), words instead of numbers, Sprout explains in plain language |
| **Highland farmers** | Inkawasi-Kañaris communities (Ferreñafe) | The same, in their language | Interface and guide in **Quechua** (beta, to be reviewed by native speakers) |
| **Advisers** | Agronomists, extension agents, the Regional Agriculture Office (GERAGRI), cooperatives | Evidence to back a recommendation | **Pro mode**: numbers, units, charts, 44 years of history, data sources and pixel sizes |
| **Water managers** | Water user boards (Juntas de Usuarios) and the National Water Authority (ANA) | Plan water allocation per season | Rain normals and El Niño scenarios per 11 km cell, groundwater trend (GRACE-FO) |
| **Finance and insurance** | Agrobanco, rural credit unions, agricultural insurers | Know which seasons and crops carry more risk | Risky months per rotation, El Niño years compared with normal years |
| **Indirectly affected** | Families who depend on farm income, consumers who buy rice and maize | Stable harvests and prices | Fewer total losses in bad years |

## 6. Our solution

**Field Shift** is a free web app (works on a phone, no installation, no account) that turns NASA Earth data into a
conversation about crop rotations.

1. **Find your field.** Pick a town, tap the map or outline your land. If the field is bigger than one data square, the app
   averages the squares it covers, weighted by area, and says so.
2. **Listen to the satellites.** Heat, rain, soil wetness, greenness and underground water for your spot, as an instrument and
   a word (Farmer mode) or as numbers and charts (Pro mode). Every reading says which satellite it comes from and **how big its
   pixel is compared with your field**.
3. **Remember the hard years.** 44 years of NASA POWER (1981–2024): warming stripes, the wettest and driest years, and the coastal
   El Niño years (NOAA Niño 1+2, the right index for this coast; the usual ONI index points the wrong way here).
4. **Say what matters to you.** Save water, earn more, care for the soil, fewer pests, withstand El Niño. The rotations
   re-rank instantly.
5. **Compare rotations as a year in the field.** Each rotation is a row of 12 plants (sown, growing, stressed, harvested, bare).
   Risky months from NASA data are marked above, and Sprout explains what you gain and what you risk compared with today.
6. **Be honest about confidence.** A confidence meter goes up when the farmer adds what they know (a soil test, their water
   allocation, past experience). The final word belongs to the farmer and a local agronomist.

**NASA data used:** NASA POWER, GPM IMERG, MODIS MOD13Q1, SMAP, GRACE-FO, NASADEM and GIBS imagery. Details and citations are in
[`DATA_SOURCES.md`](DATA_SOURCES.md); the architecture is in [`STACK.md`](STACK.md).

## 7. Expected benefits, and the evidence behind them

| Benefit | Evidence |
|---|---|
| **Higher and more stable yields from rotation** | Across 347 site-years of long-term trials in North America, more diverse rotations raised maize yields by **28.1 %** on average and cut yield losses in drought years by **14 to 90 %** (Bowles et al. 2020, *One Earth*) [17] |
| **Less fertilizer, more nitrogen in the soil** | A global meta-analysis of 462 field experiments found that a legume before the main crop raises its yield by **≈ 20 %**, and by **32 %** in low-yield, low-input systems (Zhao et al. 2022, *Nature Communications*) [18]. Cereals after grain legumes yield **+29 %** on average; the effect fades above 150 kg N/ha of fertilizer (Cernay et al. 2018) [19]. This is why cowpea after rice is one of our rotations |
| **Water savings** | Rice needs ≈ 14,000–15,000 m³/ha per season [9]. Every hectare moved to a less thirsty crop in a dry year frees water for the rest of the valley |
| **Fewer losses in El Niño years** | Knowing that February–March can bring several times the normal rain lets farmers avoid flood-sensitive crops in those months. In 2017, ≈ 21,000 ha were hit in Lambayeque's valleys alone [6] |
| **Covered soil all year** | Rotations with a second crop or green manure cut the six bare months that expose the topsoil to wind |
| **Inclusion** | Works on the phones that 86.6 % of rural households already have [14], with no login, in Spanish, English and Quechua |

**Honest note:** the rotation scores in the current prototype are **hypothetical expert rules** and are labelled as such on screen.
The benefits above come from the scientific literature, not from measurements of our app. Turning the scores into crop-water
and yield estimates (FAO-56 crop coefficients, FAO GAEZ) is the next step.

## 8. How we would measure impact

These are the indicators we would track in a pilot with farmers and the Regional Agriculture Office (proposed, not yet measured):

| Indicator | Target in a first pilot |
|---|---|
| Farmers who complete the flow (place → priorities → rotation) | 70 % of first-time users |
| Farmers who say they understood the El Niño risk for their field | 80 % in a short follow-up survey |
| Hectares that try a second-season crop (cowpea) or a less thirsty crop | Recorded by the extension agents |
| Water declared per hectare in the season (water user board records) | Compare with the same farms the year before |
| Confidence checklist answers (soil test, water allocation, past experience) | Share of users who add at least one |

## 9. Limits we state openly

- Climate cells are coarse (NASA POWER ≈ 55 km, IMERG ≈ 11 km). The app always shows the pixel size against the field.
- MODIS greenness is read at one 250 m pixel; its public API is slow and sometimes down.
- No satellite measures soil salinity directly; we only combine indirect signs.
- The Quechua translation is Southern Quechua made with AI help and must be reviewed by native speakers, ideally from Inkawasi
  or Kañaris.
- The app supports decisions; it does not replace a soil test or an agronomist.

## References

1. FAO (2023). *The Impact of Disasters on Agriculture and Food Security 2023*. Rome. [Executive summary](https://openknowledge.fao.org/server/api/core/bitstreams/19764bec-3b8e-46a6-8680-1dbab43bccaa/content/impact-of-disasters-on-agriculture-and-food-2023/executive-summary.html)
2. Ortiz-Bobea, A., Ault, T. R., Carrillo, C. M., Chambers, R. G., & Lobell, D. B. (2021). Anthropogenic climate change has slowed global agricultural productivity growth. *Nature Climate Change*, 11, 306–312. [doi:10.1038/s41558-021-01000-1](https://doi.org/10.1038/s41558-021-01000-1)
3. Cai, W., et al. (2014). Increasing frequency of extreme El Niño events due to greenhouse warming. *Nature Climate Change*, 4, 111–116. [doi:10.1038/nclimate2100](https://doi.org/10.1038/nclimate2100)
4. Lowder, S. K., Sánchez, M. V., & Bertini, R. (2021). Which farms feed the world and has farmland become more concentrated? *World Development*, 142, 105455. [FAO summary](https://www.fao.org/newsroom/detail/small-family-farmers-produce-a-third-of-the-world-s-food/en)
5. El Comercio (2017). *Daños de El Niño: US$3.124 millones hasta ahora, Macroconsult* (press report of a consultancy estimate). [Link](https://elcomercio.pe/economia/negocios/danos-nino-us-3-124-millones-macroconsult-408266-noticia/)
6. RCR Perú (2017). *Niño Costero: inundaciones generan pérdidas agrícolas por más de S/ 850 millones en el norte* (press report quoting regional agriculture offices). [Link](https://www.rcrperu.com/nino-costero-inundaciones-generan-perdidas-agricolas-por-mas-de-s-850-millones-en-el-norte/)
7. UN-ISDR / CAF (2001). The El Niño 1997–98 phenomenon in the Andean countries. [Link](https://www.eird.org/eng/revista/No1_2001/pagina22.htm); CAF (2000), *Las lecciones de El Niño: Perú*. [PDF](https://dipecholac.net/docs/files/996-publicacion-caf-peru-nino-97-98.pdf)
8. La Industria de Chiclayo, *Sembrarán 25 820 hectáreas de arroz* [link](https://laindustriadechiclayo.pe/noticia/1668113511-sembraran-25-820-hectareas-de-arroz); La República (2020), *Campaña de arroz inició con 25.000 hectáreas* [link](https://larepublica.pe/sociedad/2020/12/20/lambayeque-campana-de-arroz-inicio-con-25000-hectareas-lrnd); BCRP (2008), *Lambayeque: potencialidades productivas* [PDF](https://www.bcrp.gob.pe/docs/Proyeccion-Institucional/Encuentros-Regionales/2008/Lambayeque/Informe-Economico-Social/IES-Lambayeque-03.pdf)
9. Andina (2014), *Cada hectárea de arroz consume 14,000 m³ de agua más que la quinua* (Ministry of Agriculture) [link](https://andina.pe/agencia/noticia-cada-hectarea-arroz-consume-14000-m3-agua-mas-que-quinua-514042.aspx); MIDAGRI, *Costos de producción de arroz* [link](https://www.midagri.gob.pe/portal/26-sector-agrario/arroz/219-costos-de-produccion); *Impacto del uso de recursos productivos y del agua en la economía de agricultores de arroz en el norte del Perú* (2024), SciELO Perú [link](http://www.scielo.org.pe/scielo.php?script=sci_arttext&pid=S2414-10462024000400431); Heros, E., *Tecnologías para la producción de arroz*, MINAM/SINIA [PDF](https://sinia.minam.gob.pe/sites/default/files/archivos/public/docs/PB_ELIZABETH%20HEROS.pdf)
10. Gestión (2022), *Lambayeque: se pierden 3,000 hectáreas al año por salinidad de suelos* (Lambayeque Chamber of Commerce estimate) [link](https://gestion.pe/economia/empresas/lambayeque-se-pierden-3000-hectareas-al-ano-por-salinidad-de-suelos-noticia/); *Drenaje y salinidad en la costa peruana* (ONERN figure) [link](https://www.slideshare.net/slideshow/drenaje-salinidad-costa-peruana1/60880717); Sociotramas, *Salinidad y sodicidad de los suelos en el Perú* (INRENA 2005) [link](https://www.sociotramas.org/post/salinidad-y-sodicidad-de-los-suelos-en-el-per%C3%BA)
11. INEI (2013). *Resultados definitivos del IV Censo Nacional Agropecuario 2012* [PDF](http://proyectos.inei.gob.pe/web/documentospublicos/resultadosfinalesivcenagro.pdf); INEI, *Características del productor agropecuario*, resumen ejecutivo [PDF](https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1177/resumen.pdf); BCRP, *Caracterización del departamento de Lambayeque* [PDF](https://www.bcrp.gob.pe/docs/Sucursales/Piura/lambayeque-caracterizacion.pdf)
12. NOAA Climate Prediction Center, Niño 1+2 sea surface temperature index. [Link](https://www.cpc.ncep.noaa.gov/data/indices/)
13. INEI, *Informe técnico de empleo*, Q4 2023 [PDF](https://m.inei.gob.pe/media/MenuRecursivo/boletines/boletin_empleo_oct_nov_dic2023.pdf); Infomercado (2023), *Población ocupada en el Perú superó los 17 millones* [link](https://infomercado.pe/poblacion-ocupada-en-el-peru-supero-los-17-millones-pero-presento-disminucion-en-comparacion-al-2022/)
14. INEI (2024). *Estadísticas de las Tecnologías de Información y Comunicación en los Hogares*, Q3 2024. [PDF](https://www.inei.gob.pe/media/MenuRecursivo/boletines/boletin_tic_3t24.pdf)
15. INEI (2018), Censos Nacionales 2017 [PDF](https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1539/libro.pdf); Andina, *¿Cuántos peruanos tienen como lengua materna una lengua originaria?* [link](https://andina.pe/agencia/noticia-cuantos-peruanos-tienen-como-lengua-materna-una-lengua-originaria-975143.aspx); *Lambayeque Quechua* [link](https://en.wikipedia.org/wiki/Lambayeque_Quechua)
16. *Climate information services for smallholder farmers in sub-Saharan Africa: a systematic review* (2025), *Frontiers in Climate* [link](https://www.frontiersin.org/articles/10.3389/fclim.2025.1616691); *Targeting smallholder farmers for climate information services adoption in Africa: a systematic literature review*, CIRAD [link](https://publications.cirad.fr/une_notice.php?dk=608596)
17. Bowles, T. M., et al. (2020). Long-term evidence shows that crop-rotation diversification increases agricultural resilience to adverse growing conditions in North America. *One Earth*, 2(3), 284–293. [doi:10.1016/j.oneear.2020.02.007](https://doi.org/10.1016/j.oneear.2020.02.007)
18. Zhao, J., Chen, J., Beillouin, D., Lambers, H., Yang, Y., Smith, P., Zeng, Z., Olesen, J. E., & Zang, H. (2022). Global systematic review with meta-analysis reveals yield advantage of legume-based rotations and its drivers. *Nature Communications*, 13, 4926. [doi:10.1038/s41467-022-32464-0](https://doi.org/10.1038/s41467-022-32464-0)
19. Cernay, C., Makowski, D., & Pelzer, E. (2018). Preceding cultivation of grain legumes increases cereal yields under low nitrogen input conditions. *Environmental Chemistry Letters*. [doi:10.1007/s10311-017-0698-z](https://doi.org/10.1007/s10311-017-0698-z)
