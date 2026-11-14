<script setup>
import Backdrop from './components/Backdrop.vue'
import TopBar from './components/TopBar.vue'
import IntroStage from './components/IntroStage.vue'
import RegionPicker from './components/RegionPicker.vue'
import ExploreStage from './components/ExploreStage.vue'
import ReportSheet from './components/ReportSheet.vue'
import SproutDock from './cat/SproutDock.vue'
import { state } from './store.js'

// One screen, three stages: Sprout says hello → where do you farm → the map with one topic over it at a time.
</script>

<template>
  <Backdrop :low="state.stage !== 'intro'" />
  <TopBar />
  <main class="fixed inset-0 z-10 print:hidden">
    <Transition name="stage" mode="out-in">
      <IntroStage v-if="state.stage === 'intro'" />
      <RegionPicker v-else-if="state.stage === 'where'" />
      <ExploreStage v-else :key="state.area?.kind" />
    </Transition>
  </main>
  <SproutDock />
  <ReportSheet />
</template>
