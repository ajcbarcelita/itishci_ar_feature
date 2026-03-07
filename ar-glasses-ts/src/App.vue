<script setup lang="ts">
import ARCamera from './components/ARCamera.vue';
</script>

<template>
    <div class="min-h-screen flex flex-col bg-neutral-50 text-white font-sans">
        <header
            class="p-4 border-b border-neutral-800 text-center text-neutral-900 font-bold tracking-widest"
        >
            NAVBAR
        </header>

        <main class="flex-grow flex items-center justify-center p-4 w-full">
            <ARCamera />
        </main>

        <footer class="p-4 border-t border-neutral-800 text-center text-sm text-neutral-500">
            FOOTER
        </footer>
    </div>
</template>
