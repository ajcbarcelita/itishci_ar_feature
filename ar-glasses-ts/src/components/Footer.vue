<script setup lang="ts">
const currentYear = new Date().getFullYear();
</script>

<template>
  <footer class="w-full font-inter bg-white py-6 px-8 border-t border-gray-200 flex justify-between items-center">
    
    <div class="flex items-center gap-2 text-gray-600 text-sm font-medium">
      <span class="text-xl leading-none">&copy;</span>
      <span>{{ currentYear }} EO - Executive Optical. All Rights Reserved.</span>
    </div>

    <div class="flex items-center gap-6">
      <img src="/maya_logo.svg" alt="Maya Logo" class="h-6 object-contain" />
      <img src="/gcash_logo.svg" alt="GCash Logo" class="h-6 object-contain" />
      <img src="/paypal_logo.svg" alt="PayPal Logo" class="h-6 object-contain" />
      <img src="/mastercard_logo.svg" alt="Mastercard Logo" class="h-6 object-contain" />
    </div>

  </footer>
</template>