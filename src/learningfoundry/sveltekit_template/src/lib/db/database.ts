// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * sql.js database initialisation with IndexedDB persistence.
 *
 * The WASM binary is served from /sql-wasm.wasm (copied to static/ by the
 * postinstall script). The database is persisted to IndexedDB under the key
 * "learningfoundry-progress" so progress survives page refreshes.
 */
import type { Database, SqlJsStatic } from 'sql.js';

const IDB_DB_NAME = 'learningfoundry';
const IDB_STORE_NAME = 'progress';
const IDB_KEY = 'db';

let _db: Database | null = null;
let _SQL: SqlJsStatic | null = null;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Return the singleton Database, initialising it on first call. */
export async function getDb(): Promise<Database> {
	if (_db) return _db;
	_SQL = await initSqlJs();
	const saved = await loadFromIdb();
	_db = saved ? new _SQL.Database(saved) : new _SQL.Database();
	createSchema(_db);
	return _db;
}

/** Persist the current database state to IndexedDB. */
export async function persistDb(): Promise<void> {
	if (!_db) return;
	const data = _db.export();
	await saveToIdb(data);
}

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

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

function createSchema(db: Database): void {
	db.run(DDL);
}

// ---------------------------------------------------------------------------
// sql.js WASM loader
// ---------------------------------------------------------------------------

async function initSqlJs(): Promise<SqlJsStatic> {
	if (_SQL) return _SQL;
	// Dynamic import keeps the WASM module out of the main bundle.
	const initSqlJsFn = (await import('sql.js')).default;
	return initSqlJsFn({ locateFile: () => '/sql-wasm.wasm' });
}

// ---------------------------------------------------------------------------
// IndexedDB helpers
// ---------------------------------------------------------------------------

function openIdb(): Promise<IDBDatabase> {
	return new Promise((resolve, reject) => {
		const req = indexedDB.open(IDB_DB_NAME, 1);
		req.onupgradeneeded = () => {
			req.result.createObjectStore(IDB_STORE_NAME);
		};
		req.onsuccess = () => resolve(req.result);
		req.onerror = () => reject(req.error);
	});
}

async function loadFromIdb(): Promise<Uint8Array | null> {
	const idb = await openIdb();
	return new Promise((resolve, reject) => {
		const tx = idb.transaction(IDB_STORE_NAME, 'readonly');
		const req = tx.objectStore(IDB_STORE_NAME).get(IDB_KEY);
		req.onsuccess = () => resolve((req.result as Uint8Array) ?? null);
		req.onerror = () => reject(req.error);
	});
}

async function saveToIdb(data: Uint8Array): Promise<void> {
	const idb = await openIdb();
	return new Promise((resolve, reject) => {
		const tx = idb.transaction(IDB_STORE_NAME, 'readwrite');
		tx.objectStore(IDB_STORE_NAME).put(data, IDB_KEY);
		tx.oncomplete = () => resolve();
		tx.onerror = () => reject(tx.error);
	});
}
