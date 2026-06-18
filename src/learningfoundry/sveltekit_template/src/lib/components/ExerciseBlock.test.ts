// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story K.j.1 — `<ExerciseBlock>` ready-state banner (Option C). The static
// sections/expected_outputs renderer is retired: a `ready` exercise now shows
// a banner that drives the `learningfoundry launch` CLI — the copy-able launch
// command, an "Open Exercise" link to the local marimo server, "Mark as
// Complete" (persists `exercise_status`, fires the upward callbacks), and a
// completed slate derived on load from the persisted status. Stub status still
// renders the placeholder card.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, fireEvent, cleanup, waitFor } from '@testing-library/svelte';
import ExerciseBlock from './ExerciseBlock.svelte';
import type { ExerciseContent } from '$lib/types/index.js';

// vite.config.ts sets `globals: false`, so testing-library's auto-cleanup
// (which hooks the global afterEach) is inactive — clean up explicitly so
// renders don't accumulate in document.body across `it` blocks.
afterEach(cleanup);

const { updateExerciseStatusMock, getExerciseStatusMock } = vi.hoisted(() => ({
	updateExerciseStatusMock: vi.fn().mockResolvedValue(undefined),
	getExerciseStatusMock: vi.fn().mockResolvedValue(null)
}));

vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		updateExerciseStatus: updateExerciseStatusMock,
		getExerciseStatus: getExerciseStatusMock
	}
}));

const writeTextMock = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
	updateExerciseStatusMock.mockClear();
	getExerciseStatusMock.mockClear();
	getExerciseStatusMock.mockResolvedValue(null);
	writeTextMock.mockClear();
	Object.defineProperty(navigator, 'clipboard', {
		value: { writeText: writeTextMock },
		configurable: true,
		writable: true
	});
});

function readyContent(overrides: Partial<ExerciseContent> = {}): ExerciseContent {
	return {
		type: 'exercise',
		source: 'nbfoundry',
		ref: 'exercises/mod-01-exercise-01.yml',
		id: 'mod-01-exercise-01',
		status: 'ready',
		title: 'Train a tiny classifier',
		description: '<p>Build and train a small model.</p>',
		hints: ['Start with nn.Conv2d.', 'Flatten before the dense layer.'],
		mode: 'edit',
		port: 2718,
		environment: {
			python_version: '3.12',
			dependencies: ['torch', 'torchvision'],
			setup_instructions: 'Run pip install -r requirements.txt locally.'
		},
		...overrides
	};
}

describe('ExerciseBlock — ready banner (Option C launch flow)', () => {
	it('shows the exact `learningfoundry launch <id>` command', () => {
		const { getByText } = render(ExerciseBlock, { props: { content: readyContent() } });
		expect(getByText('learningfoundry launch mod-01-exercise-01')).toBeTruthy();
	});

	it('Copy writes the exact launch command to the clipboard', async () => {
		const { getByRole, findByText } = render(ExerciseBlock, {
			props: { content: readyContent() }
		});
		await fireEvent.click(getByRole('button', { name: /copy/i }));
		expect(writeTextMock).toHaveBeenCalledWith('learningfoundry launch mod-01-exercise-01');
		// Transient confirmation.
		expect(await findByText(/copied/i)).toBeTruthy();
	});

	it('Open Exercise links to the local marimo server in a new tab', () => {
		const { getByRole } = render(ExerciseBlock, { props: { content: readyContent() } });
		const link = getByRole('link', { name: /open exercise/i });
		expect(link.getAttribute('href')).toBe('http://localhost:2718');
		expect(link.getAttribute('target')).toBe('_blank');
	});

	it('renders the description and hints', () => {
		const { getByText } = render(ExerciseBlock, { props: { content: readyContent() } });
		expect(getByText('Build and train a small model.')).toBeTruthy();
		expect(getByText('Start with nn.Conv2d.')).toBeTruthy();
	});

	it('Mark as Complete persists exercise_status and fires both callbacks', async () => {
		const oncomplete = vi.fn();
		const onexercisecomplete = vi.fn();
		const { getByRole } = render(ExerciseBlock, {
			props: { content: readyContent(), oncomplete, onexercisecomplete }
		});
		await fireEvent.click(getByRole('button', { name: /mark as complete/i }));

		expect(updateExerciseStatusMock).toHaveBeenCalledWith('mod-01-exercise-01', 'complete');
		expect(oncomplete).toHaveBeenCalledWith({
			exerciseRef: 'mod-01-exercise-01',
			status: 'completed'
		});
		expect(onexercisecomplete).toHaveBeenCalledOnce();
	});

	it('derives the completed slate on load from the persisted status', async () => {
		getExerciseStatusMock.mockResolvedValue('complete');
		const { findByText, queryByRole } = render(ExerciseBlock, {
			props: { content: readyContent() }
		});
		expect(getExerciseStatusMock).toHaveBeenCalledWith('mod-01-exercise-01');
		expect(await findByText(/exercise complete/i)).toBeTruthy();
		// Already complete → no Mark button.
		await waitFor(() =>
			expect(queryByRole('button', { name: /mark as complete/i })).toBeNull()
		);
	});

	it('renders the placeholder (no launch command, no complete button) for stub status', () => {
		const { queryByText, queryByRole } = render(ExerciseBlock, {
			props: { content: readyContent({ status: 'stub', mode: undefined, port: undefined }) }
		});
		expect(queryByText(/learningfoundry launch/)).toBeNull();
		expect(queryByRole('button', { name: /mark as complete/i })).toBeNull();
	});
});
