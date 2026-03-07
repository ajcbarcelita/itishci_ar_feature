<script setup lang="ts">
import ARCamera from './components/ARCamera.vue';
import Navbar from './components/Navbar.vue';
import Footer from './components/Footer.vue';
</script>

<template>
    <div class="min-h-screen flex flex-col bg-neutral-50 text-white font-sans">
        <Navbar />

        <main class="flex-grow flex items-center justify-center p-4 w-full">
            <ARCamera />
        </main>

        <Footer />
    </div>
</template>
