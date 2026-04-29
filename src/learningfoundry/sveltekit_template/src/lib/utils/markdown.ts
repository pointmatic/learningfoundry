// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { marked } from 'marked';
import markedKatex from 'marked-katex-extension';

// Register the KaTeX extension once at module load. Supports both inline
// `$...$` and display `$$...$$` math, rendered to HTML at parse time using
// the KaTeX engine. Stylesheet is imported in `src/app.css`.
marked.use(markedKatex({ throwOnError: false }));

/**
 * Convert a markdown string to sanitised HTML.
 * Returns an empty string for blank/null input.
 */
export function renderMarkdown(markdown: string | null | undefined): string {
	if (!markdown?.trim()) return '';
	const html = marked.parse(markdown, { async: false });
	return html as string;
}
