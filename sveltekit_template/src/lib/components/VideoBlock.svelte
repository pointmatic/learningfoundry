<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import type { VideoContent } from '$lib/types/index.js';

	interface Props {
		content: VideoContent;
	}
	let { content }: Props = $props();

	type Provider = VideoContent['provider'];

	/** Older curriculum.json may omit `provider`. */
	const provider = $derived<Provider>((content.provider ?? 'youtube') as Provider);

	const embedUrl = $derived(() => {
		const url = content.url;
		if (provider === 'youtube') {
			const ytMatch = url.match(
				/(?:youtube\.com\/watch\?.*v=|youtu\.be\/)([\w\-]+)/
			);
			if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}`;
		}
		return url;
	});
</script>

<!-- Extensions are reserved for player-specific UI (chapters, transcripts). -->
<div class="relative w-full overflow-hidden rounded-lg" style="padding-top: 56.25%;">
	{#if provider === 'youtube'}
		<iframe
			class="absolute inset-0 h-full w-full"
			src={embedUrl()}
			title="Video"
			frameborder="0"
			allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
			allowfullscreen
		></iframe>
	{:else}
		<div
			class="absolute inset-0 flex items-center justify-center bg-gray-100 text-sm text-gray-500"
		>
			Unsupported video provider: {provider}
		</div>
	{/if}
</div>
