// Languages: English (default, Space Apps rule), Spanish and Quechua.
// The English text itself is the key: t('Rain') → 'Lluvia'. Missing Quechua falls back to Spanish, then English.
// Quechua is Southern Quechua written by the team with AI help: BETA, to be reviewed by native speakers
// (Lambayeque's highlands speak Inkawasi-Kañaris Quechua, which differs). See docs/LANGUAGES.md.
import { ref } from 'vue'

export const LANGS = [['en', 'EN', 'English'], ['es', 'ES', 'Español'], ['qu', 'QU', 'Runasimi (beta)']]
const saved = (() => { try { return localStorage.getItem('fs-lang') } catch { return null } })()
export const lang = ref(LANGS.some(l => l[0] === saved) ? saved : 'en')
document.documentElement.lang = lang.value

export function setLang(l) {
  lang.value = l
  document.documentElement.lang = l
  try { localStorage.setItem('fs-lang', l) } catch {}
}

export function t(s, params) {
  if (s == null) return s
  let out = lang.value === 'en' ? s : DICT[lang.value]?.[s] ?? (lang.value === 'qu' ? DICT.es[s] : null) ?? s
  if (params) out = out.replace(/\{(\w+)\}/g, (_, k) => params[k] ?? '')
  return out
}

const ES = {
  // Top bar, landing
  'Listen to your field': 'Escucha tu campo', 'Farmer': 'Agricultor', 'Pro': 'Pro', 'Light mode': 'Modo claro', 'Dark mode': 'Modo oscuro',
  'Prototype · live NASA data': 'Prototipo · datos NASA en vivo', 'Demo · saved NASA data': 'Demo · datos NASA guardados',
  '[ demo data ]': '[ datos demo ]', '[ demo on ]': '[ demo activo ]', 'Language': 'Idioma',
  'Your field is already talking.': 'Tu campo ya te está hablando.', "Let's learn to listen.": 'Aprendamos a escucharlo.',
  'NASA satellites measure heat, rain, soil wetness and plant greenness for every field on Earth. Sprout translates them so you can choose what to plant next.':
    'Los satélites de la NASA miden el calor, la lluvia, la humedad del suelo y el verdor de las plantas en cada campo del planeta. Sprout te los traduce para que elijas qué sembrar.',
  'Explore your field': 'Explora tu campo', 'How it works': 'Cómo funciona', '(soon)': '(pronto)', 'Pet Sprout': 'Acariciar a Sprout',
  // Layers and readings
  'Daytime heat': 'Calor de día', 'Rain': 'Lluvia', 'Soil wetness': 'Humedad del suelo', 'Plant greenness': 'Verdor de las plantas', 'Underground water': 'Agua subterránea',
  'It barely rains. Your crop depends completely on irrigation.': 'Casi no llueve. Tu cultivo depende por completo del riego.',
  'A little rain. It helps, but it is not enough for the crop.': 'Llueve poco. Ayuda, pero no alcanza para el cultivo.',
  'Moderate rain. Watch out for waterlogged fields.': 'Lluvia moderada. Cuidado con los campos encharcados.',
  'Heavy rain! Fields can flood and water can wash the soil away.': '¡Lluvia fuerte! Los campos pueden inundarse y el agua puede llevarse la tierra.',
  'The topsoil is dry. With nothing growing on it, wind can blow it away.': 'La capa de arriba está seca. Si no hay nada sembrado, el viento se la puede llevar.',
  'Low wetness. Plants start to suffer without irrigation.': 'Poca humedad. Las plantas empiezan a sufrir sin riego.',
  'Good wetness for most crops.': 'Buena humedad para la mayoría de cultivos.', 'Very wet soil. Watch out for waterlogging.': 'Suelo muy húmedo. Cuidado con el encharcamiento.',
  'Strong heat. At midday plants get stressed and drink more water.': 'Calor fuerte. Al mediodía las plantas se estresan y toman más agua.',
  'Hot days. Good for growing, as long as there is water.': 'Días calurosos. Buenos para crecer, si hay agua.',
  'Mild temperature, comfortable for many crops.': 'Temperatura templada, cómoda para muchos cultivos.',
  'Cool weather. Crops grow more slowly.': 'Clima fresco. Los cultivos crecen más lento.', 'Cold! Frost can hurt crops this month.': '¡Frío! La helada puede dañar los cultivos este mes.',
  'It looks almost bare: open soil or desert.': 'Se ve casi pelado: tierra sin sembrar o desierto.',
  'A little vegetation: scrub, or a crop that just started.': 'Poca vegetación: monte o un cultivo que recién empieza.',
  'Medium vegetation.': 'Vegetación media.', 'Very green! A dense, healthy crop.': '¡Muy verde! Un cultivo tupido y sano.',
  'Underground water keeps dropping, year after year. It needs care.': 'El agua subterránea baja año tras año. Hay que cuidarla.',
  'Underground water is slowly going down.': 'El agua subterránea baja poco a poco.', 'Underground water is holding steady.': 'El agua subterránea se mantiene estable.',
  "Underground water needs a free NASA Earthdata login, so it arrives during the hackathon. I can't see it yet.": 'El agua subterránea necesita una cuenta gratuita de NASA Earthdata; llegará durante el hackathon. Todavía no la puedo ver.',
  "I'm still listening to the satellites for this one...": 'Todavía estoy escuchando a los satélites para este dato...',
  // Farmer words
  'Coming soon': 'Muy pronto', 'Listening…': 'Escuchando…', 'Frosty': 'Helada', 'Cool': 'Fresco', 'Mild': 'Templado', 'Hot': 'Caluroso', 'Very hot': 'Muy caluroso',
  'Dry month': 'Mes seco', 'A little rain': 'Poca lluvia', 'Rainy': 'Lluvioso', 'Very rainy': 'Muy lluvioso',
  'Dry soil': 'Suelo seco', 'Slightly moist': 'Algo húmedo', 'Moist': 'Húmedo', 'Wet': 'Mojado',
  'Bare': 'Pelado', 'Sparse': 'Ralo', 'Green': 'Verde', 'Lush': 'Frondoso',
  'Dropping fast': 'Baja rápido', 'Slowly dropping': 'Baja poco a poco', 'Slowly rising': 'Sube poco a poco', 'Steady': 'Estable',
  'Good fit': 'Buena opción', 'Could work': 'Podría funcionar', 'Poor fit': 'No conviene',
  // Months
  'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril', 'May': 'Mayo', 'June': 'Junio', 'July': 'Julio',
  'August': 'Agosto', 'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre',
  // Map section
  'Find your field, anywhere on Earth': 'Encuentra tu campo, en cualquier lugar del mundo',
  'Search a place, tap the map or try an example. You can also outline your own field. We fetch real NASA data for that spot and show the grid cells each satellite uses.':
    'Busca un lugar, toca el mapa o prueba un ejemplo. También puedes marcar tu propio terreno. Traemos datos reales de la NASA para ese punto y mostramos las celdas que usa cada satélite.',
  'Town, district or lat, lon': 'Pueblo, distrito o lat, lon', 'Search': 'Buscar', 'Searching…': 'Buscando…', 'My location': 'Mi ubicación',
  'No place found. Try another name, or coordinates like -6.77, -79.84': 'No encontramos ese lugar. Prueba otro nombre o coordenadas como -6.77, -79.84',
  'Search is not available right now. Check the connection and try again.': 'La búsqueda no está disponible ahora. Revisa la conexión e inténtalo de nuevo.',
  'Tap each corner of your field': 'Toca cada esquina de tu terreno', 'Listening to NASA POWER…': 'Escuchando a NASA POWER…',
  'Tap at least 3 corners (you have {n}).': 'Toca al menos 3 esquinas (llevas {n}).', '{n} corners. Press Finish when done.': '{n} esquinas. Pulsa Terminar cuando acabes.',
  'Undo': 'Deshacer', 'Finish': 'Terminar', 'Cancel': 'Cancelar', 'Your field:': 'Tu terreno:', 'perimeter': 'perímetro', 'Edit outline': 'Editar contorno', 'Delete': 'Borrar',
  'Outline your land to get its size and read NASA data at its center.': 'Marca tu terreno para saber su tamaño y leer los datos de la NASA en su centro.',
  'Outline my field': 'Marcar mi terreno', 'Satellite only': 'Solo satélite', 'Vegetation health': 'Salud de la vegetación', 'Ground heat': 'Calor del suelo',
  'Rain (IMERG)': 'Lluvia (IMERG)', 'Soil moisture (SMAP)': 'Humedad del suelo (SMAP)', 'Rain grid 0.1° (IMERG)': 'Grilla de lluvia 0,1° (IMERG)', 'Intensity': 'Intensidad',
  'Typical year': 'Año típico', 'El Niño years': 'Años de El Niño', 'Less': 'Menos', 'More': 'Más', 'Source:': 'Fuente:',
  // Panel
  'Pick a place': 'Elige un lugar', 'Reading the climate…': 'Leyendo el clima…', 'No data': 'Sin datos', 'Last 30 days': 'Últimos 30 días',
  'Reading the last 30 days…': 'Leyendo los últimos 30 días…', 'typical year (2001–2024)': 'año típico (2001–2024)', 'El Niño years, ': 'años de El Niño, ',
  'in {month}, typical year': 'en {month}, año típico', 'in {month}, El Niño years': 'en {month}, años de El Niño', 'in {month} 2024': 'en {month} de 2024',
  'MODIS is slow, about a minute…': 'MODIS es lento, cerca de un minuto…', 'MODIS service did not answer': 'El servicio de MODIS no respondió',
  'needs Earthdata login': 'necesita cuenta Earthdata', 'trend 2002–2026, regional': 'tendencia 2002–2026, regional', 'Not available': 'No disponible',
  'Ground · NASADEM 30 m, cell mean': 'Terreno · NASADEM 30 m, promedio de la celda', 'Flat ground': 'Terreno plano', 'Gentle slope': 'Pendiente suave', 'Steep ground': 'Terreno empinado',
  'Low erosion risk.': 'Bajo riesgo de erosión.', 'Bare soil can wash away in heavy rain.': 'El suelo desnudo puede lavarse con lluvia fuerte.',
  'High erosion risk when the soil is bare: keep it covered.': 'Alto riesgo de erosión con el suelo desnudo: mantenlo cubierto.',
  'Listen to the year': 'Escuchar el año', 'Listening…': 'Escuchando…',
  'For {layer} one pixel is about {m} m wide. About {n} pixels fit in {field}, so it sees inside the field.': 'Para {layer}, un píxel mide unos {m} m. Caben unos {n} píxeles en {field}: ve dentro del campo.',
  'For {layer} one pixel is about {km} km wide. {field} fits {n} times in it: it describes the region, not the exact field.': 'Para {layer}, un píxel mide unos {km} km. {field} cabe {n} veces en él: describe la región, no el campo exacto.',
  'a 3 ha field': 'un campo de 3 ha', 'your {area} field': 'tu campo de {area}',
  'Greener = denser, more active plants. No color = no data (clouds or water).': 'Más verde = plantas más densas y activas. Sin color = sin datos (nubes o agua).',
  'Daytime temperature of the ground surface. Helps spot hotter, drier areas. No color = clouds.': 'Temperatura del suelo durante el día. Ayuda a ver zonas más calientes y secas. Sin color = nubes.',
  'Rain falling that day, from the GPM satellites. No color = no rain.': 'La lluvia de ese día, según los satélites GPM. Sin color = no llovió.',
  'Water in the top 5 cm of soil. SMAP passes every 2–3 days, so some stripes have no data.': 'El agua en los primeros 5 cm del suelo. SMAP pasa cada 2 o 3 días, por eso hay franjas sin datos.',
  'Typical rain for the chosen month in every IMERG cell of Lambayeque. Follows the month and the El Niño switch.': 'La lluvia típica del mes elegido en cada celda IMERG de Lambayeque. Sigue al mes y al interruptor de El Niño.',
  // Year by year
  'Your place, year by year': 'Tu lugar, año por año', 'Wettest year': 'Año más lluvioso', 'Driest year': 'Año más seco', 'Afternoons now vs 1981–2000': 'Las tardes de hoy frente a 1981–2000',
  'About {n}× the rain of a normal year': 'Cerca de {n} veces la lluvia de un año normal', 'The ground was at its thirstiest': 'La tierra estuvo más sedienta que nunca',
  "Noticeably hotter than in your parents' time": 'Bastante más caluroso que en tiempos de tus padres', 'A little hotter than before': 'Un poco más caluroso que antes',
  'Noticeably cooler than before': 'Bastante más fresco que antes', 'A little cooler than before': 'Un poco más fresco que antes', 'About the same as before': 'Más o menos igual que antes',
  'Each stripe is one year · turquoise = cooler afternoons · campfire = hotter': 'Cada franja es un año · turquesa = tardes más frescas · fogata = más calurosas',
  'Reading 44 years of NASA data…': 'Leyendo 44 años de datos de la NASA…', 'No NASA POWER data for this spot.': 'No hay datos de NASA POWER para este punto.',
  // Priorities and rotations
  'What matters most to you?': '¿Qué es lo más importante para ti?',
  'Tap each card to raise its importance, from none to a lot. The rotations below reorder instantly.': 'Toca cada tarjeta para subir su importancia, de nada a mucho. Las rotaciones de abajo se reordenan al instante.',
  'Save water': 'Ahorrar agua', 'Use less irrigation water': 'Usar menos agua de riego', 'Earn more': 'Ganar más', 'More income per hectare': 'Más ingreso por hectárea',
  'Care for my soil': 'Cuidar mi suelo', 'More organic matter and nitrogen': 'Más materia orgánica y nitrógeno', 'Fewer pests': 'Menos plagas', 'Break the pest cycle': 'Cortar el ciclo de las plagas',
  'Withstand El Niño': 'Aguantar El Niño', 'Handle extreme rain or heat': 'Resistir lluvias o calor extremos', 'None': 'Nada', 'Some': 'Algo', 'Quite a bit': 'Bastante', 'A lot': 'Mucho',
  'How your year could look': 'Así podría verse tu año',
  'Each row is one year, January to December, like walking along a furrow. The color strip under each plant is the crop. Icons above mark risky months at your spot, from real NASA POWER data, and the framed column is the month you picked. These four are example rotations from the Peruvian coast; the crop library can grow for other regions.':
    'Cada fila es un año, de enero a diciembre, como caminar por un surco. La franja de color bajo cada planta es el cultivo. Los íconos de arriba marcan los meses de riesgo en tu lugar, con datos reales de NASA POWER, y la columna enmarcada es el mes que elegiste. Estas cuatro son rotaciones de ejemplo de la costa peruana.',
  'Best fit for you': 'La que más te conviene', 'What you do today': 'Lo que haces hoy', 'You gain:': 'Ganas:', 'You risk:': 'Arriesgas:', 'Months of bare soil:': 'Meses de suelo desnudo:',
  'Sowing': 'Siembra', 'Growing well': 'Crece bien', 'Stressed': 'Estresada', 'Harvest': 'Cosecha', 'Strong heat': 'Calor fuerte', 'Heavy rain': 'Lluvia fuerte', 'Bare soil': 'Suelo desnudo', 'Frost': 'Helada',
  'Rice': 'Arroz', 'Yellow maize': 'Maíz amarillo duro', 'Sorghum': 'Sorgo', 'Cowpea': 'Frijol caupí', 'Green manure': 'Abono verde',
  'Rice, then fallow': 'Arroz y luego descanso', 'Rice, then cowpea': 'Arroz y luego caupí', 'Maize, cowpea and green manure': 'Maíz, caupí y abono verde', 'Sorghum, then cowpea': 'Sorgo y luego caupí',
  'You know it and it already has a buyer': 'Lo conoces y ya tiene comprador', 'Six months of bare soil': 'Seis meses de suelo desnudo',
  'An extra harvest and soil with more nitrogen': 'Una cosecha extra y suelo con más nitrógeno', 'Needs water in the second season': 'Necesita agua en la segunda campaña',
  'Much less water and soil covered all year': 'Mucha menos agua y suelo cubierto todo el año', 'Very fragile if El Niño arrives': 'Muy frágil si llega El Niño',
  'Needs the least water': 'Es la que menos agua pide', 'Less income in normal years': 'Menos ingreso en años normales',
  'It is what many valleys grow today. We use it as the starting point to compare.': 'Es lo que hoy se siembra en muchos valles. La usamos como punto de partida para comparar.',
  'Uses the empty months after rice for a short-cycle bean that feeds the soil.': 'Aprovecha los meses vacíos después del arroz con un frijol de ciclo corto que alimenta el suelo.',
  'Swaps rice for a cereal that needs far less water, and keeps the soil covered all twelve months.': 'Cambia el arroz por un cereal que pide mucha menos agua y deja el suelo cubierto los doce meses.',
  'The toughest option against drought and heat, meant for years when the reservoir runs low.': 'La opción más dura contra la sequía y el calor, pensada para años en que el reservorio baja.',
  'This tool shows patterns and possibilities. The final word belongs to your experience and to an agronomist who knows your area.': 'Esta herramienta muestra patrones y posibilidades. La última palabra la tienen tu experiencia y un agrónomo que conozca tu zona.',
  // Detail
  'Chosen strategy': 'Estrategia elegida', '{n} out of 100': '{n} de 100', 'What you gain': 'Lo que ganas', 'What you risk': 'Lo que arriesgas', 'What the satellites say': 'Lo que dicen los satélites',
  'Compared with what you do today': 'Frente a lo que haces hoy', 'Today': 'Hoy', 'Compared with what you grow today, topic by topic.': 'Frente a lo que siembras hoy, tema por tema.',
  'More filled squares = better on that topic (0 to 5). The arrow says if the change helps or hurts.': 'Más cuadros llenos = mejor en ese tema (0 a 5). La flecha dice si el cambio ayuda o perjudica.',
  'Better': 'Mejor', 'Worse': 'Peor', 'Same': 'Igual', 'How sure are we?': '¿Qué tan seguros estamos?', 'Confidence': 'Confianza', 'Low': 'Baja', 'Medium': 'Media', 'High': 'Alta',
  'What you know about your field raises the confidence.': 'Lo que sabes de tu campo sube la confianza.', 'Check what you already have:': 'Marca lo que ya tienes:',
  'I have a recent soil test': 'Tengo un análisis de suelo reciente', 'I know how much water I get per season': 'Sé cuánta agua me toca por campaña', 'I have grown these crops before': 'Ya sembré estos cultivos antes',
  // Glossary
  'Satellite words, made simple': 'Palabras de satélite, explicadas fácil',
  'Greenness (NDVI)': 'Verdor (NDVI)', 'How green and alive the field looks from above. Near 0 is bare ground. Near 0.8 is a dense, healthy crop.': 'Qué tan verde y vivo se ve el campo desde arriba. Cerca de 0 es tierra pelada. Cerca de 0,8 es un cultivo tupido y sano.',
  'Evapotranspiration': 'Evapotranspiración', 'The water that leaves the field: what evaporates from the soil plus what plants "sweat" through their leaves. It is exactly what irrigation has to replace.': 'El agua que se va del campo: la que se evapora del suelo más la que las plantas "sudan" por sus hojas. Es justo lo que el riego tiene que reponer.',
  'Soil moisture': 'Humedad del suelo', 'How much water the top few centimeters of soil hold. The SMAP satellite measures it with microwaves, even through clouds.': 'Cuánta agua guardan los primeros centímetros del suelo. El satélite SMAP la mide con microondas, incluso a través de las nubes.',
  'Satellite or soil test?': '¿Satélite o análisis de suelo?', 'A satellite sees the whole valley every few days, but it averages big areas. A soil test is exact, but only at one spot. Together they correct each other.': 'El satélite ve todo el valle cada pocos días, pero promedia zonas grandes. El análisis de suelo es exacto, pero en un solo punto. Juntos se corrigen el uno al otro.',
  // Sprout's panel
  'Sprout, your guide': 'Sprout, tu guía', 'translator': 'traductor', '[ show all ]': '[ mostrar todo ]', '[ sound on ]': '[ sonido sí ]', '[ sound off ]': '[ sonido no ]',
  '[ next ]': '[ siguiente ]', '[ skip ]': '[ saltar ]', 'Minimize Sprout': 'Minimizar a Sprout', 'Show Sprout, your guide': 'Mostrar a Sprout',
  // Sprout's script
  "Oh! Hello there! I'm Sprout. I came down from orbit to help you read what the satellites see.": '¡Oh! ¡Hola! Soy Sprout. Bajé de la órbita para ayudarte a leer lo que ven los satélites.',
  "From up there, NASA satellites measure signals about any field on Earth. They're these little buttons.": 'Desde allá arriba, los satélites de la NASA miden señales de cualquier campo del planeta. Son estos botoncitos.',
  "I know it sounds like a lot... but don't worry! We'll go one step at a time, together. Scroll down whenever you're ready.": 'Sé que suena a mucho... ¡pero no te preocupes! Iremos paso a paso, juntos. Baja cuando estés listo.',
  'This is the whole Earth! Search a town, tap the map, or try an example place. You can even outline your own field with the yellow tool.': '¡Esta es toda la Tierra! Busca un pueblo, toca el mapa o prueba un lugar de ejemplo. Incluso puedes marcar tu propio terreno.',
  'NASA data comes in squares called grid cells, and every satellite uses a different size. Here they are, nested around your point. Tap one to zoom in.': 'Los datos de la NASA vienen en cuadrados llamados celdas, y cada satélite usa un tamaño distinto. Aquí están, uno dentro de otro, alrededor de tu punto. Toca uno para acercarte.',
  'Press play to watch a whole year go by. The big square takes the color of the signal you picked.': 'Pulsa play para ver pasar un año entero. El cuadrado grande toma el color de la señal que elegiste.',
  'Over here I translate the numbers into plain words. They are real NASA numbers for that spot, averaged over 2001 to 2024!': 'Aquí te traduzco los números a palabras simples. ¡Son números reales de la NASA para ese punto, promediados de 2001 a 2024!',
  'One honest thing, though: the climate cell is about 50 km wide. It describes your region, not your exact field. Greenness comes at 250 meters, much closer.': 'Pero te digo algo con honestidad: la celda del clima mide unos 50 km. Describe tu región, no tu campo exacto. El verdor viene a 250 metros, mucho más cerca.',
  "Now let's travel back in time. Each stripe is one year at your spot, from 1981 to 2024. Turquoise years had cooler afternoons, campfire years hotter ones.": 'Ahora viajemos en el tiempo. Cada franja es un año en tu lugar, de 1981 a 2024. Los años turquesa tuvieron tardes más frescas; los de fogata, más calurosas.',
  "And these are the hard years: the wettest and the driest. They can come back, so it's good to plan for them.": 'Y estos son los años difíciles: el más lluvioso y el más seco. Pueden volver, así que conviene planificar para ellos.',
  "Every farm is different, so I'd love to know what matters to you.": 'Cada campo es distinto, así que me encantaría saber qué te importa a ti.',
  "Tap a card to make it more important. The rotations below will reorder themselves. It's your call!": 'Toca una tarjeta para darle más importancia. Las rotaciones de abajo se reordenan solas. ¡Tú decides!',
  'Each row is one year, like walking along a furrow from January to December. A seed is sowing, a golden plant is harvest, empty soil is bare land.': 'Cada fila es un año, como caminar por un surco de enero a diciembre. Una semilla es siembra, una planta dorada es cosecha y la tierra vacía es suelo desnudo.',
  'See the little icons above some months? Those are risky months at your spot: heat, heavy rain, dry soil or frost. A plant growing then looks thirsty.': '¿Ves los iconitos sobre algunos meses? Son meses de riesgo en tu lugar: calor, lluvia fuerte, suelo seco o helada. Una planta que crece en esos meses se ve sedienta.',
  "Pick any rotation and I'll compare it with what you grow today, point by point.": 'Elige cualquier rotación y la comparo con lo que siembras hoy, punto por punto.',
  "I'm not always sure, and that's okay. If you tell me what you know about your field, I get more confident.": 'No siempre estoy seguro, y está bien. Si me cuentas lo que sabes de tu campo, gano confianza.',
  "And remember: I'm only a helper. You and your local agronomist always have the final word.": 'Y recuerda: solo soy un ayudante. Tú y tu agrónomo de confianza siempre tienen la última palabra.',
  "Satellite words can sound scary. Here they are in plain words. You've got this!": 'Las palabras de satélite pueden asustar. Aquí están en palabras simples. ¡Tú puedes!',
  'Okay! Everything is out now. Explore at your own pace, and tap things if you want me to explain them.': '¡Listo! Ya está todo a la vista. Explora a tu ritmo y toca las cosas si quieres que te las explique.',
  // Reactions
  'Listening to the satellites over {place}...': 'Escuchando a los satélites sobre {place}...', '{place}. {layer}: {text}': '{place}. {layer}: {text}',
  '{place} (saved NASA data). {layer}: {text}': '{place} (datos NASA guardados). {layer}: {text}',
  "Oh no... I couldn't reach NASA POWER ({error}). Check the internet connection and tap the map again.": 'Oh no... No pude llegar a NASA POWER ({error}). Revisa la conexión a internet y vuelve a tocar el mapa.',
  "Farmer mode: I'll show you tools you know, like a thermometer and a rain gauge, and tell you what they mean.": 'Modo agricultor: te muestro herramientas que conoces, como un termómetro y un pluviómetro, y te digo qué significan.',
  'Pro mode: numbers, units and charts. Same NASA data, more detail.': 'Modo pro: números, unidades y gráficos. Los mismos datos de la NASA, con más detalle.',
  'Back to the typical year: the average of 2001 to 2024.': 'Volvemos al año típico: el promedio de 2001 a 2024.',
  'El Niño years! Now every month is the average of the El Niño years only. Watch how the colors change.': '¡Años de El Niño! Ahora cada mes es el promedio solo de los años de El Niño. Mira cómo cambian los colores.',
  'Coastal El Niño years! On this coast I use the Niño 1+2 index: 1983, 1998, 2016, 2017 and 2023, the years that flooded Lambayeque.': '¡Años de El Niño costero! En esta costa uso el índice Niño 1+2: 1983, 1998, 2016, 2017 y 2023, los años que inundaron Lambayeque.',
  'Tap each corner of your field on the map. When you have at least three, press Finish.': 'Toca cada esquina de tu terreno en el mapa. Cuando tengas al menos tres, pulsa Terminar.',
  "This browser can't share its location. You can tap the map instead.": 'Este navegador no puede compartir tu ubicación. Puedes tocar el mapa.',
  'Listen! High notes mean more, low notes mean less. One note per month.': '¡Escucha! Las notas altas son más, las bajas son menos. Una nota por mes.',
  'With what matters to you now, "{name}" fits best. Look, it moved to the front!': 'Con lo que ahora te importa, "{name}" es la que más conviene. ¡Mira, pasó adelante!',
  "Thank you! That makes me more confident. Now I'm at {level} confidence.": '¡Gracias! Eso me da más confianza. Ahora mi confianza es {level}.',
  '{name}: you gain {gain}, but you risk {lose}.': '{name}: ganas {gain}, pero arriesgas {lose}.',
  // Flags and confidence reasons
  'Dry climate here ({n} mm a year): a thirsty crop needs reliable irrigation.': 'Clima seco aquí ({n} mm al año): un cultivo sediento necesita riego seguro.',
  'In El Niño years rain here goes up {n}%: maize may flood.': 'En años de El Niño la lluvia aquí sube {n}%: el maíz se puede inundar.',
  'Cool climate: these warm-season example crops may not fit. Local rotations will differ.': 'Clima fresco: estos cultivos de ejemplo de clima cálido podrían no servir. Las rotaciones locales serán otras.',
  'Climate comes in NASA POWER cells of {size}: it describes the region, not your plot.': 'El clima viene en celdas de NASA POWER de {size}: describe la región, no tu parcela.',
  'Greenness comes from 250 m MODIS pixels: much closer to your field.': 'El verdor viene de píxeles MODIS de 250 m: mucho más cerca de tu campo.',
  'Greenness is not loaded for this spot yet.': 'El verdor todavía no se cargó para este punto.',
  'With your soil test, the suggestion is more precise.': 'Con tu análisis de suelo, la sugerencia es más precisa.', "Your plot's soil test is missing.": 'Falta el análisis de suelo de tu parcela.',
  'You know how much water you get, so fewer surprises.': 'Sabes cuánta agua te toca, así hay menos sorpresas.', "We don't know how much water you get per season.": 'No sabemos cuánta agua te toca por campaña.',
  'You have never grown this here: try it on a small plot first.': 'Nunca sembraste esto aquí: pruébalo primero en un terreno pequeño.', 'An El Niño year is harder to predict.': 'Un año de El Niño es más difícil de prever.',
}

