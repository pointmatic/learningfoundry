// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { marked } from 'marked';
import markedKatex from 'marked-katex-extension';

// Register the KaTeX extension once at module load. Supports both inline
// `$...$` and display `$$...$$` math, rendered to HTML at parse time using
// the KaTeX engine. Stylesheet is imported in `src/app.css`.
marked.use(markedKatex({ throwOnError: false }));

// `marked-katex-extension`'s upstream block regex
// (`/^(\${1,2})\n(...)\n\1(?:\n|$)/`) requires the `$$` delimiter lines to
// have no adjacent whitespace. Real-world markdown frequently violates this
// (editors, copy-paste from PDFs/chat). Collapse any line that is *only*
// whitespace + `$$` + whitespace down to bare `$$` so block math renders
// reliably. Inline math (`$x$`) and the markdown "trailing two spaces =
// `<br>`" rule on regular text are unaffected.
const DELIMITER_LINE_RE = /^[ \t]*(\$\$)[ \t]*$/gm;

/**
 * Convert a markdown string to sanitised HTML.
 * Returns an empty string for blank/null input.
 */
export function renderMarkdown(markdown: string | null | undefined): string {
	if (!markdown?.trim()) return '';
	const normalised = markdown.replace(DELIMITER_LINE_RE, '$1');
	const html = marked.parse(normalised, { async: false });
	return html as string;
}
