// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Tutorial-scaffold container directives for `marked` (Story J.d.1).
//
// Recognises three named container directives in lesson markdown:
//   ::: worked-example          → filled card
//   ::: faded-example           → outlined dim card
//   ::: independent-practice    → challenge prompt
//
// Each directive opens with `::: <name>` on its own line and closes with
// `:::` on its own line. The body is itself markdown — nested headings,
// lists, math, and inline emphasis all work because the inner body is
// re-lexed with `lexer.blockTokens(...)`.
//
// Unknown directive names (e.g. `::: tip`) deliberately do not match —
// they pass through to the rest of the markdown pipeline as plain text
// so Story J.d.2's lint pass owns the "did you mean..." surface.
import type { MarkedExtension, Tokens } from 'marked';

const KNOWN_DIRECTIVES = ['worked-example', 'faded-example', 'independent-practice'] as const;
type KnownDirective = (typeof KNOWN_DIRECTIVES)[number];

interface DirectiveToken extends Tokens.Generic {
	type: 'directive';
	raw: string;
	directive: KnownDirective;
	tokens: Tokens.Generic[];
}

const DIRECTIVE_RE =
	/^:::[ \t]+(worked-example|faded-example|independent-practice)[ \t]*\n([\s\S]*?)\n:::[ \t]*(?=\n|$)/;

/**
 * Returns a `marked` extension package that recognises tutorial-scaffold
 * container directives. Register once at module load via
 * `marked.use(containerDirectives())`.
 */
export function containerDirectives(): MarkedExtension {
	return {
		extensions: [
			{
				name: 'directive',
				level: 'block',
				start(src: string): number | undefined {
					const idx = src.search(/(^|\n):::[ \t]/);
					return idx === -1 ? undefined : idx;
				},
				tokenizer(src: string): DirectiveToken | undefined {
					const match = DIRECTIVE_RE.exec(src);
					if (!match) return undefined;
					const directive = match[1] as KnownDirective;
					const body = match[2];
					const inner: Tokens.Generic[] = [];
					this.lexer.blockTokens(body, inner);
					return {
						type: 'directive',
						raw: match[0],
						directive,
						tokens: inner
					};
				},
				renderer(token): string {
					const t = token as DirectiveToken;
					const inner = this.parser.parse(t.tokens);
					return (
						`<div class="lf-directive lf-directive-${t.directive}" ` +
						`data-directive="${t.directive}">${inner}</div>`
					);
				}
			}
		]
	};
}
