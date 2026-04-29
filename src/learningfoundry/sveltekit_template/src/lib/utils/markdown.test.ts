// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { renderMarkdown } from './markdown.js';

describe('renderMarkdown', () => {
	it('returns empty string for null/undefined/blank input', () => {
		expect(renderMarkdown(null)).toBe('');
		expect(renderMarkdown(undefined)).toBe('');
		expect(renderMarkdown('')).toBe('');
		expect(renderMarkdown('   \n\t')).toBe('');
	});

	it('renders headings as <h1>/<h2>/<h3>', () => {
		const html = renderMarkdown('# H1\n\n## H2\n\n### H3');
		expect(html).toContain('<h1');
		expect(html).toContain('<h2');
		expect(html).toContain('<h3');
		expect(html).toContain('H1');
		expect(html).toContain('H2');
		expect(html).toContain('H3');
	});

	it('renders fenced code blocks', () => {
		const html = renderMarkdown('```python\nprint("hi")\n```');
		expect(html).toContain('<pre');
		expect(html).toContain('<code');
		expect(html).toContain('print');
	});

	it('renders inline math via $...$', () => {
		const html = renderMarkdown('Euler said $e^{i\\pi} + 1 = 0$.');
		// KaTeX inline output wraps the formula in <span class="katex">…</span>
		// (without the `katex-display` wrapper used for block-level math).
		expect(html).toContain('class="katex"');
		// The literal `$...$` delimiters should be consumed by the parser.
		expect(html).not.toContain('$e^{i\\pi}');
	});

	it('renders display math via $$...$$', () => {
		const md = '$$\n\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n$$';
		const html = renderMarkdown(md);
		// Display math gets the `katex-display` wrapper. KaTeX preserves the
		// source LaTeX inside a MathML <annotation> tag for accessibility,
		// so we don't assert that the source is absent — only that the
		// rendered HTML structure is present.
		expect(html).toContain('katex-display');
		expect(html).toContain('class="katex"');
	});

	it('does not throw on malformed LaTeX (throwOnError: false)', () => {
		expect(() => renderMarkdown('$\\unknownmacro{x}$')).not.toThrow();
	});

	// Real-world editors and copy-paste from PDFs/docs frequently leave
	// stray whitespace on the delimiter-only lines of a `$$ … $$` block.
	// `marked-katex-extension`'s upstream block regex requires the closing
	// `$$` to be followed immediately by `\n` or end-of-string and the
	// opening `$$` to be followed immediately by `\n`, so any padding
	// silently breaks math rendering. `renderMarkdown` normalises these
	// delimiter-only lines so the block is still recognised.

	it('renders display math when the closing $$ has trailing whitespace', () => {
		const md = '$$\n\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n$$   ';
		const html = renderMarkdown(md);
		expect(html).toContain('katex-display');
		expect(html).toContain('class="katex"');
	});

	it('renders display math when the closing $$ has leading whitespace', () => {
		const md = '$$\n\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n   $$';
		const html = renderMarkdown(md);
		expect(html).toContain('katex-display');
		expect(html).toContain('class="katex"');
	});

	it('renders display math when the opening $$ has trailing whitespace', () => {
		const md = '$$   \n\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n$$';
		const html = renderMarkdown(md);
		expect(html).toContain('katex-display');
		expect(html).toContain('class="katex"');
	});
});
