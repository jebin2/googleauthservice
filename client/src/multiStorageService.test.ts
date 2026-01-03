/**
 * Multi-Storage Service Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { multiSet, multiGet, multiGetSync, multiRemove } from './multiStorageService';

// Mock localStorage
const mockLocalStorage = (() => {
    let store: Record<string, string> = {};
    return {
        getItem: vi.fn((key: string) => store[key] || null),
        setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
        removeItem: vi.fn((key: string) => { delete store[key]; }),
        clear: () => { store = {}; },
    };
})();

// Mock document.cookie
let mockCookies: Record<string, string> = {};

Object.defineProperty(document, 'cookie', {
    get: () => {
        return Object.entries(mockCookies)
            .map(([k, v]) => `${k}=${v}`)
            .join('; ');
    },
    set: (value: string) => {
        const [pair] = value.split(';');
        const [key, val] = pair.split('=');
        if (val) {
            mockCookies[key.trim()] = val.trim();
        }
    },
});

describe('multiStorageService', () => {
    beforeEach(() => {
        mockLocalStorage.clear();
        mockCookies = {};
        vi.stubGlobal('localStorage', mockLocalStorage);
    });

    describe('multiSet', () => {
        it('should store value in localStorage', async () => {
            await multiSet('test_key', { foo: 'bar' });
            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'test_key',
                JSON.stringify({ foo: 'bar' })
            );
        });

        it('should handle objects with toJSON', async () => {
            const obj = { value: 123 };
            await multiSet('test_key', obj);
            expect(mockLocalStorage.setItem).toHaveBeenCalled();
        });
    });

    describe('multiGetSync', () => {
        it('should return value from localStorage', () => {
            mockLocalStorage.setItem('test_key', '"test_value"');
            const result = multiGetSync('test_key');
            expect(result).toBe('"test_value"');
        });

        it('should return null for missing key', () => {
            const result = multiGetSync('missing_key');
            expect(result).toBeNull();
        });
    });

    describe('multiGet', () => {
        it('should return value from localStorage', async () => {
            mockLocalStorage.setItem('test_key', '"test_value"');
            const result = await multiGet('test_key');
            expect(result).toBe('"test_value"');
        });
    });

    describe('multiRemove', () => {
        it('should remove from localStorage', async () => {
            await multiRemove('test_key');
            expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('test_key');
        });
    });
});