const QU = {
  'Listen to your field': 'Chakraykita uyariy', 'Farmer': 'Chakrakamayuq', 'Pro': 'Yachaq', 'Language': 'Simi',
  'Your field is already talking.': 'Chakraykiqa ñam rimachkanña.', "Let's learn to listen.": 'Uyariyta yachasunchik.',
  'Explore your field': 'Chakraykita qhaway', 'How it works': 'Imaynatam llamk\'an', '(soon)': '(qayllachkanña)',
  'Daytime heat': 'P\'unchaw rupay', 'Rain': 'Para', 'Soil wetness': 'Allpa huquynin', 'Plant greenness': 'Yurakunap q\'umirnin', 'Underground water': 'Ukhu pacha yaku',
  'Coming soon': 'Qayllachkanña', 'Listening…': 'Uyarichkani…', 'Frosty': 'Qasa', 'Cool': 'Chiri', 'Mild': 'Allin rupay', 'Hot': 'Rupha', 'Very hot': 'Ancha rupha',
  'Dry month': 'Ch\'aki killa', 'A little rain': 'Pisi para', 'Rainy': 'Parayuq', 'Very rainy': 'Ancha parayuq',
  'Dry soil': 'Ch\'aki allpa', 'Slightly moist': 'Pisi huqu', 'Moist': 'Huqu', 'Wet': 'Ancha huqu',
  'Bare': 'Ch\'usaq', 'Sparse': 'Pisi yura', 'Green': 'Q\'umir', 'Lush': 'Ancha q\'umir',
  'Dropping fast': 'Utqaylla pisiyachkan', 'Slowly dropping': 'Pisi-pisimanta pisiyachkan', 'Slowly rising': 'Pisi-pisimanta yapakuchkan', 'Steady': 'Kikillanmi',
  'Good fit': 'Allinmi', 'Could work': 'Kanmanmi', 'Poor fit': 'Mana allinchu',
  'Typical year': 'Sapa wata hina', 'El Niño years': 'El Niño watakuna', 'Search': 'Maskay', 'My location': 'Maypi kasqay',
  'Outline my field': 'Chakrayta siq\'iy', 'Satellite only': 'Satelitella', 'Undo': 'Kutichiy', 'Finish': 'Tukuy', 'Cancel': 'Saqiy', 'Delete': 'Pichay',
  'Find your field, anywhere on Earth': 'Chakraykita tariy, kay pachapi maypipas', 'Pick a place': 'Huk llaqtata akllay', 'Last 30 days': 'Qhipa 30 p\'unchawkuna',
  'Your place, year by year': 'Llaqtayki, wata-watamanta', 'Wettest year': 'Aswan parayuq wata', 'Driest year': 'Aswan ch\'aki wata',
  'What matters most to you?': 'Imataq qampaq aswan chaniyuq?', 'Save water': 'Yakuta waqaychay', 'Earn more': 'Aswan qullqita tariy',
  'Care for my soil': 'Allpayta waqaychay', 'Fewer pests': 'Pisi kurukuna', 'Withstand El Niño': 'El Niñota atipay',
  'None': 'Mana', 'Some': 'Pisi', 'Quite a bit': 'Achkallan', 'A lot': 'Ancha',
  'How your year could look': 'Kay hinam watayki kanman', 'Best fit for you': 'Qampaq aswan allin', 'What you do today': 'Kunan ruwasqayki',
  'Sowing': 'Tarpuy', 'Growing well': 'Allinta wiñachkan', 'Stressed': 'Ch\'akichkan', 'Harvest': 'Pallay', 'Strong heat': 'Sinchi rupay', 'Heavy rain': 'Sinchi para', 'Bare soil': 'Ch\'usaq allpa', 'Frost': 'Qasa',
  'Rice': 'Arus', 'Yellow maize': 'Q\'illu sara', 'Sorghum': 'Sorgo', 'Cowpea': 'Chuwi purutu', 'Green manure': 'Q\'umir wanu',
  'Better': 'Aswan allin', 'Worse': 'Aswan mana allin', 'Same': 'Kikin', 'Today': 'Kunan', 'How sure are we?': 'Hayk\'atataq yachanchik?', 'Confidence': 'Iñiy',
  'Satellite words, made simple': 'Satelite simikuna, facil rimaypi', 'Sprout, your guide': 'Sprout, pusaqniyki', 'translator': 't\'ikraq',
  '[ next ]': '[ qatiq ]', '[ show all ]': '[ llapanta rikuchiy ]',
  "Oh! Hello there! I'm Sprout. I came down from orbit to help you read what the satellites see.": '¡Ay! ¡Allillanchu! Ñuqaqa Sprout kani. Hanaq pachamanta urayamuni, satelitekunap rikusqanta ñawinchanaykipaq yanapanaypaq.',
  "From up there, NASA satellites measure signals about any field on Earth. They're these little buttons.": 'Hanaqmantam NASA satelitekuna kay pachapi mayqin chakratapas tupunku. Kay huch\'uy botonkunam.',
  "I know it sounds like a lot... but don't worry! We'll go one step at a time, together. Scroll down whenever you're ready.": 'Achkha hinam, yachani... ¡ama llakikuychu! Huk-hukmanta purisunchik, kuska. Listo kaspaykiqa, urayman puriy.',
  "And remember: I'm only a helper. You and your local agronomist always have the final word.": 'Yuyariy: ñuqaqa yanapaqllam kani. Qam, agronomuykiwan kuska, qhipa simita rimankichik.',
}

const DICT = { es: ES, qu: QU }
