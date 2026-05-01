// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * LessonView block-tracking helpers.
 *
 * Extracted from `LessonView.svelte` so the completion logic can be
 * unit-tested without mounting the Svelte component.
 */

import type { ContentBlock } from '$lib/types/index.js';

/**
 * Stable identity key for a content block. Used as the `{#each}` key so
 * child components (notably `VideoBlock`, which holds an iframe player)
 * tear down and re-mount when the underlying content changes rather
 * than being reused across lessons with stale state.
 */
export function contentBlockKey(block: ContentBlock, index: number): string {
	if (block.ref) return `${block.type}:${block.ref}`;
	const url = (block.content as { url?: unknown })?.url;
	if (typeof url === 'string') return `${block.type}:${url}`;
	return `${block.type}-${index}`;
}

export interface BlockTracker {
	/** Record a block as complete. Returns true if this was the final block. */
	markBlockComplete(blockIndex: number): boolean;
	/** Number of completed blocks so far. */
	readonly completedCount: number;
	/** Whether all blocks are complete. */
	readonly allComplete: boolean;
}

/**
 * Create a block tracker for a lesson with `totalBlocks` content blocks.
 *
 * If `preComplete` is true, the lesson was already marked complete in the DB
 * on a previous visit — all blocks are considered done from the start.
 *
 * Zero-block lessons are immediately complete.
 */
export function createBlockTracker(
	totalBlocks: number,
	preComplete: boolean = false
): BlockTracker {
	const completed = new Set<number>();
	const immediate = totalBlocks === 0 || preComplete;

	return {
		markBlockComplete(blockIndex: number): boolean {
			if (immediate) return true;
			completed.add(blockIndex);
			return completed.size === totalBlocks;
		},

		get completedCount(): number {
			return immediate ? totalBlocks : completed.size;
		},

		get allComplete(): boolean {
			return immediate || completed.size === totalBlocks;
		}
	};
}
