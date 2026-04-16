// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { marked } from 'marked';

/**
 * Convert a markdown string to sanitised HTML.
 * Returns an empty string for blank/null input.
 */
export function renderMarkdown(markdown: string | null | undefined): string {
	if (!markdown?.trim()) return '';
	const html = marked.parse(markdown, { async: false });
	return html as string;
}
