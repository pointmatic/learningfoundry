// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story K.f — `<ExerciseBlock>` ready-state renderer (manual-completion).
// Renders sections / expected_outputs / hints / environment, composes image
// URLs from the runtime `id`, and on "Mark as Complete" persists
// `exercise_status` via progressRepo and fires the upward callbacks. Stub
// status still renders the placeholder card.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/svelte';
import ExerciseBlock from './ExerciseBlock.svelte';
import type { ExerciseContent } from '$lib/types/index.js';

// vite.config.ts sets `globals: false`, so testing-library's auto-cleanup
// (which hooks the global afterEach) is inactive — clean up explicitly so
// renders don't accumulate in document.body across `it` blocks.
afterEach(cleanup);

const { updateExerciseStatusMock } = vi.hoisted(() => ({
	updateExerciseStatusMock: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		updateExerciseStatus: updateExerciseStatusMock
	}
}));

function readyContent(overrides: Partial<ExerciseContent> = {}): ExerciseContent {
	return {
		type: 'exercise',
		source: 'nbfoundry',
		ref: 'exercises/mod-01-exercise-01.yml',
		id: 'mod-01-exercise-01',
		status: 'ready',
		title: 'Train a tiny classifier',
		instructions: '<p>Build and train a small model.</p>',
		sections: [
			{
				title: 'Data Loading',
				description: '<p>Load the dataset.</p>',
				code: 'import torch',
				editable: false
			},
			{
				title: 'Define Your Model',
				description: '<p>Your turn.</p>',
				code: '# YOUR CODE HERE',
				editable: true
			}
		],
		expected_outputs: [
			{
				description: 'Training loss curve',
				type: 'image',
				path: 'expected_loss_curve.png',
				alt: 'Training loss decreasing across 20 epochs'
			},
			{
				description: 'Test accuracy threshold',
				type: 'text',
				content: 'Expected: accuracy >= 0.65'
			}
		],
		assets: ['expected_loss_curve.png'],
		hints: ['Start with nn.Conv2d.', 'Flatten before the dense layer.'],
		environment: {
			python_version: '3.12',
			dependencies: ['torch', 'torchvision'],
			setup_instructions: 'Run pip install -r requirements.txt locally.'
		},
		...overrides
	};
}

describe('ExerciseBlock — ready renderer (manual completion)', () => {
	it('renders each section title and code scaffold', () => {
		const { getByText } = render(ExerciseBlock, { props: { content: readyContent() } });
		expect(getByText('Data Loading')).toBeTruthy();
		expect(getByText('Define Your Model')).toBeTruthy();
		expect(getByText('import torch')).toBeTruthy();
		expect(getByText('# YOUR CODE HERE')).toBeTruthy();
	});

	it('composes the image expected-output URL from the runtime id', () => {
		const { container } = render(ExerciseBlock, { props: { content: readyContent() } });
		const img = container.querySelector('img');
		expect(img).not.toBeNull();
		expect(img?.getAttribute('src')).toBe(
			'/exercises/mod-01-exercise-01/expected_loss_curve.png'
		);
		expect(img?.getAttribute('alt')).toBe('Training loss decreasing across 20 epochs');
		expect(img?.getAttribute('loading')).toBe('lazy');
	});

	it('renders text expected-output content inline', () => {
		const { getByText } = render(ExerciseBlock, { props: { content: readyContent() } });
		expect(getByText('Expected: accuracy >= 0.65')).toBeTruthy();
	});

	it('renders hints', () => {
		const { getByText } = render(ExerciseBlock, { props: { content: readyContent() } });
		expect(getByText('Start with nn.Conv2d.')).toBeTruthy();
	});

	it('surfaces environment setup instructions', () => {
		const { getByText } = render(ExerciseBlock, { props: { content: readyContent() } });
		expect(getByText(/Run pip install -r requirements.txt locally\./)).toBeTruthy();
	});

	it('Mark as Complete persists exercise_status and fires both callbacks', async () => {
		updateExerciseStatusMock.mockClear();
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

	it('renders the placeholder (no sections, no complete button) for stub status', () => {
		const { queryByText, queryByRole } = render(ExerciseBlock, {
			props: { content: readyContent({ status: 'stub', sections: [], expected_outputs: [] }) }
		});
		expect(queryByText('Data Loading')).toBeNull();
		expect(queryByRole('button', { name: /mark as complete/i })).toBeNull();
	});
});
