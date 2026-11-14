<script setup>
// Layout of a topic: cards on the left and right edges of the map on wide screens (they slide in from their side),
// one bottom sheet on phones. The space under the cards is left free for Sprout.
</script>

<template>
  <div class="pointer-events-none absolute inset-0 z-10 max-lg:pointer-events-auto max-lg:top-auto max-lg:flex max-lg:h-[44dvh] max-lg:flex-col max-lg:gap-3 max-lg:overflow-y-auto max-lg:border-t max-lg:border-line max-lg:bg-bg/95 max-lg:p-3">
    <div class="col-left flex flex-col gap-3 max-lg:contents lg:absolute lg:left-14 lg:top-36 lg:max-h-[calc(100dvh-9rem-9.5rem)] lg:w-[clamp(280px,27vw,380px)] lg:overflow-y-auto lg:overflow-x-hidden lg:p-0.5">
      <slot name="left" />
    </div>
    <div class="col-right flex flex-col gap-3 max-lg:contents lg:absolute lg:right-14 lg:top-36 lg:max-h-[calc(100dvh-9rem-9.5rem)] lg:w-[clamp(280px,27vw,380px)] lg:overflow-y-auto lg:overflow-x-hidden lg:p-0.5">
      <slot name="right" />
    </div>
  </div>
</template>
