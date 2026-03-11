<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  options: Array<{ name: string; value: string; image?: string }>,
  modelValue?: string,
}>();

const emit = defineEmits(['update:modelValue']);

const currentIndex = computed(() => {
  if (!props.modelValue) return 0;
  const idx = props.options.findIndex((o) => o.value === props.modelValue);
  return idx === -1 ? 0 : idx;
});

const selectedOption = computed(() => props.options[currentIndex.value] ?? null);

function selectIndex(i: number) {
  const idx = (i + props.options.length) % props.options.length;
  const val = props.options[idx]?.value;
  if (val) emit('update:modelValue', val);
}

function prev() {
  selectIndex(currentIndex.value - 1);
}

function next() {
  selectIndex(currentIndex.value + 1);
}
</script>

<template>
  <div class="w-full flex items-center justify-center">
    <button aria-label="prev" @click="prev" class="p-2 mr-2 hover:bg-neutral-100 rounded-full flex items-center">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      <span class="ml-2 text-sm font-medium">Previous</span>
    </button>

    <div class="mx-4 overflow-hidden w-full max-w-3xl">
      <div class="flex gap-4 items-center justify-start transition-transform duration-300" :style="{ transform: `translateX(${ -currentIndex * 116 }px)` }">
        <div v-for="(opt, i) in props.options" :key="opt.value" class="shrink-0 w-28 h-20 relative flex flex-col items-center">
          <button @click="selectIndex(i)" class="w-full h-full block">
            <img :src="opt.image || '/placeholder.png'" :alt="opt.name" class="w-full h-full object-contain rounded shadow" :class="{'ring-4 ring-sky-400': i === currentIndex}" />
          </button>
        </div>
      </div>

      <div v-if="selectedOption" class="mt-3 text-center text-lg font-semibold text-neutral-900">{{ selectedOption.name }}</div>
    </div>

    <button aria-label="next" @click="next" class="p-2 ml-2 hover:bg-neutral-100 rounded-full flex items-center">
      <span class="mr-2 text-sm font-medium">Next</span>
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.shadow { box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
</style>
