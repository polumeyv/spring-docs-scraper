import { writable, derived } from 'svelte/store';
import { io, Socket } from 'socket.io-client';

export interface DownloadTask {
	id: string;
	url: string;
	folder: string;
	framework: string;
	status: 'queued' | 'downloading' | 'completed' | 'cancelled' | 'error';
	progress: number;
	total_pages: number;
	pages_scraped: number;
	start_time: string;
	error?: string;
}

interface WebSocketState {
	connected: boolean;
	activeDownloads: DownloadTask[];
	queuedDownloads: DownloadTask[];
}

function createWebSocketStore() {
	let socket: Socket | null = null;
	
	const { subscribe, update } = writable<WebSocketState>({
		connected: false,
		activeDownloads: [],
		queuedDownloads: []
	});
	
	function connect() {
		if (socket?.connected) return;
		
		// Connect to the backend WebSocket server
		socket = io('http://localhost:5000', {
			transports: ['websocket'],
			reconnection: true,
			reconnectionAttempts: 5,
			reconnectionDelay: 1000
		});
		
		// Connection events
		socket.on('connect', () => {
			console.log('WebSocket connected');
			update(state => ({ ...state, connected: true }));
		});
		
		socket.on('disconnect', () => {
			console.log('WebSocket disconnected');
			update(state => ({ ...state, connected: false }));
		});
		
		// Queue updates
		socket.on('queue_update', (data: { active: DownloadTask[], queue: DownloadTask[] }) => {
			update(state => ({
				...state,
				activeDownloads: data.active,
				queuedDownloads: data.queue
			}));
		});
		
		// Task updates
		socket.on('task_update', (task: DownloadTask) => {
			update(state => {
				const activeIndex = state.activeDownloads.findIndex(t => t.id === task.id);
				if (activeIndex >= 0) {
					const newActive = [...state.activeDownloads];
					newActive[activeIndex] = task;
					return { ...state, activeDownloads: newActive };
				}
				return state;
			});
		});
	}
	
	function disconnect() {
		if (socket) {
			socket.disconnect();
			socket = null;
		}
	}
	
	function subscribeToTask(taskId: string) {
		if (socket?.connected) {
			socket.emit('subscribe_to_task', { task_id: taskId });
		}
	}
	
	async function cancelDownload(taskId: string) {
		try {
			const response = await fetch(`/api/download/${taskId}/cancel`, {
				method: 'POST'
			});
			
			if (!response.ok) {
				throw new Error('Failed to cancel download');
			}
			
			return true;
		} catch (error) {
			console.error('Error cancelling download:', error);
			return false;
		}
	}
	
	return {
		subscribe,
		connect,
		disconnect,
		subscribeToTask,
		cancelDownload
	};
}

export const websocket = createWebSocketStore();

// Derived stores for easier access
export const isConnected = derived(
	websocket,
	$websocket => $websocket.connected
);

export const activeDownloads = derived(
	websocket,
	$websocket => $websocket.activeDownloads
);

export const queuedDownloads = derived(
	websocket,
	$websocket => $websocket.queuedDownloads
);

export const totalDownloads = derived(
	websocket,
	$websocket => $websocket.activeDownloads.length + $websocket.queuedDownloads.length
);