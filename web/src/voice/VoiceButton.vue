<script setup>
import { ref, onBeforeUnmount } from 'vue'
import PixelIcon from '../components/PixelIcon.vue'
import { t, lang } from '../i18n.js'
import { supported, startRecording } from './recorder.js'
import { askByVoice, toVoiceContext, toHistory, playReply } from './voiceApi.js'

// Botón de micrófono: un toque empieza a grabar, otro toque envía. Un toque mientras piensa o habla, cancela.
// No sabe nada de Sprout: avisa con eventos y quien lo use decide qué mostrar.
const props = defineProps({
  context: { type: Function, default: () => ({}) },   // devuelve lo que el usuario ve en pantalla
  history: { type: Function, default: () => [] },     // devuelve [{ role, content }]
  speak: { type: Boolean, default: true },            // false = solo texto (por ejemplo, con el sonido apagado)
  muted: { type: Boolean, default: false },           // con el sonido apagado, Sprout responde solo con texto
})
const emit = defineEmits(['listening', 'thinking', 'reply', 'speaking', 'idle', 'error'])

const phase = ref('idle')   // idle | listening | thinking | speaking
const can = supported()
let session = null, player = null, controller = null

const micError = e => e?.name === 'NotAllowedError' ? t('Microphone permission denied.')
    : e?.name === 'NotFoundError' ? t('No microphone found.') : t('Could not use the microphone.')

async function toggle() {
  if (phase.value === 'listening') return send()
  if (phase.value !== 'idle') return cancel()
  try {
    session = await startRecording({ onAutoStop: send })
    phase.value = 'listening'
    emit('listening')
  } catch (e) { emit('error', micError(e)) }
}

async function send() {
  if (phase.value !== 'listening' || !session) return
  const s = session
  session = null
  phase.value = 'thinking'
  emit('thinking')
  controller = new AbortController()
  try {
    const blob = await s.stop()
    if (blob.size < 1500) throw new Error(t('I did not hear anything. Try again.'))
    const reply = await askByVoice(blob, {
      context: toVoiceContext(props.context()), history: toHistory(props.history()),
      speak: props.speak && !props.muted, lang: lang.value === 'en' ? 'en' : 'es', signal: controller.signal,
    })
    emit('reply', reply)
    player = playReply(reply, {
      silent: props.muted,
      onStart: () => { phase.value = 'speaking'; emit('speaking', true) },
      onEnd: () => { phase.value = 'idle'; emit('speaking', false); emit('idle') },
    })
  } catch (e) {
    phase.value = 'idle'
    if (e.name !== 'AbortError') emit('error', e.message)
    emit('idle')
  }
}

function cancel() {
  controller?.abort()
  player?.stop()
  session?.cancel()
  session = player = null
  phase.value = 'idle'
  emit('speaking', false)
  emit('idle')
}

onBeforeUnmount(cancel)
</script>

<template>
  <button v-if="can" type="button" class="px-1.5 py-1 uppercase hover:text-ink"
          :class="{ 'animate-pulse text-fire': phase === 'listening', 'text-teal': phase === 'thinking' || phase === 'speaking' }"
          :aria-pressed="phase !== 'idle'"
          :aria-label="t(phase === 'listening' ? 'Stop and send' : phase === 'idle' ? 'Talk to Sprout' : 'Cancel')"
          :title="t(phase === 'listening' ? 'Stop and send' : phase === 'idle' ? 'Talk to Sprout' : 'Cancel')"
          @click="toggle">
    <PixelIcon :name="phase === 'thinking' ? 'ai' : 'mic'" color="currentColor" :size="1.25" />
  </button>
</template>