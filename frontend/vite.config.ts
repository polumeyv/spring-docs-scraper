import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/docs': {
				target: 'http://backend:8082',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/docs/, '')
			}
		}
	}
});
