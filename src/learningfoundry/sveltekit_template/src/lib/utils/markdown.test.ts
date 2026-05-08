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

// ---------------------------------------------------------------------------
// Story J.d.1 — tutorial-scaffold container directives. The marked extension
// in `markdown-directives.ts` recognises three named directives and wraps
// each in a `<div class="lf-directive lf-directive-<name>">` so the CSS in
// `app.css` can style the worked → faded → independent-practice progression.
// ---------------------------------------------------------------------------

describe('renderMarkdown — container directives (Story J.d.1)', () => {
	it('wraps `::: worked-example` in lf-directive-worked-example', () => {
		const html = renderMarkdown(
			'::: worked-example\nCompute output shape: 30×30.\n:::'
		);
		expect(html).toContain('class="lf-directive lf-directive-worked-example"');
		expect(html).toContain('data-directive="worked-example"');
		expect(html).toContain('Compute output shape');
	});

	it('wraps `::: faded-example` in lf-directive-faded-example', () => {
		const html = renderMarkdown(
			'::: faded-example\nWhat is the output shape for 64×64?\n:::'
		);
		expect(html).toContain('class="lf-directive lf-directive-faded-example"');
		expect(html).toContain('data-directive="faded-example"');
	});

	it('wraps `::: independent-practice` in lf-directive-independent-practice', () => {
		const html = renderMarkdown(
			'::: independent-practice\nDesign a Conv2d that outputs 14×14.\n:::'
		);
		expect(html).toContain(
			'class="lf-directive lf-directive-independent-practice"'
		);
		expect(html).toContain('data-directive="independent-practice"');
	});

	it('renders inner markdown — headings, lists, and emphasis pass through', () => {
		const md =
			'::: worked-example\n' +
			'### Step 1\n\n' +
			'- compute *width*\n' +
			'- compute *height*\n' +
			':::';
		const html = renderMarkdown(md);
		expect(html).toContain('lf-directive-worked-example');
		expect(html).toContain('<h3');
		expect(html).toContain('<ul');
		expect(html).toContain('<em>width</em>');
	});

	it('renders three back-to-back directives as three sibling wrappers', () => {
		const md =
			'::: worked-example\nA\n:::\n\n' +
			'::: faded-example\nB\n:::\n\n' +
			'::: independent-practice\nC\n:::';
		const html = renderMarkdown(md);
		expect(html).toContain('lf-directive-worked-example');
		expect(html).toContain('lf-directive-faded-example');
		expect(html).toContain('lf-directive-independent-practice');
	});

	it('does not match unknown directive names — they pass through', () => {
		const html = renderMarkdown('::: tip\nA helpful note.\n:::');
		expect(html).not.toContain('lf-directive');
		// The literal `:::` survives in the rendered HTML somewhere — exact
		// recovery shape is up to marked's default block lexer; we only
		// guarantee the wrapper isn't created.
	});

	it('does not match `:::` inside a fenced code block', () => {
		const md = '```\n::: worked-example\nfake\n:::\n```';
		const html = renderMarkdown(md);
		expect(html).not.toContain('lf-directive');
		// The `:::` literals must survive inside the rendered <code>.
		expect(html).toContain(':::');
	});
});
