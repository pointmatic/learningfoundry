<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  Dispatcher component — renders the correct block component based on `block.type`.
  Forwards child completion events upward as `onblockcomplete(blockIndex)`.
-->
<script lang="ts">
	import type { ContentBlock, QuizScore } from '$lib/types/index.js';
	import type {
		ExerciseContent,
		QuizManifest,
		TextContent,
		VideoContent,
		VisualizationContent
	} from '$lib/types/index.js';
	import ExerciseBlock from './ExerciseBlock.svelte';
	import PlaceholderBlock from './PlaceholderBlock.svelte';
	import QuizBlock from './QuizBlock.svelte';
	import TextBlock from './TextBlock.svelte';
	import VideoBlock from './VideoBlock.svelte';
	import VisualizationBlock from './VisualizationBlock.svelte';

	interface Props {
		block: ContentBlock;
		blockIndex: number;
		onblockcomplete?: (blockIndex: number) => void;
		onquizcomplete?: (score: QuizScore) => void;
	}
	let { block, blockIndex, onblockcomplete, onquizcomplete }: Props = $props();

	function handleBlockComplete() {
		onblockcomplete?.(blockIndex);
	}
</script>

{#if block.type === 'text'}
	<TextBlock content={block.content as TextContent} ontextcomplete={handleBlockComplete} />
{:else if block.type === 'video'}
	<VideoBlock content={block.content as VideoContent} onvideocomplete={handleBlockComplete} />
{:else if block.type === 'quiz'}
	<QuizBlock
		manifest={block.content as QuizManifest}
		quizRef={block.ref ?? ''}
		passThreshold={(block.content as QuizManifest).passThreshold ?? 0.0}
		oncomplete={onquizcomplete}
		onquizcomplete={handleBlockComplete}
	/>
{:else if block.type === 'exercise'}
	<ExerciseBlock content={block.content as ExerciseContent} />
{:else if block.type === 'visualization'}
	<VisualizationBlock content={block.content as VisualizationContent} />
{:else}
	<PlaceholderBlock label="Unknown block type: {block.type}" />
{/if}
