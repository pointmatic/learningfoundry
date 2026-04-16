<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { renderMarkdown } from '$lib/utils/markdown.js';
	import type { TextContent } from '$lib/types/index.js';

	interface Props {
		content: TextContent;
	}
	let { content }: Props = $props();

	const html = $derived(renderMarkdown(content.markdown));
</script>

<div class="prose prose-slate max-w-none">
	{@html html}
</div>
