<script setup lang="ts">
import { ref } from 'vue';
import ARCamera from './components/ARCamera.vue';
import Navbar from './components/Navbar.vue';
import Footer from './components/Footer.vue';

import { SelectButton } from 'primevue';

const arModes = ref([
    { name: 'Glasses', value: 'glasses' },
    { name: 'Contacts', value: 'contacts' }
]);
const currentMode = ref('glasses');
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

            <ARCamera :mode="currentMode" />
            
        </main>

        <Footer />
    </div>
</template>

<style scoped>
    
</style>
