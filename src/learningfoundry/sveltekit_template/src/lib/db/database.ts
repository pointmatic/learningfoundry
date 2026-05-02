// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * sql.js database wrapper with IndexedDB persistence.
 *
 * The WASM binary is served from /sql-wasm.wasm (copied to static/ by the
 * postinstall script). The database is persisted to IndexedDB under the
 * key "learningfoundry-progress" so progress survives page refreshes.
 */
import type { Database as SqlDatabase, SqlJsStatic } from 'sql.js';

const IDB_DB_NAME = 'learningfoundry';
const IDB_STORE_NAME = 'progress';
const IDB_KEY = 'db';

const DDL = `
CREATE TABLE IF NOT EXISTS lesson_progress (
  module_id   TEXT NOT NULL,
  lesson_id   TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'not_started',
  completed_at TEXT,
  PRIMARY KEY (module_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS quiz_scores (
  quiz_ref      TEXT NOT NULL,
  score         INTEGER NOT NULL,
  max_score     INTEGER NOT NULL,
  question_count INTEGER NOT NULL,
  completed_at  TEXT NOT NULL,
  PRIMARY KEY (quiz_ref)
);

CREATE TABLE IF NOT EXISTS exercise_status (
  exercise_ref  TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'not_started',
  updated_at    TEXT NOT NULL,
  PRIMARY KEY (exercise_ref)
);
`;

export class Database {
	#db: SqlDatabase | null = null;
	#SQL: SqlJsStatic | null = null;
	#dbInitPromise: Promise<SqlDatabase> | null = null;
	#sqlInitPromise: Promise<SqlJsStatic> | null = null;

	/** Return the underlying sql.js Database, initialising it on first call. */
	async getDb(): Promise<SqlDatabase> {
		if (this.#db) return this.#db;
		// Memoise the init promise so concurrent callers share one
		// initialisation (Story I.v fix; preserved here as a method).
		if (!this.#dbInitPromise) {
			this.#dbInitPromise = (async () => {
				const SQL = await this.#initSqlJs();
				const saved = await this.#loadFromIdb();
				const db = saved ? new SQL.Database(saved) : new SQL.Database();
				db.run(DDL);
				this.#db = db;
				return db;
			})();
		}
		return this.#dbInitPromise;
	}

	/** Persist the current database state to IndexedDB. */
	async persist(): Promise<void> {
		if (!this.#db) return;
		const data = this.#db.export();
		await this.#saveToIdb(data);
	}

	async #initSqlJs(): Promise<SqlJsStatic> {
		if (this.#SQL) return this.#SQL;
		if (!this.#sqlInitPromise) {
			this.#sqlInitPromise = (async () => {
				// Dynamic import keeps the WASM module out of the main bundle.
				const initSqlJsFn = (await import('sql.js')).default;
				const SQL = await initSqlJsFn({ locateFile: () => '/sql-wasm.wasm' });
				this.#SQL = SQL;
				return SQL;
			})();
		}
		return this.#sqlInitPromise;
	}

	#openIdb(): Promise<IDBDatabase> {
		return new Promise((resolve, reject) => {
			const req = indexedDB.open(IDB_DB_NAME, 1);
			req.onupgradeneeded = () => {
				req.result.createObjectStore(IDB_STORE_NAME);
			};
			req.onsuccess = () => resolve(req.result);
			req.onerror = () => reject(req.error);
		});
	}

	async #loadFromIdb(): Promise<Uint8Array | null> {
		const idb = await this.#openIdb();
		return new Promise((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readonly');
			const req = tx.objectStore(IDB_STORE_NAME).get(IDB_KEY);
			req.onsuccess = () => resolve((req.result as Uint8Array) ?? null);
			req.onerror = () => reject(req.error);
		});
	}

	async #saveToIdb(data: Uint8Array): Promise<void> {
		const idb = await this.#openIdb();
		return new Promise((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readwrite');
			tx.objectStore(IDB_STORE_NAME).put(data, IDB_KEY);
			tx.oncomplete = () => resolve();
			tx.onerror = () => reject(tx.error);
		});
	}
}
