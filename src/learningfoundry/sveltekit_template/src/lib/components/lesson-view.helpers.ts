// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * LessonView block-tracking helpers.
 *
 * Extracted from `LessonView.svelte` so the completion logic can be
 * unit-tested without mounting the Svelte component.
 */

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
