<script setup lang="ts">
</script>

<template>
  <header class="w-full font-inter text-black">
    
    <div class="bg-sky-50 text-center py-2 text-sm underline font-bold">
      <span>Enjoy 12% Sale on February 28!</span>
    </div>

    <div class="bg-white flex justify-between items-center py-4 px-8">
      
      <div class="flex items-center">
        <img src="/eo_logo.png" alt="Executive Optical Logo" class="h-10 object-contain" />
      </div>
      
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2 py-1.5 px-4 border border-ocean-900 rounded-full font-bold text-sm cursor-pointer hover:bg-sky-50 transition-colors">
          <span>📞</span> Book an Appointment
        </div>
        
        <div class="w-[1px] h-6 bg-gray-400"></div>
        
        <div class="flex items-center gap-2 py-1.5 px-4 border border-ocean-900 rounded-full font-bold text-sm cursor-pointer hover:bg-sky-50 transition-colors">
          <span>📍</span> Branch Locator
        </div>
      </div>

    </div>

    <div class="bg-sky-400 flex justify-start items-center py-3 px-8 gap-8">
      
      <div class="flex gap-6 text-gray-500 font-bold text-sm">
        <span class="cursor-pointer hover:text-ocean-900 transition-colors">Contact Us</span>
        <span class="cursor-pointer hover:text-ocean-900 transition-colors">Eyeglasses</span>
        <span class="cursor-pointer hover:text-ocean-900 transition-colors">Contact Lens</span>
      </div>
      
      <div class="w-80 ml-4">
        <input 
          type="text" 
          placeholder="Search what you need" 
          class="w-full py-2 px-4 rounded-md bg-white border-none outline-none text-sm text-gray-600 placeholder-gray-400 font-semibold" 
        />
      </div>

    </div>
  </header>
</template>