import { createApp } from 'vue';
import App from './App.vue';
import './main.css';

import PrimeVue from 'primevue/config';
import { definePreset } from '@primeuix/themes';
import Lara from '@primeuix/themes/lara';

const MyPreset = definePreset(Lara, {
    components: {
        togglebutton: {
            colorScheme: {
                light: {
                    root: {
                        checkedBackground: '#b2dff8', // Your custom sky-400
                        checkedBorderColor: '#b2dff8',
                        checkedColor: '#104378' 
                    }
                }
            }
        }
    }
});

const app = createApp(App);

app.use(PrimeVue, { 
    ripple: true,
    theme: {
        // 🛡️ THE FIX: Pass your custom MyPreset instead of raw Nora
        preset: MyPreset, 
        options: {
            darkModeSelector: false
        }
    }
});

app.mount('#app');