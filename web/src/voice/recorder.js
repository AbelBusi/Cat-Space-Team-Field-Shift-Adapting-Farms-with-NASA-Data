// Graba audio del micrófono con MediaRecorder. El navegador exige https o localhost.
const MIMES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']

export const supported = () => !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder)

export async function startRecording({ maxMs = 30000, onAutoStop } = {}) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    const mimeType = MIMES.find(m => MediaRecorder.isTypeSupported(m))
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    const chunks = []
    const release = () => stream.getTracks().forEach(t => t.stop())
    rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data) }
    const done = new Promise(resolve => {
        rec.onstop = () => { release(); resolve(new Blob(chunks, { type: rec.mimeType || 'audio/webm' })) }
    })
    rec.start()
    const timer = setTimeout(() => { if (rec.state === 'recording') { rec.stop(); onAutoStop?.() } }, maxMs)
    return {
        stop() { clearTimeout(timer); if (rec.state === 'recording') rec.stop(); return done },
        cancel() { clearTimeout(timer); rec.onstop = release; rec.state === 'recording' ? rec.stop() : release() },
    }
}