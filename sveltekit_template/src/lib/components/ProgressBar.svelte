<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	interface Props {
		/** 0–100 */
		percent: number;
		label?: string;
	}
	let { percent, label }: Props = $props();
	const clamped = $derived(Math.min(100, Math.max(0, percent)));
</script>

<div class="w-full">
	{#if label}
		<div class="mb-1 flex items-center justify-between text-xs text-gray-500">
			<span>{label}</span>
			<span>{Math.round(clamped)}%</span>
		</div>
	{/if}
	<div class="h-2 w-full overflow-hidden rounded-full bg-gray-200">
		<div
			class="h-full rounded-full bg-blue-500 transition-all duration-300"
			style="width: {clamped}%"
			role="progressbar"
			aria-valuenow={clamped}
			aria-valuemin={0}
			aria-valuemax={100}
		></div>
	</div>
</div>
