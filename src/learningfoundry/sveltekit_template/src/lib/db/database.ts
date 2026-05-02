// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * sql.js database wrapper with per-user IndexedDB persistence.
 *
 * The WASM binary is served from /sql-wasm.wasm (copied to static/ by the
 * postinstall script). The database is persisted to IndexedDB under the
 * key `db:${userId}` so each learner's progress is partitioned. The
 * `userId` is a UUID v4 stored in `localStorage` (Story I.x).
 *
 * Pre-v0.58.0 progress lived under the unkeyed `db` IDB record. On first
 * init for any userId the legacy `db` record is migrated under
 * `db:${userId}` and removed — see `#migrateLegacyKey`.
 */
import type { Database as SqlDatabase, SqlJsStatic } from 'sql.js';
import { getUserId } from './user-id.js';

const IDB_DB_NAME = 'learningfoundry';
const IDB_STORE_NAME = 'progress';
const LEGACY_KEY = 'db';

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
	#userId: string | null;
	#userIdPromise: Promise<string> | null = null;
	#db: SqlDatabase | null = null;
	#SQL: SqlJsStatic | null = null;
	#dbInitPromise: Promise<SqlDatabase> | null = null;
	#sqlInitPromise: Promise<SqlJsStatic> | null = null;

	/**
	 * @param userId Optional. Tests pass an explicit value for partition
	 * isolation; production omits it and the class lazy-resolves via
	 * `getUserId()` on first method call.
	 */
	constructor(userId?: string) {
		this.#userId = userId ?? null;
	}

	/** Return the underlying sql.js Database, initialising it on first call. */
	async getDb(): Promise<SqlDatabase> {
		if (this.#db) return this.#db;
		// Memoise the init promise so concurrent callers share one
		// initialisation (Story I.v fix).
		if (!this.#dbInitPromise) {
			this.#dbInitPromise = (async () => {
				const userId = await this.#ensureUserId();
				const SQL = await this.#initSqlJs();
				await this.#migrateLegacyKey(userId);
				const saved = await this.#loadFromIdb(userId);
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
		const userId = await this.#ensureUserId();
		const data = this.#db.export();
		await this.#saveToIdb(userId, data);
	}

	async #ensureUserId(): Promise<string> {
		if (this.#userId !== null) return this.#userId;
		if (!this.#userIdPromise) {
			this.#userIdPromise = getUserId().then((id) => {
				this.#userId = id;
				return id;
			});
		}
		return this.#userIdPromise;
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

	async #loadFromIdb(userId: string): Promise<Uint8Array | null> {
		const idb = await this.#openIdb();
		return new Promise((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readonly');
			const req = tx.objectStore(IDB_STORE_NAME).get(`db:${userId}`);
			req.onsuccess = () => resolve((req.result as Uint8Array) ?? null);
			req.onerror = () => reject(req.error);
		});
	}

	async #saveToIdb(userId: string, data: Uint8Array): Promise<void> {
		const idb = await this.#openIdb();
		return new Promise((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readwrite');
			tx.objectStore(IDB_STORE_NAME).put(data, `db:${userId}`);
			tx.oncomplete = () => resolve();
			tx.onerror = () => reject(tx.error);
		});
	}

	/**
	 * One-shot legacy migration. If pre-v0.58.0 progress exists under the
	 * unkeyed `db` IDB record, copy it to `db:${userId}` (only if the
	 * per-user record doesn't already exist) and delete the legacy
	 * record. Idempotent — second call is a no-op.
	 */
	async #migrateLegacyKey(userId: string): Promise<void> {
		const idb = await this.#openIdb();
		const legacy = await new Promise<Uint8Array | null>((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readonly');
			const req = tx.objectStore(IDB_STORE_NAME).get(LEGACY_KEY);
			req.onsuccess = () => resolve((req.result as Uint8Array) ?? null);
			req.onerror = () => reject(req.error);
		});
		if (!legacy) return;

		const existing = await new Promise<Uint8Array | null>((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readonly');
			const req = tx.objectStore(IDB_STORE_NAME).get(`db:${userId}`);
			req.onsuccess = () => resolve((req.result as Uint8Array) ?? null);
			req.onerror = () => reject(req.error);
		});

		await new Promise<void>((resolve, reject) => {
			const tx = idb.transaction(IDB_STORE_NAME, 'readwrite');
			const store = tx.objectStore(IDB_STORE_NAME);
			// Only adopt the legacy bytes if no per-user record exists yet —
			// otherwise the per-user data wins and the legacy record is
			// just cleaned up.
			if (!existing) {
				store.put(legacy, `db:${userId}`);
			}
			store.delete(LEGACY_KEY);
			tx.oncomplete = () => resolve();
			tx.onerror = () => reject(tx.error);
		});
	}
}
