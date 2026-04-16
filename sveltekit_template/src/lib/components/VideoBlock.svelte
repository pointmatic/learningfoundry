<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import type { VideoContent } from '$lib/types/index.js';

	interface Props {
		content: VideoContent;
	}
	let { content }: Props = $props();

	const embedUrl = $derived(() => {
		const url = content.url;
		// Convert watch?v=ID or youtu.be/ID to embed URL
		const ytMatch = url.match(/(?:youtube\.com\/watch\?.*v=|youtu\.be\/)([\w\-]+)/);
		if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}`;
		return url;
	});
</script>

<div class="relative w-full overflow-hidden rounded-lg" style="padding-top: 56.25%;">
	<iframe
		class="absolute inset-0 h-full w-full"
		src={embedUrl()}
		title="Video"
		frameborder="0"
		allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
		allowfullscreen
	></iframe>
</div>
