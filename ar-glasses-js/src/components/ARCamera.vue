<script setup>
import { ref, onMounted } from 'vue'

const videoRef = ref(null)

onMounted(async () => {
  if (!videoRef.value) return

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    videoRef.value.srcObject = stream
    await videoRef.value.play()
    console.log('Camera feed running!')
  } catch (err) {
    console.error('Camera access failed:', err)
  }
})
</script>

<template>
  <div class="relative w-full h-full">
    <video ref="videoRef" class="w-full h-full object-cover" autoplay playsinline muted></video>
  </div>
</template>

<style scoped></style>