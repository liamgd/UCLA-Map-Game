import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { render } from '@testing-library/react';
import { JSDOM } from 'jsdom';
import usePersistentState from './usePersistentState.js';

function setupDom() {
  const dom = new JSDOM('<!doctype html><html><body></body></html>', {
    url: 'http://localhost'
  });
  global.window = dom.window;
  global.document = dom.window.document;
  global.localStorage = dom.window.localStorage;
}

describe('usePersistentState', () => {
  it('reads and writes from localStorage', () => {
    setupDom();
    function TestComponent() {
      const [value, setValue] = usePersistentState('key', 'a');
      global.setValue = setValue;
      return React.createElement('div', null, value);
    }
    const { getByText, rerender } = render(React.createElement(TestComponent));
    assert.equal(getByText('a').textContent, 'a');
    assert.equal(localStorage.getItem('key'), JSON.stringify('a'));
    global.setValue('b');
    rerender(React.createElement(TestComponent));
    assert.equal(getByText('b').textContent, 'b');
    assert.equal(localStorage.getItem('key'), JSON.stringify('b'));
  });
});
