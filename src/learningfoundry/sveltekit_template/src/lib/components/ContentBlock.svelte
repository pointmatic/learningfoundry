<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  Dispatcher component — renders the correct block component based on `block.type`.
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
		onquizcomplete?: (score: QuizScore) => void;
	}
	let { block, onquizcomplete }: Props = $props();
</script>

{#if block.type === 'text'}
	<TextBlock content={block.content as TextContent} />
{:else if block.type === 'video'}
	<VideoBlock content={block.content as VideoContent} />
{:else if block.type === 'quiz'}
	<QuizBlock
		manifest={block.content as QuizManifest}
		quizRef={block.ref ?? ''}
		oncomplete={onquizcomplete}
	/>
{:else if block.type === 'exercise'}
	<ExerciseBlock content={block.content as ExerciseContent} />
{:else if block.type === 'visualization'}
	<VisualizationBlock content={block.content as VisualizationContent} />
{:else}
	<PlaceholderBlock label="Unknown block type: {block.type}" />
{/if}
