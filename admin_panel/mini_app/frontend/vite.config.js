import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    allowedHosts: [
      'b723-37-27-91-108.ngrok-free.app',
      '.ngrok-free.app',
      '.ngrok.io',
      'localhost'
    ],
    // Проксирование API запросов к бэкенду
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        timeout: 10000,
        rewrite: (path) => path, // Не изменяем путь
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            // Улучшенная обработка ошибок прокси
            if (err.code === 'ECONNREFUSED') {
              console.warn('⚠️  Бэкенд недоступен на http://localhost:8000');
              console.warn('   Запустите бэкенд: cd admin_panel/mini_app/backend && python3 run.py');
              // Возвращаем понятную ошибку клиенту
              if (!res.headersSent) {
                res.writeHead(503, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                  detail: 'Сервер недоступен. Убедитесь, что бэкенд запущен на порту 8000.'
                }));
              }
            } else {
              console.error('Proxy error:', err.message);
            }
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log(`[Proxy] ${req.method} ${req.url} -> http://localhost:8000${req.url}`);
          });
        }
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
