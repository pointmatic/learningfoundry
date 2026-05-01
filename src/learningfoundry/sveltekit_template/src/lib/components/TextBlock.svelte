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
	// Observe a zero-size sentinel placed at the *end* of the rendered
	// markdown rather than the wrapper itself. Otherwise a tall block fires
	// `textcomplete` simply because the top of the block is in view on
	// initial render — the learner would never have to scroll to the lesson
	// body. With the sentinel, completion requires the bottom of the block
	// to be in view for 1 s.
	let sentinelEl: HTMLDivElement | undefined = $state();
	let fired = false;

	onMount(() => {
		if (!sentinelEl || !ontextcomplete) return;
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

		observer.observe(sentinelEl);

		return () => {
			observer.disconnect();
			if (timer !== null) clearTimeout(timer);
		};
	});
</script>

<div class="prose prose-slate max-w-none">
	{@html html}
	<div bind:this={sentinelEl} aria-hidden="true" data-textblock-end></div>
</div>
