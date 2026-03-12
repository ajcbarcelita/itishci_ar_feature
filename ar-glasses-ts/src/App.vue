<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import ARCamera from './components/ARCamera.vue';
import Navbar from './components/Navbar.vue';
import Footer from './components/Footer.vue';
import PreviewCarousel from './components/PreviewCarousel.vue';

import { SelectButton } from 'primevue';

const arModes = ref([
    { name: 'Glasses', value: 'glasses' },
    { name: 'Contacts', value: 'contacts' }
]);
const currentMode = ref('glasses');
const models = ref([
    { name: 'EO Mangekyou Itachi', value: 'lens1.png', image: '/lens1.png', type: 'contacts' },
    { name: 'EO Eyewear Dell', value: 'classic_nerd_black', image: '/1stglasses.png', type: 'glasses' },
    { name: 'EO Rect Metal (Silver)', value: 'rect_metal_silver', image: '/2ndglasses.png', type: 'glasses' },
    { name: 'EO Aqua Lens', value: 'lens2.png', image: '/lens2.png', type: 'contacts' },
    { name: 'EO Fuchsia Lens', value: 'lens3.png', image: '/lens3.png', type: 'contacts' },
]);
const selectedModel = ref('classic_nerd_black');

// Show only PNG lens items when in `contacts` mode
const displayedModels = computed(() => {
    // Filter models by explicit `type` to separate glasses vs contacts
    return models.value.filter((m) => (m as any).type === currentMode.value);
});

// Remember previous selection so switching back to glasses restores it
const previousSelected = ref<string | null>(null);
watch(currentMode, (mode, oldMode) => {
    if (mode === 'contacts') {
        // store previous selection
        previousSelected.value = selectedModel.value;
        const first = displayedModels.value[0];
        if (first) selectedModel.value = first.value;
    } else if (oldMode === 'contacts') {
        // restore previous selection when going back to glasses
        if (previousSelected.value) selectedModel.value = previousSelected.value;
        previousSelected.value = null;
    }
});
</script>

<template>
    <div class="min-h-screen flex flex-col bg-neutral-50 text-neutral-900 font-sans">
        <Navbar />

        <main class="bg-sky-50 grow flex flex-col items-center justify-center p-4 w-full relative">
            
            <div class="mb-6 z-20">
                <SelectButton 
                    v-model="currentMode" 
                    :options="arModes" 
                    optionLabel="name" 
                    optionValue="value" 
                    :allowEmpty="false"
                    class="shadow-md bg-white rounded-full p-1" 
                    
                />
            </div>

            <div class="mb-6 z-20 w-full">
                <div class="bg-white shadow-2xl rounded-3xl p-6 w-full max-w-3xl mx-auto flex flex-col items-center border border-neutral-200 ring-1 ring-sky-50">
                    <PreviewCarousel v-model="selectedModel" :options="displayedModels" />
                </div>
            </div>

            <ARCamera :mode="currentMode" :model="selectedModel" />
            
        </main>

        <Footer />
    </div>
</template>

<style scoped>
    
</style>
