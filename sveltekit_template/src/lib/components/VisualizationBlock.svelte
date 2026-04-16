<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import type { VisualizationContent } from '$lib/types/index.js';
	import PlaceholderBlock from './PlaceholderBlock.svelte';

	interface Props {
		content: VisualizationContent;
	}
	let { content }: Props = $props();

	const isStub = $derived(content.status === 'stub');
	const isSvg = $derived(content.content_type === 'image/svg+xml' && content.content);
	const isImage = $derived(content.render_type === 'image' && content.content && !isSvg);
</script>

{#if isStub}
	<PlaceholderBlock
		label="Visualization: {content.title}"
		message="d3foundry integration pending."
	/>
{:else if isSvg}
	<figure class="my-4">
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="flex justify-center">{@html content.content}</div>
		{#if content.caption}
			<figcaption class="mt-2 text-center text-xs text-gray-500">{content.caption}</figcaption>
		{/if}
	</figure>
{:else if isImage}
	<figure class="my-4">
		<img
			src={`data:${content.content_type};base64,${content.content}`}
			alt={content.alt_text}
			class="mx-auto max-w-full rounded"
		/>
		{#if content.caption}
			<figcaption class="mt-2 text-center text-xs text-gray-500">{content.caption}</figcaption>
		{/if}
	</figure>
{:else}
	<PlaceholderBlock label="Visualization: {content.title}" message="Unsupported render type." />
{/if}
