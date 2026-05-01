<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';
	import { currentPosition, nextLesson, previousLesson } from '$lib/stores/curriculum.js';
	import { resolveGoNext, resolveGoPrev } from './navigation.helpers.js';

	interface Props {
		disabled?: boolean;
	}
	let { disabled = false }: Props = $props();

	const prev = $derived($previousLesson);
	const next = $derived($nextLesson);

	function goNext() {
		const action = resolveGoNext(disabled, next);
		if (action.kind === 'noop') return;
		// Clear the position *before* `goto` so the sidebar's auto-expand
		// effect sees the null transition and collapses the previously
		// expanded module before the route change settles.
		if (action.clearPosition) currentPosition.set(null);
		void goto(action.url);
	}

	function goPrev() {
		const action = resolveGoPrev(prev);
		if (action.kind === 'goto') void goto(action.url);
	}
</script>

<div class="flex items-center justify-between border-t border-gray-200 pt-4">
	<button
		onclick={goPrev}
		disabled={!prev}
		class="flex items-center gap-1 rounded px-3 py-2 text-sm font-medium transition-colors
			{prev
			? 'text-gray-700 hover:bg-gray-100'
			: 'cursor-not-allowed text-gray-300'}"
	>
		<ChevronLeft size={16} />
		Previous
	</button>

	<button
		onclick={goNext}
		disabled={disabled}
		class="flex items-center gap-1 rounded px-4 py-2 text-sm font-medium transition-colors
			{disabled
			? 'bg-gray-300 text-gray-500 opacity-50 cursor-not-allowed'
			: 'bg-blue-600 text-white hover:bg-blue-700'}"
	>
		{next ? 'Next' : 'Finish'}
		{#if next}<ChevronRight size={16} />{/if}
	</button>
</div>
