import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit(),
	],
	server: {
		proxy: {
			'/docs': {
				target: 'http://backend:8082',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/docs/, '')
			},
			'/api': {
				target: 'http://api:5000',
				changeOrigin: true
			}
		}
	}
});
