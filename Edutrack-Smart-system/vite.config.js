import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        login: resolve(__dirname, 'login.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        analysis: resolve(__dirname, 'analysis.html'),
        records: resolve(__dirname, 'records.html'),
        settings: resolve(__dirname, 'settings.html'),
        manual_attendance: resolve(__dirname, 'manual_attendance.html'),
        privacy: resolve(__dirname, 'privacy.html'),
        signup: resolve(__dirname, 'signup.html'),
        register: resolve(__dirname, 'register_student.html')
      }
    }
  }
});
