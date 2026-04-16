<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	interface Props {
		label?: string;
		message?: string;
	}
	let { label = 'Content', message = 'This content is coming soon.' }: Props = $props();
</script>

<div class="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center">
	<p class="text-sm font-medium text-gray-500">{label}</p>
	<p class="mt-1 text-xs text-gray-400">{message}</p>
</div>
