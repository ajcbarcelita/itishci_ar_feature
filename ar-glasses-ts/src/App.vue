<script setup lang="ts">
import { ref } from 'vue';
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
    { name: 'EO Eyewear Dell', value: 'classic_nerd_black', image: '/1stglasses.png' },
    { name: 'EO Rect Metal (Silver)', value: 'rect_metal_silver', image: '/2ndglasses.png' },
]);
const selectedModel = ref('classic_nerd_black');
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
                    <PreviewCarousel v-model="selectedModel" :options="models" />
                </div>
            </div>

            <ARCamera :mode="currentMode" :model="selectedModel" />
            
        </main>

        <Footer />
    </div>
</template>

<style scoped>
    
</style>
