import { writable, derived, get } from 'svelte/store';
import { io, Socket } from 'socket.io-client';

export interface ScrapeTask {
	id: string;
	url: string;
	framework: string;
	status: 'queued' | 'starting' | 'discovering' | 'scraping' | 'completed' | 'error';
	progress: number;
	message: string;
	total_pages?: number;
	pages_scraped?: number;
	current_page?: string;
	scraped_content?: Array<{
		url: string;
		title: string;
		content: string;
	}>;
	error?: string;
}

function createScrapingStore() {
	const { subscribe, set, update } = writable<ScrapeTask | null>(null);
	
	let socket: Socket | null = null;
	
	return {
		subscribe,
		
		connect() {
			if (socket?.connected) return;
			
			socket = io('http://localhost:5000', {
				transports: ['websocket'],
				reconnection: true,
				reconnectionAttempts: 5,
				reconnectionDelay: 1000
			});
			
			socket.on('connect', () => {
				console.log('WebSocket connected');
			});
			
			socket.on('task_update', (task: ScrapeTask) => {
				set(task);
			});
			
			socket.on('disconnect', () => {
				console.log('WebSocket disconnected');
			});
		},
		
		disconnect() {
			if (socket) {
				socket.disconnect();
				socket = null;
			}
		},
		
		async startScraping(url: string, framework: string, topic_name?: string, mode: string = 'intelligent') {
			try {
				const response = await fetch('/api/scrape', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ 
						url, 
						framework, 
						topic_name: topic_name || framework,
						mode 
					})
				});
				
				if (!response.ok) throw new Error('Failed to start scraping');
				
				const data = await response.json();
				
				// Subscribe to task updates
				if (socket && data.task_id) {
					socket.emit('subscribe_task', { task_id: data.task_id });
				}
				
				return data.task_id;
			} catch (error) {
				console.error('Error starting scrape:', error);
				throw error;
			}
		},
		
		reset() {
			set(null);
		}
	};
}

export const scraping = createScrapingStore();