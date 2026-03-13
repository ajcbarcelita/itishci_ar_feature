<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
const emit = defineEmits<{
  (e: 'close', payload: { dontAskAgain: boolean }): void
}>();

const step = ref(0);
const dontAsk = ref(false);
const steps = [
  {
    title: 'Enable Camera',
    desc: 'Allow camera access when prompted so AR can track your face. You can toggle permissions in your browser settings.'
  },
  {
    title: 'Position Your Device',
    desc: 'Hold your device at eye level and center your face in the frame. Good lighting improves tracking.'
  },
  {
    title: 'Controls Overview',
    desc: 'Use the mode selector to switch between glasses and contacts. Tap a model to preview it. Use the help button to reopen this guide.'
  }
];

const current = computed(() => {
  const s = steps[step.value];
  return s ?? { title: '', desc: '' };
});
const stepIndex = computed(() => (typeof step.value === 'number' ? step.value : 0));

function next() {
  if (step.value < steps.length - 1) step.value++;
  else close();
}

function prev() {
  if (step.value > 0) step.value--;
}

function close() {
  emit('close', { dontAskAgain: dontAsk.value });
}

onMounted(() => {
  const el = document.getElementById('onboarding-close-btn');
  if (el) (el as HTMLElement).focus();
});
</script>

<template>
  <div
    role="dialog"
    aria-modal="true"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
  >
    <div class="bg-white rounded-xl shadow-2xl max-w-xl w-full p-6" tabindex="-1">
      <header class="flex items-start justify-between">
        <div>
            <h2 class="text-xl font-semibold">{{ current.title }}</h2>
            <p class="text-sm text-neutral-600 mt-1">Step {{ stepIndex + 1 }} of {{ steps.length }}</p>
        </div>
        <button id="onboarding-close-btn" @click="close" class="ml-4 text-sm text-neutral-600 hover:text-neutral-800">Close</button>
      </header>

      <section class="mt-4 text-neutral-800">
        <p>{{ current.desc }}</p>
      </section>

      <footer class="mt-6 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <label class="inline-flex items-center text-sm text-neutral-700">
            <input type="checkbox" v-model="dontAsk" class="mr-2" /> Don't show again
          </label>
        </div>

        <div class="flex items-center space-x-2">
          <button @click="prev" :disabled="stepIndex===0" class="px-3 py-1 rounded bg-neutral-100 text-sm disabled:opacity-50">Back</button>
          <button @click="next" class="px-4 py-2 rounded bg-sky-600 text-white text-sm">{{ stepIndex < steps.length - 1 ? 'Next' : 'Done' }}</button>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.disabled\:opacity-50[disabled] { opacity: 0.5; }
</style>
