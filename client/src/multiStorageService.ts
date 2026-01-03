/**
 * Multi-Storage Service
 * 
 * Stores data redundantly in localStorage, cookies, and IndexedDB.
 * If one storage is cleared, data can be recovered from others.
 */

// IndexedDB configuration
const DB_NAME = 'google_auth_storage';
const DB_VERSION = 1;
const STORE_NAME = 'keyvalue';

let dbPromise: Promise<IDBDatabase> | null = null;

/**
 * Initialize IndexedDB
 */
function getDB(): Promise<IDBDatabase> {
    if (dbPromise) return dbPromise;

    dbPromise = new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = (event.target as IDBOpenDBRequest).result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME);
            }
        };
    });

    return dbPromise;
}

/**
 * Set a cookie with expiry
 */
function setCookie(key: string, value: string, days: number = 7): void {
    try {
        const expires = new Date();
        expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
        document.cookie = `${encodeURIComponent(key)}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
    } catch (e) {
        console.warn('[MultiStorage] Failed to set cookie:', e);
    }
}

/**
 * Get a cookie value
 */
function getCookie(key: string): string | null {
    try {
        const name = encodeURIComponent(key) + '=';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name)) {
                return decodeURIComponent(cookie.substring(name.length));
            }
        }
    } catch (e) {
        console.warn('[MultiStorage] Failed to get cookie:', e);
    }
    return null;
}

/**
 * Delete a cookie
 */
function deleteCookie(key: string): void {
    try {
        document.cookie = `${encodeURIComponent(key)}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
    } catch (e) {
        console.warn('[MultiStorage] Failed to delete cookie:', e);
    }
}

/**
 * Set value in IndexedDB
 */
async function setIndexedDB(key: string, value: string): Promise<void> {
    try {
        const db = await getDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            const request = store.put(value, key);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    } catch (e) {
        console.warn('[MultiStorage] Failed to set IndexedDB:', e);
    }
}

/**
 * Get value from IndexedDB
 */
async function getIndexedDB(key: string): Promise<string | null> {
    try {
        const db = await getDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readonly');
            const store = tx.objectStore(STORE_NAME);
            const request = store.get(key);
            request.onsuccess = () => resolve(request.result ?? null);
            request.onerror = () => reject(request.error);
        });
    } catch (e) {
        console.warn('[MultiStorage] Failed to get IndexedDB:', e);
        return null;
    }
}

/**
 * Delete value from IndexedDB
 */
async function deleteIndexedDB(key: string): Promise<void> {
    try {
        const db = await getDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            const request = store.delete(key);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    } catch (e) {
        console.warn('[MultiStorage] Failed to delete IndexedDB:', e);
    }
}

/**
 * Store data in all available storage mechanisms
 * @param key - Storage key
 * @param value - Value to store (will be JSON stringified if object)
 * @param cookieDays - Cookie expiry in days (default 7)
 */
export async function multiSet(key: string, value: unknown, cookieDays: number = 7): Promise<void> {
    const stringValue = typeof value === 'string' ? value : JSON.stringify(value);

    // Store in localStorage
    try {
        localStorage.setItem(key, stringValue);
    } catch (e) {
        console.warn('[MultiStorage] Failed to set localStorage:', e);
    }

    // Store in cookie
    setCookie(key, stringValue, cookieDays);

    // Store in IndexedDB
    await setIndexedDB(key, stringValue);
}

/**
 * Get data from any available storage (priority: localStorage > cookie > IndexedDB)
 * If found in one but missing from others, restores to all
 * @param key - Storage key
 * @returns The stored value or null if not found anywhere
 */
export async function multiGet(key: string): Promise<string | null> {
    // Try localStorage first (fastest)
    let value: string | null = null;
    let source = '';

    try {
        value = localStorage.getItem(key);
        if (value) source = 'localStorage';
    } catch (e) {
        console.warn('[MultiStorage] Failed to read localStorage:', e);
    }

    // Try cookie if localStorage failed
    if (!value) {
        value = getCookie(key);
        if (value) source = 'cookie';
    }

    // Try IndexedDB if both failed
    if (!value) {
        value = await getIndexedDB(key);
        if (value) source = 'indexedDB';
    }

    // If found in one place, restore to all others
    if (value && source) {
        // Restore to missing locations silently
        if (source !== 'localStorage') {
            try { localStorage.setItem(key, value); } catch (e) { }
        }
        if (source !== 'cookie') {
            setCookie(key, value);
        }
        if (source !== 'indexedDB') {
            setIndexedDB(key, value).catch(() => { });
        }
    }

    return value;
}

/**
 * Synchronous get - checks localStorage first, then cookie
 * Use multiGet for full redundancy check including IndexedDB
 */
export function multiGetSync(key: string): string | null {
    // Try localStorage first
    try {
        const value = localStorage.getItem(key);
        if (value) return value;
    } catch (e) {
        // localStorage not available, continue to cookie
    }

    // Try cookie as fallback
    return getCookie(key);
}

/**
 * Remove data from all storage mechanisms
 * @param key - Storage key to remove
 */
export async function multiRemove(key: string): Promise<void> {
    // Remove from localStorage
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.warn('[MultiStorage] Failed to remove from localStorage:', e);
    }

    // Remove from cookie
    deleteCookie(key);

    // Remove from IndexedDB
    await deleteIndexedDB(key);
}
