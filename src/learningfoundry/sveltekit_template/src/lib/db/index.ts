// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { Database } from './database.js';
import { ProgressRepo } from './progress.js';

export { Database } from './database.js';
export { ProgressRepo } from './progress.js';

export const database = new Database();
export const progressRepo = new ProgressRepo(database);
