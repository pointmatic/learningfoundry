<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { resetProgress } from '$lib/db/index.js';
	import { currentPosition, curriculum } from '$lib/stores/curriculum.js';
	import { invalidateProgress } from '$lib/stores/progress.js';
	import { RotateCcw } from 'lucide-svelte';

	interface Props {
		disabled?: boolean;
		/** Override for unit tests; defaults to `window.confirm`. */
		confirmFn?: (message: string) => boolean;
	}
	let {
		disabled = false,
		confirmFn = (msg: string) => window.confirm(msg)
	}: Props = $props();

	const PROMPT = 'Reset all progress for this curriculum? This cannot be undone.';

	async function handleClick() {
		if (disabled) return;
		if (!confirmFn(PROMPT)) return;
		await resetProgress();
		// Clearing the position triggers the FR-P14 sidebar collapse path
		// in `ModuleList`'s auto-expand `$effect` once Story I.n ships;
		// pre-I.n it is a harmless no-op.
		currentPosition.set(null);
		await invalidateProgress($curriculum);
		await goto('/');
	}
</script>

<button
	type="button"
	onclick={handleClick}
	disabled={disabled}
	aria-disabled={disabled}
	class="flex w-full items-center justify-center gap-2 rounded border border-transparent px-3 py-2 text-xs font-medium transition-colors
		{disabled
		? 'cursor-not-allowed text-gray-300'
		: 'text-red-600 hover:bg-red-50'}"
>
	<RotateCcw size={14} aria-hidden="true" />
	Reset course progress
</button>
