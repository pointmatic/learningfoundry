<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { renderMarkdown } from '$lib/utils/markdown.js';
	import type { TextContent } from '$lib/types/index.js';
	import { onMount } from 'svelte';

	interface Props {
		content: TextContent;
		ontextcomplete?: () => void;
	}
	let { content, ontextcomplete }: Props = $props();

	const html = $derived(renderMarkdown(content.markdown));
	let blockEl: HTMLDivElement | undefined = $state();
	let fired = false;

	onMount(() => {
		if (!blockEl || !ontextcomplete) return;
		let timer: ReturnType<typeof setTimeout> | null = null;

		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting && !fired) {
						timer = setTimeout(() => {
							if (!fired) {
								fired = true;
								ontextcomplete?.();
							}
						}, 1000);
					} else if (!entry.isIntersecting && timer !== null) {
						clearTimeout(timer);
						timer = null;
					}
				}
			},
			{ threshold: 0.1 }
		);

		observer.observe(blockEl);

		return () => {
			observer.disconnect();
			if (timer !== null) clearTimeout(timer);
		};
	});
</script>

<div bind:this={blockEl} class="prose prose-slate max-w-none">
	{@html html}
</div>
