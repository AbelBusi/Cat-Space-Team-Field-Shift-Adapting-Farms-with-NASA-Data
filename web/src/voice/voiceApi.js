// Cliente del asistente de voz (ml-api/voice_assistant). La clave de Groq nunca llega aquí: vive en el backend.
// TODO: cuando me pases lib/mlApi.js, tomar la URL de ahí en vez de leer la variable de entorno.
const ROOT = (import.meta.env.VITE_ML_API_URL || 'http://localhost:8000').replace(/\/+$/, '').replace(/\/api\/v1$/, '')
const BASE = `${ROOT}/api/v1/assistant`

// El backend rechaza campos desconocidos: solo se envía lo que el schema acepta.
export function toVoiceContext(c = {}) {
    const out = {}
    if (Number.isFinite(c.lat) && Number.isFinite(c.lon)) { out.lat = c.lat; out.lon = c.lon }
    if (c.district) out.district = String(c.district).slice(0, 80)
    if (c.month != null) out.month = String(c.month).slice(0, 10)
    if (c.topic) out.topic = String(c.topic).slice(0, 60)
    if (c.readings && typeof c.readings === 'object') out.readings = c.readings
    return out
}

export const toHistory = (turns = []) =>
    turns.slice(-10).map(t => ({ role: t.role === 'user' ? 'user' : 'assistant', content: String(t.content).slice(0, 2000) }))

async function readError(res) {
    let detail = ''
    try { const j = await res.json(); detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j) } catch { /* sin cuerpo */ }
    const err = new Error(detail || `HTTP ${res.status}`)
    err.status = res.status
    err.retryAfter = res.headers.get('Retry-After')
    return err
}

const ext = type => (type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm')

// Audio -> { transcript, text, mood, actions, tools_used, audio_base64, audio_mime }
export async function askByVoice(blob, { context, history, speak = true, signal } = {}) {
    const fd = new FormData()
    fd.append('audio', blob, `voice.${ext(blob.type)}`)
    if (context && Object.keys(context).length) fd.append('context', JSON.stringify(context))
    if (history?.length) fd.append('history', JSON.stringify(history))
    fd.append('speak', String(speak))
    let res
    try { res = await fetch(`${BASE}/voice`, { method: 'POST', body: fd, signal }) }
    catch (e) { if (e.name === 'AbortError') throw e; throw new Error('No se pudo conectar con el asistente.') }
    if (!res.ok) throw await readError(res)
    return res.json()
}

// Texto -> misma respuesta (sin transcript). Útil para probar o para escribirle al asistente con herramientas.
export async function askByText(message, { context, history, speak = false, signal } = {}) {
    const res = await fetch(`${BASE}/chat`, {
        method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, context, history, speak }),
    })
    if (!res.ok) throw await readError(res)
    return res.json()
}

// Reproduce el audio de la respuesta. onStart/onEnd permiten que el gato mueva la boca mientras suena.
export function playReply(reply, { onStart, onEnd } = {}) {
    let ended = false
    const end = () => { if (!ended) { ended = true; onEnd?.() } }
    if (!reply?.audio_base64) { end(); return { stop: end } }
    const audio = new Audio(`data:${reply.audio_mime || 'audio/wav'};base64,${reply.audio_base64}`)
    audio.onplay = () => onStart?.()
    audio.onended = end
    audio.onerror = end
    audio.play().catch(end)
    return { stop() { audio.pause(); end() } }
}