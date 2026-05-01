<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import type { VideoContent } from '$lib/types/index.js';
	import { onMount } from 'svelte';

	interface Props {
		content: VideoContent;
		onvideocomplete?: () => void;
	}
	let { content, onvideocomplete }: Props = $props();

	type Provider = VideoContent['provider'];

	/** Older curriculum.json may omit `provider`. */
	const provider = $derived<Provider>((content.provider ?? 'youtube') as Provider);

	let containerEl: HTMLDivElement | undefined = $state();
	const playerId = `yt-player-${Math.random().toString(36).slice(2, 9)}`;
	let fired = false;

	function extractYouTubeId(url: string): string | null {
		const m = url.match(/(?:youtube\.com\/watch\?.*v=|youtu\.be\/)([\w\-]+)/);
		return m ? m[1] : null;
	}

	function setupViewportFallback(): () => void {
		if (!containerEl || !onvideocomplete) return () => {};
		let timer: ReturnType<typeof setTimeout> | null = null;
		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting && !fired) {
						timer = setTimeout(() => {
							if (!fired) {
								fired = true;
								onvideocomplete?.();
							}
						}, 3000);
					} else if (!entry.isIntersecting && timer !== null) {
						clearTimeout(timer);
						timer = null;
					}
				}
			},
			{ threshold: 0.1 }
		);
		observer.observe(containerEl);
		return () => {
			observer.disconnect();
			if (timer !== null) clearTimeout(timer);
		};
	}

	onMount(() => {
		if (provider !== 'youtube' || !onvideocomplete) return;
		const videoId = extractYouTubeId(content.url);
		if (!videoId) return;

		let cleanup: (() => void) | undefined;
		/* eslint-disable @typescript-eslint/no-explicit-any */
		let player: any;

		function createPlayer() {
			if (fired) return;
			try {
				player = new (window as any).YT.Player(playerId, {
					videoId,
					playerVars: { rel: 0 },
					events: {
						onStateChange: (event: any) => {
							if (event.data === (window as any).YT.PlayerState.ENDED && !fired) {
								fired = true;
								onvideocomplete?.();
							}
						}
					}
				});
			} catch {
				cleanup = setupViewportFallback();
			}
		}

		if ((window as any).YT?.Player) {
			createPlayer();
		} else {
			if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
				const tag = document.createElement('script');
				tag.src = 'https://www.youtube.com/iframe_api';
				document.head.appendChild(tag);
			}

			const prevReady = (window as any).onYouTubeIframeAPIReady;
			(window as any).onYouTubeIframeAPIReady = () => {
				prevReady?.();
				createPlayer();
			};

			const fallbackTimer = setTimeout(() => {
				if (!(window as any).YT?.Player && !fired) {
					cleanup = setupViewportFallback();
				}
			}, 5000);

			return () => {
				clearTimeout(fallbackTimer);
				player?.destroy?.();
				cleanup?.();
			};
		}
		/* eslint-enable @typescript-eslint/no-explicit-any */

		return () => {
			player?.destroy?.();
			cleanup?.();
		};
	});
</script>

<!-- Extensions are reserved for player-specific UI (chapters, transcripts). -->
<div bind:this={containerEl} class="relative w-full overflow-hidden rounded-lg" style="padding-top: 56.25%;">
	{#if provider === 'youtube'}
		<div id={playerId} class="absolute inset-0 h-full w-full"></div>
	{:else}
		<div
			class="absolute inset-0 flex items-center justify-center bg-gray-100 text-sm text-gray-500"
		>
			Unsupported video provider: {provider}
		</div>
	{/if}
</div>
