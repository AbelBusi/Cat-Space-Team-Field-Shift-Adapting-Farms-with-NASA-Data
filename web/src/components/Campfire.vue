<script setup>
// The campfire of the landing: crossed logs on a ring of stones, three layers of flame that flicker at different
// speeds, a few sparks rising and a soft glow on the ground. Smooth vector art (not pixel art), only DESIGN.md colors.
</script>

<template>
  <svg class="campfire" viewBox="0 0 52 60" aria-hidden="true">
    <ellipse class="glow" cx="26" cy="53" rx="26" ry="6" />
    <g class="sparks">
      <circle cx="22" cy="30" r="1.1" /><circle cx="29" cy="26" r="0.9" /><circle cx="25" cy="34" r="0.8" />
    </g>
    <g class="flames">
      <path class="outer" d="M26 51C13 49 11 37 17 28C20 23 22 17 26 8C28 17 34 22 36 31C40 41 37 50 26 51Z" />
      <path class="middle" d="M26 51C17 50 15 41 20 34C22 31 24 26 26 19C28 26 31 30 33 35C35 43 33 50 26 51Z" />
      <path class="inner" d="M26 51C21 50 20 44 23 39C24 37 25 34 26 30C27 34 29 37 30 41C31 46 30 50 26 51Z" />
    </g>
    <g class="logs">
      <rect x="10" y="48" width="32" height="5" rx="2.5" transform="rotate(-14 26 50.5)" />
      <rect x="10" y="48" width="32" height="5" rx="2.5" transform="rotate(14 26 50.5)" />
      <circle class="cut" cx="11.5" cy="54.2" r="2" /><circle class="cut" cx="40.5" cy="54.2" r="2" />
    </g>
    <g class="stones">
      <ellipse cx="6" cy="56" rx="4" ry="2.4" /><ellipse cx="15" cy="57.5" rx="4.5" ry="2.3" /><ellipse cx="26" cy="58" rx="4.5" ry="2.2" />
      <ellipse cx="37" cy="57.5" rx="4.5" ry="2.3" /><ellipse cx="46" cy="56" rx="4" ry="2.4" />
    </g>
  </svg>
</template>

<style scoped>
.campfire { overflow: visible; }
.glow { fill: var(--fire); opacity: .22; animation: glow 2.4s ease-in-out infinite; transform-origin: 26px 53px; }
.logs rect { fill: var(--soil); }
.logs .cut { fill: var(--sand); }
.stones ellipse { fill: var(--line); stroke: var(--muted); stroke-opacity: .35; stroke-width: .6; }
.flames path { transform-box: fill-box; transform-origin: 50% 100%; }
.outer { fill: var(--ember); animation: flick 1.3s ease-in-out infinite; }
.middle { fill: var(--fire); animation: flick 0.9s ease-in-out infinite reverse; }
.inner { fill: var(--sky-ink); opacity: .9; animation: flick 0.7s ease-in-out infinite; }
.sparks circle { fill: var(--fire); animation: rise 2.2s ease-out infinite; }
.sparks circle:nth-child(2) { animation-delay: -.8s; animation-duration: 2.6s; }
.sparks circle:nth-child(3) { animation-delay: -1.5s; animation-duration: 1.9s; }
@keyframes flick {
  0%, 100% { transform: scale(1, 1) skewX(0deg); }
  25% { transform: scale(.94, 1.06) skewX(2deg); }
  50% { transform: scale(1.04, .95) skewX(-1.5deg); }
  75% { transform: scale(.97, 1.04) skewX(1deg); }
}
@keyframes rise { 0% { transform: translate(0, 0); opacity: 0; } 15% { opacity: 1; } 100% { transform: translate(3px, -26px); opacity: 0; } }
@keyframes glow { 50% { opacity: .32; transform: scale(1.08, 1.15); } }
</style>
