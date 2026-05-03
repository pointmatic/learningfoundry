<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  Story I.bb: surfaces the `WasmAssetMissingError` recovery state.
  Reads the layout-level `dbInit` store; renders only when init failed
  with a missing /sql-wasm.wasm asset. Refresh CTA reloads the page so
  a freshly-served wasm has a chance to satisfy the precheck.
-->
<script lang="ts">
	import AlertTriangle from 'lucide-svelte/icons/triangle-alert';
	import { dbInit } from '$lib/stores/db-init.js';

	function handleRefresh() {
		if (typeof location !== 'undefined') location.reload();
	}
</script>

{#if $dbInit === 'wasm-missing'}
	<div
		role="status"
		aria-live="polite"
		data-testid="recording-paused-banner"
		class="flex items-center gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900"
	>
		<AlertTriangle size={18} class="shrink-0 text-amber-600" aria-hidden="true" />
		<span class="flex-1">
			<strong class="font-medium">Progress recording is paused.</strong>
			Your activity in this session will not be saved. Try refreshing to retry.
		</span>
		<button
			type="button"
			onclick={handleRefresh}
			class="rounded-md border border-amber-300 bg-white px-3 py-1 text-amber-900 hover:bg-amber-100"
		>
			Refresh
		</button>
	</div>
{/if}
